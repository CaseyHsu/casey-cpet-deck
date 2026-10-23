#!/usr/bin/env python3
"""extract_legacy.py — 舊簡報（.pptx）內容抽取器，供「舊簡報 → 新模板」轉換前置使用。

用法：
    python extract_legacy.py input.pptx outdir/

輸出：
    outdir/media/          所有內嵌圖片（sNN_shapeID.ext 命名）
    outdir/extract_report.md   逐頁抽取報告：文字、表格（Markdown）、圖片清單、
                               旗標（HIDDEN／OMML／GROUP／SPARSE／EMPTY_TABLE）
    outdir/pages/          被旗標「需視讀補齊」頁面的 PDF 渲染圖（150 dpi，
                               需要 LibreOffice + pdftoppm；不在場時略過並註明）

旗標意義（對應 references/legacy-conversion.md 的 SOP）：
    HIDDEN       原稿隱藏頁——依原稿設定預設排除，不轉換
    OMML         含 Office 數學物件——文字層抽不到，公式須自渲染頁視讀轉錄為 LaTeX
    GROUP        含群組物件（疊標註拼貼）——建議採內容區裁切策略
    SPARSE       文字稀疏且無圖——內容可能整頁是 OMML／OLE，必須視讀
    EMPTY_TABLE  表格存在但儲存格為空——內容可能是浮動文字框拼出的假表格，必須視讀
"""
import os
import sys
import subprocess

from pptx import Presentation
from pptx.util import Emu

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

M_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def extract(pptx_path: str, outdir: str) -> None:
    os.makedirs(os.path.join(outdir, "media"), exist_ok=True)
    prs = Presentation(pptx_path)
    lines = [f"# 抽取報告：{os.path.basename(pptx_path)}",
             f"- 總頁數：{len(prs.slides.__iter__.__self__._sldIdLst)}（見下方逐頁旗標）",
             f"- 版面：{prs.slide_width/914400:.2f}\" × {prs.slide_height/914400:.2f}\"", ""]
    flagged_pages = []
    visible_idx = 0   # LibreOffice 轉 PDF 時隱藏頁不輸出——PDF 頁碼只對可見頁遞增
    for i, s in enumerate(prs.slides, 1):
        flags = []
        hidden = s._element.get("show") == "0"
        if hidden:
            flags.append("HIDDEN")
        else:
            visible_idx += 1
        if s._element.findall(f".//{M_NS}oMath"):
            flags.append("OMML")
        texts, tables, images, nchar = [], [], [], 0
        for sh in s.shapes:
            if sh.shape_type == 6:
                if "GROUP" not in flags:
                    flags.append("GROUP")
            if getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in sh.table.rows]
                if not any(any(c for c in r) for r in rows):
                    flags.append("EMPTY_TABLE")
                tables.append(rows)
            elif sh.has_text_frame:
                t = "\n".join(p.text for p in sh.text_frame.paragraphs if p.text.strip())
                if t.strip():
                    texts.append(t)
                    nchar += len(t)
            elif sh.shape_type == 13:
                img = sh.image
                fn = f"s{i}_{sh.shape_id}.{img.ext}"
                with open(os.path.join(outdir, "media", fn), "wb") as f:
                    f.write(img.blob)
                images.append((fn, Emu(sh.width).inches, Emu(sh.height).inches))
        if nchar < 30 and not images and not hidden:
            flags.append("SPARSE")
        if any(f in flags for f in ("OMML", "GROUP", "SPARSE", "EMPTY_TABLE")) and not hidden:
            flagged_pages.append((i, visible_idx))
        lines.append(f"## slide {i}" + (f"　⚑ {' / '.join(flags)}" if flags else ""))
        for t in texts:
            lines.append("```text\n" + t + "\n```")
        for rows in tables:
            if rows and any(any(c for c in r) for r in rows):
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "---|" * len(rows[0]))
                for r in rows[1:]:
                    lines.append("| " + " | ".join(r) + " |")
        for fn, w, h in images:
            lines.append(f"- 圖片 `media/{fn}`（{w:.1f}\" × {h:.1f}\"）")
        lines.append("")
    # 渲染被旗標頁（隱藏頁不渲染；PDF 頁碼＝可見頁序）
    if flagged_pages:
        lines.append("---\n## 需視讀補齊之頁面（已渲染至 pages/，PDF 頁碼＝可見頁序）")
        pages_dir = os.path.join(outdir, "pages")
        os.makedirs(pages_dir, exist_ok=True)
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                            pptx_path, "--outdir", outdir],
                           check=True, capture_output=True, timeout=300)
            pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf")
            for slide_no, pdf_page in flagged_pages:
                subprocess.run(["pdftoppm", "-f", str(pdf_page), "-l", str(pdf_page),
                                "-r", "150", "-png", pdf,
                                os.path.join(pages_dir, f"slide{slide_no:02d}")],
                               check=True, capture_output=True)
                lines.append(f"- slide {slide_no} → `pages/slide{slide_no:02d}-*.png`")
        except Exception as e:  # noqa: BLE001
            lines.append(f"（渲染略過：{e}——請手動 soffice 轉 PDF 後 pdftoppm 渲染上列頁面）")
    with open(os.path.join(outdir, "extract_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✔ 抽取完成：{outdir}/extract_report.md（旗標頁 {len(flagged_pages)} 頁）")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2])
