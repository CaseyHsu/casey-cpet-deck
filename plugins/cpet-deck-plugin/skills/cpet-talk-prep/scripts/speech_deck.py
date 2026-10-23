"""Speech deck builder (python-pptx port of the ECCE 2026 pptxgenjs generator).

One slide per talk page: navy header with page number, title and timing; left = slide thumbnail +
Chinese hint; right = the script, click markers [k] in orange, stress (**…**) in dark red, and every
"the" that must be read "thee" in blue + underline. Then one slide per backup page (Q&A), one
"useful phrases" slide, and the other questions three per slide.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from talk import mark_thee, page_timing, thee_regex

NAVY, RED, ORANGE, GREY, LIGHT = "14274E", "C00000", "C55A11", "595959", "F2F4F8"
BODY, BLUE, PALE = "1F1F1F", "0070C0", "D9E1F2"
FONT = "Calibri"
W, H = 13.333, 7.5
TOKEN = re.compile(r"(\*\*.+?\*\*|\x01.+?\x02)")


def rgb(h):
    return RGBColor.from_string(h)


def rect(slide, x, y, w, h, fill, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line); s.line.width = Pt(0.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP, margin=0.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(margin))
    return tf


def add_run(p, text, size, color, bold=False, italic=False, underline=False):
    r = p.add_run()
    r.text = text
    f = r.font
    f.name, f.size, f.bold, f.italic = FONT, Pt(size), bold, italic
    f.color.rgb = rgb(color)
    if underline:
        f.underline = True
    return r


def add_marked(p, text, size, base, rx):
    """**bold** -> red bold; marked 'the' -> blue underline (keeps bold if inside **)."""
    marked = mark_thee(text, rx, "\x01", "\x02")
    for part in TOKEN.split(marked):
        if not part:
            continue
        bold = part.startswith("**")
        body = part[2:-2] if bold else part
        for seg in re.split(r"(\x01[^\x02]*\x02)", body):
            if not seg:
                continue
            if seg.startswith("\x01"):
                add_run(p, seg[1:-1], size, BLUE, bold=bold, underline=True)
            elif bold:
                add_run(p, seg, size, RED, bold=True)
            else:
                add_run(p, seg, size, base)


def header(slide, num, title, meta, core):
    rect(slide, 0, 0, W, 0.8, NAVY)
    rect(slide, 0, 0, 1.0, 0.8, ORANGE if core else RED)
    for x, w, txt, size, color, align, bold in (
            (0, 1.0, str(num), 32, "FFFFFF", PP_ALIGN.CENTER, True),
            (1.2, 8.9, title, 24, "FFFFFF", PP_ALIGN.LEFT, True),
            (10.1, 3.0, meta or "", 14, PALE, PP_ALIGN.RIGHT, False)):
        if not txt:
            continue
        tf = textbox(slide, x, 0, w, 0.8, MSO_ANCHOR.MIDDLE)
        p = tf.paragraphs[0]
        p.alignment = align
        add_run(p, txt, size, color, bold=bold)


def left_panel(slide, num, hint, thumbs, tw=4.2, hs=14):
    th = tw * 9 / 16
    img = thumbs / f"s-{num:02d}.png" if thumbs else None
    if img and img.exists():
        rect(slide, 0.28, 0.98, tw + 0.04, th + 0.04, "FFFFFF", "BFBFBF")
        slide.shapes.add_picture(str(img), Inches(0.3), Inches(1.0), Inches(tw), Inches(th))
    if hint:
        rect(slide, 0.3, 1.2 + th, tw, 6.15 - th, LIGHT)
        tf = textbox(slide, 0.45, 1.3 + th, tw - 0.3, 5.9 - th)
        p = tf.paragraphs[0]
        add_run(p, "中文提示", hs, NAVY, bold=True)
        for line in hint.split("\n"):
            p = tf.add_paragraph()
            p.space_after = Pt(4)
            add_run(p, line, hs, GREY)


def fit_size(paras, w, h, sizes):
    for s in sizes:
        cpl = math.floor(w / (s * 0.0060))  # average character width ≈ 0.52 em
        lines = sum(math.ceil((len(t.replace("**", "")) + 4) / cpl) for t in paras)
        if lines * s * 1.22 / 72 + len(paras) * s * 0.45 / 72 <= h:
            return s
    return sizes[-1]


def build(t: dict, out, thumbs: Path | None) -> int:
    meta = t["meta"]
    rx = thee_regex(t.get("thee_before", []))
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    blank = prs.slide_layouts[6]

    for p in t["pages"]:
        w, c, sec, _ = page_timing(p, meta, meta["wpm"])
        core = p["n"] in meta["core_pages"]
        s = prs.slides.add_slide(blank)
        header(s, p["n"], p["title"], f"≈ {sec} s · {c} click{'' if c == 1 else 's'} · {w} words", core)
        tw = 3.3 if core else 4.2
        left_panel(s, p["n"], p.get("hint"), thumbs, tw)
        sx = 0.3 + tw + 0.3
        sw = 13.05 - sx
        size = fit_size([x[1] for x in p["lines"]], sw - 0.05, 6.3, [28, 26, 24, 22, 21, 20, 19, 18])
        tf = textbox(s, sx, 0.98, sw, 6.3, margin=0.05)
        for i, (k, text) in enumerate(p["lines"]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.space_after = Pt(round(size * 0.45))
            para.line_spacing = 1.05
            if k:
                add_run(para, f"[{k}]  ", size, ORANGE, bold=True)
            add_marked(para, text, size, BODY, rx)

    for b in t.get("backup", []):
        s = prs.slides.add_slide(blank)
        header(s, b["n"], f"Q&A  ·  {b['title']}", "備用頁 · 被問到才翻", False)
        left_panel(s, b["n"], b.get("hint"), thumbs, 4.2, 12)
        size = 21 if len(b["qa"]) >= 3 else 24
        tf = textbox(s, 4.8, 0.98, 8.25, 6.3, margin=0.05)
        first = True
        for q, ans in b["qa"]:
            para = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
            add_run(para, "Q: " + q, size - 2, NAVY, bold=True, italic=True)
            para = tf.add_paragraph(); para.space_after = Pt(10)
            add_marked(para, "A: " + ans, size, BODY, rx)

    next_n = (t["backup"][-1]["n"] if t.get("backup") else t["pages"][-1]["n"]) + 1
    if t.get("phrases"):
        s = prs.slides.add_slide(blank)
        header(s, next_n, "Q&A  ·  Useful Phrases", "聽不懂時先用這頁", False)
        rows = len(t["phrases"])
        tbl = s.shapes.add_table(rows, 2, Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.95 * rows)).table
        tbl.columns[0].width, tbl.columns[1].width = Inches(2.2), Inches(10.1)
        tbl.first_row = False
        tbl.horz_banding = False
        for i, (zh, en) in enumerate(t["phrases"]):
            for j, (txt, size, col) in enumerate(((zh, 18, NAVY), (en, 24, BODY))):
                cell = tbl.cell(i, j)
                cell.fill.solid(); cell.fill.fore_color.rgb = rgb("FFFFFF")
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                para = cell.text_frame.paragraphs[0]
                if j == 0:
                    add_run(para, txt, size, col, bold=True)
                else:
                    add_marked(para, txt, size, col, rx)
        if t.get("phrases_note"):
            tf = textbox(s, 0.5, 6.25, 12.3, 0.8)
            head, _, rest = t["phrases_note"].partition("：")
            p = tf.paragraphs[0]
            if rest:
                add_run(p, head + "：", 16, NAVY, bold=True)
                add_run(p, rest, 16, GREY)
            else:
                add_run(p, head, 16, GREY)
        next_n += 1

    per = 3
    other = t.get("other", [])
    for pi in range(0, len(other), per):
        s = prs.slides.add_slide(blank)
        header(s, next_n, f"Q&A  ·  Other Questions ({pi // per + 1})", "無備用頁 · 口頭回答", False)
        next_n += 1
        tf = textbox(s, 0.5, 0.98, 12.3, 6.35, margin=0.05)
        first = True
        for x in other[pi:pi + per]:
            para = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
            add_run(para, "Q: " + x["q"], 19, NAVY, bold=True, italic=True)
            para = tf.add_paragraph(); para.space_after = Pt(6)
            add_marked(para, "A: " + x["a"], 20, BODY, rx)
            if x.get("note"):
                para = tf.add_paragraph(); para.space_after = Pt(6)
                add_run(para, "備註：" + x["note"], 14, GREY)
    prs.save(out)
    return len(prs.slides)
