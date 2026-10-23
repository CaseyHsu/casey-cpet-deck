"""Derive companion decks from the master (animated) deck.

  noanim  <master.pptx> <out.pptx> [--drop-prefix EntryPrompt]
      Remove every slide's p:timing and drop shapes whose name starts with the
      given prefix (entry prompts that only make sense when animated). All other
      parts are copied unchanged, so the result differs from the master only in
      the slides that had animation.

  notes   <deck.pptx> <notes.json> <out.pptx>
      Write speaker notes. notes.json = {"<slide number>": "text", ...}. Lines
      are paragraphs. Inline markup: **bold**, __word__ = blue + underline
      (the "thee" reminder). Slides without an existing notes part are skipped
      and reported (creating notes parts is left to PowerPoint).

  verify-noanim <master.pptx> <noanim.pptx> [--drop-prefix EntryPrompt]
      Re-derive in memory and compare every part (c14n) with an existing file.

Exit codes: 0 ok, 1 mismatch/warnings, 2 usage or input error.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_xml import NS, P, A, Package, c14n  # noqa: E402

THEE_COLOR = "0070C0"


def strip_animation(pkg: Package, drop_prefix: str | None) -> list[str]:
    log = []
    for i, name in enumerate(pkg.slides(), 1):
        t = pkg.tree(name)
        timing = t.find("p:timing", NS)
        dropped = []
        if drop_prefix:
            for nv in list(t.iter(P + "cNvPr")):
                if (nv.get("name") or "").startswith(drop_prefix):
                    shape = nv.getparent().getparent()
                    shape.getparent().remove(shape)
                    dropped.append(nv.get("name"))
        if timing is None and not dropped:
            pkg._trees.pop(name)  # untouched: keep original bytes
            continue
        if timing is not None:
            t.remove(timing)
        log.append(f"slide {i}: timing {'removed' if timing is not None else 'none'}"
                   + (f", dropped {dropped}" if dropped else ""))
    return log


def cmd_noanim(a) -> int:
    pkg = Package(a.master)
    for line in strip_animation(pkg, a.drop_prefix):
        print(line)
    pkg.save(a.out)
    print("wrote", a.out)
    return 0


def cmd_verify(a) -> int:
    pkg = Package(a.master)
    strip_animation(pkg, a.drop_prefix)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "derived.pptx"
        pkg.save(out)
        got, ref = Package(out), Package(a.noanim)
    bad = []
    for n in sorted(set(got.parts) | set(ref.parts)):
        x, y = got.parts.get(n), ref.parts.get(n)
        if x == y:
            continue
        if x is None or y is None:
            bad.append(f"{n}: present only in {'reference' if x is None else 'derived'}")
            continue
        if n.endswith((".xml", ".rels")) and c14n(etree.fromstring(x)) == c14n(etree.fromstring(y)):
            continue
        bad.append(f"{n}: content differs")
    if bad:
        print("MISMATCH", *bad, sep="\n  ")
        return 1
    print(f"OK: {len(ref.parts)} parts identical (c14n) to {a.noanim}")
    return 0


_TOKEN = re.compile(r"(\*\*.+?\*\*|__.+?__)")


def _runs(text: str, tmpl_rpr):
    for piece in _TOKEN.split(text):
        if not piece:
            continue
        r = etree.Element(A + "r")
        rpr = copy.deepcopy(tmpl_rpr) if tmpl_rpr is not None else etree.Element(A + "rPr", lang="en-US")
        if piece.startswith("**") and piece.endswith("**"):
            piece = piece[2:-2]
            rpr.set("b", "1")
        elif piece.startswith("__") and piece.endswith("__"):
            piece = piece[2:-2]
            rpr.set("u", "sng")
            for old in rpr.findall(A + "solidFill"):
                rpr.remove(old)
            fill = etree.Element(A + "solidFill")
            etree.SubElement(fill, A + "srgbClr", val=THEE_COLOR)
            rpr.insert(0, fill)
        r.append(rpr)
        etree.SubElement(r, A + "t").text = piece
        yield r


def cmd_notes(a) -> int:
    notes = json.loads(Path(a.notes).read_text(encoding="utf-8"))
    pkg = Package(a.deck)
    slides = pkg.slides()
    warn = 0
    for key, text in notes.items():
        idx = int(key)
        if not 1 <= idx <= len(slides):
            print(f"slide {idx}: out of range"); warn = 1; continue
        np_ = pkg.notes_part(slides[idx - 1])
        if np_ is None:
            print(f"slide {idx}: no notes part, skipped"); warn = 1; continue
        t = pkg.tree(np_)
        body = None
        for sp in t.iter(P + "sp"):
            ph = sp.find(".//p:nvPr/p:ph", NS)
            if ph is not None and ph.get("type") == "body":
                body = sp.find("p:txBody", NS)
                break
        if body is None:
            print(f"slide {idx}: notes has no body placeholder, skipped"); warn = 1; continue
        old_p = body.findall("a:p", NS)
        tmpl_rpr = body.find(".//a:r/a:rPr", NS)
        if tmpl_rpr is not None:
            tmpl_rpr = copy.deepcopy(tmpl_rpr)
            for attr in ("b", "u"):
                tmpl_rpr.attrib.pop(attr, None)
            for f in tmpl_rpr.findall(A + "solidFill"):
                tmpl_rpr.remove(f)
        for p_ in old_p:
            body.remove(p_)
        for line in text.split("\n"):
            p_ = etree.SubElement(body, A + "p")
            for r in _runs(line, tmpl_rpr):
                p_.append(r)
            if not len(p_):
                etree.SubElement(p_, A + "endParaRPr", lang="en-US")
        print(f"slide {idx}: {len(text.splitlines())} paragraphs")
    pkg.save(a.out)
    print("wrote", a.out)
    return warn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("noanim"); s.add_argument("master"); s.add_argument("out")
    s.add_argument("--drop-prefix", default="EntryPrompt")
    s.set_defaults(fn=cmd_noanim)
    s = sub.add_parser("verify-noanim"); s.add_argument("master"); s.add_argument("noanim")
    s.add_argument("--drop-prefix", default="EntryPrompt")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("notes"); s.add_argument("deck"); s.add_argument("notes"); s.add_argument("out")
    s.set_defaults(fn=cmd_notes)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, KeyError, ValueError, etree.XMLSyntaxError) as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
