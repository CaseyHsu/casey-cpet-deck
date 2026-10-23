#!/usr/bin/env python3
"""backfill_pending.py — 把 forge/figprep 的 manifest.json 讀出的產出路徑，
回填進 input_template.md 對應的 PENDING:forge-鍵值／PENDING:figprep-鍵值。

背景（cpet-deck-workflow-overhaul_v2 段2a，2026-08-16 依 Casey 裁決納入）：
v4 工作流指引 §4 原本記載「回填方式手動 vs 自動化，尚未定案，留待之後決定」。
本腳本是「已定案」的自動化實作，但**只做機械式字串取代**——判斷「這頁該用哪個
佔位鍵、鍵值該叫什麼名字」仍是 cpet-input-template 轉譯階段（本技能主體）的職責，
不是本腳本的職責。本腳本不做任何內容或版面判斷，純粹是：讀 manifest → 找
PENDING:字串 → 換成路徑。

設計原則：
  - 只取代「已在 manifest 裡確認成功」的鍵值；manifest 裡標記錯誤的鍵值維持原樣
    不動，讓 input_template.md 裡still看得到「這個還沒處理好」的訊號。
  - 不主動猜測回填路徑該用相對還是絕對——依 v4 指引§4「跨 session 重建應使用
    相對路徑」的既定規則，預設輸出相對於 input_template.md 所在目錄的路徑，
    可用 --absolute 覆寫（僅供除錯用途，不建議正式流程使用）。
  - 找不到任何 PENDING 字串可對應的鍵值時警示但不中止（manifest 裡可能含有
    這份 input_template.md 用不到的鍵值，例如處理了但這次沒用上的素材）。
  - input_template.md 裡若還留有未被任何 manifest 涵蓋的 PENDING: 字串，
    執行結束後明確列出，不要讓使用者誤以為已經全部回填完成。

用法：
    python backfill_pending.py <input_template.md> \
        [--forge-manifest forge_manifest.json] \
        [--figprep-manifest figprep_manifest.json] \
        [-o 輸出路徑（預設覆寫原檔，並另存 .bak）]
"""
import argparse
import json
import os
import re
import sys


def _die(msg, code=1):
    print(f"✘ {msg}", file=sys.stderr)
    sys.exit(code)


def load_manifest(path, prefix):
    """讀 forge 或 figprep 的 manifest.json，回傳 {完整鍵值(含前綴): 產出路徑}。

    forge 的 manifest.figures[].id 本身不含 'forge-' 前綴（見 forge.mjs），
    figprep 的 manifest（本次新增）之 figures[].id 已含 'figprep-' 前綴
    （cmd_manifest 已強制加上）——兩種格式在此統一補齊前綴後再回傳，呼叫端
    不需要關心兩邊 manifest 內部欄位命名的差異。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    mapping = {}
    for fig in data.get("figures", []):
        key = fig["id"]
        if not key.startswith(prefix):
            key = f"{prefix}{key}"
        png = fig.get("png") or fig.get("path")
        if not png:
            continue
        mapping[key] = png
    errors = [e.get("id", "?") for e in data.get("errors", [])]
    return mapping, errors


def backfill(template_text, mapping, template_dir, absolute=False):
    """回傳 (新文字, 已回填鍵值清單, 找不到對應的PENDING清單)。"""
    filled = []
    pattern = re.compile(r"PENDING:([\w-]+)")

    def repl(m):
        key = m.group(1)
        if key not in mapping:
            return m.group(0)
        path = mapping[key]
        if not absolute:
            try:
                path = os.path.relpath(path, template_dir)
            except ValueError:
                pass  # 不同磁碟機（Windows）時 relpath 會拋錯，退回絕對路徑
        filled.append(key)
        return path.replace("\\", "/")

    new_text = pattern.sub(repl, template_text)
    remaining = sorted(set(re.findall(r"PENDING:([\w-]+)", new_text)))
    return new_text, filled, remaining


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("template", help="input_template.md 路徑")
    ap.add_argument("--forge-manifest", help="cpet-infographic-forge 產出的 manifest.json")
    ap.add_argument("--figprep-manifest", help="cpet-figure-prep manifest 子命令產出的 manifest.json")
    ap.add_argument("-o", "--out", help="輸出路徑（預設覆寫原檔，並另存 <原檔>.bak）")
    ap.add_argument("--absolute", action="store_true",
                    help="回填絕對路徑而非相對路徑（僅供除錯，正式流程不建議）")
    a = ap.parse_args()

    if not a.forge_manifest and not a.figprep_manifest:
        _die("至少需要 --forge-manifest 或 --figprep-manifest 其中一個")

    if not os.path.exists(a.template):
        _die(f"找不到 input_template.md：{a.template}")

    with open(a.template, encoding="utf-8") as f:
        text = f.read()
    template_dir = os.path.dirname(os.path.abspath(a.template))

    mapping = {}
    manifest_errors = []
    if a.forge_manifest:
        m, errs = load_manifest(a.forge_manifest, "forge-")
        mapping.update(m)
        manifest_errors += [("forge", e) for e in errs]
    if a.figprep_manifest:
        m, errs = load_manifest(a.figprep_manifest, "figprep-")
        mapping.update(m)
        manifest_errors += [("figprep", e) for e in errs]

    new_text, filled, remaining = backfill(text, mapping, template_dir, a.absolute)

    out_path = a.out or a.template
    if out_path == a.template:
        bak_path = a.template + ".bak"
        with open(bak_path, "w", encoding="utf-8") as f:
            f.write(text)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"✔ 回填完成：{out_path}")
    print(f"  已回填 {len(filled)} 個鍵值：{', '.join(filled) if filled else '（無）'}")
    if remaining:
        print(f"  ⚠ 仍有 {len(remaining)} 個 PENDING 未回填（manifest 未涵蓋或標記為錯誤）："
              f"{', '.join(remaining)}")
    if manifest_errors:
        print(f"  ⚠ manifest 中標記失敗、未納入回填的鍵值：")
        for src, key in manifest_errors:
            print(f"    - [{src}] {key}")
    if out_path == a.template:
        print(f"  原檔已備份至：{a.template}.bak")


if __name__ == "__main__":
    main()
