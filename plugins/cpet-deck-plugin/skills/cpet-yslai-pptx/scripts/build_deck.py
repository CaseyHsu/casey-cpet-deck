#!/usr/bin/env python3
"""build_deck.py — 以 slide_plan.json 在 CPET-YS Lai Lab 模板上確定性生成簡報。

用法：
    python build_deck.py plan.json output.pptx [--template /path/to/template.pptx]

slide_plan.json 結構（完整規格見 SKILL.md）：
{
  "slides": [
    {"type":"cover","title_en":"...","title_zh":"...","presenter":"...","advisor":"Y.S. Lai","date":"2026.07.05"},
    {"type":"outline","title":"Outline","items":[{"text":"Motivation","em":true},"Proposed Method"]},
    {"type":"section","title":"Proposed Method","parts":["Part-I: ...","Part-II: ..."],"active":0},
    {"type":"bullets","title":"...","subtitle":"(Part-I: ...)","bullets":[{"text":"...","level":0,"bold":true},"純字串也可"],"takeaway":"..."},
    {"type":"equation","title":"...","subtitle":"...","intro":"...","blocks":[{"latex":"...","note":"物理意義..."}],"takeaway":"..."},
    {"type":"figure","title":"...","bullets":[...],"images":[{"path":"a.png","caption":"圖 1. ..."}],"takeaway":"..."},
    {"type":"two_col","title":"...","left_bullets":[...],
     "right":{"image":{"path":"...","caption":"..."}}  或  "right":{"latex":"...","note":"..."}},
    {"type":"table","title":"...","columns":["A","B"],"rows":[["1","2"]],"note":"..."}
  ]
}
"""
import argparse
import copy
import json
import math
import os
import sys
import tempfile

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_eq import render_latex  # noqa: E402

# 主控台編碼：Windows 繁中環境的管線 stdout 預設 cp950，印「≤」「✔」等字元會 UnicodeEncodeError 崩潰。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

EMU_IN = 914400
SLIDE_W = 13.333
SLIDE_H = 7.5

# ── 版面常數（吋）─────────────────────────────────────────────
MARGIN_X = 0.38
CONTENT_R = SLIDE_W - MARGIN_X
# v2.7：新模板把標題 placeholder 由 top=0.40 上移至 0.29、內容版面配置區由 1.15 上移至
# 1.07，以下內容起點常數同步上移 0.08–0.11in，維持與 placeholder 的既有相對關係。
TITLE_TOP = 0.25        # 無 title placeholder 時的後備文字框位置（對應 layout 標題 0.29）
SUB_TOP = 0.91          # 副標（Part-X 深紅行）
BODY_TOP_PLAIN = 1.07   # 無副標時內容起點（＝新模板內容版面配置區 top）
BODY_TOP_SUB = 1.51     # 有副標時內容起點
BODY_BOTTOM = 7.02      # 底部藍線上方安全界線
TAKEAWAY_H = 0.52

# 封面資訊區塊（ph14）底端錨定基準：母片底線在 7.25in，留 0.2in（約一字元）淨空。
MASTER_RULE_Y = 7.25
COVER_INFO_BOTTOM = MASTER_RULE_Y - 0.2
COVER_INFO_TOP_MIN = 5.20   # 上限保護：不得侵入封面主標 placeholder（2.16+2.97=5.13）

# ── 色彩（v2.8：結構色／語意色兩層制）──────────────────────────
#
# 結構色：承載版面結構（標題、表頭、內文、輔助文字、卡片），色相本身不帶訊息，
#         不計入「單頁語意色 ≤2、全簡報 ≤3」的色數限制。取自實驗室參考簡報實測值。
# 語意色：承載訊息（結論、對照、警示），一律取自 Okabe-Ito 色盲友善色票
#         （Okabe & Ito, Color Universal Design, CUDO 2008；Wong, Nature Methods, 2011）。
#         舊版的綠 #2E6010 與紅 #C00000 並用構成紅綠對立，第一/二型色覺異常者
#         （男性約 8%）無法區分，v2.8 起自語意層完全退出。
#
# ── 結構色 ──
C_TITLE = RGBColor(0x00, 0x00, 0xFF)     # 章 running title（母片既有藍，不動）
C_HEAD = RGBColor(0x14, 0x27, 0x4E)      # 頁大標／表頭／徽章／卡片標題：navy
C_BODY = RGBColor(0x1F, 0x29, 0x37)      # 正文
C_MUTED = RGBColor(0x6B, 0x72, 0x80)     # 頁副標／圖說／註腳／來源
C_CARD_BG = RGBColor(0xF5, 0xF7, 0xFA)   # 卡片底
C_CARD_LN = RGBColor(0xD6, 0xDE, 0xE9)   # 卡片框線
C_COL1_BG = RGBColor(0xDC, 0xE6, 0xF1)   # 表格第一欄（項目欄）底色
C_TBL_LN = "8EA9C9"                      # 表格框線色
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK = RGBColor(0x00, 0x00, 0x00)
C_GRAY = RGBColor(0xA6, 0xA6, 0xA6)

# ── 語意色（Okabe-Ito）──
C_ORANGE = RGBColor(0xE6, 0x9F, 0x00)      # 結論／主強調（takeaway、KPI、pro 底色）
C_ORANGE_BG = RGBColor(0xFB, 0xEF, 0xD8)   # 上者的淡階（參考簡報實測值）
C_ORANGE_DK = RGBColor(0x8A, 0x5A, 0x00)   # 橙的暗階，供橙底上需要同色系文字時使用
C_BLUE = RGBColor(0x00, 0x72, 0xB2)        # 對照／次強調／pro 符號
C_VERMILION = RGBColor(0xD5, 0x5E, 0x00)   # 警示／差異／進度 active／con 符號
C_BGREEN = RGBColor(0x00, 0x9E, 0x73)      # 第四類別，**僅供圖表內部**，版面層不用

# ── v2.11（ECCE 2026 回饋，conventions §2.5c）──
C_EMPH = RGBColor(0xC0, 0x00, 0x00)        # 行內重點字 !!…!!（白底 6.48:1、卡片底 6.04:1）；唯一的重點紅
C_TAKEAWAY_EM = RGBColor(0xFF, 0xD5, 0x4F) # navy 結論橫條內的重點字（10.41:1）；黃只在深底上當文字
# 淡底卡（tint）：底色＝語意色淡階、框線＝語意色本色、標題維持 navy（文字不用語意色本色）
TINTS = {
    "blue":      (RGBColor(0xE3, 0xF0, 0xF9), C_BLUE),
    "orange":    (C_ORANGE_BG, C_ORANGE),
    "vermilion": (RGBColor(0xFB, 0xE9, 0xDD), C_VERMILION),
    "green":     (RGBColor(0xE0, 0xF4, 0xEE), C_BGREEN),   # 第四色：只在有雙重編碼（✓／✗、文字標籤）時用
}

# ── v2.6 相容常數（meta.visual: "v2.6" 時由 _apply_visual() 覆寫回這組）──
V26 = {
    "C_HEAD": RGBColor(0x00, 0x37, 0x81), "C_BODY": RGBColor(0x1F, 0x1F, 0x6E),
    "C_MUTED": RGBColor(0x59, 0x59, 0x59), "C_SUB": RGBColor(0x9B, 0x42, 0x3D),
    "C_EM": RGBColor(0x2D, 0x2D, 0x8A), "C_ACTIVE": RGBColor(0xC0, 0x00, 0x00),
    "C_TAKEAWAY_BG": RGBColor(0xE2, 0xEF, 0xDA), "C_TAKEAWAY_LN": RGBColor(0x2E, 0x60, 0x10),
    "C_TAKEAWAY_TX": RGBColor(0x2E, 0x60, 0x10), "C_TAKEAWAY_MK": RGBColor(0x2E, 0x60, 0x10),
}

# 以下為「會被 meta.visual 切換」的別名，程式各處一律引用這些別名而非硬編色碼
C_SUB = C_MUTED               # 頁副標
C_EM = C_BLUE                 # 詞句內強調
C_ACTIVE = C_VERMILION        # section 進度 active
C_NAVY = C_HEAD               # 表頭（沿用舊名，避免大量改寫）
# takeaway 與 accent 卡的區分是**層級**而非色相：accent 卡是同層元素中的一個，takeaway
# 是整頁結論、層級更高。v2.8.1 前兩者都用淡橙底＋橙框，視覺重量完全相同、無法區分。
# 改為：takeaway＝全頁唯一的 navy 實心橫幅＋白字（對比 14.69:1，灰階底 38 vs 卡片 240，
# 分離最大），箭頭維持橙色以保留「橙＝結論」的語意線索；accent 卡保留淡橙底。
C_TAKEAWAY_BG = C_HEAD
C_TAKEAWAY_LN = C_HEAD
C_TAKEAWAY_TX = C_WHITE
C_TAKEAWAY_MK = C_ORANGE      # 前綴箭頭：橙（在 navy 上對比足夠，保留語意線索）
VISUAL = "v2.11"
TITLE_STYLE = "three-level"   # meta.title_style："three-level"（預設）／"two-level"（章名＋頁名同一行）
PROFILE = None                # --profile：官方模板的描述檔（見 references/template-profiles.md）
EQ_NOTES = {}                 # v2.11：slide 物件 id -> [LaTeX 原始碼]，建置後寫入該頁備忘錄

FONT_TITLE_EN, FONT_TITLE_EA = "Times New Roman", "標楷體"
FONT_BODY_EN, FONT_BODY_EA = "Arial", "微軟正黑體"

# ── 語言標籤（meta.language: "zh-TW" 預設 / "en"）────────────
LABELS = {
    "zh-TW": {"presenter": "報告人：", "advisor": "指導教授：", "sep": "　　",
              "note": "物理意義："},
    "en": {"presenter": "Presenter: ", "advisor": "Advisor: ", "sep": "    ",
           "note": "Physical meaning: "},
}
LANG = "zh-TW"


def L(key):
    return LABELS.get(LANG, LABELS["zh-TW"])[key]


def _sub_size(sz):
    """第二層字級：主層-4，但版面允許時不低於 22（Casey 指定 22–24 區間）。"""
    s = sz - 4
    if s >= 22:
        return s
    return max(SZ["bullet_l1"][1], sz - 2)


# ── 分角色字級表（v2.8）────────────────────────────────────────
# v2.6 用單一 MIN_BODY_SZ = 18 管全簡報，等於把「防止正文太小」誤套到輔助文字上，
# 圖說與註腳因此和正文一樣重，視覺層次做不出來。改為依角色分別設起始值與下限，
# 數值對齊實驗室參考簡報 54 頁實測字級譜（44/40/36/28/24/20/19/18/16/14/13/12/11.5）。
# 格式：角色 -> (起始字級, 下限)
SZ = {
    "running_title": (40, 32),   # 章 running title
    "page_head":     (32, 26),   # 頁大標（v2.8 同版修訂：36→32，Casey 實機驗收裁定）
    "page_sub":      (16, 16),   # 頁副標
    "bullet_l0":     (24, 20),   # 正文條列第一層
    "bullet_l1":     (20, 18),   # 正文條列第二層
    "card_head":     (20, 18),   # 卡片標題
    "card_body":     (18, 16),   # 卡片內文
    "takeaway":      (16, 16),   # v2.11：基準 16pt，重點片語 +4pt 黃字（v2.8 為 20/18、無重點字）
    "table":         (20, 18),
    "caption":       (13, 12),   # 圖說
    "source":        (11.5, 11),  # 圖片來源／表格註腳
    "eq_source":     (11, 11),   # 公式 LaTeX 原碼標註
    "kpi":           (44, 28),   # KPI 大數值
    "badge":         (19, 16),   # 圓徽章數字
}
SZ_V26 = {  # meta.visual: "v2.6" 時全部回到 18pt 全域下限
    k: (v[0], 18) for k, v in SZ.items()
    if k not in ("caption", "source", "eq_source", "page_sub")
}
SZ_V26.update({"caption": (18, 18), "source": (18, 18), "eq_source": (11, 11),
               "page_sub": (22, 18), "bullet_l0": (28, 18), "bullet_l1": (24, 18),
               "takeaway": (20, 18)})

MIN_BODY_SZ = 18  # 保留供既有呼叫點使用＝正文語境的下限（非全簡報下限，見 SZ）


NO_PROOF = True   # 由 plan meta.no_proof 控制（預設 true，見 _set_font()）

WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print(f"⚠ {msg}")


# ── 基礎工具 ─────────────────────────────────────────────────
def _set_font(run, sz, bold=False, color=C_BODY, title_font=False, italic=False):
    f = run.font
    f.size = Pt(sz)
    f.bold = bold
    f.italic = italic
    if color is not None:   # None：沿用模板文字框的顏色（官方模板 profile 用）
        f.color.rgb = color
    f.name = FONT_TITLE_EN if title_font else FONT_BODY_EN
    ea = FONT_TITLE_EA if title_font else FONT_BODY_EA
    rPr = run._r.get_or_add_rPr()
    for tag in ("latin", "ea"):
        el = rPr.find(f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag}")
        if el is None:
            el = rPr.makeelement(
                f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag}", {})
            rPr.append(el)
        el.set("typeface", FONT_TITLE_EN if title_font else FONT_BODY_EN)
    rPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea").set("typeface", ea)
    # v2.7：關閉 PowerPoint 編輯畫面的拼字／文法檢查紅波浪線。中英混排是本 skill 的常態
    # 使用情境（CPET、MTPA、SVPWM 等專有名詞與中文字都會被標記），此標記僅出現在編輯
    # 畫面，放映與列印本就不受影響，故預設關閉；plan 可設 meta.no_proof: false 還原。
    if NO_PROOF:
        rPr.set("noProof", "1")
    elif rPr.get("noProof") is not None:
        del rPr.attrib["noProof"]


def _no_bullet(para):
    pPr = para._p.get_or_add_pPr()
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for t in ("buChar", "buAutoNum", "buNone"):
        for el in pPr.findall(ns + t):
            pPr.remove(el)
    pPr.append(pPr.makeelement(ns + "buNone", {}))


def _bullet_char(para, char="\u27A2", color=None, font="Arial", size_pct=None):
    """項目符號字元。改用標準 Unicode 箭頭 U+27A2（➢），而非 Wingdings 私有編碼字元 Ø。
    原因：Wingdings 的 'Ø' 依賴 Windows 內建 Wingdings 字型的私有映射，任何未安裝該字型
    的環境（LibreOffice/部分 PowerPoint 字型替換設定）都會退化成缺字方框（tofu）。
    U+27A2 是標準 Unicode 字符，DejaVu Sans、FreeSans、LibreOffice OpenSymbol 等常見
    字型都原生支援，可跨平台正確顯示，且視覺上與原箭頭高度相似。"""
    pPr = para._p.get_or_add_pPr()
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for t in ("buChar", "buAutoNum", "buNone", "buClr", "buFont", "buSzPct"):
        for el in pPr.findall(ns + t):
            pPr.remove(el)
    if color is not None:
        clr = pPr.makeelement(ns + "buClr", {})
        srgb = pPr.makeelement(ns + "srgbClr", {"val": "%02X%02X%02X" % (color[0], color[1], color[2])})
        clr.append(srgb)
        pPr.append(clr)
    # v2.8：buSzPct 統一控制項目符號相對字級。原本未寫此屬性，PowerPoint 一律以 100%
    # 呈現，而 Wingdings 的勾（ü）／叉（û）視覺重量明顯大於箭頭（Ø），同一頁不同語意
    # 符號會顯得忽大忽小——這是「尺寸異常」的真正來源，不是字元選錯。
    # val 採「千分之一百分比」整數（100000 = 100%），這是 PowerPoint 實際寫出的形式——
    # 依 Casey 提供的實驗室參考簡報（真實 PowerPoint 產出）實測，112 處 buSzPct 全部是
    # val="100000"。注意：ISO-IEC29500-4:2016 的 CT_TextBulletSizePercent/@val 型別宣告為
    # ST_TextBulletSizePercent（只允許 "85%" 這種百分比字串），因此**真實 PowerPoint 檔案
    # 反而過不了官方 schema**（該參考簡報 38 張投影片皆因此被判 FAIL）。取捨：以 PowerPoint
    # 實機行為為準（MAINTENANCE.md §4），並在 schema_check.py 內把這一條列為具名已知例外，
    # 避免它淹沒真正的 schema 錯誤。
    # 100% 時直接不寫此屬性（預設即跟隨文字大小），減少無謂的例外。
    if size_pct is not None and abs(size_pct - 1.0) > 1e-6:
        pPr.append(pPr.makeelement(ns + "buSzPct",
                                   {"val": str(int(round(size_pct * 100000)))}))
    bf = pPr.makeelement(ns + "buFont", {"typeface": font, "pitchFamily": "34", "charset": "0"})
    pPr.append(bf)
    bc = pPr.makeelement(ns + "buChar", {"char": char})
    pPr.append(bc)


BULLET_L0 = "\u00D8"        # Wingdings 'Ø'：PowerPoint 原生 3D 箭頭式樣（2026-07 Casey 裁定：以 PowerPoint 觀感為準）
BULLET_L0_FONT = "Wingdings"
BULLET_L0_UNI = "\u27A4"    # ➤ Unicode 後備（meta.bullet_unicode: true 時使用，跨平台安全）
BULLET_UNICODE = False       # 由 plan meta.bullet_unicode 控制
CM_EMU = 360000              # EMU per cm


def _l0_bullet():
    """回傳第一層項目符號 (char, font)。預設 Wingdings Ø；meta.bullet_unicode 時退回 ➤/Arial。"""
    return (BULLET_L0_UNI, "Arial") if BULLET_UNICODE else (BULLET_L0, BULLET_L0_FONT)
BULLET_L1 = "\u25CF"   # ● 實心圓
BULLET_CARD = "\u006E"      # Wingdings 'n' = ■ 小實心方塊（卡片內文；參考簡報 71 處實測用法）

# ── 語意項目符號（v2.8）─────────────────────────────────────────
# 一律使用 PowerPoint 內建字型（Wingdings／Arial）的既有字元，不自行繪製圖形，
# 尺寸由 buSzPct 統一控制。
#
# 刻意避開的碼點（重要）：
#   U+2714（勾）與 U+274C（叉）是 emoji 碼點，Windows 會由 Segoe UI Emoji 接手渲染成
#     彩色，尺寸與基線都不受 buSzPct 控制；U+274C 更是連文字呈現變體都沒有。
#   U+25B6（實心右三角）同樣帶 emoji 呈現變體。
#   以上三者一律不用，改用 Wingdings 的 U+00FC／U+00FB 與 U+25BA
#   （BLACK RIGHT-POINTING POINTER，無 emoji 變體）。
# 格式：mark -> (char, font, color 常數名, buSzPct)
MARKS = {
    "pro":  ("\u00FC", "Wingdings", "C_BLUE", 0.88),       # 勾：優勢／實驗結果驗證
    # 叉：前人方法缺陷／研究痛點。原用 Wingdings U+00FB（ballot X），Casey 實機驗收回饋
    # 「太小、希望是正體的 X」——該字元是細筆畫的打勾框叉，視覺重量遠低於同組的勾號。
    # 改用 Arial 的拉丁大寫 X：字型必定涵蓋（無缺字風險）、無 emoji 呈現變體、筆畫粗細
    # 與內文一致，尺寸回到 100%。（U+2715 MULTIPLICATION X 幾何上更對稱，但屬 Dingbats
    # 區塊、Arial 未必涵蓋，會有 tofu 風險，故不採用。）
    "con":  ("X", "Arial", "C_VERMILION", 1.00),
    "step": ("\u25BA", "Arial", "C_HEAD", 1.00),           # 箭頭：演算法順序／實驗步驟
}
ARROW_RIGHT = "\u25BA"      # 一般行內右箭頭（取代 U+25B6）


def add_textbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                                  Emu(int(w * EMU_IN)), Emu(int(h * EMU_IN)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return tb


EMPH_MARK = "!!"   # v2.11 行內重點：!!片語!! → 粗體＋重點色（conventions §2.5c）


def _plain(text):
    return str(text).replace(EMPH_MARK, "")


def _emph_count(text):
    return str(text).count(EMPH_MARK) // 2


def _add_rich(para, text, sz, color, bold=False, title_font=False, em_color=None, em_sz=None):
    """寫入一段文字；!!…!! 包住的片語改用粗體＋重點色（預設 C_EMPH）與 em_sz 字級。
    沒有 !! 時只產生一個 run，與 v2.10 以前的輸出完全相同。"""
    parts = str(text).split(EMPH_MARK)
    if len(parts) % 2 == 0:            # 標記沒有成對：當一般文字處理，避免吃掉內容
        warn(f"重點標記 !! 沒有成對：{_plain(text)[:30]}…")
        parts = [_plain(text)]
    runs = []
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = para.add_run()
        r.text = seg
        if i % 2:
            _set_font(r, em_sz or sz, bold=True, color=em_color or C_EMPH, title_font=title_font)
        else:
            _set_font(r, sz, bold=bold, color=color, title_font=title_font)
        runs.append(r)
    if not runs:                        # 空字串：維持舊版「一個空 run」的輸出
        r = para.add_run()
        r.text = ""
        _set_font(r, sz, bold=bold, color=color, title_font=title_font)
        runs.append(r)
    return runs


def _est_lines(text, sz_pt, width_in):
    """估算換行行數：CJK 每字寬 ≈ sz pt，拉丁 ≈ 0.52 sz。"""
    text = _plain(text) if text else text
    if not text:
        return 1
    w_pt = 0.0
    for ch in text:
        w_pt += sz_pt * (1.0 if ord(ch) > 0x2E7F else 0.52)
    return max(1, math.ceil(w_pt / (width_in * 72)))


def _fit_bullet_size(bullets, width_in, height_in, start_sz=None, min_sz=None):
    start_sz = SZ["bullet_l0"][0] if start_sz is None else start_sz
    min_sz = SZ["bullet_l0"][1] if min_sz is None else min_sz
    total = 0.0
    for sz in range(start_sz, min_sz - 2, -2):
        total = 0.0
        for b in bullets:
            t = b["text"] if isinstance(b, dict) else str(b)
            lvl = b.get("level", 0) if isinstance(b, dict) else 0
            eff_w = width_in - 0.35 * (lvl + 1)
            s = sz if lvl == 0 else _sub_size(sz)
            lines = _est_lines(t, s, eff_w)
            total += lines * s * 1.32 / 72 + 0.07
        if total <= height_in:
            return sz, total
    return min_sz, total


def write_bullets(slide, bullets, x, y, w, h, start_sz=None):
    """自動決定條列字級：由 start_sz 往下試到內容可容納為止（下限見 SZ["bullet_l0"]）。"""
    start_sz = SZ["bullet_l0"][0] if start_sz is None else start_sz
    sz, used = _fit_bullet_size(bullets, w, h, start_sz=start_sz)
    if sz <= SZ["bullet_l0"][1]:
        n_img = ""
        warn(f"條列內容偏多（{len(bullets)} 條），字級已觸底 {sz}pt{n_img} — "
             f"建議改用 two_col（左文右圖）或拆成兩頁")
    tb = add_textbox(slide, x, y, w, h)
    tf = tb.text_frame
    from pptx.enum.text import MSO_AUTO_SIZE
    try:
        tf.auto_size = MSO_AUTO_SIZE.NONE
    except Exception:
        pass
    first = True
    for b in bullets:
        d = b if isinstance(b, dict) else {"text": str(b)}
        lvl = d.get("level", 0)
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.level = lvl
        para.space_after = Pt(10)
        pPr = para._p.get_or_add_pPr()
        # 縮排規格取自實驗室模板段落設定：文字之前 1.37cm、特別凸排 1.27cm、後段 10pt、單行間距
        pPr.set("marL", str(int((1.37 + 1.27 * lvl) * CM_EMU)))
        pPr.set("indent", str(-int(1.27 * CM_EMU)))
        _mark_bullet(para, d.get("mark"), level=lvl)
        s = sz if lvl == 0 else _sub_size(sz)
        _add_rich(para, d["text"], s, C_EM if d.get("em") else (C_BODY if lvl == 0 else C_MUTED),
                  bold=d.get("bold", False))
    return y + used


CURRENT_SECTION = None   # 章名沿用狀態（同章連續多頁只需第一頁寫 section）


def _title_frame(slide):
    """標題要寫進哪個文字框：官方模板 profile → 模板頁上的標題文字框（清空後沿用其格式）；
    實驗室模板 → layout 的 title placeholder（沒有就補一個文字框）。"""
    if PROFILE:
        shp = _find_shape(slide, PROFILE["content"]["title"])
        if shp is not None:
            _clear_runs(shp.text_frame)
            return shp.text_frame
        warn("profile 的標題文字框在模板頁上找不到，改用後備文字框")
        return add_textbox(slide, MARGIN_X, 0.05, SLIDE_W - 2 * MARGIN_X, 0.65).text_frame
    tph = None
    for ph in slide.placeholders:
        if ph.placeholder_format.type == 13 or ph.placeholder_format.idx == 0:
            tph = ph
            break
    if tph is None:
        tph = add_textbox(slide, 0, TITLE_TOP, SLIDE_W, 0.7)
    tf = tph.text_frame
    tf.word_wrap = True
    return tf


def _set_running_title(slide, text):
    """章 running title：寫入 layout 的 title placeholder（40pt 藍置中）。"""
    tf = _title_frame(slide)
    p = tf.paragraphs[0]
    if not PROFILE:
        p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    start, floor = SZ["running_title"]
    _set_font(run, start if len(text) <= 34 else floor, bold=True,
              color=None if PROFILE else C_TITLE, title_font=not PROFILE)


def _set_two_level_title(slide, section, title):
    """v2.11 雙層標題（F8，ECCE 2026）：同一行「章名 32pt small caps＋頁名 16pt 粗體 navy」。
    比三層標題省下一整行高度，聽眾仍知道自己在哪一章。"""
    tf = _title_frame(slide)
    tf.word_wrap = False
    p = tf.paragraphs[0]
    # 官方模板（ECCE 等）標題框本來就靠左；實驗室模板的標題框橫跨全寬、左上角有校徽，靠左會壓到
    p.alignment = PP_ALIGN.LEFT if PROFILE else PP_ALIGN.CENTER
    r1 = p.add_run()
    r1.text = section + "    "
    _set_font(r1, 32, bold=False, color=None if PROFILE else C_TITLE, title_font=False)
    r1._r.get_or_add_rPr().set("cap", "small")
    if title:
        r2 = p.add_run()
        r2.text = title
        _set_font(r2, 16, bold=True, color=C_HEAD, title_font=False)
        r2._r.get_or_add_rPr().set("cap", "small")
        if _disp_len(section) * 32 / 16 + _disp_len(title) > 62:
            warn(f"雙層標題偏長（{section}｜{title}）— 可能壓到模板右上角的 logo，請縮短頁名")


def add_title(slide, title, subtitle=None, section=None, as_running=False,
              set_section=False):
    """標題區。

    v2.8 起支援三層標題，但**只在 plan 提供 section 欄位時啟用**：

      有 section →  章 running title（40pt 藍置中，母片 placeholder）
                    頁大標（36pt bold navy 靠左，前置 Wingdings 箭頭）
                    頁副標（16pt 灰靠左，選填）

      無 section →  完全維持 v2.6 行為（title 進 placeholder 當章名、subtitle 為
                    磚紅置中 Part 標記）。既有 plan 因此不需要改一個字即可重建。

    回傳內容區起點 y（吋）。
    """
    global CURRENT_SECTION
    if section:
        CURRENT_SECTION = section
    if set_section:
        CURRENT_SECTION = title
    if as_running or (not section and CURRENT_SECTION is None):
        # ── v2.6 相容路徑 ──
        _set_running_title(slide, title)
        if subtitle:
            stb = add_textbox(slide, 0.3, SUB_TOP, SLIDE_W - 0.6, 0.5)
            sp = stb.text_frame.paragraphs[0]
            sp.alignment = PP_ALIGN.CENTER
            r = sp.add_run()
            r.text = subtitle
            _set_font(r, 22 if len(subtitle) <= 52 else 18, bold=True,
                      color=C_SUB, title_font=True)
            return BODY_TOP_SUB
        return BODY_TOP_PLAIN

    if TITLE_STYLE == "two-level":
        _set_two_level_title(slide, CURRENT_SECTION, title)
        y = BODY_TOP_PLAIN
        if subtitle:
            ssz = SZ["page_sub"][0]
            stb = add_textbox(slide, MARGIN_X, y, SLIDE_W - 2 * MARGIN_X, 0.34)
            sp = stb.text_frame.paragraphs[0]
            _no_bullet(sp)
            r = sp.add_run()
            r.text = subtitle
            _set_font(r, ssz, bold=False, color=C_MUTED)
            y += ssz * 1.5 / 72.0
        return y + 0.05

    # ── v2.8 三層路徑 ──
    _set_running_title(slide, CURRENT_SECTION)
    y = BODY_TOP_PLAIN - 0.02
    if title:
        start, floor = SZ["page_head"]
        hsz = start if _disp_len(title) <= 20 else floor
        if _disp_len(title) > 26:
            warn(f"頁大標偏長（{title}）— 建議把後段移到 subtitle")
        htb = add_textbox(slide, MARGIN_X + 0.05, y, SLIDE_W - 2 * MARGIN_X - 0.1, 0.62)
        hp = htb.text_frame.paragraphs[0]
        hp.alignment = PP_ALIGN.LEFT
        ch, fo = _l0_bullet()
        _bullet_char(hp, ch, color=C_HEAD, font=fo, size_pct=0.85)
        pPr = hp._p.get_or_add_pPr()
        pPr.set("marL", str(int(0.95 * CM_EMU)))
        pPr.set("indent", str(-int(0.95 * CM_EMU)))
        r = hp.add_run()
        r.text = title
        _set_font(r, hsz, bold=True, color=C_HEAD, title_font=True)
        y += hsz * 1.42 / 72.0
    if subtitle:
        ssz = SZ["page_sub"][0]
        stb = add_textbox(slide, MARGIN_X + 0.42, y, SLIDE_W - 2 * MARGIN_X - 0.5, 0.34)
        sp = stb.text_frame.paragraphs[0]
        sp.alignment = PP_ALIGN.LEFT
        _no_bullet(sp)
        r = sp.add_run()
        r.text = subtitle
        _set_font(r, ssz, bold=False, color=C_MUTED)
        y += ssz * 1.5 / 72.0
    return y + 0.10


TAKEAWAY_H2 = 0.85   # v2.11：兩行結論橫條的高度（ECCE 2026 實測，16pt 兩行＋上下留白）


def _takeaway_lines(text):
    """v2.11 結論橫條行數估算：重點片語以 +4pt 計寬。"""
    start = SZ["takeaway"][0]
    w = SLIDE_W - 2 * MARGIN_X - 0.4
    plain = ARROW_RIGHT + " " + _plain(text)
    em_chars = sum(len(seg) for i, seg in enumerate(str(text).split(EMPH_MARK)) if i % 2)
    pad = em_chars * 0.52 * 4 / start   # 重點字放大造成的額外寬度，折算成字元數
    return _est_lines(plain + "x" * math.ceil(pad), start, w)


def _takeaway_h(text):
    if VISUAL != "v2.11":
        return TAKEAWAY_H
    return TAKEAWAY_H if _takeaway_lines(text) == 1 else TAKEAWAY_H2


def _takeaway_reserve(d):
    """內容區底部要讓給結論橫條的高度（含 0.15in 間距）；沒有 takeaway 回 0。"""
    return _takeaway_h(d["takeaway"]) + 0.15 if d.get("takeaway") else 0


def add_takeaway(slide, text):
    th = _takeaway_h(text)
    y = BODY_BOTTOM - th
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Emu(int(MARGIN_X * EMU_IN)), Emu(int(y * EMU_IN)),
                                 Emu(int((SLIDE_W - 2 * MARGIN_X) * EMU_IN)),
                                 Emu(int(th * EMU_IN)))
    shp.adjustments[0] = 0.18
    shp.fill.solid()
    shp.fill.fore_color.rgb = C_TAKEAWAY_BG
    shp.line.color.rgb = C_TAKEAWAY_LN
    shp.line.width = Pt(1)
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(int(0.18 * EMU_IN))
    tf.margin_right = Emu(int(0.15 * EMU_IN))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    # v2.8：前綴符號由 U+25B6（有 emoji 呈現變體，Windows 可能渲染成彩色）改為 U+25BA
    # （無 emoji 變體）；箭頭用橙、文字用 navy——橙在 #FBEFD8 底上對比僅 1.98:1 不可作
    # 文字色，navy 為 12.90:1（舊版綠底綠字 6.29:1，本次為提升而非妥協）。
    start, floor = SZ["takeaway"]
    r0 = p.add_run()
    r0.text = ARROW_RIGHT + " "
    sz = start if _est_lines(ARROW_RIGHT + " " + text, start,
                             SLIDE_W - 2 * MARGIN_X - 0.4) == 1 else floor
    _set_font(r0, sz, bold=True, color=C_TAKEAWAY_MK)
    # v2.11：!!片語!! → 黃字 +4pt（navy 底上 10.41:1）；每條最多 3 個，再多就失去重點
    n_em = _emph_count(text)
    if n_em > 3:
        warn(f"結論橫條有 {n_em} 個重點片語（建議 ≤3）：{_plain(text)[:30]}…")
    if VISUAL == "v2.11" and _takeaway_lines(text) > 2:
        warn(f"結論橫條超過兩行，文字會溢出：{_plain(text)[:30]}… — 請縮短")
    _add_rich(p, text, sz, C_TAKEAWAY_TX, bold=True, em_color=C_TAKEAWAY_EM, em_sz=sz + 4)
    return y


def add_picture_fit(slide, path, x, y, max_w, max_h):
    from PIL import Image
    with Image.open(path) as im:
        pw, ph = im.size
    scale = min(max_w / (pw / 96), max_h / (ph / 96), 4.0)
    w = pw / 96 * scale
    h = ph / 96 * scale
    left = x + (max_w - w) / 2
    top = y + (max_h - h) / 2
    slide.shapes.add_picture(path, Emu(int(left * EMU_IN)), Emu(int(top * EMU_IN)),
                             Emu(int(w * EMU_IN)), Emu(int(h * EMU_IN)))
    return left, top, w, h


def add_caption(slide, text, x, y, w, sz=None, align=PP_ALIGN.CENTER, h=None):
    """圖說／註腳／來源等輔助文字。v2.8 起預設字級取自 SZ["caption"]（13pt）而非
    正文下限 18pt——輔助資訊刻意壓低正是視覺層次的來源（參考簡報實測字級譜）。

    v2.9：框高預設改為依字級推算（原本固定 0.35in）。固定值在 13pt 時比行進距離
    （0.31in）還高，導致圖說框與其下方的來源框宣告座標重疊——`layout_lint.py` 上線
    後第一次執行就抓到這一點。渲染上因文字靠上對齊而看不出來，但宣告幾何重疊是隱患：
    只要之後有人把文字框改成垂直置中或加底色，就會變成可見的錯位。
    """
    sz = SZ["caption"][0] if sz is None else sz
    h = (sz * 1.5 / 72.0 + 0.04) if h is None else h
    tb = add_textbox(slide, x, y, w, h)
    p = tb.text_frame.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    _set_font(r, sz, bold=False, color=C_MUTED)


def add_source(slide, text, x, y, w, align=PP_ALIGN.CENTER):
    """圖片來源標註（v2.8 新增）。學術誠信要求：取自網路或文獻的圖必須標示出處。"""
    prefix = "來源：" if LANG == "zh-TW" else "Source: "
    add_caption(slide, prefix + text, x, y, w, sz=SZ["source"][0], align=align, h=0.28)


def _apply_visual(mode):
    """meta.visual 把外觀鎖回舊版常數（已交付簡報要小改一頁重出的情境）：
      "v2.8"（含 v2.9／v2.10 產出）：結論橫條 20/18pt、公式原始碼小字顯示在投影片上、不寫公式備忘錄。
      "v2.6"：再加上舊配色與 18pt 全域下限。
    v2.7 的四項修復與 v2.8 的 table note 幾何修正不受此開關影響——那些是修 bug。"""
    global VISUAL, SZ, C_HEAD, C_BODY, C_MUTED, C_SUB, C_EM, C_ACTIVE, C_NAVY
    global C_TAKEAWAY_BG, C_TAKEAWAY_LN, C_TAKEAWAY_TX, C_TAKEAWAY_MK, EQ_SHOW_SOURCE
    VISUAL = mode
    if mode == "v2.11":
        EQ_SHOW_SOURCE = False   # F3：LaTeX 原始碼改寫進備忘錄與 equations/*.tex，不留在投影片上
        return
    SZ = dict(SZ)
    SZ["takeaway"] = (20, 18)
    EQ_SHOW_SOURCE = True
    if mode != "v2.6":
        return
    C_HEAD = V26["C_HEAD"]; C_BODY = V26["C_BODY"]; C_MUTED = V26["C_MUTED"]
    C_SUB = V26["C_SUB"]; C_EM = V26["C_EM"]; C_ACTIVE = V26["C_ACTIVE"]
    C_NAVY = V26["C_HEAD"]
    C_TAKEAWAY_BG = V26["C_TAKEAWAY_BG"]; C_TAKEAWAY_LN = V26["C_TAKEAWAY_LN"]
    C_TAKEAWAY_TX = V26["C_TAKEAWAY_TX"]; C_TAKEAWAY_MK = V26["C_TAKEAWAY_MK"]
    SZ = dict(SZ); SZ.update(SZ_V26)


# ── 卡片原語（v2.8）───────────────────────────────────────────
# 幾何全部取自實驗室參考簡報實測值：roundRect adj≈1800、底 #F5F7FA、框 #D6DEE9 0.75pt、
# 內距左右 0.28in／上下 0.16in、卡間距 0.20in、徽章 ellipse 0.40in 徑。
CARD_PAD_X = 0.28
CARD_PAD_Y = 0.16
CARD_GAP = 0.20
CARD_ADJ = 0.018
# 圖片優先的高度分配比例（見 slide_bands）
MIN_FLEX_RATIO = 0.52   # 有圖時，圖片 band 至少取得可用高度的 52%
CARDS_MAX_RATIO = 0.32  # 字卡 band 上限
TEXT_MAX_RATIO = 0.24   # 文字 band 上限
BADGE_D = 0.40
BAND_GAP = 0.20


def _mark_bullet(para, mark, default_color=None, level=0, in_card=False):
    """依 mark 語意套用項目符號；mark 為 None 時用該語境的預設符號。"""
    if mark in MARKS:
        ch, fo, cname, pct = MARKS[mark]
        _bullet_char(para, ch, color=globals()[cname], font=fo, size_pct=pct)
        return globals()[cname]
    if in_card:
        _bullet_char(para, BULLET_CARD, color=C_HEAD, font="Wingdings", size_pct=0.72)
        return None
    if level == 0:
        ch, fo = _l0_bullet()
        _bullet_char(para, ch, color=default_color or C_TITLE, font=fo, size_pct=1.0)
    else:
        _bullet_char(para, BULLET_L1, color=default_color or C_TITLE, font="Arial",
                     size_pct=1.0)
    return None


CARD_ARROW_INDENT = 0.42   # 卡片標題前的箭號縮排（draw_card 的 arrow_indent）


def _card_head_width(card, inner):
    """卡片標題實際可用寬度：有箭號時要扣掉縮排，有徽章時扣掉徽章。
    v2.11 修正：舊版估算沒扣箭號縮排，3 欄卡片的長標題會被低估一行，換行後壓到內文。"""
    if card.get("badge") is not None and card.get("marker", "badge") == "badge":
        return inner - BADGE_D - 0.18
    marker = card.get("marker") or ("arrow" if card.get("head") and not card.get("kpi") else "none")
    return inner - (CARD_ARROW_INDENT if marker == "arrow" else 0.0)


def _fit_kpi(text, ksz, width):
    """KPI 大數字在窄卡片裡縮到一行放得下（下限 20pt），避免數字與單位被拆成兩行。"""
    while ksz > 20 and _est_lines(str(text), ksz, width) > 1:
        ksz -= 2
    return ksz


def _card_body_lines(card, w_in, bsz=None):
    """估算卡片所需高度（吋），供 band 高度分配與字級適配使用。"""
    bsz = SZ["card_body"][0] if bsz is None else bsz
    inner = w_in - 2 * CARD_PAD_X
    h = 0.0
    hsz = max(SZ["card_head"][1], bsz + 2)
    ksz = SZ["kpi"][0] if bsz >= SZ["card_body"][0] else max(
        SZ["kpi"][1], SZ["kpi"][0] - (SZ["card_body"][0] - bsz) * 6)
    if card.get("kpi"):
        ksz = _fit_kpi(card["kpi"], ksz, inner)
        h += ksz * 1.22 / 72.0
        if card.get("head"):
            # kpi 卡的 head 目前假設不換行（kpi 卡標題慣例較短）；一般卡見下方完整處理。
            h += hsz * 1.45 / 72.0
        if card.get("body"):
            csz = SZ["caption"][0]
            h += _est_lines(str(card["body"]), csz, inner) * csz * 1.42 / 72.0
        return h + 2 * CARD_PAD_Y
    if card.get("head"):
        # head 與 body／bullets 一樣可能換行——尤其欄數多（cols=4）時卡片窄，長標題
        # 很容易撐到 2 行。舊版這裡固定只留一行高度（hsz*1.55/72），head 換行時
        # draw_card() 會把 body 畫在同一個 y 起點，兩者疊在一起。改用 _est_lines
        # 依實際欄寬估算行數，並在下方 draw_card() 用同一個算法算出對應的起繪位置，
        # 兩處必須同步——否則會重蹈「估算與繪製用不同公式」的覆轍（見 slide_bands
        # 的 _band_natural_h vs write_bullets 那個 bug）。
        h += _est_lines(str(card["head"]), hsz, _card_head_width(card, inner)) * hsz * 1.28 / 72.0 + 0.10
    if card.get("body"):
        h += _est_lines(str(card["body"]), bsz, inner) * bsz * 1.42 / 72.0
    for b in card.get("bullets", []):
        t = b["text"] if isinstance(b, dict) else str(b)
        h += _est_lines(t, bsz, inner - 0.30) * bsz * 1.42 / 72.0 + 0.06
    return h + 2 * CARD_PAD_Y


def draw_card(slide, card, x, y, w, h, body_sz=None):
    """繪製一張卡片。支援 head／body／bullets／badge／marker／accent／kpi 欄位。"""
    bsz = SZ["card_body"][0] if body_sz is None else body_sz
    hsz = max(SZ["card_head"][1], bsz + 2)
    ksz = SZ["kpi"][0] if bsz >= SZ["card_body"][0] else max(
        SZ["kpi"][1], SZ["kpi"][0] - (SZ["card_body"][0] - bsz) * 6)
    accent = bool(card.get("accent"))
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                                 Emu(int(w * EMU_IN)), Emu(int(h * EMU_IN)))
    try:
        shp.adjustments[0] = CARD_ADJ
    except Exception:
        pass
    shp.fill.solid()
    tint = TINTS.get(card.get("tint")) if card.get("tint") else None
    if card.get("tint") and tint is None:
        warn(f"未知的 tint：{card.get('tint')}（可用：{'／'.join(TINTS)}）")
    if tint and not accent:
        shp.fill.fore_color.rgb, shp.line.color.rgb = tint
    else:
        shp.fill.fore_color.rgb = C_ORANGE_BG if accent else C_CARD_BG
        shp.line.color.rgb = C_ORANGE if accent else C_CARD_LN
    shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    _clear_shape_text(shp)
    n_em = _emph_count(card.get("body", "")) + sum(
        _emph_count(b["text"] if isinstance(b, dict) else b) for b in card.get("bullets", []))
    if n_em > 2:
        warn(f"字卡「{_plain(card.get('head', ''))[:16]}」有 {n_em} 個重點片語（建議每卡 1–2 個）")

    tx = x + CARD_PAD_X
    tw = w - 2 * CARD_PAD_X
    ty = y + CARD_PAD_Y
    arrow_head = False
    arrow_indent = 0.0
    # marker：badge（navy 數字圓徽章）／arrow（與 outline 一致的箭號）／none
    badge = card.get("badge")
    # 預設：有 head 的卡片一律用箭號（與 slide_outline 同一字元同一色），確保目錄與
    # Outline 風格一致；要數字圓徽章必須明確給 badge。kpi 卡不加符號（大數字自己就是重點）。
    marker = card.get("marker") or (
        "badge" if badge is not None
        else ("arrow" if card.get("head") and not card.get("kpi") else "none"))
    if marker == "badge" and badge is not None:
        by = y + CARD_PAD_Y if card.get("head") else y + (h - BADGE_D) / 2
        _draw_badge(slide, str(badge), x + CARD_PAD_X, by)
        tx += BADGE_D + 0.18
        tw -= BADGE_D + 0.18
    elif marker == "arrow":
        # 走真正的項目符號（buChar + buFont），與 slide_outline 完全同一條路徑。
        # 早期版本把箭號當成一般文字 run 並指定 Wingdings 字型，LibreOffice 會直接印出
        # 字面 "Ø"——Wingdings 的私有字元映射只有在 buChar/buFont 這條路徑上才被正確處理。
        arrow_head = True
        arrow_indent = 0.42

    if card.get("kpi"):
        ksz = _fit_kpi(card["kpi"], ksz, tw)
        ktb = add_textbox(slide, tx, ty, tw, ksz * 1.22 / 72.0)
        kp = ktb.text_frame.paragraphs[0]
        kp.alignment = PP_ALIGN.CENTER
        _no_bullet(kp)
        r = kp.add_run(); r.text = str(card["kpi"])
        # 橙底上的大數值一律用 navy（12.90:1）或深橙（5.20:1），絕不用 #E69F00 本色（1.98:1）
        _set_font(r, ksz, bold=True,
                  color=C_ORANGE_DK if accent else C_HEAD, title_font=True)
        ty += ksz * 1.22 / 72.0
        if card.get("head"):
            htb = add_textbox(slide, tx, ty, tw, hsz * 1.45 / 72.0)
            hp = htb.text_frame.paragraphs[0]
            hp.alignment = PP_ALIGN.CENTER
            _no_bullet(hp)
            r = hp.add_run(); r.text = str(card["head"])
            _set_font(r, hsz, bold=True, color=C_HEAD)
            ty += hsz * 1.45 / 72.0
        if card.get("body"):
            add_caption(slide, str(card["body"]), tx, ty, tw,
                        sz=SZ["caption"][0], align=PP_ALIGN.CENTER, h=0.42)
        return

    if card.get("head"):
        # 換行行數用與 _card_body_lines 完全相同的算法（_est_lines，同一個 inner
        # 寬度概念——這裡用 tw，該處用 inner=w_in-2*CARD_PAD_X，兩者定義一致）。
        # 文字框高度與 ty 前進量都依實際行數計算，而非固定假設一行，避免多行
        # 標題把 body／bullets 疊在自己身上。
        head_lines = _est_lines(str(card["head"]), hsz, tw - (arrow_indent if arrow_head else 0.0))
        head_box_h = head_lines * hsz * 1.28 / 72.0 + 0.10
        htb = add_textbox(slide, tx, ty, tw, head_box_h)
        hp = htb.text_frame.paragraphs[0]
        hp.alignment = PP_ALIGN.LEFT
        if arrow_head:
            ch, fo = _l0_bullet()
            _bullet_char(hp, ch, color=C_TITLE, font=fo, size_pct=1.0)
            pPr = hp._p.get_or_add_pPr()
            pPr.set("marL", str(int(arrow_indent * 2.54 * CM_EMU)))
            pPr.set("indent", str(-int(arrow_indent * 2.54 * CM_EMU)))
        else:
            _no_bullet(hp)
        r = hp.add_run(); r.text = str(card["head"])
        _set_font(r, hsz, bold=True, color=C_HEAD)
        ty += head_box_h

    bx = tx + (arrow_indent if arrow_head else 0.0)
    bw = tw - (arrow_indent if arrow_head else 0.0)
    if card.get("body"):
        btb = add_textbox(slide, bx, ty, bw, y + h - CARD_PAD_Y - ty)
        bp = btb.text_frame.paragraphs[0]
        bp.alignment = PP_ALIGN.LEFT
        _no_bullet(bp)
        _add_rich(bp, str(card["body"]), bsz, C_BODY)
    elif card.get("bullets"):
        btb = add_textbox(slide, bx, ty, bw, max(0.2, y + h - CARD_PAD_Y - ty))
        tf = btb.text_frame
        first = True
        for b in card["bullets"]:
            d = b if isinstance(b, dict) else {"text": str(b)}
            para = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            para.space_after = Pt(5)
            pPr = para._p.get_or_add_pPr()
            pPr.set("marL", str(int(0.72 * CM_EMU)))
            pPr.set("indent", str(-int(0.72 * CM_EMU)))
            _mark_bullet(para, d.get("mark"), in_card=True)
            _add_rich(para, d["text"], bsz, C_EM if d.get("em") else C_BODY, bold=d.get("bold", False))


def _draw_badge(slide, text, x, y):
    """navy 實心圓徽章＋白字（目錄與有序清單）。"""
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                 Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                                 Emu(int(BADGE_D * EMU_IN)), Emu(int(BADGE_D * EMU_IN)))
    shp.fill.solid()
    shp.fill.fore_color.rgb = C_HEAD
    shp.line.color.rgb = C_HEAD
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _no_bullet(p)
    r = p.add_run(); r.text = text
    _set_font(r, SZ["badge"][0], bold=True, color=C_WHITE, title_font=True)


def _clear_shape_text(shp):
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.word_wrap = True


EQ_PREAMBLE = "\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage{bm}"

# ── IguanaTex 相容方案（v3：檔案交換法）───────────────────────
# 背景：IguanaTex 判斷「這是不是它產生的公式」是透過 PowerPoint VBA 物件模型的
# Shape.Tags 集合（TryProcessShape 函式檢查 Tags.item("LATEXADDIN")）。這個集合
# 只有在真正的 PowerPoint 應用程式載入 IguanaTex 增益集、執行其 VBA 巨集時才會
# 被實例化——python-pptx 只能寫入語法合法的 OOXML User Defined Tags Part，但無法
# 驗證、也無法保證 PowerPoint 執行期會把它正確映射回 VBA 集合（這一步完全取決於
# PowerPoint 內部反序列化邏輯，屬於檔案生成環境無法閉環驗證的範疇；經兩輪實測
# 確認此路徑不可行）。
#
# 改採「檔案交換法」：
#   1. 每張公式圖正下方附一行等寬字型、灰階小字的 LaTeX 原始碼純文字，可直接反白複製，
#      貼進 IguanaTex「New LaTeX Display」對話框的 Input code 欄位重新生成。
#   2. 同時把每條公式輸出成獨立的完整 .tex 檔案（含 documentclass/preamble），供
#      IguanaTex 官方公開支援的「Read from File」功能直接指向使用，不必手動複製貼上。
#   3. 輸出目錄額外附一份 equations_index.md 對照表（投影片序號、位置、.tex 檔名）。
# 這個方案只依賴「正確寫文字到投影片」與「正確寫檔案到磁碟」，兩者都可在生成端
# 完全驗證，不涉及對 PowerPoint/IguanaTex 內部行為的任何猜測。
EQ_SOURCES = []  # 累積 (slide_no, latex, tex_filename)，供 build() 結束後輸出對照表與 .tex 檔
EQ_SOURCE_SIZE = 11    # 公式原始碼小字標註的字級（中繼資料用途，預設不受 MIN_BODY_SZ=18 正文下限管轄；
                       # 可由 meta.eq_source_size 覆寫，例如工作草稿階段想放大方便複製時設 18）
EQ_SHOW_SOURCE = True  # 是否顯示原始碼小字標註；可由 meta.eq_show_source=false 關閉（正式發表版可能不想露出 LaTeX 原始碼）


def _iguanatex_source(latex: str) -> str:
    """組出可直接被 IguanaTex「Read from File」讀取的完整 .tex 文件內容。"""
    return ("\\documentclass{article}\n"
            f"{EQ_PREAMBLE}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
            f"$\\displaystyle {latex}$\n"
            "\\end{document}\n")


def add_eq_image(slide, latex, x, y, max_w, fontsize=22, dpi=300, tmpdir=None,
                 align="center", slide_no=None, show_source=None):
    """置入公式圖，並在下方附原始碼小字（可複製貼進 IguanaTex）。
    show_source=None 時採用全域設定 EQ_SHOW_SOURCE（可由 meta.eq_show_source 覆寫）。
    回傳總高度（含原始碼行），供呼叫端排版時正確估算已用空間。"""
    if show_source is None:
        show_source = EQ_SHOW_SOURCE
    out = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=tmpdir).name
    info = render_latex(latex, out, fontsize=fontsize, dpi=dpi)
    w_in = info["w_px"] / dpi
    h_in = info["h_px"] / dpi
    if w_in > max_w:
        scale = max_w / w_in
        w_in, h_in = max_w, h_in * scale
        warn(f"公式寬度超過版面已縮小 {scale:.2f}x：{latex[:40]}…")
    left = x + ((max_w - w_in) / 2 if align == "center" else 0)
    pic = slide.shapes.add_picture(out, Emu(int(left * EMU_IN)), Emu(int(y * EMU_IN)),
                                   Emu(int(w_in * EMU_IN)), Emu(int(h_in * EMU_IN)))
    pic._element.nvPicPr.cNvPr.set("name", "LaTeX Equation")
    # 替代文字用 LaTeX 原始碼（原本是暫存檔名，每次建置都不同，且對報讀軟體沒有意義）
    pic._element.nvPicPr.cNvPr.set("descr", latex)
    total_h = h_in

    if show_source:
        src_line = f"LaTeX: {latex}"
        src_sz = EQ_SOURCE_SIZE
        src_h = 0.05 + 0.16 * _est_lines(src_line, src_sz, max_w)
        tb = add_textbox(slide, x, y + h_in + 0.03, max_w, src_h)
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if align == "center" else PP_ALIGN.LEFT
        r = p.add_run()
        r.text = src_line
        f = r.font
        f.size = Pt(src_sz)
        f.italic = True
        f.color.rgb = RGBColor(0x8A, 0x8A, 0x8A)
        f.name = "Consolas"  # python-pptx 已透過此高階屬性正確建立唯一的 <a:latin> 元素，
                             # 不可再手動 append 第二個，否則違反 CT_TextCharacterProperties
                             # schema（<a:latin> 最多只能出現一次），會觸發 PowerPoint 修復對話框
        total_h += src_h + 0.03

    n = len(EQ_SOURCES) + 1
    tex_name = f"eq{n:02d}.tex"
    EQ_SOURCES.append({"slide_no": slide_no, "latex": latex, "tex_filename": tex_name})
    if VISUAL == "v2.11":   # F3：原始碼進備忘錄（簡報者檢視看得到、可複製），不佔投影片版面
        EQ_NOTES.setdefault(slide.slide_id, []).append(f"LaTeX（equations/{tex_name}）：{latex}")
    return total_h


def export_eq_sources(out_dir):
    """建構完成後呼叫：把所有公式輸出成獨立 .tex 檔＋對照表，供 IguanaTex Read from File 使用。"""
    if not EQ_SOURCES:
        return
    eq_dir = os.path.join(out_dir, "equations")
    os.makedirs(eq_dir, exist_ok=True)
    lines = ["# 公式對照表（供 IguanaTex 使用）\n",
             "投影片上每條公式下方已附 LaTeX 原始碼小字，可直接複製貼進 IguanaTex「New LaTeX",
             "Display」對話框。若想改用官方「Read from File」功能，可直接指向下表對應的 .tex 檔。\n",
             "| 投影片 | 公式檔案 | LaTeX 原始碼 |", "|---|---|---|"]
    for item in EQ_SOURCES:
        tex_path = os.path.join(eq_dir, item["tex_filename"])
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(_iguanatex_source(item["latex"]))
        latex_display = item["latex"].replace("|", "\\|")
        lines.append(f"| {item['slide_no']} | `equations/{item['tex_filename']}` | `{latex_display}` |")
    with open(os.path.join(out_dir, "equations_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✔ 已輸出 {len(EQ_SOURCES)} 條公式的 .tex 檔至 {eq_dir}/，對照表見 equations_index.md")




# ── 官方模板 profile（v2.11，P3）──────────────────────────────
# 研討會官方模板常把 logo、線條、頁尾都畫在「範例投影片」上，而不是母片／版面配置。
# 這種模板無法用 add_slide(layout) 建頁，只能複製範例頁再填內容。profile 用 JSON 描述
# 「哪一張範例頁擔任哪個角色、上面哪個文字框是標題／頁尾、哪些範例文字要刪」，
# 取代 ECCE 2026 build.py 裡寫死的文字比對與座標（見 references/template-profiles.md）。
PROFILE_SRC = {}     # role -> 範例投影片（複製來源）
PROFILE_ORIG_PARTS = []   # 模板原有的全部投影片 part（建置結束後刪除）
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _find_shape(slide, spec):
    """依 {"text": 開頭文字} 或 {"name": 形狀名稱} 找形狀（含群組內）。"""
    want_text = (spec.get("text") or "").strip().lower()
    want_name = spec.get("name")

    def walk(shapes):
        for sh in shapes:
            yield sh
            if sh.shape_type == 6:
                yield from walk(sh.shapes)

    for sh in walk(slide.shapes):
        if want_name and sh.name == want_name:
            return sh
        if want_text and sh.has_text_frame and \
                sh.text_frame.text.strip().lower().startswith(want_text):
            return sh
    return None


def _clear_runs(tf):
    """清空文字但保留第一段的段落格式（對齊、縮排、lstStyle 都留著）。"""
    ps = tf.paragraphs
    for p in ps[1:]:
        p._p.getparent().remove(p._p)
    p0 = tf.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    for br in p0._p.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}br"):
        p0._p.remove(br)


def _set_shape_lines(shape, lines):
    """把文字換成多行，每行沿用原本第一個 run 的字型格式（官方模板的字級與顏色不動）。"""
    tf = shape.text_frame
    # 以「字最多的 run」當格式樣板：範例文字常以上標編號開頭（"¹ Author Affiliation"），
    # 拿第一個 run 會把整段變成上標小字（ECCE 2026 D20 的手修項目之一）
    runs = [r for p in tf.paragraphs for r in p.runs]
    tmpl_r = copy.deepcopy(max(runs, key=lambda r: len(r.text))._r) if runs else None
    if tmpl_r is not None:
        rpr = tmpl_r.find("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
        if rpr is not None and rpr.get("baseline"):
            del rpr.attrib["baseline"]
    _clear_runs(tf)
    p0 = tf.paragraphs[0]._p
    for i, line in enumerate(lines):
        p = p0 if i == 0 else copy.deepcopy(p0)
        if i:
            for r in p.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}r"):
                p.remove(r)
            p0.getparent().append(p)
        r = copy.deepcopy(tmpl_r) if tmpl_r is not None else None
        if r is None:
            tf.paragraphs[-1].add_run().text = line
            continue
        r.find("{http://schemas.openxmlformats.org/drawingml/2006/main}t").text = line
        end = p.find("{http://schemas.openxmlformats.org/drawingml/2006/main}endParaRPr")
        if end is not None:
            end.addprevious(r)
        else:
            p.append(r)


def clone_slide(prs, src):
    """複製一張範例投影片（形狀＋圖片等關聯），回傳新投影片。"""
    s = prs.slides.add_slide(src.slide_layout)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    rid_map = {}
    for el in src.shapes._spTree.iterchildren():
        tag = el.tag.split("}")[-1]
        if tag in ("nvGrpSpPr", "grpSpPr"):
            continue
        new_el = copy.deepcopy(el)
        for node in new_el.iter():
            for attr in ("embed", "link", "id"):
                key = f"{{{R_NS}}}{attr}"
                old = node.get(key)
                if not old:
                    continue
                if old not in rid_map:
                    rel = src.part.rels[old]
                    if rel.is_external:
                        rid_map[old] = s.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
                    else:
                        rid_map[old] = s.part.relate_to(rel.target_part, rel.reltype)
                node.set(key, rid_map[old])
        s.shapes._spTree.append(new_el)
    return s


def new_slide(prs, role):
    """建一張新頁：實驗室模板走 layout；官方模板 profile 走複製範例頁＋清理。"""
    if not PROFILE:
        return prs.slides.add_slide(prs.slide_layouts[1 if role == "content" else 0])
    s = clone_slide(prs, PROFILE_SRC[role])
    spec = PROFILE.get(role, {})
    for rm in spec.get("remove", []):
        while True:
            shp = _find_shape(s, rm)
            if shp is None:
                break
            shp._element.getparent().remove(shp._element)
    foot = spec.get("footer")
    if foot:
        shp = _find_shape(s, foot["match"])
        if shp is not None and PROFILE_FOOTER:
            _set_shape_lines(shp, [PROFILE_FOOTER])
            _apply_box(shp, foot)
            if foot.get("size"):
                for p in shp.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(float(foot["size"]))
            shp.text_frame.word_wrap = True
    return s


PROFILE_FOOTER = None   # 由 meta.footer 或 profile footer.format 組出


def load_profile(path, prs, meta):
    """讀 profile、套用版面常數、記下範例頁。回傳 dict。"""
    global PROFILE, MARGIN_X, BODY_TOP_PLAIN, BODY_TOP_SUB, BODY_BOTTOM, CONTENT_R
    global TITLE_STYLE, PROFILE_FOOTER
    with open(path, encoding="utf-8") as f:
        prof = json.load(f)
    slides = list(prs.slides)
    PROFILE_ORIG_PARTS[:] = [s.part for s in slides]   # 全部範例頁（含沒指定角色的）建置完都要刪
    for role, idx in prof["slides"].items():
        if not 1 <= idx <= len(slides):
            raise SystemExit(f"✘ profile 的 {role} 指向第 {idx} 張，但模板只有 {len(slides)} 張")
        PROFILE_SRC[role] = slides[idx - 1]
    body = prof.get("body", {})
    MARGIN_X = float(body.get("margin_x", MARGIN_X))
    CONTENT_R = SLIDE_W - MARGIN_X
    BODY_TOP_PLAIN = float(body.get("top", BODY_TOP_PLAIN))
    BODY_TOP_SUB = BODY_TOP_PLAIN + 0.44
    BODY_BOTTOM = float(body.get("bottom", BODY_BOTTOM))
    TITLE_STYLE = meta.get("title_style", prof.get("title_style", TITLE_STYLE))
    fmt = (prof.get("content", {}).get("footer") or {}).get("format")
    if meta.get("footer"):
        PROFILE_FOOTER = meta["footer"]
    elif fmt:
        try:
            PROFILE_FOOTER = fmt.format(**meta)
        except KeyError as e:
            warn(f"profile 頁尾格式需要 meta.{e.args[0]}，未提供——頁尾維持模板原文")
    PROFILE = prof
    return prof


def _finish_profile(prs):
    """刪除範例頁、加頁碼。"""
    src_parts = list(PROFILE_ORIG_PARTS)
    keep = [s for s in prs.slides if s.part not in src_parts]
    lst = prs.slides._sldIdLst
    for sld in list(lst):
        rid = sld.get(f"{{{R_NS}}}id")
        if prs.part.related_part(rid) in src_parts:
            prs.part.drop_rel(rid)
            lst.remove(sld)
    pn = PROFILE.get("page_number")
    if pn:
        for i, s in enumerate(keep, 1):
            tb = add_textbox(s, pn["x"], pn["y"], pn.get("w", 0.5), pn.get("h", 0.35))
            p = tb.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            r = p.add_run()
            r.text = str(i)
            _set_font(r, pn.get("size", 12), color=C_MUTED)


def slide_cover_profile(prs, d):
    s = new_slide(prs, "cover")
    fields = PROFILE.get("cover", {}).get("fields", {})
    values = {
        "title": d.get("title_en") or d.get("title_zh"),
        "authors": d.get("authors") or d.get("presenter"),
        "affiliation": d.get("affiliation"),
        "date": d.get("date"),
    }
    for key, spec in fields.items():
        shp = _find_shape(s, spec)
        if shp is None:
            warn(f"profile 封面欄位 {key} 在模板上找不到")
            continue
        val = values.get(key)
        if not val:
            warn(f"封面欄位 {key} 沒有內容——模板範例文字已移除")
            shp._element.getparent().remove(shp._element)
            continue
        lines = val if isinstance(val, list) else str(val).split("\n")
        _set_shape_lines(shp, lines)
        _apply_box(shp, spec)
        if spec.get("size"):
            _fit_shape_text(shp, lines, float(spec["size"]), int(spec.get("max_lines", 2)))
    return s


def _apply_box(shp, spec):
    """profile 欄位可指定 box: [x, y, w, h]（吋）重新定位；模板原位置放不下長標題時用。"""
    box = spec.get("box")
    if box:
        shp.left, shp.top, shp.width, shp.height = (Emu(int(v * EMU_IN)) for v in box)


def _fit_shape_text(shp, lines, start, max_lines):
    """從 start 往下縮字級，直到最長的一行在框寬內不超過 max_lines 行（下限 18pt）。"""
    w = shp.width / EMU_IN - 0.2
    sz = start
    while sz > 18 and max(_est_lines(t, sz, w) for t in lines) > max_lines:
        sz -= 2
    from pptx.enum.text import MSO_AUTO_SIZE
    shp.text_frame.auto_size = MSO_AUTO_SIZE.NONE   # 模板若設了「壓縮文字以配合」，指定字級會被再縮一次
    for p in shp.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(sz)


def slide_closing_profile(prs, d):
    s = new_slide(prs, "closing")
    spec = PROFILE.get("closing", {}).get("text")
    if spec and d.get("text"):
        shp = _find_shape(s, spec)
        if shp is not None:
            _set_shape_lines(shp, [d["text"]])
    return s


# ── 各版型 ───────────────────────────────────────────────────
def slide_cover(prs, d):
    if PROFILE:
        return slide_cover_profile(prs, d)
    s = prs.slides.add_slide(prs.slide_layouts[0])
    ph13 = ph14 = None
    for ph in s.placeholders:
        if ph.placeholder_format.idx == 13:
            ph13 = ph
        elif ph.placeholder_format.idx == 14:
            ph14 = ph
    tf = ph13.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    # v2.7：換行估算改用 ph13 的實際寬度（新模板由 8.54in 加寬為 12.01in），
    # 原本寫死 8.4in 會在新模板上高估行數、無謂縮小標題字級。
    title_w = ph13.width / EMU_IN - 0.2
    lines = [(d.get("title_en"), 40, True), (d.get("title_zh"), 30, True)]
    first = True
    for text, sz, bold in lines:
        if not text:
            continue
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.CENTER
        _no_bullet(p)
        r = p.add_run()
        r.text = text
        if _est_lines(text, sz, title_w) > 2:
            sz -= 6
        _set_font(r, sz, bold=bold, color=C_TITLE, title_font=True)
    tf2 = ph14.text_frame
    tf2.word_wrap = True
    info_lines = []
    who = d.get("presenter", "")
    if d.get("advisor"):
        who = f"{L('presenter')}{who}{L('sep')}{L('advisor')}{d['advisor']}" if who else f"{L('advisor')}{d['advisor']}"
    elif who:
        who = f"{L('presenter')}{who}"
    if who:
        info_lines.append((who, 22, True))
    for extra in d.get("extra_lines", ["CPET – Center for Power Electronics Technology",
                                       "National Taipei University of Technology"]):
        info_lines.append((extra, MIN_BODY_SZ, False))
    if d.get("date"):
        info_lines.append((d["date"], MIN_BODY_SZ, False))
    # v2.7：ph14 改為「底端錨定」——原本沿用 placeholder 的固定 top/height，資訊行數
    # 一多（報告人＋CPET＋NTUT＋日期共 4 行）末行就會壓到母片底線（7.25in）之外被遮。
    # 改為先依實際行數估高，再把方框底端固定在底線上方 0.2in，文字向下貼齊：行數不論
    # 多寡，末行落點都一致，且永遠不會溢出。
    est_h = sum(sz * 1.40 / 72.0 for _t, sz, _b in info_lines) + 0.12
    est_h = max(est_h, 0.60)
    top14 = max(COVER_INFO_TOP_MIN, COVER_INFO_BOTTOM - est_h)
    # 注意：placeholder 的 left/width 原本是「向 layout 繼承」而非寫在 slide 上；一旦
    # 設定 top/height，python-pptx 會在 slide 端建立 <a:xfrm>，未指定的 off.x／ext.cx
    # 即固定為 0（實測：資訊區塊被推到投影片左緣外、文字左半被裁掉）。因此必須先把繼承
    # 到的 left/width 讀出來，再連同 top/height 四個值一次寫回。
    left14, width14 = ph14.left, ph14.width
    ph14.left, ph14.width = left14, width14
    ph14.top = Emu(int(top14 * EMU_IN))
    ph14.height = Emu(int((COVER_INFO_BOTTOM - top14) * EMU_IN))
    tf2.vertical_anchor = MSO_ANCHOR.BOTTOM
    first = True
    for text, sz, bold in info_lines:
        p = tf2.paragraphs[0] if first else tf2.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.CENTER
        _no_bullet(p)
        r = p.add_run()
        r.text = text
        _set_font(r, sz, bold=bold, color=C_BLACK)
    return s


def slide_outline(prs, d):
    """Outline 頁：依範例簡報規格 — Times New Roman 全粗體，
    奇數項黑色、偶數項藍色 #0000FF 交替；em:true 可強制藍色。"""
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    add_title(s, d.get("title", "Outline"), as_running=True)
    items = d.get("items", [])
    tb = add_textbox(s, 1.2, 1.5, SLIDE_W - 2.4, BODY_BOTTOM - 1.6)
    tf = tb.text_frame
    first = True
    for i, it in enumerate(items):
        dd = it if isinstance(it, dict) else {"text": str(it)}
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.space_after = Pt(10)
        pPr = para._p.get_or_add_pPr()
        pPr.set("marL", str(int(1.37 * CM_EMU)))
        pPr.set("indent", str(-int(1.27 * CM_EMU)))
        ch, fo = _l0_bullet()
        _bullet_char(para, ch, color=C_TITLE, font=fo)
        run = para.add_run()
        run.text = dd["text"]
        blue = dd.get("em", i % 2 == 1)   # 預設交替：第 1 項黑、第 2 項藍…
        _set_font(run, 28, bold=True,
                  color=C_TITLE if blue else C_BLACK, title_font=True)
    return s


def slide_section(prs, d):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    add_title(s, d.get("title", ""), as_running=True, set_section=True)
    parts = d.get("parts", [])
    active = d.get("active", -1)
    lead = d.get("lead")
    y = 1.9
    if lead:
        tb = add_textbox(s, 1.0, 1.45, SLIDE_W - 2.0, 0.5)
        p = tb.text_frame.paragraphs[0]
        ch, fo = _l0_bullet()
        _bullet_char(p, ch, color=C_TITLE, font=fo)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(1.37 * CM_EMU)))
        pPr.set("indent", str(-int(1.27 * CM_EMU)))
        r = p.add_run()
        r.text = lead
        _set_font(r, 26, bold=True, color=C_BODY)
        y = 2.35
    tb = add_textbox(s, 1.6, y, SLIDE_W - 3.2, BODY_BOTTOM - y)
    tf = tb.text_frame
    first = True
    for i, part in enumerate(parts):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(14)
        _bullet_char(p, "▪")
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(1.37 * CM_EMU)))
        pPr.set("indent", str(-int(1.27 * CM_EMU)))
        r = p.add_run()
        r.text = part
        if i == active:
            _set_font(r, 26, bold=True, color=C_ACTIVE)
        else:
            _set_font(r, 26, bold=False, color=C_GRAY)
    return s


def slide_bullets(prs, d):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    write_bullets(s, d.get("bullets", []), MARGIN_X + 0.1, top + 0.1,
                  SLIDE_W - 2 * MARGIN_X - 0.2, bottom - top - 0.2,
                  start_sz=d.get("size", 24))
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s


def slide_equation(prs, d, tmpdir, slide_no=None):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    y = top + 0.08
    if d.get("intro"):
        y = write_bullets(s, [{"text": d["intro"], "bold": True}],
                          MARGIN_X + 0.1, y, SLIDE_W - 2 * MARGIN_X - 0.2, 0.9, start_sz=22) + 0.12
    blocks = d.get("blocks", [])
    n = len(blocks)
    avail = bottom - y
    fs = 22 if n <= 2 else (19 if n == 3 else 17)
    for blk in blocks:
        h = add_eq_image(s, blk["latex"], MARGIN_X + 0.3, y,
                         SLIDE_W - 2 * MARGIN_X - 0.6, fontsize=fs, tmpdir=tmpdir,
                         slide_no=slide_no)
        y += h + 0.08
        if blk.get("note"):
            tb = add_textbox(s, MARGIN_X + 0.55, y, SLIDE_W - 2 * MARGIN_X - 1.1, 0.6)
            p = tb.text_frame.paragraphs[0]
            r1 = p.add_run()
            note_sz = max(MIN_BODY_SZ, 20 if n <= 2 else 18)
            r1.text = L("note")
            _set_font(r1, note_sz, bold=True, color=C_HEAD)
            r2 = p.add_run()
            r2.text = blk["note"]
            _set_font(r2, note_sz, bold=False, color=C_MUTED)
            y += 0.24 * _est_lines(L("note") + blk["note"], note_sz, SLIDE_W - 2 * MARGIN_X - 1.1) + 0.14
        else:
            y += 0.1
        if y > bottom:
            warn(f"公式頁內容超出版面（{d.get('title','')}）— 建議拆頁")
            break
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s


def slide_figure(prs, d, base_dir):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    y = top + 0.05
    if d.get("bullets"):
        y = write_bullets(s, d["bullets"], MARGIN_X + 0.1, y,
                          SLIDE_W - 2 * MARGIN_X - 0.2, 1.6, start_sz=20) + 0.1
    imgs = d.get("images", [])
    if not imgs:
        warn(f"figure 頁沒有提供 images（{d.get('title','')}）")
    n = len(imgs)
    cols = 1 if n == 1 else 2
    rows = math.ceil(n / cols) if n else 1
    cap_h = SZ["caption"][0] * 1.5 / 72.0 + 0.04
    src_h = SZ["source"][0] * 1.5 / 72.0 + 0.03
    has_src = any(im.get("source") for im in imgs)
    shared = d.get("source_shared")
    foot_h = (src_h if has_src else 0.0)  # 同 band 內取最大值，避免圖高參差
    share_h = (src_h + 0.02) if shared else 0.0
    cell_w = (SLIDE_W - 2 * MARGIN_X - 0.25 * (cols - 1)) / cols
    cell_h = ((bottom - share_h) - y - 0.25 * (rows - 1)) / rows - cap_h - foot_h
    for i, img in enumerate(imgs):
        c, rrow = i % cols, i // cols
        x0 = MARGIN_X + c * (cell_w + 0.25)
        y0 = y + rrow * (cell_h + cap_h + foot_h + 0.25)
        path = img["path"] if os.path.isabs(img["path"]) else os.path.join(base_dir, img["path"])
        if not os.path.exists(path):
            warn(f"找不到圖檔：{path}")
            continue
        left, topp, w, h = add_picture_fit(s, path, x0, y0, cell_w, cell_h)
        ty = y0 + cell_h + 0.03
        if img.get("caption"):
            add_caption(s, img["caption"], x0, ty, cell_w)
            ty += cap_h
        if img.get("source"):
            add_source(s, img["source"], x0, ty, cell_w)
    if shared:
        add_source(s, shared, MARGIN_X, bottom - share_h + 0.02,
                   SLIDE_W - 2 * MARGIN_X)
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s


def slide_two_col(prs, d, base_dir, tmpdir, slide_no=None):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    col_w = (SLIDE_W - 2 * MARGIN_X - 0.35) / 2
    write_bullets(s, d.get("left_bullets", []), MARGIN_X + 0.05, top + 0.15,
                  col_w, bottom - top - 0.3, start_sz=d.get("size", 24))
    right = d.get("right", {})
    rx = MARGIN_X + col_w + 0.35
    if "image" in right:
        img = right["image"]
        path = img["path"] if os.path.isabs(img["path"]) else os.path.join(base_dir, img["path"])
        if os.path.exists(path):
            cap_h = (SZ["caption"][0] * 1.5 / 72.0 + 0.04) if img.get("caption") else 0.0
            src_h = (SZ["source"][0] * 1.5 / 72.0 + 0.03) if img.get("source") else 0.0
            add_picture_fit(s, path, rx, top + 0.15, col_w,
                            bottom - top - 0.3 - cap_h - src_h)
            ty = bottom - 0.06 - cap_h - src_h
            if img.get("caption"):
                add_caption(s, img["caption"], rx, ty, col_w)
                ty += cap_h
            if img.get("source"):
                add_source(s, img["source"], rx, ty, col_w)
        else:
            warn(f"找不到圖檔：{path}")
    elif "latex" in right:
        h = add_eq_image(s, right["latex"], rx, top + 0.6, col_w, fontsize=18, tmpdir=tmpdir,
                         slide_no=slide_no)
        if right.get("note"):
            tb = add_textbox(s, rx, top + 0.75 + h, col_w, 0.9)
            p = tb.text_frame.paragraphs[0]
            r1 = p.add_run(); r1.text = L("note")
            _set_font(r1, MIN_BODY_SZ, bold=True, color=C_HEAD)
            r2 = p.add_run(); r2.text = right["note"]
            _set_font(r2, MIN_BODY_SZ, color=C_MUTED)
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s



def _disp_len(s):
    """顯示寬度估計：全形字 1、半形 0.5。"""
    return sum(1.0 if ord(c) > 0x2E7F else 0.5 for c in str(s))


def _cell_border(cell, color=None, w=9525):
    """為儲存格四邊加細框線（依 a:tcPr 子元素順序，ln* 必須置於 fill 之前）。"""
    color = color or C_TBL_LN
    tcPr = cell._tc.get_or_add_tcPr()
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for idx, tag in enumerate(("lnL", "lnR", "lnT", "lnB")):
        el = tcPr.find(ns + tag)
        if el is None:
            el = tcPr.makeelement(ns + tag, {})
            tcPr.insert(idx, el)
        el.set("w", str(w)); el.set("cap", "flat")
        for ch in list(el):
            el.remove(ch)
        fill = el.makeelement(ns + "solidFill", {})
        clr = el.makeelement(ns + "srgbClr", {"val": color})
        fill.append(clr); el.append(fill)


def _table_metrics(d, w, room=None):
    """依實際字級與欄寬估算表格的每列高度與總高（吋）。

    提案 A 的根因是「配置高度 ≠ 實際渲染高度」：PowerPoint 的表格列高會依儲存格內容
    自動撐開，而舊版用 `0.42 * nr` 這個與內容無關的常數估高，只要有任何一格文字換行，
    實際渲染就會超出配置範圍、壓到下方元素。v2.8 改為**逐格估算換行行數**取該列最大值，
    並把算出來的列高明確寫回表格，讓配置與渲染一致。

    回傳 (body_sz, [列高...], 總高)。
    """
    cols, rows = d.get("columns", []), d.get("rows", [])
    nr, nc = len(rows) + 1, len(cols)
    if nc == 0:
        return SZ["table"][0], [], 0.0
    cw = w / nc - 0.18          # 扣除儲存格左右內距

    def _at(sz):
        lh = sz * 1.34 / 72.0
        hs = [max(sz * 1.9 / 72.0,
                  max((_est_lines(str(c), sz + 1, cw) for c in cols), default=1)
                  * (sz + 1) * 1.34 / 72.0 + 0.14)]
        for row in rows:
            n = max((_est_lines(str(v), sz, cw) for v in row), default=1)
            hs.append(max(sz * 1.75 / 72.0, n * lh + 0.12))
        return hs

    start = SZ["table"][0] if nr <= 8 else SZ["table"][0] - 2
    floor = SZ["table"][1]
    # 字級適配：**不壓縮列高**。PowerPoint／LibreOffice 會依字級強制最小列高，把 rowHeight
    # 改小並不會讓渲染變矮，只會讓「配置」與「渲染」再度脫鉤——這正是提案 A 的老問題換一
    # 個位置重演（實測：壓縮後 note 仍與最後一列重疊）。唯一真正有效的手段是降字級。
    for sz in range(int(start), int(floor) - 1, -1):
        hs = _at(sz)
        if room is None or sum(hs) <= room:
            return sz, hs, sum(hs)
    hs = _at(floor)
    return floor, hs, sum(hs)


def draw_table(slide, d, x, y, w, h_avail):
    """繪製表格（v2.8 抽出成獨立原語，供 table 頁型與 table band 共用）。

    提案 A 修正（真實 bug）：原本可用空間 `bottom` 只為 takeaway 讓出高度，`note` 完全
    沒被扣除，且 note 的 y 座標是「表格配置高度 th」算出來的——但 PowerPoint 表格列高
    會依內容自動撐開，配置高度 ≠ 實際渲染高度，列數一多就與最後一列文字重疊。實測在
    同一份 51 頁簡報中三張不同表格都踩到，而像素 QA 顯示 100% PASS（它只做色塊統計，
    不做文字框幾何碰撞偵測）。改法：note 比照 takeaway，**先從可用空間扣除、再固定畫
    在扣除後的區域**，不再依賴表格高度推算座標。

    回傳實際佔用高度（吋）。
    """
    cols = d.get("columns", [])
    rows = d.get("rows", [])
    nr, nc = len(rows) + 1, len(cols)
    if nc == 0 or nr <= 1:
        warn(f"表格缺少 columns 或 rows（{d.get('title', '')}）")
        return 0.0
    note = d.get("note")
    note_sz = SZ["source"][0]
    note_h = 0.0
    if note:
        note_h = _est_lines(str(note), note_sz, w) * note_sz * 1.45 / 72.0 + 0.10
    room = h_avail - note_h - 0.06
    body_sz, row_hs, th = _table_metrics(d, w, room=room)
    if th > room + 0.01:
        warn(f"表格在最小字級 {body_sz}pt 下仍需 {th:.2f}in、可用僅 {room:.2f}in"
             f"（{d.get('title', '') or '表格 band'}）— 必須拆頁或減少列數／欄位文字")
    gf = slide.shapes.add_table(nr, nc, Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                                Emu(int(w * EMU_IN)), Emu(int(th * EMU_IN)))
    tbl = gf.table
    # 明確寫回列高，讓「配置」與「渲染」一致（不寫的話 PowerPoint 會平均分配再自動撐開）
    for i, hh in enumerate(row_hs):
        try:
            tbl.rows[i].height = Emu(int(hh * EMU_IN))
        except Exception:
            pass
    # 關閉預設樣式的橫紋與首列強調：配色由下方手動落實（表頭 navy、第一欄淡藍、細框線）
    try:
        tbl.horz_banding = False
        tbl.first_row = False
    except Exception:
        pass
    # 第一欄視為「項目欄」：淡藍底＋粗體（可用 "first_col_item": false 關閉）
    first_col_item = d.get("first_col_item", True) and nc >= 2
    # 欄位對齊：整欄皆為短內容（顯示寬 ≤10）→ 置中，否則靠左；可用 "col_align" 逐欄覆寫
    col_align = d.get("col_align")
    # 整列強調（v2.8）：highlight_rows 內的資料列索引（0 起算）套橙底，用於「本文」列
    hl = set(d.get("highlight_rows", []))

    def _auto_align(j):
        vals = [str(r[j]) for r in rows if j < len(r)]
        return "center" if vals and all(_disp_len(v) <= 10 for v in vals) else "left"

    aligns = [(col_align[j] if col_align and j < len(col_align) else _auto_align(j))
              for j in range(nc)]
    for j, cname in enumerate(cols):
        cell = tbl.cell(0, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        _cell_border(cell)
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = str(cname)
        _set_font(r, body_sz + 1, bold=True, color=C_WHITE)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            _cell_border(cell)
            item_col = first_col_item and j == 0
            cell.fill.solid()
            if i in hl:
                cell.fill.fore_color.rgb = C_ORANGE_BG
            elif item_col:
                cell.fill.fore_color.rgb = C_COL1_BG
            else:
                cell.fill.fore_color.rgb = C_WHITE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if aligns[j] == "center" else PP_ALIGN.LEFT
            r = p.add_run(); r.text = str(val)
            _set_font(r, body_sz, bold=(item_col or i in hl),
                      color=C_BODY if (item_col or i in hl) else C_BLACK)
    used = th
    if note:
        # 固定畫在「已扣除」的區域，不再由 th 推算 → 不可能與表格最後一列重疊
        add_caption(slide, str(note), x, y + th + 0.06, w, sz=note_sz,
                    align=PP_ALIGN.LEFT, h=note_h)
        used += note_h + 0.06
    return used


def slide_table(prs, d):
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    draw_table(s, d, MARGIN_X + 0.2, top + 0.15, SLIDE_W - 2 * MARGIN_X - 0.4,
               bottom - top - 0.25)
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s


# ── bands 頁型（v2.8）─────────────────────────────────────────
def _band_natural_h(band, avail_w):
    """估算 band 的自然高度（吋，以起始／偏好字級計算）。figure band 回傳 None
    代表 flex（吃剩餘空間）。

    這是「偏好」高度，不是「最小可行」高度——text／cards 兩種 kind 在字級允許下探
    （write_bullets 探到 SZ["bullet_l0"][1]、draw_card 探到 SZ["card_body"][1]）
    仍可能裝進更小的空間。分配版面時只用這個數字做初始估算，真正的下限請用
    _band_min_h（見下）。兩者的差距正是 v2.9 之前 bands 頁面重疊 bug 的根源：
    slide_bands() 舊版只知道「偏好高度」，把 band 壓縮到偏好高度以下時，完全不
    知道是否已經低於文字在最小字級下也放不進去的那條線——write_bullets／
    draw_card 兩者都只印警告、不會裁切或撐開文字框，PowerPoint 文字框本身也不
    自動裁切，於是文字就悄悄畫出邊界、疊到下一個 band 上，四層 QA 都測不出來
    （layout_lint 的 §2b 只驗證了表格這一種 kind，見該檔案同一批修正）。
    """
    kind = band.get("kind")
    if kind in ("figure", "lanes"):   # lanes 內含圖片，與 figure 一樣吃剩餘空間
        return None
    if kind == "chevrons":
        return _chevrons_h(band, avail_w)
    if kind == "text":
        bullets = band.get("bullets", [])
        sz = SZ["bullet_l0"][0]
        h = 0.0
        for b in bullets:
            d = b if isinstance(b, dict) else {"text": str(b)}
            lvl = d.get("level", 0)
            ssz = sz if lvl == 0 else _sub_size(sz)
            h += _est_lines(d["text"], ssz, avail_w - 0.35 * (lvl + 1)) * ssz * 1.42 / 72.0 + 0.10
        return h
    if kind == "cards":
        cards = band.get("cards", [])
        cols = min(int(band.get("cols", len(cards)) or 1), 4)
        cw = (avail_w - CARD_GAP * (cols - 1)) / cols
        rows = math.ceil(len(cards) / cols) if cards else 0
        h = 0.0
        for r in range(rows):
            row_cards = cards[r * cols:(r + 1) * cols]
            h += max((_card_body_lines(c, cw) for c in row_cards), default=0.4)
            if r < rows - 1:
                h += CARD_GAP
        return h
    if kind == "table":
        h = _table_metrics(band, avail_w - 0.4)[2]
        if band.get("note"):
            nsz = SZ["source"][0]
            h += _est_lines(str(band["note"]), nsz, avail_w) * nsz * 1.45 / 72.0 + 0.16
        return h
    warn(f"未知的 band kind：{kind} — 已略過")
    return 0.0


def _band_min_h(band, avail_w):
    """估算 band 在「文字已降到最小可讀字級」時仍然需要的高度下限（吋）。

    只對 text／cards 回傳有意義的值；其餘 kind 回傳 None（figure 本身是 flex，
    table 列高不可壓、下限就是 _band_natural_h 的值，呼叫端已個別處理）。

    slide_bands() 把 text／cards band 壓縮到低於這個下限時，代表 write_bullets／
    draw_card 就算把字級探到底也放不下——此時必須改成拆頁警告，而不是把一個
    「連最小字級都裝不下」的高度硬塞給繪製函式，任由文字溢出到下一個 band。
    """
    kind = band.get("kind")
    if kind == "text":
        bullets = band.get("bullets", [])
        min_sz = SZ["bullet_l0"][1]
        h = 0.0
        for b in bullets:
            d = b if isinstance(b, dict) else {"text": str(b)}
            lvl = d.get("level", 0)
            ssz = min_sz if lvl == 0 else _sub_size(min_sz)
            # 與 _fit_bullet_size 使用同一組行高常數（1.32／0.07），而非
            # _band_natural_h 的 1.42／0.10——兩處常數不一致是舊版誤差的一部分，
            # 若這裡沿用 natural_h 的常數，算出的下限會偏高，起不到下限作用。
            h += _est_lines(d["text"], ssz, avail_w - 0.35 * (lvl + 1)) * ssz * 1.32 / 72.0 + 0.07
        return h
    if kind == "cards":
        cards = band.get("cards", [])
        cols = min(int(band.get("cols", len(cards)) or 1), 4)
        cw = (avail_w - CARD_GAP * (cols - 1)) / cols
        rows = math.ceil(len(cards) / cols) if cards else 0
        bsz = SZ["card_body"][1]
        h = 0.0
        for r in range(rows):
            row_cards = cards[r * cols:(r + 1) * cols]
            h += max((_card_body_lines(c, cw, bsz) for c in row_cards), default=0.4)
            if r < rows - 1:
                h += CARD_GAP
        return h
    return None


def _draw_band(slide, band, x, y, w, h, base_dir):
    kind = band.get("kind")
    if kind == "text":
        write_bullets(slide, band.get("bullets", []), x + 0.1, y, w - 0.2, h,
                      start_sz=band.get("size", SZ["bullet_l0"][0]))
    elif kind == "cards":
        cards = band.get("cards", [])
        cols = min(int(band.get("cols", len(cards)) or 1), 4)
        cw = (w - CARD_GAP * (cols - 1)) / cols
        rows = math.ceil(len(cards) / cols) if cards else 0

        def _rows_at(bsz):
            hs = []
            for r in range(rows):
                rc = cards[r * cols:(r + 1) * cols]
                hs.append(max((_card_body_lines(c, cw, bsz) for c in rc), default=0.4))
            return hs

        # 字級適配：當 band 被壓縮（例如同頁有圖片要留空間）時，降卡片內文字級讓內容
        # 真的裝得下，而不是把卡片高度硬壓小——後者只會讓文字溢出卡片邊界。
        room = h - CARD_GAP * max(0, rows - 1)
        bsz = SZ["card_body"][0]
        row_hs = _rows_at(bsz)
        while sum(row_hs) > room and bsz > SZ["card_body"][1]:
            bsz -= 1
            row_hs = _rows_at(bsz)
        if sum(row_hs) > room:
            k = room / sum(row_hs)
            warn(f"字卡內容在最小字級 {bsz}pt 下仍超出配置高度 {1/k:.0%} — 已夾至邊界"
                 f"（避免壓到 takeaway），建議減少卡片文字或拆頁")
            row_hs = [hh * k for hh in row_hs]
        cy = y
        for r in range(rows):
            rh = row_hs[r]
            for c, card in enumerate(cards[r * cols:(r + 1) * cols]):
                draw_card(slide, card, x + c * (cw + CARD_GAP), cy, cw, rh, body_sz=bsz)
            cy += rh + CARD_GAP
    elif kind == "figure":
        imgs = band.get("images", [])
        cols = min(int(band.get("cols", len(imgs)) or 1), 3)
        rows = math.ceil(len(imgs) / cols) if imgs else 0
        shared = band.get("source_shared")
        share_h = SZ["source"][0] * 1.5 / 72.0 + 0.04 if shared else 0.0
        cw = (w - 0.25 * (cols - 1)) / cols
        avail = h - share_h
        # 圖說／來源的高度取「同一 band 內的最大值」而非逐圖各自計算——否則有來源的圖
        # 會比沒來源的矮一截，兩圖上緣對齊、下緣參差（實測目視發現）。
        cap_h = (SZ["caption"][0] * 1.5 / 72.0 + 0.04) if any(
            im.get("caption") for im in imgs) else 0.0
        src_h = (SZ["source"][0] * 1.5 / 72.0 + 0.03) if any(
            im.get("source") for im in imgs) else 0.0
        for i, img in enumerate(imgs):
            ch = avail / rows - 0.20 * (rows - 1) / max(rows, 1)
            cx = x + (i % cols) * (cw + 0.25)
            cy = y + (i // cols) * (ch + 0.20)
            path = img["path"] if os.path.isabs(img["path"]) \
                else os.path.join(base_dir, img["path"])
            if not os.path.exists(path):
                warn(f"找不到圖檔：{path}")
                continue
            add_picture_fit(slide, path, cx, cy, cw, ch - cap_h - src_h)
            ty = cy + ch - cap_h - src_h
            if img.get("caption"):
                add_caption(slide, img["caption"], cx, ty, cw)
                ty += SZ["caption"][0] * 1.5 / 72.0 + 0.02
            if img.get("source"):
                add_source(slide, img["source"], cx, ty, cw)
        if shared:
            add_source(slide, shared, x, y + h - share_h + 0.02, w)
    elif kind == "table":
        draw_table(slide, band, x + 0.2, y, w - 0.4, h)
    elif kind == "chevrons":
        _draw_chevrons(slide, band, x, y, w, h)
    elif kind == "lanes":
        _draw_lanes(slide, band, x, y, w, h, base_dir)


# ── v2.11 新 band：chevrons（流程階段）與 lanes（並列對照流程）────────────
CHEV_H = 0.9          # 箭頭形狀高度（吋）
CHEV_OVERLAP = 0.22   # 相鄰箭頭的重疊量，讓尖端嵌進下一個的凹口
CHEV_BODY_SZ = 14


def _chevrons_h(band, w):
    steps = band.get("steps", [])
    n = max(1, len(steps))
    cw = (w + CHEV_OVERLAP * (n - 1)) / n
    body_lines = max((_est_lines(s.get("body", ""), CHEV_BODY_SZ, cw - 0.5) for s in steps
                      if s.get("body")), default=0)
    return CHEV_H + (0.08 + body_lines * CHEV_BODY_SZ * 1.35 / 72.0 if body_lines else 0)


def _draw_chevrons(slide, band, x, y, w, h):
    """一列 3–5 個階段箭頭（第一個為五邊形），下方各一行說明。accent 指定的階段用橙底。"""
    steps = band.get("steps", [])
    n = len(steps)
    if not n:
        return
    if n > 5:
        warn(f"chevrons 有 {n} 個階段（建議 ≤5），字會太小")
    cw = (w + CHEV_OVERLAP * (n - 1)) / n
    acc = band.get("accent")
    hsz = 16 if n <= 4 else 14
    for i, st in enumerate(steps):
        cx = x + i * (cw - CHEV_OVERLAP)
        shape = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        shp = slide.shapes.add_shape(shape, Emu(int(cx * EMU_IN)), Emu(int(y * EMU_IN)),
                                     Emu(int(cw * EMU_IN)), Emu(int(CHEV_H * EMU_IN)))
        is_acc = acc == i
        shp.fill.solid()
        shp.fill.fore_color.rgb = C_ORANGE if is_acc else C_HEAD
        shp.line.fill.background()
        shp.shadow.inherit = False
        tf = shp.text_frame
        tf.word_wrap = True
        tf.margin_left = Emu(int((0.12 if i == 0 else 0.32) * EMU_IN))
        tf.margin_right = Emu(int(0.28 * EMU_IN))
        tf.margin_top = tf.margin_bottom = Emu(0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _no_bullet(p)
        # 橙底上用 navy 字（白字對比只有 2.25:1），navy 底上用白字
        _add_rich(p, st.get("head", ""), hsz, C_HEAD if is_acc else C_WHITE, bold=True,
                  em_color=C_HEAD if is_acc else C_TAKEAWAY_EM)
        if st.get("body"):
            tb = add_textbox(slide, cx + 0.25, y + CHEV_H + 0.08, cw - 0.5, h - CHEV_H - 0.08)
            bp = tb.text_frame.paragraphs[0]
            bp.alignment = PP_ALIGN.CENTER
            _no_bullet(bp)
            _add_rich(bp, st["body"], CHEV_BODY_SZ, C_BODY)


LANE_LABEL_W = 1.6
LANE_KPI_W = 1.9
LANE_GAP = 0.15


def _lane_label_color(tint_name):
    bg, line = TINTS.get(tint_name, TINTS["blue"])
    # 標籤底用語意色本色；白字只在對比夠時用（橙底改 navy 字）
    return line, (C_HEAD if tint_name == "orange" else C_WHITE)


def _draw_lanes(slide, band, x, y, w, h, base_dir):
    """2 條（最多 3 條）水平泳道：左側標籤＋依序的圖／文字格（以箭頭連接）＋右側 KPI。
    用於「傳統做法 vs 本文做法」同一流程的並列對照（ECCE 2026 #5）。"""
    lanes = band.get("lanes", [])
    n = len(lanes)
    if not n:
        return
    if n > 3:
        warn(f"lanes 有 {n} 條（建議 ≤3）")
    lh = (h - LANE_GAP * (n - 1)) / n
    for li, lane in enumerate(lanes):
        ly = y + li * (lh + LANE_GAP)
        tint = lane.get("tint", "blue" if li == 0 else "orange")
        bg, line = TINTS.get(tint, TINTS["blue"])
        outer = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x * EMU_IN)),
                                       Emu(int(ly * EMU_IN)), Emu(int(w * EMU_IN)),
                                       Emu(int(lh * EMU_IN)))
        outer.adjustments[0] = CARD_ADJ
        outer.fill.solid(); outer.fill.fore_color.rgb = bg
        outer.line.color.rgb = line; outer.line.width = Pt(0.75)
        outer.shadow.inherit = False
        _clear_shape_text(outer)
        lab_bg, lab_fg = _lane_label_color(tint)
        lab = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int((x + 0.1) * EMU_IN)),
                                     Emu(int((ly + 0.1) * EMU_IN)), Emu(int(LANE_LABEL_W * EMU_IN)),
                                     Emu(int((lh - 0.2) * EMU_IN)))
        lab.fill.solid(); lab.fill.fore_color.rgb = lab_bg
        lab.line.fill.background(); lab.shadow.inherit = False
        tf = lab.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Emu(int(0.08 * EMU_IN))
        lines = str(lane.get("label", "")).split("\n")
        for k, t in enumerate(lines):
            p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            _no_bullet(p)
            _add_rich(p, t, 14, lab_fg, bold=True)
        kpi = lane.get("kpi")
        ix = x + 0.1 + LANE_LABEL_W + 0.2
        iw = w - (LANE_LABEL_W + 0.4) - ((LANE_KPI_W + 0.2) if kpi else 0)
        items = lane.get("items", [])
        m = max(1, len(items))
        arrow_w = 0.24
        cw = (iw - arrow_w * (m - 1) - 0.1 * 2 * (m - 1)) / m
        cap_h = SZ["caption"][0] * 1.5 / 72.0 + 0.04
        for k, it in enumerate(items):
            cx = ix + k * (cw + arrow_w + 0.2)
            if it.get("image"):
                path = it["image"] if os.path.isabs(it["image"]) else os.path.join(base_dir, it["image"])
                if os.path.exists(path):
                    add_picture_fit(slide, path, cx, ly + 0.08, cw, lh - 0.16 - (cap_h if it.get("caption") else 0))
                else:
                    warn(f"找不到圖檔：{path}")
            elif it.get("text"):
                tb = add_textbox(slide, cx, ly + 0.15, cw, lh - 0.3 - (cap_h if it.get("caption") else 0))
                tb.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tb.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                _no_bullet(p)
                _add_rich(p, it["text"], 14, C_BODY)
            if it.get("caption"):
                add_caption(slide, it["caption"], cx, ly + lh - 0.06 - cap_h, cw, sz=12)
            if k < len(items) - 1:
                ax = cx + cw + 0.1
                ar = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Emu(int(ax * EMU_IN)),
                                            Emu(int((ly + lh / 2 - 0.1) * EMU_IN)),
                                            Emu(int(arrow_w * EMU_IN)), Emu(int(0.2 * EMU_IN)))
                ar.fill.solid(); ar.fill.fore_color.rgb = C_HEAD
                ar.line.fill.background(); ar.shadow.inherit = False
        if kpi:
            kx = x + w - LANE_KPI_W - 0.1
            card = {"kpi": kpi.get("value"), "body": kpi.get("body"), "accent": tint == "orange"}
            draw_card(slide, card, kx, ly + 0.1, LANE_KPI_W, lh - 0.2)


def slide_bands(prs, d, base_dir):
    """由 1–3 個水平帶垂直堆疊組成的組合式頁型。

    設計要點：
      - band 上限 3 個——這同時是密度閘門（一頁一核心）。
      - text／cards／table 依內容估自然高度；figure 為 flex，吃剩餘空間。
      - 一頁若無 figure band，剩餘空間留在底部不拉伸，這就是結構性留白。
      - 左右分欄不走 bands（band 是垂直堆疊模型），用既有的 two_col 頁型。
    """
    s = new_slide(prs, "content")
    _clear_body_ph(s)
    top = add_title(s, d.get("title", ""), d.get("subtitle"), d.get("section"))
    bottom = BODY_BOTTOM - _takeaway_reserve(d)
    bands = d.get("bands", [])
    if len(bands) > 3:
        warn(f"bands 超過 3 個（{d.get('title','')}）— 僅取前 3 個，建議拆頁")
        bands = bands[:3]
    x, w = MARGIN_X, SLIDE_W - 2 * MARGIN_X
    avail = bottom - top - BAND_GAP * max(0, len(bands) - 1)
    nat = [_band_natural_h(b, w) for b in bands]
    # 每個 band 在「最小可讀字級」下仍然需要的高度——text／cards 有意義的下限，
    # 其餘 kind（含 figure 的 None）維持 None，下面統一以 min_floor[i] is not None
    # 判斷是否要套用下限。這是 v2.9.1 修正：舊版只有「偏好高度」與「比例上限」，
    # 沒有「內容在最小字級下的絕對下限」，導致 band 可以被壓縮到比文字本身還小
    # ——write_bullets／draw_card 隨後把字級探到底仍放不下時只印警告，不裁切、
    # 不撐開文字框，PowerPoint 也不自動裁切，於是文字畫出邊界疊到下一個 band。
    min_floor = [(_band_min_h(b, w) if b.get("kind") in ("text", "cards") else None)
                 for b in bands]
    fixed = sum(v for v in nat if v is not None)
    flex_n = sum(1 for v in nat if v is None)
    if flex_n:
        # 圖片優先：一頁若有圖，圖必須拿到足夠高度才看得出波形與趨勢。先把非 flex 的
        # band 各自壓到上限比例（text 24%、cards 32%、table 不設限——表格列高不可壓），
        # 若加總後 flex 仍拿不到 MIN_FLEX_RATIO，再把可壓的 band 等比縮小補足。
        caps = []
        for b, v, mf in zip(bands, nat, min_floor):
            if v is None:
                caps.append(None)
                continue
            k = b.get("kind")
            if "max_h" in b:
                cap_v = min(v, float(b["max_h"]))
            elif k == "cards":
                cap_v = min(v, avail * CARDS_MAX_RATIO)
            elif k == "text":
                cap_v = min(v, avail * TEXT_MAX_RATIO)
            else:
                cap_v = v
            # 比例上限（TEXT_MAX_RATIO／CARDS_MAX_RATIO）的用意是「圖片優先」，但它是
            # 一個與內容量無關的固定比例——內容少的 band 用不到 24%／32% 也會被這個
            # 比例硬性砍掉，砍到比它自己在最小字級下的下限還小。這只有在真的需要把
            # 空間讓給 figure 時才合理；如果 avail 本來就寬裕（图片早就能拿到遠超過
            # MIN_FLEX_RATIO 的空間），比例上限就不該把文字砍到低於可讀下限。
            # 因此這裡先用 max(cap_v, mf) 兜底，讓「比例上限」只在真正吃緊時才生效，
            # 吃緊與否交給下面 need／avail 的比較統一判斷與示警。
            if mf is not None and cap_v < mf:
                cap_v = mf
            caps.append(cap_v)
        fixed = sum(v for v in caps if v is not None)
        need = avail * MIN_FLEX_RATIO * flex_n
        if avail - fixed < need:
            shrinkable = [i for i, (b, v) in enumerate(zip(bands, caps))
                          if v is not None and b.get("kind") != "table"]
            room_for_fixed = max(0.0, avail - need)
            cur = sum(caps[i] for i in shrinkable)
            other = fixed - cur
            if cur > 0 and room_for_fixed - other > 0:
                k = (room_for_fixed - other) / cur
                for i in shrinkable:
                    caps[i] *= k
                fixed = sum(v for v in caps if v is not None)
            # 下限檢查：等比縮小後，若有 band 被壓到低於它在最小字級下的絕對下限，
            # 代表 write_bullets／draw_card 接下來會悄悄溢出——把它們拉回各自的
            # min_floor（犧牲一些圖片高度也好過看不見的文字重疊），並用更明確的
            # 措辭示警，讓使用者知道這不是「版面略緊」而是「內容量必須減少」。
            over_floor = False
            for i in shrinkable:
                if min_floor[i] is not None and caps[i] < min_floor[i]:
                    caps[i] = min_floor[i]
                    over_floor = True
            if over_floor:
                fixed = sum(v for v in caps if v is not None)
                warn(f"「{d.get('title','')}」的字卡／條列內容在最小字級下仍超出可壓縮"
                     f"範圍，已強制拉回內容下限（圖片區將因此變窄）——這代表內容量必須"
                     f"實際減少或拆頁，而不只是版面略緊，請優先處理此頁")
            else:
                warn(f"為保留圖片可讀高度，字卡／條列區已縮至配置上限"
                     f"（{d.get('title','')}）— 內容過多時建議拆頁")
        flex_h = max(0.8, (avail - fixed) / flex_n)
        heights = [flex_h if v is None else v for v in caps]
    else:
        # 無 flex band：各 band 用自然高度，剩餘空間留在底部（結構性留白）
        if fixed > avail:
            scale = avail / fixed
            warn(f"bands 內容超出版面（{d.get('title','')}）— 各 band 高度已縮至 "
                 f"{scale:.0%}（表格會改以降字級適配，卡片會壓縮內距），建議拆頁")
            heights = [v * scale for v in nat]
        else:
            heights = list(nat)
    y = top
    for band, bh in zip(bands, heights):
        _draw_band(s, band, x, y, w, bh, base_dir)
        y += bh + BAND_GAP
    if d.get("takeaway"):
        add_takeaway(s, d["takeaway"])
    return s


def slide_closing(prs, d):
    """結尾感謝頁：沿用封面 layout（標題投影片），移除其 placeholder 後置中大字
    （母片 header/校訓/頁碼/底線照常保留，與模板 assets/template.pptx 內建的
    致謝頁範例版式一致）。"""
    if PROFILE:
        return slide_closing_profile(prs, d)
    s = prs.slides.add_slide(prs.slide_layouts[0])
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    tb = s.shapes.add_textbox(Emu(int(MARGIN_X * EMU_IN)), Emu(int(2.9 * EMU_IN)),
                              Emu(int((SLIDE_W - 2 * MARGIN_X) * EMU_IN)),
                              Emu(int(1.5 * EMU_IN)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _no_bullet(p)
    r = p.add_run()
    r.text = d.get("text", "Thank You for Your Attention")
    _set_font(r, int(d.get("size", 40)), bold=True, color=C_TITLE, title_font=True)
    return s


def _clear_body_ph(slide):
    """移除 layout 帶進來的空 body placeholder，避免殘留提示框。"""
    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx != 0 and ph.placeholder_format.type != 13:
            ph._element.getparent().remove(ph._element)


def _ensure_closing_slide(prs, plan):
    """每份簡報一律以致謝頁收尾（v2.6 硬規則，不受 plan 是否撰寫 closing 影響）。

    規則：
    - plan 最後一張已是 closing 型 → 視為使用者已自訂收尾文字，不重複加。
    - 否則（包含成果報告型以 Conclusions 收尾、未寫 closing 的情況）→
      自動在簡報末追加一張標準致謝頁，維持模板一致的收尾動作。
    - meta.no_closing_slide: true 時可關閉此自動行為（例外情境，如簡報僅為單一
      章節片段、非完整交付版本）。
    """
    if plan.get("meta", {}).get("no_closing_slide"):
        return
    slides = plan.get("slides", [])
    if slides and slides[-1].get("type") == "closing":
        return
    slide_closing(prs, {})


def _delete_all_slides(prs):
    xml_slides = prs.slides._sldIdLst
    for sld in list(xml_slides):
        rId = sld.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        prs.part.drop_rel(rId)
        xml_slides.remove(sld)


HANDLERS = {}


def _write_notes(slide, lines):
    """寫入備忘錄（v2.11，P3）。plan 的 notes 字串在前，公式原始碼在後。"""
    text = "\n".join(l for l in lines if l is not None)
    if not text.strip():
        return
    slide.notes_slide.notes_text_frame.text = text


def build(plan_path, out_path, template, run_lint=True, profile=None):
    # v2.9：建置前先跑結構驗證。這是刻意做成「預設執行、要主動關掉」而非「另外記得跑」——
    # 缺圖與缺欄位這兩類靜默失敗的共同點是「不報錯、檔案也產得出來」，一個必須靠人記得
    # 執行的 lint 等於沒有 lint。錯誤級問題直接中止建置，不產出半殘的檔案。
    if run_lint:
        try:
            from plan_lint import lint, print_report
            rep = lint(plan_path)
            if rep.errors or rep.warnings:
                print_report(rep, quiet=True)
            if rep.errors:
                raise SystemExit("✘ plan 結構檢查未通過，已中止建置"
                                 "（確認要照舊建置可加 --no-lint）")
        except ImportError:
            warn("找不到 plan_lint.py，已跳過結構檢查")
    global LANG, EQ_PREAMBLE, EQ_SHOW_SOURCE, EQ_SOURCE_SIZE, TITLE_STYLE
    EQ_SOURCES.clear()
    EQ_NOTES.clear()
    global CURRENT_SECTION
    CURRENT_SECTION = None
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    meta = plan.get("meta", {})
    lang = meta.get("language", "zh-TW")
    LANG = lang if lang in LABELS else "zh-TW"
    if meta.get("eq_preamble"):
        EQ_PREAMBLE = meta["eq_preamble"]
    global BULLET_UNICODE, NO_PROOF
    BULLET_UNICODE = bool(meta.get("bullet_unicode", False))
    NO_PROOF = bool(meta.get("no_proof", True))
    _apply_visual(meta.get("visual", "v2.11"))
    # 明確寫在 meta 的設定優先於 visual 的預設（_apply_visual 會重設 EQ_SHOW_SOURCE）
    if "eq_show_source" in meta:
        EQ_SHOW_SOURCE = bool(meta["eq_show_source"])
    if "eq_source_size" in meta:
        EQ_SOURCE_SIZE = int(meta["eq_source_size"])
    TITLE_STYLE = meta.get("title_style", "three-level")
    if "caption_size" in meta:
        SZ["caption"] = (float(meta["caption_size"]), SZ["caption"][1])
    base_dir = os.path.dirname(os.path.abspath(plan_path))
    prs = Presentation(template)
    if profile:
        load_profile(profile, prs, meta)   # 範例頁先留著當複製來源，建置完才刪
    else:
        _delete_all_slides(prs)
    tmpdir = tempfile.mkdtemp(prefix="cpet_eq_")
    all_slides = plan.get("slides", [])
    # v2.11（P3）：backup: true 的頁放到致謝頁之後（Q&A 備用頁），其餘照原順序
    main = [d for d in all_slides if not d.get("backup")]
    backups = [d for d in all_slides if d.get("backup")]
    notes = []   # (slide, plan notes)

    def build_one(d, slide_no):
        t = d.get("type")
        n_before = len(prs.slides)
        try:
            if t == "cover":
                slide_cover(prs, d)
            elif t == "outline":
                slide_outline(prs, d)
            elif t == "section":
                slide_section(prs, d)
            elif t == "bullets":
                slide_bullets(prs, d)
            elif t == "equation":
                slide_equation(prs, d, tmpdir, slide_no=slide_no)
            elif t == "figure":
                slide_figure(prs, d, base_dir)
            elif t == "two_col":
                slide_two_col(prs, d, base_dir, tmpdir, slide_no=slide_no)
            elif t == "table":
                slide_table(prs, d)
            elif t == "bands":
                slide_bands(prs, d, base_dir)
            elif t == "closing":
                slide_closing(prs, d)
            else:
                warn(f"未知的投影片類型：{t}（第 {slide_no} 張）— 已略過")
        except Exception as e:
            warn(f"第 {slide_no} 張（{t}）生成失敗：{e}")
            raise
        if len(prs.slides) > n_before:
            notes.append((prs.slides[len(prs.slides) - 1], d.get("notes")))

    for i, d in enumerate(main):
        build_one(d, i + 1)
    _ensure_closing_slide(prs, {**plan, "slides": main})
    for j, d in enumerate(backups):
        if not d.get("section") and j == 0:
            d = {**d, "section": "Backup"}
        build_one(d, len(main) + 2 + j)
    for s, plan_notes in notes:
        _write_notes(s, [plan_notes] + EQ_NOTES.get(s.slide_id, []))
    if profile:
        _finish_profile(prs)
    prs.save(out_path)
    export_eq_sources(os.path.dirname(os.path.abspath(out_path)))
    print(f"✔ 已產生：{out_path}（{len(prs.slides)} 張）")
    if WARNINGS:
        print(f"共 {len(WARNINGS)} 則警告，請於 QA 時特別檢查上述投影片。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--template",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "assets", "template.pptx"))
    ap.add_argument("--no-lint", action="store_true",
                    help="跳過建置前的 plan 結構檢查（不建議；僅供除錯）")
    ap.add_argument("--profile",
                    help="官方模板描述檔（JSON，見 references/template-profiles.md）；需搭配 --template")
    a = ap.parse_args()
    build(a.plan, a.out, a.template, run_lint=not a.no_lint, profile=a.profile)
