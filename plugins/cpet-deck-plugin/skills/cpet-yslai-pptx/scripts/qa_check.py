#!/usr/bin/env python3
"""qa_check.py — 對渲染後的投影片 JPG 做像素級自動檢查。

用法：
    python qa_check.py slide-1.jpg slide-2.jpg ...   # 建議：呼叫端先展開好的檔案清單
    python qa_check.py "slide-*.jpg"                  # 相容舊介面：單一 glob pattern

介面說明（2026-08-30 修正）：main() 現在接受多個檔案路徑參數（sys.argv[1:] 全收）。
這是為了修正 Windows/Git-Bash 環境下的一個真實 bug——full_qa.sh 用 bash 的
compgen -G 展開 glob 拿到 MSYS 形式路徑（如 /c/Users/.../slide-1.png），但若把
「未展開的字面 glob 字串」原樣傳給本腳本、由 Python 的 glob.glob() 二次展開，
Windows 版 Python 不認得 /c/... 這種路徑前綴，回傳空 list，导致誤判為找不到
圖檔。改為「呼叫端先展開、逐檔案路徑當獨立參數傳入」可完全避開此問題，也
順便解決路徑含中文或空格時 glob pattern 傳遞不可靠的問題。若參數本身含有
* 或 ?（呼叫端仍想沿用舊的單一 pattern 介面），才 fallback 用 glob.glob() 展開。

檢查項目（每張）：
  1. header bar（頂部藍色漸層橫條）存在
  2. 底部藍色分隔線存在
  3. 左下角頁腳文字存在
  4. 內容區非空白
  5. 底線以下無溢出內容（頁腳與頁碼區除外）
回傳非零 exit code 表示至少一張未通過，訊息列出問題頁。
本檢查是輔助手段，不取代逐張目視 QA（版面美觀、重疊、對齊仍需人眼確認）。

已知限制：封面頁（layout1）版型本身在版面下方有機構標誌區塊的深藍色裝飾線，
座標恰好落在本腳本「底部溢出偵測」的掃描帶內，會被誤判為溢出（overflow_px
會落在 100~300 區間、略高於閾值）。這是模板固有設計、非內容錯誤，只要溢出
頁是封面頁（通常是第 1 張）且 overflow_px 沒有顯著超過 300，可視為誤報安全
忽略；其餘頁面的溢出警告仍應視為真實問題並修正。
"""
import glob
import os
import sys

from PIL import Image

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def analyze(f, generic=False):
    """generic=True（官方模板 profile 建置的簡報）：只查內容區是否空白；
    header bar／底部藍線／左下頁腳是實驗室模板的母片元素，官方模板沒有，不能當通過條件。"""
    im = Image.open(f).convert("RGB")
    w, h = im.size
    issues = []
    if generic:
        c = im.crop((int(w * 0.05), int(h * 0.18), int(w * 0.95), int(h * 0.9)))
        content = sum(1 for p in c.getdata() if sum(p) < 600)
        if content < 400:
            issues.append(f"內容區近乎空白（content_px={content}）")
        return issues

    hd = im.crop((0, 6, w, 26))
    d = list(hd.getdata())
    n = len(d)
    avg = tuple(sum(p[i] for p in d) // n for i in range(3))
    if not (avg[2] > avg[0] + 20 and avg[2] > 120):
        issues.append("header bar 缺失或顏色異常")

    line_y = None
    for y in range(h - 60, h - 20):
        row = [im.getpixel((x, y)) for x in range(0, w, 12)]
        if sum(1 for r, g, b in row if b > 120 and b - r > 60) > len(row) * 0.5:
            line_y = y
            break
    if line_y is None:
        issues.append("底部藍色分隔線缺失")

    crop = im.crop((10, h - 30, 220, h - 5))
    if sum(1 for p in crop.getdata() if sum(p) < 600) < 100:
        issues.append("左下角頁腳缺失")

    c = im.crop((int(w * 0.05), int(h * 0.18), int(w * 0.95), int(h * 0.9)))
    content = sum(1 for p in c.getdata() if sum(p) < 600)
    if content < 400:
        issues.append(f"內容區近乎空白（content_px={content}）")

    if line_y:
        c2 = im.crop((240, line_y + 4, w - 200, h - 4))
        ov = sum(1 for p in c2.getdata() if sum(p) < 550)
        if ov > 40:
            issues.append(f"底線以下疑似溢出（overflow_px={ov}）")

    return issues


def main():
    args = sys.argv[1:]
    generic = "--generic" in args
    args = [a for a in args if a != "--generic"] or ["slide-*.jpg"]
    if len(args) == 1 and ("*" in args[0] or "?" in args[0]):
        # 相容舊介面：單一 glob pattern，本腳本自行展開
        files = sorted(glob.glob(args[0]))
        if not files:
            print(f"找不到符合 {args[0]} 的圖檔")
            sys.exit(2)
    else:
        # 新介面：呼叫端已展開好的檔案路徑清單
        files = sorted(args)
        missing = [f for f in files if not os.path.isfile(f)]
        if missing:
            print(f"找不到檔案：{missing}")
            sys.exit(2)
        if not files:
            print("未提供任何圖檔路徑")
            sys.exit(2)
    bad = 0
    for f in files:
        issues = analyze(f, generic)
        if issues:
            bad += 1
            print(f"*** {f}: " + "；".join(issues))
        else:
            print(f"OK  {f}")
    if bad:
        print(f"\n{bad}/{len(files)} 張未通過像素檢查")
        sys.exit(1)
    print(f"\n全部 {len(files)} 張通過像素檢查（仍建議逐張目視確認版面）")


if __name__ == "__main__":
    main()
