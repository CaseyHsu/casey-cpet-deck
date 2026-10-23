"""Regression against a finished project (paths as arguments; nothing is copied into the repo).

    python regress_on_project.py <speech.json> <speech_txt_dir> <Final.pptx> <Speech.pptx> <work_dir>

1. import-speech: per-page words / clicks / seconds equal the project's own timing table.
2. txt: every page file and _all.txt equal the delivered speech_txt (line endings normalised).
3. notes: generated notes == Final.pptx notes, paragraph by paragraph, and the blue-underlined
   "the" runs sit on the same paragraphs.
4. deck: generated speech deck has the same slide count and the same visible text per slide
   as the delivered Speech.pptx.
"""
import json
import sys
from pathlib import Path

from pptx import Presentation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import talk  # noqa: E402


def norm(s):
    return s.replace("\r\n", "\n").strip()


def slide_texts(prs):
    out = []
    for s in prs.slides:
        bits = []
        for sh in s.shapes:
            if sh.has_text_frame:
                bits += [p.text for p in sh.text_frame.paragraphs if p.text.strip()]
            elif sh.has_table:
                bits += [c.text for r in sh.table.rows for c in r.cells if c.text.strip()]
        out.append(sorted(b.strip() for b in bits))
    return out


def main(speech, txt_dir, final, speech_pptx, work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    tj = work / "talk.json"
    results = {}
    results["import (timing matches)"] = talk.main(["import-speech", speech, str(tj)]) == 0

    # 2. txt — the delivered files use the project prefix; detect it from the folder
    any_file = next(Path(txt_dir).glob("*_p01.txt"))
    prefix = any_file.name[: -len("_p01.txt")]
    talk.main(["txt", str(tj), str(work / "txt"), "--prefix", prefix])
    bad = []
    for ref in sorted(Path(txt_dir).glob(f"{prefix}_*.txt")):
        got = work / "txt" / ref.name
        if not got.exists() or norm(got.read_text(encoding="utf-8")) != norm(ref.read_text(encoding="utf-8")):
            bad.append(ref.name)
    results[f"txt ({len(list(Path(txt_dir).glob(prefix + '_*.txt')))} files)"] = not bad
    if bad:
        print("txt mismatch:", bad)

    # 3. notes — script / Q&A lines must match exactly (incl. which lines carry a "thee" mark);
    #    【…】 header lines are hand-maintained in some projects and only reported as drift
    payload = talk.notes_payload(talk.load(tj))
    prs = Presentation(final)
    nbad, drift = [], []
    for n, text in payload.items():
        tf = prs.slides[int(n) - 1].notes_slide.notes_text_frame
        ref = [(p.text, any(r.font.underline for r in p.runs)) for p in tf.paragraphs]
        got = [(l.replace("__", ""), "__" in l) for l in text.split("\n")]
        ref_h = [x[0] for x in ref if x[0].startswith("【")]
        got_h = [x[0] for x in got if x[0].startswith("【")]
        ref_b = [x for x in ref if x[0] and not x[0].startswith("【")]
        got_b = [x for x in got if x[0] and not x[0].startswith("【")]
        if ref_b != got_b:
            nbad.append((n, [x for x in ref_b if x not in got_b][:2], [x for x in got_b if x not in ref_b][:2]))
        if ref_h != got_h:
            drift.append(n)
    results[f"notes script/Q&A lines ({len(payload)} slides)"] = not nbad
    for x in nbad[:5]:
        print("notes mismatch:", x)
    if drift:
        print(f"INFO 【…】 header lines differ from the source on slides {drift} (hand edits in the deck or source)")

    # 4. deck — the phrases-slide footnote lived in the old generator's code, not in speech.json
    ref_prs = Presentation(speech_pptx)
    note = next((sh.text_frame.text for s in ref_prs.slides for sh in s.shapes
                 if sh.has_text_frame and sh.text_frame.text.startswith("原則：")), None)
    if note:
        d = json.loads(tj.read_text(encoding="utf-8")); d["phrases_note"] = note
        tj.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    out = work / "speech.pptx"
    talk.main(["deck", str(tj), str(out)])
    a, b = slide_texts(Presentation(out)), slide_texts(Presentation(speech_pptx))
    dbad = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    results[f"deck ({len(a)} vs {len(b)} slides)"] = len(a) == len(b) and not dbad
    for i in dbad[:3]:
        print(f"deck slide {i}:\n  got {sorted(set(a[i-1]) - set(b[i-1]))[:4]}\n  ref {sorted(set(b[i-1]) - set(a[i-1]))[:4]}")

    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:]))
