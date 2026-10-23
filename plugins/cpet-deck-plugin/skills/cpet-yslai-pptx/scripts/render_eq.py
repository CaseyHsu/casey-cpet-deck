#!/usr/bin/env python3
"""render_eq.py — 將 LaTeX 數學式渲染為透明背景 PNG，供簡報插圖使用。

用法（CLI）：
    python render_eq.py "\\Psi_d = L_d i_d + \\lambda_{pm}" out.png [--fontsize 22] [--dpi 300]

也可作為模組使用：
    from render_eq import render_latex
    info = render_latex(latex, out_path, fontsize=22, dpi=300)
    # info = {"path": ..., "w_px": ..., "h_px": ..., "dpi": ...}

策略：
  1. 預設使用 matplotlib mathtext（快、不需完整 TeX；支援 frac/sqrt/上下標/希臘字母/粗體等）。
  2. 若 LaTeX 含 \\begin{...} 環境（cases、aligned、matrix…）或 mathtext 解析失敗，
     自動 fallback 到 pdflatex(standalone + amsmath) → pdftoppm → 白轉透明。
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

NEEDS_LATEX_RE = re.compile(r"\\begin\{|\\text\{|\\overbrace|\\underbrace|\\boxed")


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        return s[2:-2].strip()
    if s.startswith("$") and s.endswith("$"):
        return s[1:-1].strip()
    return s


def _white_to_transparent(path: str, threshold: int = 245) -> None:
    im = Image.open(path).convert("RGBA")
    data = [
        (r, g, b, 0) if (r >= threshold and g >= threshold and b >= threshold) else (r, g, b, a)
        for (r, g, b, a) in im.getdata()
    ]
    im.putdata(data)
    im.save(path)


def _render_mathtext(latex: str, out_path: str, fontsize: int, dpi: int) -> None:
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0, 0, f"${latex}$", fontsize=fontsize, math_fontfamily="cm")
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", transparent=True, pad_inches=0.05)
    plt.close(fig)


def _render_pdflatex(latex: str, out_path: str, fontsize: int, dpi: int) -> None:
    """standalone + amsmath；\\displaystyle 內聯數學。fontsize 以 12pt 文件基準縮放。"""
    scale = fontsize / 12.0
    tex = (
        "\\documentclass[border=2pt]{standalone}\n"
        "\\usepackage{amsmath,amssymb,bm}\n"
        "\\usepackage{graphicx}\n"   # \scalebox 必要——缺此套件時 scalebox 靜默失效，公式一律 12pt 輸出

        "\\begin{document}\n"
        f"\\scalebox{{{scale:.3f}}}{{$\\displaystyle {latex}$}}\n"
        "\\end{document}\n"
    )
    with tempfile.TemporaryDirectory() as td:
        texfile = os.path.join(td, "eq.tex")
        with open(texfile, "w", encoding="utf-8") as f:
            f.write(tex)
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", td, texfile],
            capture_output=True, text=True,
        )
        pdf = os.path.join(td, "eq.pdf")
        if not os.path.exists(pdf):
            raise RuntimeError("pdflatex 失敗：\n" + r.stdout[-1500:])
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", pdf, os.path.join(td, "eqimg")],
            check=True,
        )
        img = os.path.join(td, "eqimg.png")
        Image.open(img).save(out_path)
    _white_to_transparent(out_path)


def render_latex(latex: str, out_path: str, fontsize: int = 22, dpi: int = 300) -> dict:
    latex = _strip_dollars(latex)
    used = "mathtext"
    if NEEDS_LATEX_RE.search(latex):
        _render_pdflatex(latex, out_path, fontsize, dpi)
        used = "pdflatex"
    else:
        try:
            _render_mathtext(latex, out_path, fontsize, dpi)
        except Exception:
            _render_pdflatex(latex, out_path, fontsize, dpi)
            used = "pdflatex"
    w, h = Image.open(out_path).size
    return {"path": out_path, "w_px": w, "h_px": h, "dpi": dpi, "engine": used}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("latex")
    ap.add_argument("out")
    ap.add_argument("--fontsize", type=int, default=22)
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    print(json.dumps(render_latex(a.latex, a.out, a.fontsize, a.dpi), ensure_ascii=False))
