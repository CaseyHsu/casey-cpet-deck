"""Click-animation tools for the pptx-master phase (Appear / Disappear only).

  extract <deck.pptx> <spec.json>        read existing animation into a spec
  inject  <deck.pptx> <spec.json> <out>  replace p:timing on the listed slides
  check   <deck.pptx>                    per-slide click count + grpId lint

Spec format (slide numbers are 1-based, in presentation order):

  {"slides": {"9": [
      [{"shape": "EntryPrompt2", "effect": "appear"}],
      [{"shape": "EntryPrompt", "effect": "exit"},
       {"shape": "EntryPrompt2", "effect": "exit"},
       {"shape": "Picture 5", "effect": "appear"}]
  ]}}

Each inner list is one click: the first effect starts on click, the rest run
"with previous". "shape" matches the shape name; use "spid" instead when names
are not unique on the slide.

grpId rule (PowerPoint keys build state by (spid, grpId)): every effect on the
same shape gets its own grpId 0, 1, 2 ... and every text-bearing p:sp gets one
p:bldP per grpId. Reusing grpId 0 for an appear and a later exit on the same
shape makes PowerPoint ignore the exit (ECCE 2026 D53).

Exit codes: 0 ok, 1 lint failure or mismatch, 2 usage/input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_xml import NS, P, Package, shape_index  # noqa: E402

PRESET = {"appear": ("entr", "visible"), "exit": ("exit", "hidden")}


# ---------------------------------------------------------------- read
def read_clicks(slide_tree) -> list[list[dict]]:
    timing = slide_tree.find("p:timing", NS)
    if timing is None:
        return []
    main = timing.find(".//p:cTn[@nodeType='mainSeq']", NS)
    if main is None:
        return []
    clicks = []
    for click_par in main.find("p:childTnLst", NS).findall("p:par", NS):
        effects = []
        for ctn in click_par.iter(P + "cTn"):
            cls = ctn.get("presetClass")
            if cls is None:
                continue
            tgt = ctn.find(".//p:spTgt", NS)
            effects.append({
                "spid": tgt.get("spid") if tgt is not None else None,
                "class": cls, "preset": ctn.get("presetID"),
                "node": ctn.get("nodeType"), "grpId": ctn.get("grpId"),
            })
        clicks.append(effects)
    return clicks


def lint(slide_tree) -> list[str]:
    """Return problems: shared grpId on one shape, unsupported nodes."""
    problems = []
    seen = defaultdict(list)
    for c, effects in enumerate(read_clicks(slide_tree), 1):
        for e in effects:
            seen[(e["spid"], e["grpId"] or "0")].append((c, e["class"]))
            if e["node"] == "afterEffect":
                problems.append(f"click {c}: afterEffect on spid {e['spid']} (not modelled by spec)")
    for (spid, grp), uses in seen.items():
        if len(uses) > 1:
            problems.append(f"spid {spid} grpId {grp} used by {len(uses)} effects {uses} -> later ones ignored")
    return problems


def cmd_extract(a) -> int:
    pkg = Package(a.deck)
    spec = {"slides": {}}
    for i, name in enumerate(pkg.slides(), 1):
        t = pkg.tree(name)
        idx = shape_index(t)
        names = [v["name"] for v in idx.values()]
        clicks = read_clicks(t)
        if not clicks:
            continue
        out = []
        for effects in clicks:
            group = []
            for e in effects:
                if e["class"] not in ("entr", "exit") or e["preset"] != "1":
                    print(f"slide {i}: preset {e['class']}/{e['preset']} not supported, kept as appear/exit")
                nm = idx.get(e["spid"], {}).get("name")
                ref = {"shape": nm} if nm and names.count(nm) == 1 else {"spid": e["spid"]}
                ref["effect"] = "exit" if e["class"] == "exit" else "appear"
                group.append(ref)
            out.append(group)
        spec["slides"][str(i)] = out
    Path(a.spec).write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {a.spec}: {len(spec['slides'])} slides, "
          f"{sum(len(v) for v in spec['slides'].values())} clicks")
    return 0


# ---------------------------------------------------------------- write
def _el(tag, parent=None, **attrs):
    e = etree.Element(P + tag) if parent is None else etree.SubElement(parent, P + tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    return e


def _cond_list(parent, tag, delay):
    lst = _el(tag, parent)
    _el("cond", lst, delay=delay)
    return lst


def build_timing(clicks: list[list[dict]], idx: dict) -> etree._Element:
    by_name = defaultdict(list)
    for spid, v in idx.items():
        by_name[v["name"]].append(spid)

    def resolve(ref):
        if "spid" in ref:
            if ref["spid"] not in idx:
                raise ValueError(f"spid {ref['spid']} not on slide")
            return ref["spid"]
        hits = by_name.get(ref["shape"], [])
        if len(hits) != 1:
            raise ValueError(f"shape name {ref['shape']!r} matches {len(hits)} shapes; use spid")
        return hits[0]

    ids = iter(range(1, 100000))
    timing = _el("timing")
    root_par = _el("par", _el("tnLst", timing))
    root = _el("cTn", root_par, id=next(ids), dur="indefinite", restart="never", nodeType="tmRoot")
    seq = _el("seq", _el("childTnLst", root), concurrent="1", nextAc="seek")
    main = _el("cTn", seq, id=next(ids), dur="indefinite", nodeType="mainSeq")
    main_children = _el("childTnLst", main)
    for tag, evt in (("prevCondLst", "onPrev"), ("nextCondLst", "onNext")):
        lst = _el(tag, seq)
        c = _el("cond", lst, evt=evt, delay="0")
        _el("sldTgt", _el("tgtEl", c))

    grp_next = defaultdict(int)
    builds = []  # (spid, grpId)
    for effects in clicks:
        click_par = _el("par", main_children)
        click_ctn = _el("cTn", click_par, id=next(ids), fill="hold")
        _cond_list(click_ctn, "stCondLst", "indefinite")
        inner_par = _el("par", _el("childTnLst", click_ctn))
        inner_ctn = _el("cTn", inner_par, id=next(ids), fill="hold")
        _cond_list(inner_ctn, "stCondLst", "0")
        holder = _el("childTnLst", inner_ctn)
        for k, ref in enumerate(effects):
            spid = resolve(ref)
            cls, vis = PRESET[ref.get("effect", "appear")]
            grp = grp_next[spid]
            grp_next[spid] += 1
            eff_par = _el("par", holder)
            eff = _el("cTn", eff_par, id=next(ids), presetID="1", presetClass=cls, presetSubtype="0",
                      fill="hold", grpId=grp, nodeType="clickEffect" if k == 0 else "withEffect")
            _cond_list(eff, "stCondLst", "0")
            st = _el("set", _el("childTnLst", eff))
            bhvr = _el("cBhvr", st)
            ctn = _el("cTn", bhvr, id=next(ids), dur="1", fill="hold")
            _cond_list(ctn, "stCondLst", "0")
            _el("spTgt", _el("tgtEl", bhvr), spid=spid)
            names = _el("attrNameLst", bhvr)
            _el("attrName", names).text = "style.visibility"
            _el("strVal", _el("to", st), val=vis)
            if idx[spid]["kind"] == "sp" and idx[spid]["el"].find("p:txBody", NS) is not None:
                builds.append((spid, grp))
    if builds:
        bld = _el("bldLst", timing)
        for spid, grp in builds:
            _el("bldP", bld, spid=spid, grpId=grp, animBg="1")
    return timing


def _place_timing(slide_tree, timing):
    old = slide_tree.find("p:timing", NS)
    if old is not None:
        slide_tree.remove(old)
    # schema order: cSld, clrMapOvr, transition, timing, extLst
    anchor = slide_tree.find("p:extLst", NS)
    if anchor is not None:
        anchor.addprevious(timing)
    else:
        slide_tree.append(timing)


def cmd_inject(a) -> int:
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    pkg = Package(a.deck)
    slides = pkg.slides()
    for key, clicks in spec["slides"].items():
        t = pkg.tree(slides[int(key) - 1])
        timing = build_timing(clicks, shape_index(t))
        _place_timing(t, timing)
        print(f"slide {key}: {len(clicks)} clicks")
    pkg.save(a.out)
    return cmd_check(argparse.Namespace(deck=a.out))


def cmd_check(a) -> int:
    pkg = Package(a.deck)
    total, bad = 0, 0
    for i, name in enumerate(pkg.slides(), 1):
        t = pkg.tree(name)
        n = len(read_clicks(t))
        total += n
        probs = lint(t)
        bad += len(probs)
        if n or probs:
            print(f"slide {i}: {n} clicks" + "".join(f"\n  ! {p}" for p in probs))
    print(f"TOTAL {total} clicks, {bad} problems")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("extract"); s.add_argument("deck"); s.add_argument("spec"); s.set_defaults(fn=cmd_extract)
    s = sub.add_parser("inject"); s.add_argument("deck"); s.add_argument("spec"); s.add_argument("out")
    s.set_defaults(fn=cmd_inject)
    s = sub.add_parser("check"); s.add_argument("deck"); s.set_defaults(fn=cmd_check)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, KeyError, ValueError, IndexError, etree.XMLSyntaxError) as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
