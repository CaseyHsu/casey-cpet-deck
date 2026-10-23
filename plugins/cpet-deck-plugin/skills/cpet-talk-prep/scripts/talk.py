"""talk.py — one script source (talk.json) for everything a talk needs besides the slides.

  timing   <talk.json> [--wpm N]                     per-page words / clicks / seconds + checkpoints
  notes    <talk.json> <notes.json>                  speaker-notes payload for cpet-deck-finalize derive.py notes
  txt      <talk.json> <out_dir> [--prefix NAME]     TTS / rehearsal text: one file per page + _all.txt
  deck     <talk.json> <out.pptx> [--thumbs DIR]     speech deck (script + hints + Q&A pages)
  thumbs   <deck.pptx> <out_dir>                     render slide thumbnails s-01.png … for `deck`
  diff     <old.json> <new.json>                     which pages changed -> which artifacts to rebuild
  import-speech <speech.json> <talk.json> [--title T] convert an ECCE-2026-style speech.json

talk.json (schema "cpet-talk/0.1"):
  meta:   title, wpm (main), wpm_alt, click_sec, page_sec, core_pages [n], checkpoints [n],
          limit_sec, spoken {"LUT": "lookup table", ...}   (spoken = replacements for TTS text)
  thee_before: words after which "the" is read "thee" (lower case)
  pages:  [{n, title, hint, lines: [[click, text], ...], notes_pre: [line, ...]}]
          click k>0 = said after the k-th click; 0 = on entry, or (after the first line) no new click;
          **bold** = stress; notes_pre (optional) = lines put above the script in the speaker notes
  backup: [{n, title, hint, qa: [[question, answer], ...]}]
  phrases:[[situation_zh, sentence_en], ...];  phrases_note (optional) = footnote on that slide
  other:  [{q, a, note}]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_META = {"wpm": 90, "wpm_alt": 105, "click_sec": 0.7, "page_sec": 1.0,
                "core_pages": [], "checkpoints": [], "limit_sec": None, "spoken": {}}


def load(path) -> dict:
    t = json.loads(Path(path).read_text(encoding="utf-8"))
    if t.get("schema") != "cpet-talk/0.1":
        raise ValueError(f"{path}: schema must be 'cpet-talk/0.1'")
    t["meta"] = {**DEFAULT_META, **t.get("meta", {})}
    return t


# ------------------------------------------------------------------ text helpers
BOLD = re.compile(r"\*\*(.+?)\*\*")


def plain(text: str) -> str:
    return BOLD.sub(r"\1", text)


def thee_regex(words):
    if not words:
        return None
    alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    # "the" followed by (optional **) a listed word; the word must end there ("input-output" is not "input")
    return re.compile(rf"\b([Tt]he)(\s+(?:\*\*)?)(?=(?:{alt})(?![\w'‑-]))", re.I)


def mark_thee(text: str, rx, open_="__", close="__") -> str:
    if rx is None:
        return text
    return rx.sub(lambda m: f"{open_}{m.group(1)}{close}{m.group(2)}", text)


def spoken(text: str, table: dict) -> str:
    out = plain(text)
    for k in sorted(table, key=len, reverse=True):
        v = table[k]
        if re.fullmatch(r"\w+", k):
            out = re.sub(rf"\b{re.escape(k)}\b", v, out)
        else:
            out = out.replace(k, v)
    return out


def words(text: str) -> int:
    return len(text.split())


# ------------------------------------------------------------------ timing
def page_timing(p, meta, wpm):
    w = sum(words(t) for _, t in p["lines"])
    clicks = max((k for k, _ in p["lines"]), default=0)
    exact = w / wpm * 60 + clicks * meta["click_sec"] + meta["page_sec"]
    return w, clicks, round(exact), exact  # round(): half-to-even, same as the ECCE timing table


def timing_table(t, wpm=None):
    """Rows with per-page rounded seconds; start times and total use the unrounded sum."""
    meta = t["meta"]
    wpm = wpm or meta["wpm"]
    rows, start = [], 0.0
    for p in t["pages"]:
        w, c, s, exact = page_timing(p, meta, wpm)
        rows.append({"n": p["n"], "title": p["title"], "words": w, "clicks": c, "sec": s, "start": round(start)})
        start += exact
    return rows, round(start)


def fmt(sec):
    return f"{sec // 60}:{sec % 60:02d}"


def cmd_timing(a) -> int:
    t = load(a.talk)
    meta = t["meta"]
    rows, total = timing_table(t, a.wpm)
    print(f"| # | 頁 | 字數 | 點擊 | 秒 | 開始 |\n|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']} | {r['title']} | {r['words']} | {r['clicks']} | {r['sec']} | {fmt(r['start'])} |")
    tw = sum(r["words"] for r in rows)
    print(f"\n全文 {tw} 字、{sum(r['clicks'] for r in rows)} 次點擊；{a.wpm or meta['wpm']} wpm 約 {fmt(total)}", end="")
    if meta.get("wpm_alt") and not a.wpm:
        _, alt = timing_table(t, meta["wpm_alt"])
        print(f"，{meta['wpm_alt']} wpm 約 {fmt(alt)}", end="")
    print()
    if meta["checkpoints"]:
        cps = [f"#{r['n']} ≤ {fmt(r['start'])}" for r in rows if r["n"] in meta["checkpoints"]]
        print("檢查點（開始時間）：" + "｜".join(cps))
    if meta.get("limit_sec") and total > meta["limit_sec"]:
        print(f"WARN 超過上限 {fmt(meta['limit_sec'])}：多 {total - meta['limit_sec']} 秒")
        return 1
    return 0


# ------------------------------------------------------------------ notes
def notes_payload(t) -> dict:
    rx = thee_regex(t.get("thee_before", []))
    out = {}
    for p in t["pages"]:
        lines = list(p.get("notes_pre", []))  # e.g. 【發音】 reminders shown above the script
        for k, text in p["lines"]:
            s = plain(mark_thee(text, rx))
            lines.append(f"[{k}] {s}" if k else s)
        out[str(p["n"])] = "\n".join(lines)
    for b in t.get("backup", []):
        lines = ["【中文提示】" + " ／ ".join(b["hint"].split("\n")), ""]
        for q, ans in b["qa"]:
            lines += [f"Q: {plain(q)}", "A: " + plain(mark_thee(ans, rx)), ""]
        out[str(b["n"])] = "\n".join(lines)
    return out


def cmd_notes(a) -> int:
    payload = notes_payload(load(a.talk))
    Path(a.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {a.out}: {len(payload)} slides -> run cpet-deck-finalize derive.py notes")
    return 0


# ------------------------------------------------------------------ txt
def page_text(p, table) -> str:
    """One paragraph per click: a line with click 0 after the first line continues the previous paragraph."""
    paras, cur = [], []
    for k, text in p["lines"]:
        if cur and k:
            paras.append(" ".join(cur)); cur = []
        cur.append(spoken(text, table))
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras)


def cmd_txt(a) -> int:
    t = load(a.talk)
    meta, out = t["meta"], Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = a.prefix or "Speech"
    allparts = []
    for p in t["pages"]:
        body = page_text(p, meta["spoken"])
        (out / f"{prefix}_p{p['n']:02d}.txt").write_text(body, encoding="utf-8")
        mark = "  ★ 核心頁" if p["n"] in meta["core_pages"] and "★" not in p["title"] else ""
        allparts.append(f"### Slide {p['n']}: {spoken(p['title'], meta['spoken'])}{mark}\n\n{body}")
    (out / f"{prefix}_all.txt").write_text("\n\n".join(allparts), encoding="utf-8")
    print(f"wrote {len(t['pages'])} page files + {prefix}_all.txt to {out}")
    return 0


# ------------------------------------------------------------------ diff
def cmd_diff(a) -> int:
    old, new = load(a.old), load(a.new)
    def index(t, key):
        return {x["n"]: x for x in t.get(key, [])}
    changed_pages = [n for n, p in index(new, "pages").items() if index(old, "pages").get(n) != p]
    changed_backup = [n for n, b in index(new, "backup").items() if index(old, "backup").get(n) != b]
    other_changed = old.get("other") != new.get("other") or old.get("phrases") != new.get("phrases")
    thee_changed = old.get("thee_before") != new.get("thee_before")
    if thee_changed:
        changed_pages = sorted(index(new, "pages"))
        changed_backup = sorted(index(new, "backup"))
    if not (changed_pages or changed_backup or other_changed):
        print("no content change")
        return 0
    print("重產清單：")
    if changed_pages:
        ps = ", ".join(f"#{n}" for n in changed_pages)
        print(f"- 主檔備忘錄 {ps}（talk.py notes → derive.py notes），之後重產無動畫版")
        print(f"- 講稿版簡報（talk.py deck）")
        print(f"- 文字稿 p{', p'.join(f'{n:02d}' for n in changed_pages)} 與 _all（talk.py txt）")
        print(f"- 語音（若有）：上列頁的單頁檔＋完整版")
        print(f"- 時間表（talk.py timing）")
    if changed_backup:
        print(f"- 備用頁備忘錄 {', '.join(f'#{n}' for n in changed_backup)}；講稿版簡報；Q&A 語音（若有）")
    if other_changed:
        print("- 講稿版簡報的應對句／其他問題頁；Q&A 語音（若有）")
    if thee_changed:
        print("- thee_before 改變：全部頁的備忘錄與講稿版標記都要重產")
    return 1


# ------------------------------------------------------------------ thumbs
def find_soffice():
    for c in (shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/bin/soffice"):
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("LibreOffice (soffice) not found")


def cmd_thumbs(a) -> int:
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([find_soffice(), "--headless", "--convert-to", "pdf", "--outdir", d, a.deck],
                       capture_output=True)
        pdf = Path(d) / (Path(a.deck).stem + ".pdf")
        # soffice exits non-zero when it inherits PYTHONHOME/PYTHONPATH even though the PDF is fine
        # (cpet-yslai-pptx v2.10), so judge by the file
        if not pdf.exists():
            print("PDF not produced", file=sys.stderr)
            return 2
        pdftoppm = shutil.which("pdftoppm")
        if not pdftoppm:
            raise FileNotFoundError("pdftoppm not found")
        subprocess.run([pdftoppm, "-png", "-r", "80", str(pdf), str(Path(d) / "s")], check=True)
        n = 0
        for p in sorted(Path(d).glob("s-*.png")):
            num = int(re.search(r"(\d+)$", p.stem).group(1))
            shutil.copy(p, out / f"s-{num:02d}.png")
            n += 1
    print(f"wrote {n} thumbnails to {out}")
    return 0


# ------------------------------------------------------------------ speech deck
def cmd_deck(a) -> int:
    from speech_deck import build
    t = load(a.talk)
    n = build(t, a.out, Path(a.thumbs) if a.thumbs else None)
    print(f"wrote {a.out}: {n} slides")
    return 0


# ------------------------------------------------------------------ import
def cmd_import(a) -> int:
    d = json.loads(Path(a.speech).read_text(encoding="utf-8"))
    talk = {
        "schema": "cpet-talk/0.1",
        "meta": {"title": a.title or "Talk", "wpm": 90, "wpm_alt": 105, "click_sec": 0.7, "page_sec": 1.0,
                 "core_pages": [p[0] for p in d["pages"] if "★" in p[1]], "checkpoints": [],
                 "spoken": {"LUTs": "lookup tables", "LUT": "lookup table", "\u2011": "-"}},
        "thee_before": d.get("theeBefore", []),
        "pages": [{"n": n, "title": ti, "hint": h, "lines": [[k, s] for k, s in items]}
                  for n, ti, h, items in d["pages"]],
        "backup": [{"n": n, "title": ti, "hint": h, "qa": [[q, ans] for q, ans in qa]}
                   for n, ti, h, qa in d.get("backup", [])],
        "phrases": d.get("phrases", []),
        "other": [{"q": x[0], "a": x[1], "note": x[2] if len(x) > 2 else ""} for x in d.get("other", [])],
    }
    Path(a.talk).write_text(json.dumps(talk, ensure_ascii=False, indent=1), encoding="utf-8")
    # report timing drift against the source's own table, if any
    if "timing" in d:
        t = load(a.talk)
        bad = []
        for p in t["pages"]:
            w, c, s, _ = page_timing(p, t["meta"], 90)
            ref = d["timing"].get(str(p["n"]))
            if ref and [w, c, s] != ref[1:]:
                bad.append((p["n"], [w, c, s], ref[1:]))
        print("timing matches source" if not bad else f"timing differs on {bad}")
    print(f"wrote {a.talk}: {len(talk['pages'])} pages, {len(talk['backup'])} backup, {len(talk['other'])} other")
    return 0


def main(argv=None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("timing"); s.add_argument("talk"); s.add_argument("--wpm", type=int); s.set_defaults(fn=cmd_timing)
    s = sub.add_parser("notes"); s.add_argument("talk"); s.add_argument("out"); s.set_defaults(fn=cmd_notes)
    s = sub.add_parser("txt"); s.add_argument("talk"); s.add_argument("out_dir"); s.add_argument("--prefix")
    s.set_defaults(fn=cmd_txt)
    s = sub.add_parser("deck"); s.add_argument("talk"); s.add_argument("out"); s.add_argument("--thumbs")
    s.set_defaults(fn=cmd_deck)
    s = sub.add_parser("thumbs"); s.add_argument("deck"); s.add_argument("out_dir"); s.set_defaults(fn=cmd_thumbs)
    s = sub.add_parser("diff"); s.add_argument("old"); s.add_argument("new"); s.set_defaults(fn=cmd_diff)
    s = sub.add_parser("import-speech"); s.add_argument("speech"); s.add_argument("talk"); s.add_argument("--title")
    s.set_defaults(fn=cmd_import)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
