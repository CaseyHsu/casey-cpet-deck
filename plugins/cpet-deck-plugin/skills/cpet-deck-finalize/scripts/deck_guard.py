"""Write guard for the pptx-master phase: know what changed before touching a deck.

  register <deck> --manifest M [--role master|derived] [--from MASTER] [--note TEXT]
      Record the deck's current md5 (and per-slide fingerprints) in the manifest.
      Run after every write you make, so the next check has a baseline.

  check <deck> --manifest M
      0 = deck matches the manifest; 1 = it changed since registration (someone
      edited it in PowerPoint) and a per-slide report is printed; 3 = the file is
      open/locked in PowerPoint (do not write, ask the user to close it);
      2 = not registered / input error.

  snapshot <deck> --archive ROOT --action SLUG [--reason TEXT]
      Copy the deck to ROOT/<YYYYMMDD>_before_<SLUG>/ with a generated README.md.
      Take one before every write to the master.

  stale --manifest M
      List derived decks whose recorded source md5 no longer matches the master.

Typical write sequence: check -> (if 1: report changes to the user, register to
accept them) -> snapshot -> edit -> register -> re-derive companions -> register.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_xml import NS, Package, c14n, md5, shape_index, shape_text  # noqa: E402

A_OFF = "{http://schemas.openxmlformats.org/drawingml/2006/main}off"


def _h(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def fingerprint(path: Path) -> dict:
    """Per slide: whole-slide hash, timing hash, notes hash, per-shape (name, text, offset) hash."""
    pkg = Package(path)
    slides = []
    for name in pkg.slides():
        t = pkg.tree(name)
        timing = t.find("p:timing", NS)
        notes = pkg.notes_part(name)
        shapes = {}
        for sid, v in shape_index(t).items():
            if v["kind"] == "spTree":  # slide root: changes whenever any child does
                continue
            off = v["el"].find(".//" + A_OFF)
            pos = f"{off.get('x')},{off.get('y')}" if off is not None else ""
            shapes[sid] = [v["name"], _h(c14n(v["el"])), shape_text(v["el"])[:60], pos]
        slides.append({
            "part": name,
            "slide": _h(c14n(t)),
            "timing": _h(c14n(timing)) if timing is not None else None,
            "notes": _h(c14n(pkg.tree(notes))) if notes else None,
            "shapes": shapes,
        })
    return {"md5": md5(path), "slides": slides}


def load_manifest(p: Path) -> dict:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema": "cpet-deck-manifest/0.1", "decks": {}}


def save_manifest(p: Path, m: dict) -> None:
    p.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def is_locked(deck: Path) -> str | None:
    owner = deck.with_name("~$" + deck.name)
    if owner.exists():
        return f"PowerPoint owner file present: {owner.name}"
    try:
        with open(deck, "r+b"):
            pass
    except PermissionError:
        return "file cannot be opened for writing (open in another program)"
    return None


def cmd_register(a) -> int:
    deck, mp = Path(a.deck), Path(a.manifest)
    m = load_manifest(mp)
    entry = {"role": a.role, "registered": dt.datetime.now().isoformat(timespec="seconds"),
             "fingerprint": fingerprint(deck)}
    if a.note:
        entry["note"] = a.note
    if a.source:
        src = Path(a.source)
        entry["from"] = src.name
        entry["from_md5"] = md5(src)
    hist = m["decks"].get(deck.name, {}).get("history", [])
    hist.append({"md5": entry["fingerprint"]["md5"], "at": entry["registered"], "note": a.note or ""})
    entry["history"] = hist
    m["decks"][deck.name] = entry
    save_manifest(mp, m)
    print(f"registered {deck.name} md5 {entry['fingerprint']['md5']}")
    return 0


def diff_report(old: dict, new: dict) -> list[str]:
    out = []
    if len(old["slides"]) != len(new["slides"]):
        out.append(f"slide count {len(old['slides'])} -> {len(new['slides'])}")
    for i, (o, n) in enumerate(zip(old["slides"], new["slides"]), 1):
        if o["slide"] == n["slide"] and o["notes"] == n["notes"]:
            continue
        what = []
        if o["timing"] != n["timing"]:
            what.append("animation")
        if o["notes"] != n["notes"]:
            what.append("notes")
        for sid in sorted(set(o["shapes"]) | set(n["shapes"]), key=int):
            so, sn = o["shapes"].get(sid), n["shapes"].get(sid)
            if so == sn:
                continue
            if so is None:
                what.append(f"+ added {sn[0]!r}")
            elif sn is None:
                what.append(f"- removed {so[0]!r}")
            else:
                kind = []
                if so[2] != sn[2]:
                    kind.append(f"text {so[2]!r} -> {sn[2]!r}")
                if so[3] != sn[3]:
                    kind.append(f"moved {so[3]} -> {sn[3]}")
                if not kind:
                    kind.append("format/size")
                what.append(f"~ {sn[0]!r}: " + "; ".join(kind))
        out.append(f"slide {i}: " + ("\n    ".join([""] + what) if what else "changed (layout-level)"))
    return out


def cmd_check(a) -> int:
    deck = Path(a.deck)
    lock = is_locked(deck)
    if lock:
        print("LOCKED:", lock)
        return 3
    m = load_manifest(Path(a.manifest))
    entry = m["decks"].get(deck.name)
    if entry is None:
        print("not registered:", deck.name)
        return 2
    cur = md5(deck)
    if cur == entry["fingerprint"]["md5"]:
        print(f"OK {deck.name} unchanged ({cur})")
        return 0
    print(f"CHANGED {deck.name}: {entry['fingerprint']['md5']} -> {cur}")
    for line in diff_report(entry["fingerprint"], fingerprint(deck)):
        print("  " + line)
    return 1


README = """# {folder}

- 原檔：`{deck}`
- md5：`{md5}`
- 時間：{when}
- 動作前快照：{action}
- 原因：{reason}

本資料夾由 `deck_guard.py snapshot` 自動產生。還原時把檔案複製回原位置後，執行 `deck_guard.py register`。
"""


def cmd_snapshot(a) -> int:
    deck = Path(a.deck)
    now = dt.datetime.now()
    folder = Path(a.archive) / f"{now:%Y%m%d}_before_{a.action}"
    n = 2
    while folder.exists():
        folder = Path(a.archive) / f"{now:%Y%m%d}_before_{a.action}_{n}"
        n += 1
    folder.mkdir(parents=True)
    shutil.copy2(deck, folder / deck.name)
    (folder / "README.md").write_text(README.format(
        folder=folder.name, deck=deck.name, md5=md5(deck), when=now.isoformat(timespec="seconds"),
        action=a.action, reason=a.reason or "(未填)"), encoding="utf-8")
    print("snapshot", folder)
    return 0


def cmd_stale(a) -> int:
    m = load_manifest(Path(a.manifest))
    current = {k: v["fingerprint"]["md5"] for k, v in m["decks"].items()}
    stale = 0
    for name, v in m["decks"].items():
        src = v.get("from")
        if not src:
            continue
        if current.get(src) != v.get("from_md5"):
            print(f"STALE {name}: built from {src} {v.get('from_md5')}, master now {current.get(src)}")
            stale += 1
    if not stale:
        print("all derived decks are current")
    return 1 if stale else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("register"); s.add_argument("deck"); s.add_argument("--manifest", required=True)
    s.add_argument("--role", default="master", choices=["master", "derived"])
    s.add_argument("--from", dest="source"); s.add_argument("--note")
    s.set_defaults(fn=cmd_register)
    s = sub.add_parser("check"); s.add_argument("deck"); s.add_argument("--manifest", required=True)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("snapshot"); s.add_argument("deck"); s.add_argument("--archive", required=True)
    s.add_argument("--action", required=True); s.add_argument("--reason")
    s.set_defaults(fn=cmd_snapshot)
    s = sub.add_parser("stale"); s.add_argument("--manifest", required=True); s.set_defaults(fn=cmd_stale)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, KeyError, ValueError) as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
