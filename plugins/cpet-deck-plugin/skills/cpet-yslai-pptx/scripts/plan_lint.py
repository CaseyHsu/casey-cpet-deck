#!/usr/bin/env python3
"""plan_lint.py — plan.json 結構驗證器（v2.9）。

**為什麼需要**：`build_deck.py` 對缺欄位、打錯 type、圖檔不存在一律採「盡量跑、印警告」
的寬鬆容錯風格。這在多輪迭代修改 plan 的情境下不夠安全——以下兩個都是實際發生過、
且**三層 QA 全數 PASS** 的靜默失敗：

1. plan 中 6 個圖片路徑指向尚未複製過去的子目錄，`build_deck` 只 `warn()` 一行就繼續，
   警告淹沒在 build log 裡；當時靠臨時手寫的核對腳本才一次抓到 17 個路徑失效。
2. `equation` 頁把公式寫成頂層 `latex`／`note` 而非 `blocks[]`，建構器**靜默產出一張
   只有標題的空白頁**，零警告，schema 驗證與像素 QA 雙雙 PASS。

兩者的共通點是「不報錯、檔案也產得出來，但結果是錯的」——這正是像素 QA 抓不到的類別。
因此本腳本的必要欄位檢查一律是**錯誤級（非零退出）**，而非警告。

用法：
    python plan_lint.py plan.json            # 錯誤→退出碼 1
    python plan_lint.py plan.json --strict   # 警告也視為失敗
    python plan_lint.py plan.json --quiet    # 只印問題，不印通過摘要
"""
import argparse
import json
import os
import sys

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── 白名單 ────────────────────────────────────────────────────
SLIDE_TYPES = {"cover", "outline", "section", "bullets", "equation",
               "figure", "two_col", "table", "bands", "closing"}
BAND_KINDS = {"text", "figure", "cards", "table", "chevrons", "lanes"}
META_KEYS = {"language", "visual", "no_proof", "bullet_unicode", "caption_size",
             "no_closing_slide", "eq_preamble", "eq_show_source", "eq_source_size",
             # v2.11
             "title_style", "deck_type", "footer", "paper_title", "presenter"}
VISUALS = ("v2.6", "v2.8", "v2.11")
TITLE_STYLES = ("three-level", "two-level")
DECK_TYPES = ("research", "lecture", "weekly", "sop", "conference-oral")
MARKS = {"pro", "con", "step"}
MARKERS = {"badge", "arrow", "none"}
TINTS = {"blue", "orange", "vermilion", "green"}
EMPH = "!!"

# 每種頁型認得的欄位（未列出的欄位會被建構器靜默忽略 → 警告，多半是打錯字）
# v2.11：每種頁型都可加 notes（備忘錄）與 backup（放到致謝頁之後的備用頁）
EXTRA = {"notes", "backup"}
COMMON = {"type", "title", "subtitle", "section", "takeaway"} | EXTRA
KNOWN_KEYS = {
    "cover":    {"type", "title_en", "title_zh", "presenter", "advisor", "date", "extra_lines",
                 "authors", "affiliation"} | EXTRA,
    "outline":  {"type", "title", "items"} | EXTRA,
    "section":  {"type", "title", "parts", "active", "lead"} | EXTRA,
    "bullets":  COMMON | {"bullets", "size"},
    "equation": COMMON | {"blocks", "intro"},
    "figure":   COMMON | {"images", "bullets", "source_shared"},
    "two_col":  COMMON | {"left_bullets", "right", "size"},
    "table":    COMMON | {"columns", "rows", "note", "first_col_item", "col_align",
                          "highlight_rows"},
    "bands":    COMMON | {"bands"},
    "closing":  {"type", "text", "size"} | EXTRA,
}
BAND_KEYS = {
    "text":   {"kind", "bullets", "size", "weight", "max_h"},
    "figure": {"kind", "images", "cols", "source_shared", "weight", "max_h"},
    "cards":  {"kind", "cards", "cols", "weight", "max_h"},
    "table":  {"kind", "columns", "rows", "note", "first_col_item", "col_align",
               "highlight_rows", "title", "weight", "max_h"},
    "chevrons": {"kind", "steps", "accent"},
    "lanes":  {"kind", "lanes"},
}
CARD_KEYS = {"head", "body", "bullets", "badge", "marker", "accent", "kpi", "tint"}
# 視為「自製素材」的目錄名：路徑中任一層命中即不強制要求 source。
# 注意要比對「路徑的每一層」而非只看第一層——實際 plan 常用絕對路徑
# （/sessions/<id>/mnt/outputs/figs/xxx.png），只看第一層會把自製圖全部誤判為外部素材。
SELF_MADE_DIRS = {"figs", "figures", "equations", "screenshots", "shots"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, where, msg):
        self.errors.append((where, msg))

    def warn(self, where, msg):
        self.warnings.append((where, msg))


def _where(i, d):
    t = d.get("type", "?")
    title = d.get("title") or d.get("title_zh") or d.get("title_en") or ""
    return f"第 {i} 張（{t}）{('「' + str(title)[:24] + '」') if title else ''}"


def _check_image(rep, where, img, base_dir, label="images[]"):
    if not isinstance(img, dict):
        rep.err(where, f"{label} 的元素必須是物件（含 path），實際是 {type(img).__name__}")
        return
    path = img.get("path")
    if not path:
        rep.err(where, f"{label} 缺少 path")
        return
    full = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(full):
        rep.err(where, f"圖檔不存在：{path}（解析為 {full}）")
    # 外部素材必須標來源（學術誠信要求，見 conventions §2.6）
    parts = {seg for seg in str(path).replace("\\", "/").split("/") if seg}
    if not img.get("source") and not (parts & SELF_MADE_DIRS):
        rep.warn(where, f"外部圖片未標 source：{path}"
                        f"（取自網路或文獻的圖須標出處；自繪圖建議放 figs/ 或標「本文實測」）")


def _check_bullets(rep, where, bullets, label="bullets"):
    if not isinstance(bullets, list):
        rep.err(where, f"{label} 必須是陣列")
        return
    for b in bullets:
        if isinstance(b, str):
            continue
        if not isinstance(b, dict):
            rep.err(where, f"{label} 的元素必須是字串或物件")
            continue
        if "text" not in b:
            rep.err(where, f"{label} 的物件缺少 text")
        m = b.get("mark")
        if m is not None and m not in MARKS:
            rep.err(where, f"未知的 mark：{m!r}（可用：{'／'.join(sorted(MARKS))}）")
        unknown = set(b) - {"text", "level", "mark", "bold", "em"}
        if unknown:
            rep.warn(where, f"{label} 有未知欄位 {sorted(unknown)}——會被靜默忽略，請檢查拼字")
    if len(bullets) > 6:
        rep.warn(where, f"{label} 有 {len(bullets)} 條（建議 ≤6）——一頁一訊息，建議拆頁")


def _check_table(rep, where, d):
    cols, rows = d.get("columns"), d.get("rows")
    if not cols:
        rep.err(where, "table 缺少 columns")
    if not rows:
        rep.err(where, "table 缺少 rows")
    if isinstance(cols, list) and isinstance(rows, list):
        nc = len(cols)
        for ri, r in enumerate(rows):
            if not isinstance(r, list):
                rep.err(where, f"rows[{ri}] 必須是陣列")
            elif len(r) != nc:
                rep.err(where, f"rows[{ri}] 有 {len(r)} 欄，與 columns 的 {nc} 欄不符")
        hl = d.get("highlight_rows", [])
        if not isinstance(hl, list):
            rep.err(where, "highlight_rows 必須是陣列（資料列索引，0 起算）")
        else:
            for h in hl:
                if not isinstance(h, int) or not (0 <= h < len(rows)):
                    rep.err(where, f"highlight_rows 的 {h!r} 超出資料列範圍 0–{len(rows)-1}")


def _emph_n(text):
    return str(text).count(EMPH) // 2


def _check_cards(rep, where, cards, deck_type=None, used_tints=None):
    if not isinstance(cards, list) or not cards:
        rep.err(where, "cards band 缺少 cards 或不是陣列")
        return
    n_accent = 0
    for ci, c in enumerate(cards):
        if not isinstance(c, dict):
            rep.err(where, f"cards[{ci}] 必須是物件")
            continue
        t = c.get("tint")
        if t is not None:
            if t not in TINTS:
                rep.err(where, f"cards[{ci}] 未知的 tint：{t!r}（可用：{'／'.join(sorted(TINTS))}）")
            elif used_tints is not None:
                used_tints.add(t)
        texts = [c.get("body", "")] + [b["text"] if isinstance(b, dict) else b
                                       for b in c.get("bullets", []) or []]
        n_em = sum(_emph_n(x) for x in texts)
        if n_em > 2:
            rep.warn(where, f"cards[{ci}] 有 {n_em} 個重點片語 !!…!!（建議每卡 1–2 個，conventions §2.5c）")
        if any(str(x).count(EMPH) % 2 for x in texts):
            rep.err(where, f"cards[{ci}] 的重點標記 !! 沒有成對")
        if deck_type == "conference-oral" and len(c.get("bullets") or []) > 3:
            rep.warn(where, f"cards[{ci}] 有 {len(c['bullets'])} 點——口頭報告每卡 ≤3 點（F11）")
        if not (c.get("head") or c.get("body") or c.get("bullets") or c.get("kpi")):
            rep.err(where, f"cards[{ci}] 是空卡（head／body／bullets／kpi 至少要有一項）")
        if c.get("body") and c.get("bullets"):
            rep.warn(where, f"cards[{ci}] 同時有 body 與 bullets——建構器只會畫 body")
        mk = c.get("marker")
        if mk is not None and mk not in MARKERS:
            rep.err(where, f"cards[{ci}] 未知的 marker：{mk!r}（可用：{'／'.join(sorted(MARKERS))}）")
        if c.get("accent"):
            n_accent += 1
        if c.get("bullets"):
            _check_bullets(rep, where, c["bullets"], f"cards[{ci}].bullets")
        unknown = set(c) - CARD_KEYS
        if unknown:
            rep.warn(where, f"cards[{ci}] 有未知欄位 {sorted(unknown)}——會被靜默忽略")
    if n_accent > 1:
        rep.warn(where, f"同一 band 有 {n_accent} 張 accent 卡——強調卡一頁以一張為原則"
                        f"（conventions §2.5b.1）")


def _check_band(rep, where, bi, band, base_dir, deck_type=None, used_tints=None):
    if not isinstance(band, dict):
        rep.err(where, f"bands[{bi}] 必須是物件")
        return
    kind = band.get("kind")
    if kind not in BAND_KINDS:
        rep.err(where, f"bands[{bi}] 的 kind {kind!r} 不在白名單："
                       f"{'／'.join(sorted(BAND_KINDS))}")
        return
    unknown = set(band) - BAND_KEYS[kind]
    if unknown:
        rep.warn(where, f"bands[{bi}]（{kind}）有未知欄位 {sorted(unknown)}——會被靜默忽略")
    if kind == "text":
        if not band.get("bullets"):
            rep.err(where, f"bands[{bi}] 是 text band 但沒有 bullets")
        else:
            _check_bullets(rep, where, band["bullets"], f"bands[{bi}].bullets")
    elif kind == "figure":
        imgs = band.get("images")
        if not imgs:
            rep.err(where, f"bands[{bi}] 是 figure band 但沒有 images")
        else:
            for img in imgs:
                _check_image(rep, where, img, base_dir, f"bands[{bi}].images[]")
            cols = band.get("cols", len(imgs))
            if isinstance(cols, int) and not (1 <= cols <= 3):
                rep.err(where, f"bands[{bi}] 的 cols={cols} 超出 figure band 的 1–3")
    elif kind == "cards":
        _check_cards(rep, where, band.get("cards"), deck_type, used_tints)
        cols = band.get("cols", len(band.get("cards") or []))
        if isinstance(cols, int) and not (1 <= cols <= 4):
            rep.err(where, f"bands[{bi}] 的 cols={cols} 超出 cards band 的 1–4")
    elif kind == "table":
        _check_table(rep, where, band)
    elif kind == "chevrons":
        steps = band.get("steps")
        if not steps or not isinstance(steps, list):
            rep.err(where, f"bands[{bi}] 是 chevrons band 但沒有 steps")
        else:
            if not 2 <= len(steps) <= 5:
                rep.warn(where, f"bands[{bi}] chevrons 有 {len(steps)} 個階段（建議 3–5）")
            for si, st in enumerate(steps):
                if not isinstance(st, dict) or not st.get("head"):
                    rep.err(where, f"bands[{bi}].steps[{si}] 缺少 head")
            acc = band.get("accent")
            if acc is not None and not (isinstance(acc, int) and 0 <= acc < len(steps)):
                rep.err(where, f"bands[{bi}] 的 accent={acc!r} 不是 steps 的索引")
    elif kind == "lanes":
        lanes = band.get("lanes")
        if not lanes or not isinstance(lanes, list):
            rep.err(where, f"bands[{bi}] 是 lanes band 但沒有 lanes")
            return
        if len(lanes) > 3:
            rep.warn(where, f"bands[{bi}] 有 {len(lanes)} 條 lane（建議 ≤3）")
        for li, ln in enumerate(lanes):
            if not isinstance(ln, dict) or not ln.get("label"):
                rep.err(where, f"bands[{bi}].lanes[{li}] 缺少 label")
                continue
            t = ln.get("tint")
            if t is not None and t not in TINTS:
                rep.err(where, f"bands[{bi}].lanes[{li}] 未知的 tint：{t!r}")
            elif t and used_tints is not None:
                used_tints.add(t)
            items = ln.get("items") or []
            if not items:
                rep.err(where, f"bands[{bi}].lanes[{li}] 沒有 items")
            if len(items) > 4:
                rep.warn(where, f"bands[{bi}].lanes[{li}] 有 {len(items)} 格（建議 ≤4）")
            for it in items:
                if isinstance(it, dict) and it.get("image"):
                    _check_image(rep, where, {"path": it["image"], "source": it.get("source")},
                                 base_dir, f"bands[{bi}].lanes[{li}].items[]")
                elif not (isinstance(it, dict) and it.get("text")):
                    rep.err(where, f"bands[{bi}].lanes[{li}] 的格子需要 image 或 text")


def lint(plan_path, base_dir=None):
    """回傳 Report。base_dir 預設為 plan.json 所在目錄（與 build_deck 的解析基準一致）。"""
    rep = Report()
    base_dir = base_dir or os.path.dirname(os.path.abspath(plan_path))
    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except json.JSONDecodeError as e:
        rep.err("plan.json", f"JSON 解析失敗：{e}")
        return rep
    except OSError as e:
        rep.err("plan.json", f"無法讀取：{e}")
        return rep

    meta = plan.get("meta", {})
    if not isinstance(meta, dict):
        rep.err("meta", "meta 必須是物件")
        meta = {}
    for k in set(meta) - META_KEYS:
        rep.warn("meta", f"未知的 meta 欄位 {k!r}——會被靜默忽略，請檢查拼字")
    if "visual" in meta and meta["visual"] not in VISUALS:
        rep.err("meta", f"meta.visual 只能是 {'／'.join(VISUALS)}，實際是 {meta['visual']!r}")
    if "title_style" in meta and meta["title_style"] not in TITLE_STYLES:
        rep.err("meta", f"meta.title_style 只能是 {'／'.join(TITLE_STYLES)}")
    deck_type = meta.get("deck_type")
    if deck_type is not None and deck_type not in DECK_TYPES:
        rep.err("meta", f"meta.deck_type 只能是 {'／'.join(DECK_TYPES)}")
    used_tints = set()

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        rep.err("plan.json", "缺少 slides 陣列或為空")
        return rep

    for i, d in enumerate(slides, 1):
        if not isinstance(d, dict):
            rep.err(f"第 {i} 張", "投影片必須是物件")
            continue
        where = _where(i, d)
        t = d.get("type")
        if t not in SLIDE_TYPES:
            rep.err(where, f"type {t!r} 不在白名單：{'／'.join(sorted(SLIDE_TYPES))}")
            continue
        unknown = set(d) - KNOWN_KEYS[t]
        if unknown:
            rep.warn(where, f"未知欄位 {sorted(unknown)}——建構器會靜默忽略，請檢查拼字")

        if t == "cover":
            if not (d.get("title_zh") or d.get("title_en")):
                rep.err(where, "cover 缺少 title_zh／title_en（至少要有一個）")
        elif t == "outline":
            if not d.get("items"):
                rep.err(where, "outline 缺少 items")
            elif len(d["items"]) > 8:
                rep.warn(where, f"outline 有 {len(d['items'])} 項（上限 8，見 conventions §3 C2）")
        elif t == "section":
            if not d.get("parts"):
                rep.err(where, "section 缺少 parts")
        elif t == "bullets":
            if not d.get("bullets"):
                rep.err(where, "bullets 頁缺少 bullets")
            else:
                _check_bullets(rep, where, d["bullets"])
        elif t == "equation":
            blocks = d.get("blocks")
            if not blocks:
                extra = ""
                if "latex" in d or "note" in d:
                    extra = ("——偵測到頂層 latex／note，公式必須包在 blocks[] 陣列裡："
                             '"blocks": [{"latex": "…", "note": "…"}]')
                rep.err(where, f"equation 缺少 blocks{extra}")
            else:
                for bi, blk in enumerate(blocks):
                    if not isinstance(blk, dict) or not blk.get("latex"):
                        rep.err(where, f"blocks[{bi}] 缺少 latex")
                    elif not blk.get("note"):
                        rep.warn(where, f"blocks[{bi}] 沒有 note——公式須附物理意義"
                                        f"（conventions §2 硬規則）")
        elif t == "figure":
            imgs = d.get("images")
            if not imgs:
                rep.err(where, "figure 缺少 images")
            else:
                for img in imgs:
                    _check_image(rep, where, img, base_dir)
            if d.get("bullets"):
                _check_bullets(rep, where, d["bullets"])
        elif t == "two_col":
            if not d.get("left_bullets") and not d.get("right"):
                rep.err(where, "two_col 缺少 left_bullets 與 right（至少要有一個）")
            if d.get("left_bullets"):
                _check_bullets(rep, where, d["left_bullets"], "left_bullets")
            right = d.get("right") or {}
            if isinstance(right, dict) and "image" in right:
                _check_image(rep, where, right["image"], base_dir, "right.image")
        elif t == "table":
            _check_table(rep, where, d)
        elif t == "bands":
            bands = d.get("bands")
            if not bands:
                rep.err(where, "bands 頁缺少 bands 陣列")
            else:
                if len(bands) > 3:
                    rep.err(where, f"bands 有 {len(bands)} 個（上限 3）——這是密度閘門，"
                                   f"請拆頁而非放寬")
                for bi, band in enumerate(bands):
                    _check_band(rep, where, bi, band, base_dir, deck_type, used_tints)
        # closing 無必要欄位

        if d.get("notes") is not None and not isinstance(d["notes"], str):
            rep.err(where, "notes 必須是字串（多行用 \\n）")
        tk = d.get("takeaway")
        if tk:
            if str(tk).count(EMPH) % 2:
                rep.err(where, "takeaway 的重點標記 !! 沒有成對")
            elif _emph_n(tk) > 3:
                rep.warn(where, f"takeaway 有 {_emph_n(tk)} 個重點片語（≤3，conventions §2.5c）")

        head = d.get("title")
        if t in ("bullets", "equation", "figure", "two_col", "table", "bands") and head:
            disp = sum(1.0 if ord(c) > 0x2E7F else 0.5 for c in str(head))
            if disp > 20:
                rep.warn(where, f"頁大標顯示寬度 {disp:.0f}（建議 ≤20）——建議把後段移到 subtitle")

    # F5：語意色全簡報 ≤3 種；第 4 種（green）只在有雙重編碼時使用
    sem = set(used_tints)
    if sem and len(sem | {"orange"}) > 3:
        rep.warn("全簡報", f"淡底卡／泳道用了 {len(sem | {'orange'})} 種語意色 {sorted(sem | {'orange'})}"
                         f"（含結論橙）——上限 3 種；第 4 種須有 ✓／✗ 或文字標籤等雙重編碼（conventions §2.5.2）")
    return rep


def print_report(rep, quiet=False):
    for where, msg in rep.errors:
        print(f"ERROR  {where}\n       {msg}")
    for where, msg in rep.warnings:
        print(f"WARN   {where}\n       {msg}")
    if rep.errors or rep.warnings:
        print()
    if rep.errors:
        print(f"✘ {len(rep.errors)} 個錯誤、{len(rep.warnings)} 則警告 — "
              f"錯誤會導致靜默缺頁或缺圖，必須修正後再建置。")
    elif not quiet:
        print(f"✔ plan 結構檢查通過（{len(rep.warnings)} 則警告）。")


def main():
    ap = argparse.ArgumentParser(description="plan.json 結構驗證器")
    ap.add_argument("plan")
    ap.add_argument("--strict", action="store_true", help="警告也視為失敗")
    ap.add_argument("--quiet", action="store_true", help="通過時不印摘要")
    a = ap.parse_args()
    rep = lint(a.plan)
    print_report(rep, quiet=a.quiet)
    if rep.errors or (a.strict and rep.warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
