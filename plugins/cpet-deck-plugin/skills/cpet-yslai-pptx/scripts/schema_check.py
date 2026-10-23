#!/usr/bin/env python3
"""schema_check.py — 用官方 ISO/IEC 29500 PresentationML schema 驗證 pptx 內每張投影片。

背景：LibreOffice（soffice --headless 轉圖 QA 用）的 XML 解析器對 schema 違規的容錯度
遠高於 PowerPoint。曾實際發生過的案例：手動用 lxml 對 <a:rPr> 重複附加 <a:latin> 元素，
LibreOffice 完全無視並正常轉圖，但在真正的 PowerPoint 開啟時觸發「PowerPoint 發現內容
有問題，可以嘗試修復」的對話框。像素 QA（qa_check.py）與 LibreOffice 轉圖成功都不能
證明 PowerPoint 能正常開啟檔案——只有官方 schema 驗證能夠。

任何在 build_deck.py 中新增手動 XML 操作（etree.SubElement、makeelement、直接 append
子節點）之後，都必須先跑本腳本再交付。

用法：
    python schema_check.py output.pptx
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REL = "office/schemas/ISO-IEC29500-4_2016/pml.xsd"


def _find_schema():
    """定位官方 pml.xsd。

    v2.7：原本寫死 /mnt/skills/public/pptx/... 這一條絕對路徑，只在該掛載配置下成立；
    Cowork session 的實際路徑是 /sessions/<id>/mnt/.claude/skills/pptx/...，換環境即
    整層 schema QA 失效（且症狀是「找不到檔案」而非「驗證失敗」，容易被當成環境問題
    跳過）。改為三段式搜尋，並以本 skill 自帶的副本為第一優先，徹底去除對 pptx skill
    掛載位置的依賴。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, _REL),                              # 1) 本 skill 內建（v2.7 起）
        "/mnt/skills/public/pptx/scripts/" + _REL,              # 2) 舊有固定掛載
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    # 3) 動態搜尋常見的 skill 掛載根目錄（限定深度，避免掃全碟）
    for root in ("/sessions", "/mnt", os.path.expanduser("~")):
        if not os.path.isdir(root):
            continue
        hits = glob.glob(os.path.join(root, "*", "**", "skills", "*", "scripts", _REL),
                         recursive=True)
        if hits:
            return hits[0]
    return None


SCHEMA = _find_schema()

# 依 part 類型對應到 schema 的根元素，逐一验证
CHECK_TARGETS = [
    ("ppt/presentation.xml", "presentation.xml"),
]


# ── 具名已知例外 ─────────────────────────────────────────────
# schema 比 PowerPoint 實際行為更嚴格的已知案例。每一條都必須寫明「為何確定是 schema
# 的問題而不是我們的問題」，並附可重現的佐證，否則不得列入——這個清單一旦浮濫，schema
# 驗證就失去意義。
KNOWN_EXCEPTIONS = [
    (
        "buSzPct val 使用千分之一百分比整數",
        # lxml 寫 "Element '{ns}buSzPct'"、xmllint 寫 "element buSzPct"，兩種格式都要吃
        re.compile(r"element '?(\{[^}]*\})?buSzPct'?.*attribute 'val'.*facet 'pattern'", re.I),
        "ISO-IEC29500-4:2016 把 CT_TextBulletSizePercent/@val 宣告為 "
        "ST_TextBulletSizePercent（只接受 '85%' 這種百分比字串），但真實 PowerPoint "
        "寫出的是 val=\"100000\" 這種千分之一百分比整數。佐證：Casey 以 PowerPoint "
        "實際製作的實驗室參考簡報，112 處 buSzPct 全為此形式，且該檔 38 張投影片全部"
        "因此被本 schema 判 FAIL。故此為 schema 與實作的落差，非本 builder 的錯誤。",
    ),
    (
        "mc:AlternateContent（Markup Compatibility 包裝）",
        re.compile(r"element '?\{http://schemas\.openxmlformats\.org/markup-compatibility/2006\}"
                   r"AlternateContent'?.*no matching global element declaration", re.I),
        "mc:AlternateContent 由 ISO-IEC29500-3（Markup Compatibility）定義，規範要求驗證前先做 "
        "MCE 前處理；pml.xsd（Part 4）本身不宣告它，直接驗證必然報 strict wildcard 錯誤。"
        "佐證：ECCE 2026 定稿（PowerPoint 存檔、Casey 實機播放無修復對話框）有 2 個 part "
        "只因此報錯。本 builder 不產生 mc:AlternateContent，只會在 PowerPoint 存過的檔案出現。",
    ),
]


def _filter_known(err: str):
    """回傳 (真實錯誤行, 命中的已知例外名稱集合)。"""
    real, hit = [], set()
    for line in err.splitlines():
        if not line.strip() or line.endswith("validates"):
            continue
        matched = None
        for name, pat, _why in KNOWN_EXCEPTIONS:
            if pat.search(line):
                matched = name
                break
        if matched:
            hit.add(matched)
        elif "fails to validate" not in line:
            real.append(line)
    return real, hit


_LXML_SCHEMA_CACHE: dict[str, object] = {}


def _validate_with_lxml(schema_path: str, xml_bytes: bytes, label: str) -> tuple[bool, str]:
    """用 lxml 的 XMLSchema 做 XSD 驗證（與 xmllint --schema 等效）。

    2026-08-17 新增：原實作只走 `xmllint` 外部指令，但 Windows 沒有內建
    libxml2 工具鏈，`xmllint` 常缺席，導致整層 schema QA 無法執行（症狀是
    FileNotFoundError，容易被誤判為環境問題而整層跳過——這正是本檔案 v2.7
    註解警告過的失效模式）。lxml 本身就綁定 libxml2，能做完全相同的驗證，
    且 pptx 產線既已依賴 lxml（build_deck.py 的手動 XML 操作即用它），
    不新增任何相依。schema 編譯結果快取，避免逐張投影片重複解析 XSD。
    """
    from lxml import etree

    schema = _LXML_SCHEMA_CACHE.get(schema_path)
    if schema is None:
        schema = etree.XMLSchema(etree.parse(schema_path))
        _LXML_SCHEMA_CACHE[schema_path] = schema

    doc = etree.fromstring(xml_bytes)
    ok = schema.validate(doc)
    if ok:
        return True, f"{label} validates"
    # error_log 逐條列出違規位置，格式與 xmllint 的 stderr 精神一致
    return False, "\n".join(str(e) for e in schema.error_log)


def _validate_with_xmllint(schema_path: str, xml_bytes: bytes, label: str) -> tuple[bool, str]:
    """原有的 xmllint 外部指令路徑，保留作為 lxml 不可用時的後備。"""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(xml_bytes)
        tmp_path = f.name
    try:
        r = subprocess.run(
            ["xmllint", "--noout", "--schema", schema_path, tmp_path],
            capture_output=True, text=True,
        )
        ok = "validates" in r.stderr or r.returncode == 0 and "fails" not in r.stderr
        return ok, r.stderr.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _validate_one(schema_path: str, xml_bytes: bytes, label: str) -> tuple[bool, str]:
    """驗證單一 XML。優先用 lxml（無外部指令相依），缺 lxml 才退回 xmllint。

    兩條路徑的判定結果等價（同一個 libxml2 驗證引擎）；順序上把 lxml 放前面是
    因為它不依賴 PATH 上有 xmllint，跨環境（Windows／Linux 容器）行為一致。
    """
    try:
        return _validate_with_lxml(schema_path, xml_bytes, label)
    except ImportError:
        return _validate_with_xmllint(schema_path, xml_bytes, label)


def main():
    if len(sys.argv) < 2:
        print("用法：python schema_check.py output.pptx")
        sys.exit(2)
    pptx_path = sys.argv[1]
    if SCHEMA is None or not Path(SCHEMA).exists():
        print("找不到官方 ISO/IEC 29500 schema（pml.xsd）。本 skill 自 v2.7 起於\n"
              "  scripts/office/schemas/ISO-IEC29500-4_2016/ 內建一份，若此訊息出現，\n"
              "  代表 skill 檔案不完整，請重新安裝 .skill 套件。")
        sys.exit(2)
    print(f"schema: {SCHEMA}")

    z = zipfile.ZipFile(pptx_path)
    slide_names = sorted(
        [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
        key=lambda n: int("".join(filter(str.isdigit, n.split("/")[-1]))),
    )
    targets = [(n, n.split("/")[-1]) for n in slide_names] + list(CHECK_TARGETS)

    failures = []
    exceptions = set()
    for part_name, label in targets:
        try:
            xml_bytes = z.read(part_name)
        except KeyError:
            continue
        ok, err = _validate_one(SCHEMA, xml_bytes, label)
        if ok:
            print(f"PASS  {label}")
            continue
        real, hit = _filter_known(err)
        exceptions.update(hit)
        if not real:
            print(f"PASS  {label}  （僅命中已知例外：{', '.join(sorted(hit))}）")
            continue
        print(f"FAIL  {label}")
        for line in real:
            print(f"      {line}")
        failures.append(label)

    print()
    if failures:
        print(f"{len(failures)}/{len(targets)} 個 part 未通過官方 schema 驗證，"
              f"PowerPoint 開啟時很可能觸發修復對話框，禁止交付。")
        sys.exit(1)
    if exceptions:
        print("已知例外（schema 比 PowerPoint 實際行為嚴格，非本 builder 的錯誤）：")
        for name, _pat, why in KNOWN_EXCEPTIONS:
            if name in exceptions:
                print(f"  · {name}\n    {why}")
        print()
    print(f"全部 {len(targets)} 個 part 通過官方 schema 驗證，可安全交付。")


if __name__ == "__main__":
    main()
