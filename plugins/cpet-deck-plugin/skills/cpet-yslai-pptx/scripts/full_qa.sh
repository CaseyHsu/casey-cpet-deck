#!/usr/bin/env bash
# full_qa.sh — 四層 QA 單一入口（v2.9）
#
# 為什麼需要：三層 QA 原本是三段互不知情的命令，呼叫者得自己記得
#   ① schema_check.py  ② soffice --headless --convert-to pdf  ③ pdftoppm  ④ qa_check.py
# 的順序與參數。連續兩個 session 都在重打同一串，且 schema 層曾因路徑問題整層靜默跳過。
# 本腳本把它們包成一個入口，統一輸出彙總報告與渲染圖路徑供後續人工目視。
# v2.9 第二批另加入**第 4 層版面幾何**（layout_lint.py）——這是像素層抓不到的類別。
#
# 層號命名統一（2026-08-16，CPET簡報工作流整備任務段2a）：本腳本實際執行並印出的層號
# 為「第1層內容／第2層schema／第3層像素／第4層版面幾何」（見下方各 echo 標題），這是
# 本產線 QA 層號的權威定義。此順序與本段註解②③的物理執行順序（soffice轉pdf在前、
# schema_check.py實際在①）不同——註解描述的是「需要哪些外部工具」，echo輸出描述的是
# 「對使用者呈現的檢查類別順序」，兩者不必然一致，以下方echo輸出為準。
# `簡報內容共創工作流指引_v4.md` §12流程圖曾用「schema／plan_lint／pixel／人工目視」
# 描述四層，與此處類別劃分不同（v4的「plan_lint」是建置前置檢查，非本腳本涵蓋範圍；
# 「人工目視」不是本腳本的第4層，第4層版面幾何是自動化幾何檢查，人工目視在四層全過
# 之後仍須另外進行，見本檔案結尾提示）——v4指引已標記待v5校正統一，本腳本以此處
# 為準，不隨v4指引的舊講法變動。
# 若未來啟用 OfficeCLI 語意QA（Code-only 選配，見 cpet-yslai-pptx SKILL.md 步驟4），
# 該層級命名為「第5層」，接在本腳本四層之後、不佔用第4之前的任何編號。

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Windows 繁中環境的 Python 管線輸出預設 cp950，各層腳本印「≤」「✔」會崩潰並被誤判為該層 FAIL。
export PYTHONIOENCODING=utf-8

if [[ $# -lt 1 ]]; then
  echo "用法：[QA_PROFILE=profile.json] bash full_qa.sh <deck.pptx> [輸出目錄]" >&2
  exit 2
fi

DECK="$1"
[[ -f "$DECK" ]] || { echo "✘ 找不到檔案：$DECK" >&2; exit 2; }
case "$DECK" in *.pptx) ;; *) echo "✘ 需要 .pptx 檔，收到：$DECK" >&2; exit 2;; esac

DECK_ABS="$(cd "$(dirname "$DECK")" && pwd)/$(basename "$DECK")"
BASE="$(basename "${DECK%.pptx}")"
OUTDIR="${2:-$(dirname "$DECK_ABS")/qa_$BASE}"
mkdir -p "$OUTDIR" || { echo "✘ 無法建立輸出目錄：$OUTDIR" >&2; exit 2; }

# ── 工具探測（2026-08-17 跨平台強化）─────────────────────────
# 原實作只檢查 PATH 上是否有 python3／soffice／pdftoppm，缺一即 exit 2。
# 在 Windows 上這三者常見的實際狀況：
#   - python3：可能是指向 Microsoft Store 安裝提示的 App Execution Alias（假指令），
#     真正可用的是官方 launcher `py`
#   - soffice：LibreOffice 預設不把安裝目錄加進 PATH（需重開 shell 或手動加）
#   - pdftoppm：TeX Live 夾帶的 0.75.0 舊版不支援 -jpeg，只支援 -png
# 因此改為「逐項尋找可用實作」而非「假設 PATH 上有標準名稱」。
PY_BIN=""
for c in python3 py python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import pptx" >/dev/null 2>&1; then
    PY_BIN="$c"; break
  fi
done
[[ -n "$PY_BIN" ]] || {
  echo "✘ 找不到可用的 Python（需含 python-pptx）——已嘗試 python3／py／python" >&2
  exit 2; }

SOFFICE_BIN=""
for c in soffice "/c/Program Files/LibreOffice/program/soffice.exe" \
         "/c/Program Files (x86)/LibreOffice/program/soffice.exe" \
         "$PROGRAMFILES/LibreOffice/program/soffice.exe"; do
  if command -v "$c" >/dev/null 2>&1 || [[ -x "$c" ]]; then
    SOFFICE_BIN="$c"; break
  fi
done
[[ -n "$SOFFICE_BIN" ]] || {
  echo "✘ 缺少必要工具：soffice" >&2
  echo "  （LibreOffice 未安裝，無法進行渲染與像素層 QA）" >&2
  echo "  Windows 可用：winget install TheDocumentFoundation.LibreOffice" >&2
  exit 2; }

command -v pdftoppm >/dev/null 2>&1 || {
  echo "✘ 缺少必要工具：pdftoppm（poppler-utils）" >&2
  exit 2; }

# pdftoppm 的輸出格式：優先 jpeg，舊版（如 TeX Live 夾帶的 0.75.0）不支援時退回 png。
# qa_check.py 用 PIL 讀圖，兩種格式皆可，故此差異不影響檢查結果。
if pdftoppm -h 2>&1 | grep -q -- "-jpeg"; then
  PDFTOPPM_FMT="-jpeg"; IMG_EXT="jpg"
else
  PDFTOPPM_FMT="-png";  IMG_EXT="png"
fi

L1=FAIL; L2=FAIL; L3=FAIL; L4=FAIL
echo "════════ 第 1 層：內容 ════════"
"$PY_BIN" - "$DECK_ABS" "$OUTDIR/text_dump.txt" <<'PY'
import sys
from pptx import Presentation
deck, out = sys.argv[1], sys.argv[2]
p = Presentation(deck)
lines, empty = [], []
for i, s in enumerate(p.slides, 1):
    txts = [sh.text_frame.text.strip() for sh in s.shapes
            if sh.has_text_frame and sh.text_frame.text.strip()]
    tbl = sum(1 for sh in s.shapes if sh.has_table)
    pic = sum(1 for sh in s.shapes if sh.shape_type == 13)
    lines.append(f"── slide {i}  (表格 {tbl}、圖片 {pic}) ──")
    lines += txts or ["（無文字）"]
    lines.append("")
    if not txts and not tbl and not pic:
        empty.append(i)
open(out, "w", encoding="utf-8").write("\n".join(lines))
print(f"已輸出文字稿：{out}（{len(p.slides)} 張）")
if empty:
    print(f"✘ 完全空白的投影片：{empty} — 通常代表 plan 欄位寫錯導致內容沒被畫上去")
    sys.exit(1)
print("✔ 無完全空白的投影片（漏字／錯字／順序仍請自行掃過文字稿）")
PY
[[ $? -eq 0 ]] && L1=PASS

echo
echo "════════ 第 2 層：官方 schema ════════"
"$PY_BIN" "$SCRIPT_DIR/schema_check.py" "$DECK_ABS" && L2=PASS

echo
echo "════════ 第 3 層：渲染與像素 ════════"
rm -f "$OUTDIR/$BASE.pdf" "$OUTDIR"/slide-*.jpg "$OUTDIR"/slide-*.png
# 2026-08-30 修正（BUG2）：LibreOffice 內建 bundled Python 若繼承呼叫端 shell 的
# PYTHONHOME／PYTHONPATH（常見於本機另外裝了獨立 Python 環境的情況），會去讀
# 這些變數、找不到自己的 stdlib，印出 "Could not find platform independent
# libraries <prefix>" 到 stderr 並以非零 exit code 結束——即使 PDF 其實已正常
# 產出。soffice 在 headless 轉檔情境下 exit code 本就不可靠，因此改用
# env -u 清空這兩個變數以避免污染，並且一律以「PDF 檔案是否存在」而非
# exit code 判定成功與否。
env -u PYTHONHOME -u PYTHONPATH "$SOFFICE_BIN" --headless --convert-to pdf "$DECK_ABS" --outdir "$OUTDIR" >/dev/null 2>&1 || true
if [[ ! -f "$OUTDIR/$BASE.pdf" ]]; then
  echo "✘ LibreOffice 未產出 PDF"
else
  pdftoppm "$PDFTOPPM_FMT" -r 100 "$OUTDIR/$BASE.pdf" "$OUTDIR/slide"
  # 2026-08-30 修正（BUG1）：先前直接把「未展開的字面 glob 字串」傳給
  # qa_check.py，由 Python 的 glob.glob() 二次展開；但 $OUTDIR 此時是 bash/MSYS
  # 形式路徑（如 /c/Users/.../qa），Windows 版 Python 的 glob 不認得這種前綴，
  # 回傳空 list，誤判為找不到圖檔。改為讓 bash 自己先展開好 glob、把每個檔案
  # 路徑當獨立參數傳給 qa_check.py（該腳本已同步改為接受多檔案路徑清單）。
  mapfile -t IMGS < <(compgen -G "$OUTDIR/slide-*.$IMG_EXT")
  if [[ ${#IMGS[@]} -gt 0 ]]; then
    if [[ -n "${QA_PROFILE:-}" ]]; then   # 官方模板：不檢查實驗室母片元素
      "$PY_BIN" "$SCRIPT_DIR/qa_check.py" --generic "${IMGS[@]}" 2>/dev/null && L3=PASS
    else
      "$PY_BIN" "$SCRIPT_DIR/qa_check.py" "${IMGS[@]}" 2>/dev/null && L3=PASS
    fi
  else
    echo "✘ pdftoppm 未產出圖檔"
  fi
fi

echo
echo "════════ 第 4 層：版面幾何 ════════"
# v2.11：官方模板建置的簡報要帶同一份 profile（QA_PROFILE=<profile.json> bash full_qa.sh …），
# 否則會用實驗室模板的保留區（頂部 header bar、7.25in 底線）誤判
if [[ -n "${QA_PROFILE:-}" ]]; then
  "$PY_BIN" "$SCRIPT_DIR/layout_lint.py" "$DECK_ABS" --profile "$QA_PROFILE" && L4=PASS
else
  "$PY_BIN" "$SCRIPT_DIR/layout_lint.py" "$DECK_ABS" && L4=PASS
fi

echo
echo "════════ 彙總 ════════"
printf '  第 1 層 內容      %s\n  第 2 層 schema    %s\n  第 3 層 像素      %s\n  第 4 層 版面幾何  %s\n' \
  "$L1" "$L2" "$L3" "$L4"
echo "  文字稿：$OUTDIR/text_dump.txt"
echo "  渲染圖：$OUTDIR/slide-*.$IMG_EXT  ← 請逐張目視（自動化只驗幾何與統計，不驗觀感）"
if [[ "$L1" == PASS && "$L2" == PASS && "$L3" == PASS && "$L4" == PASS ]]; then
  echo "✔ 四層全過。仍須完成逐張目視才算 QA 完成。"
  exit 0
fi
echo "✘ 有層未通過，禁止交付。"
exit 1
