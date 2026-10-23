#!/usr/bin/env python3
"""figprep.py — 簡報素材前處理工具（cpet-figure-prep v1.0）。

處理「既有的點陣圖」讓它能安全放進投影片：去背、裁邊、格式轉換、紅框標註、品質檢查。
**不產生圖**（那是 cpet-infographic-forge 的職責），也**不組裝投影片**（那是
cpet-yslai-pptx 的職責）。

子命令：
    inspect   檢查尺寸／透明度／白邊／置入投影片後的有效解析度
    debg      去背（邊界 flood-fill，保留圖示內部白）＋ autocrop ＋ padding
    convert   EMF／WMF／SVG／PDF → PNG（透過 LibreOffice）
    locate    查詢某個目標在圖上的像素座標（除錯用）
    annotate  依 spec 畫紅框與文字標籤（標籤自動避讓既有內容）
    sheet     產生編號預覽拼接圖——**輸出前的人工確認閘門**
    manifest  登記 PENDING:figprep-鍵值→產出路徑對應表（v1.1 新增，供
              cpet-input-template 回填腳本讀取；人工在 sheet 閘門確認後才登記）

設計原則：本工具的失敗模式全部是「不報錯、圖也產得出來、但結果是錯的」，
因此每個子命令都有自己的守門檢查，且 annotate 一律附帶預覽。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── 配色（與 cpet-yslai-pptx 的 Okabe-Ito 語意色一致）────────────
C_MARK = (213, 94, 0)       # Vermilion #D55E00：標註框與標籤底
C_MARK2 = (0, 114, 178)     # Blue #0072B2：次要標註
C_TEXT = (255, 255, 255)
# 2026-09-20：原本只列 Linux 容器路徑，在 Windows／macOS 上一條都命中不了，
# 於是落到 load_default() 的點陣字型——中文標籤全變方框，而程式只印一行警告
# 就照常輸出，屬於本技能 SKILL.md 開宗明義要擋的「不報錯、圖也產得出來、
# 結果是錯的」那一類靜默失敗。改為三平台路徑並列，且找不到 CJK 字型時中止。
FONT_CANDIDATES = [
    # Linux（Chat／Cowork 容器）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    # Windows（微軟正黑體為 Win 7 以後內建；Noto TC 需另行安裝）
    r"C:\Windows\Fonts\msjhbd.ttc",
    r"C:\Windows\Fonts\msjh.ttc",
    r"C:\Windows\Fonts\NotoSansTC-VF.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]

# 純西文字型：不含 CJK 字符，只在確認本次不需要繪製中文時才可接受。
FONT_CANDIDATES_LATIN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

_CJK_RE = re.compile(
    "[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]"
)


def _font(size, text=None):
    """標籤字型。必須支援 CJK——用預設點陣字型會讓中文標籤變成方框。

    text 有給且不含 CJK 字元時，允許退到純西文字型；含 CJK（或未指定）時，
    找不到 CJK 字型一律中止，不以方框輸出。
    """
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue

    needs_cjk = text is None or bool(_CJK_RE.search(text))
    if not needs_cjk:
        for p in FONT_CANDIDATES_LATIN:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    continue

    _die(
        "找不到可用的 CJK 字型，中文標籤會變成方框，已中止以免產出錯誤的圖。\n"
        "  已嘗試：\n    " + "\n    ".join(FONT_CANDIDATES) + "\n"
        "  請安裝其一：Windows 內建微軟正黑體（msjh.ttc）／Noto Sans TC；\n"
        "  Linux `apt-get install fonts-noto-cjk`；macOS 內建 PingFang。"
    )


def _die(msg, code=1):
    print(f"✘ {msg}", file=sys.stderr)
    sys.exit(code)


# ══════════════════════════════════════════════════════════════
# inspect
# ══════════════════════════════════════════════════════════════
def cmd_inspect(a):
    rows = []
    for p in a.images:
        if not os.path.exists(p):
            _die(f"找不到檔案：{p}")
        im = Image.open(p)
        w, h = im.size
        has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        arr = np.asarray(im.convert("RGB"))
        near_white = (arr >= a.threshold).all(axis=2)
        # 四邊各取 2% 厚度，看白邊佔比
        t = max(1, int(min(w, h) * 0.02))
        edge = np.concatenate([near_white[:t].ravel(), near_white[-t:].ravel(),
                               near_white[:, :t].ravel(), near_white[:, -t:].ravel()])
        edge_white = float(edge.mean())
        dpi = w / a.width_in if a.width_in > 0 else 0
        notes = []
        if edge_white > 0.9 and not has_alpha:
            notes.append("四邊幾乎全白且無透明度 → 建議跑 debg 去背裁邊")
        if dpi and dpi < 110:
            notes.append(f"以 {a.width_in}in 寬置入時有效解析度僅 {dpi:.0f} dpi"
                         f"（投影建議 ≥110、列印 ≥150）→ 放大會糊")
        if w < 600:
            notes.append(f"原圖寬 {w}px 偏小")
        rows.append((os.path.basename(p), f"{w}×{h}", f"{w/h:.2f}",
                     "有" if has_alpha else "無", f"{edge_white:.0%}",
                     f"{dpi:.0f}" if dpi else "—", notes))
    wid = [max(len(str(r[i])) for r in rows + [("檔名", "尺寸", "長寬比", "透明", "白邊", "dpi")])
           for i in range(6)]
    hdr = ("檔名", "尺寸", "長寬比", "透明", "白邊", "dpi")
    print("  ".join(h.ljust(wid[i]) for i, h in enumerate(hdr)))
    print("  ".join("─" * wid[i] for i in range(6)))
    issues = 0
    for r in rows:
        print("  ".join(str(r[i]).ljust(wid[i]) for i in range(6)))
        for n in r[6]:
            print(f"    ⚠ {n}")
            issues += 1
    print()
    print(f"{len(rows)} 張，{issues} 項提醒。" if issues else f"{len(rows)} 張，無提醒。")


# ══════════════════════════════════════════════════════════════
# debg
# ══════════════════════════════════════════════════════════════
def debg_image(im, threshold=238, pad=6, autocrop=True):
    """邊界 flood-fill 去背。

    **關鍵設計：只去除「從邊界連通進來」的近白像素，不做全域白轉透明。**
    外部生圖工具（Gemini／DALL·E 等）輸出的近白底 PNG，圖示內部往往也有白色
    （放大鏡的鏡片、機器人的眼白、流程圖方塊的填色）。全域白轉透明會把這些一起
    挖空、把圖挖爛，而且**不會報錯**——這正是本工具存在的理由之一。

    實作用 PIL 的 floodfill 跑在二值遮罩上（而非直接在彩圖上），可避免
    「填充色恰好與圖中某個顏色相同」的碰撞問題，且是 C 速度。
    """
    im = im.convert("RGBA")
    w, h = im.size
    arr = np.asarray(im.convert("RGB"))
    near = (arr >= threshold).all(axis=2)
    # 外圈補 1px「白」，讓所有邊界白區都連通到 (0,0)
    m = np.zeros((h + 2, w + 2), dtype=np.uint8)
    m[1:-1, 1:-1] = np.where(near, 255, 0)
    m[0, :] = m[-1, :] = m[:, 0] = m[:, -1] = 255
    # 必須用 frombytes 而非 Image.fromarray：後者建立的影像會與 numpy 緩衝區共享記憶體，
    # 而 ImageDraw.floodfill 對它的寫入會被**靜默丟棄**——實測 floodfill 在 0 ms 內返回、
    # 不拋任何例外、遮罩完全沒變，結果就是「去背比例 0%」而圖看起來沒問題。這正是本技能
    # 針對的那類失敗（不報錯、產得出來、但結果是錯的），已列入 references/pitfalls.md。
    mask = Image.frombytes("L", (w + 2, h + 2), m.tobytes())
    ImageDraw.floodfill(mask, (0, 0), 128, thresh=0)
    bg = (np.array(mask)[1:-1, 1:-1] == 128)

    ratio = float(bg.mean())
    out = np.array(im)
    out[..., 3] = np.where(bg, 0, out[..., 3])
    res = Image.fromarray(out, "RGBA")
    if autocrop:
        bbox = res.getbbox()
        if bbox:
            res = res.crop(bbox)
    if pad:
        p = Image.new("RGBA", (res.width + 2 * pad, res.height + 2 * pad), (0, 0, 0, 0))
        p.paste(res, (pad, pad))
        res = p
    return res, ratio


def cmd_debg(a):
    outs = []
    for p in a.images:
        if not os.path.exists(p):
            _die(f"找不到檔案：{p}")
        im = Image.open(p)
        res, ratio = debg_image(im, a.threshold, a.pad, not a.no_crop)
        # 守門：兩種「不報錯但結果錯」的情況
        if ratio > 0.97:
            _die(f"{os.path.basename(p)}：去背比例 {ratio:.0%} 過高，"
                 f"整張圖幾乎會被清空——多半是 threshold({a.threshold}) 太低或圖本身"
                 f"就是淺色。已中止，請調高 --threshold 或確認素材。")
        if ratio < 0.01:
            print(f"⚠ {os.path.basename(p)}：去背比例僅 {ratio:.1%}，"
                  f"邊界可能不是白色（有外框？），本張實質未改變")
        out = a.out if (a.out and len(a.images) == 1) else os.path.join(
            a.outdir or os.path.dirname(p) or ".",
            os.path.splitext(os.path.basename(p))[0] + "_debg.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        res.save(out)
        outs.append(out)
        print(f"✔ {os.path.basename(p)} → {out}  "
              f"（去背 {ratio:.0%}，{im.size[0]}×{im.size[1]} → {res.size[0]}×{res.size[1]}）")
    return outs


# ══════════════════════════════════════════════════════════════
# convert
# ══════════════════════════════════════════════════════════════
def cmd_convert(a):
    for p in a.images:
        if not os.path.exists(p):
            _die(f"找不到檔案：{p}")
        outdir = a.outdir or os.path.dirname(os.path.abspath(p))
        os.makedirs(outdir, exist_ok=True)
        r = subprocess.run(["soffice", "--headless", "--convert-to", "png",
                            os.path.abspath(p), "--outdir", outdir],
                           capture_output=True, text=True, timeout=180)
        exp = os.path.join(outdir, os.path.splitext(os.path.basename(p))[0] + ".png")
        if not os.path.exists(exp):
            _die(f"轉檔失敗：{p}\n{r.stdout}\n{r.stderr}")
        print(f"✔ {os.path.basename(p)} → {exp}  ({Image.open(exp).size})")


# ══════════════════════════════════════════════════════════════
# locate
# ══════════════════════════════════════════════════════════════
def _ocr_langs():
    try:
        import pytesseract
        return set(pytesseract.get_languages())
    except Exception:
        return set()


def locate_text(im, phrase, min_conf=60, lang=None):
    """以文字內容定位（OCR）。回傳 (x0,y0,x1,y1) 或 None。

    語言限制：Cowork 沙箱只裝得到 eng（chi_tra 需要 root，`apt-get` 會被拒）。
    中文介面的截圖請改用 region＋snap 路徑——那條不依賴 OCR。
    """
    import pytesseract
    langs = _ocr_langs()
    if lang is None:
        lang = "chi_tra+eng" if "chi_tra" in langs else "eng"
    if any(ord(c) > 0x2E7F for c in phrase) and "chi_tra" not in langs:
        raise RuntimeError(
            "要以中文字串定位需要 tesseract 的 chi_tra 語言包，本環境未安裝"
            "（Cowork 沙箱無 root 權限，apt-get 會被拒）。\n"
            "  → 在 Claude Code／本機環境：apt-get install -y tesseract-ocr-chi-tra\n"
            "  → 在 Cowork：改用 region 路徑，例如 "
            '{"region": [0.05, 0.10, 0.45, 0.22], "snap": true}')
    d = pytesseract.image_to_data(im, lang=lang, output_type=pytesseract.Output.DICT)
    words = phrase.lower().split()
    toks = [(i, d["text"][i].strip().lower())
            for i in range(len(d["text"])) if d["text"][i].strip()]
    for k in range(len(toks) - len(words) + 1):
        if all(words[m] in toks[k + m][1] for m in range(len(words))):
            idxs = [toks[k + m][0] for m in range(len(words))]
            if min(int(d["conf"][i]) for i in idxs) < min_conf:
                continue
            return (min(d["left"][i] for i in idxs),
                    min(d["top"][i] for i in idxs),
                    max(d["left"][i] + d["width"][i] for i in idxs),
                    max(d["top"][i] + d["height"][i] for i in idxs))
    return None


def snap_region(im, region, threshold=238):
    """把粗略框吸附到框內「實際內容」的邊界。

    不依賴 OCR，純影像處理——對圖示、輸入框、色塊一樣有效，且在任何環境都能跑。
    做法：取框內非背景（非近白）像素的 bbox。若框內全是背景則原樣返回。
    """
    W, H = im.size
    x0, y0, x1, y1 = [int(round(v)) for v in _denorm(region, W, H)]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return (x0, y0, x1, y1)
    sub = np.asarray(im.convert("RGB"))[y0:y1, x0:x1]
    content = ~(sub >= threshold).all(axis=2)
    if not content.any():
        return (x0, y0, x1, y1)
    ys, xs = np.where(content)
    return (x0 + int(xs.min()), y0 + int(ys.min()),
            x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1)


def _denorm(r, W, H):
    """region 支援 0–1 正規化座標與絕對像素兩種寫法，依數值大小自動判斷。"""
    if all(0.0 <= v <= 1.0 for v in r):
        return (r[0] * W, r[1] * H, r[2] * W, r[3] * H)
    return tuple(r)


def resolve_find(im, find, threshold=238):
    """把一個 find 描述解析成像素 bbox。"""
    if "px" in find:
        return tuple(int(v) for v in find["px"])
    if "region" in find:
        if find.get("snap", True):
            return snap_region(im, find["region"], threshold)
        return tuple(int(round(v)) for v in _denorm(find["region"], *im.size))
    if "text" in find:
        b = locate_text(im, find["text"], find.get("min_conf", 60))
        if b is None:
            raise RuntimeError(
                f"OCR 找不到文字 {find['text']!r}。可能是字太小、對比不足或拼字不符；"
                f"改用 region 路徑較穩：{{\"region\": [x0,y0,x1,y1], \"snap\": true}}")
        return b
    raise RuntimeError(f"find 必須含 text／region／px 其中之一，收到：{sorted(find)}")


def cmd_locate(a):
    im = Image.open(a.image).convert("RGB")
    find = {"text": a.text} if a.text else {"region": json.loads(a.region)}
    b = resolve_find(im, find, a.threshold)
    W, H = im.size
    print(f"像素 bbox: {b}")
    print(f"正規化   : [{b[0]/W:.3f}, {b[1]/H:.3f}, {b[2]/W:.3f}, {b[3]/H:.3f}]")


# ══════════════════════════════════════════════════════════════
# annotate
# ══════════════════════════════════════════════════════════════
def _ink_integral(im):
    g = np.asarray(im.convert("L"), dtype=np.float32)
    ink = (g < 200).astype(np.float32)
    return np.pad(ink, ((1, 0), (1, 0))).cumsum(0).cumsum(1)


def _density(integ, W, H, x0, y0, x1, y1):
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, int(x1)), min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return 1e9
    s = (integ[y1, x1] - integ[y0, x1] - integ[y1, x0] + integ[y0, x0])
    return float(s) / ((x1 - x0) * (y1 - y0))


def place_label(integ, W, H, box, lw, lh, gap=10, occupied=()):
    """為標籤挑一個「不蓋到既有內容、也不蓋到先前標籤」的位置。

    這是本工具最值錢的一段：手工標註時，標籤蓋到截圖既有文字的問題往往要到
    圖被縮放置入投影片後才看得出來，來回成本很高。做法是對候選位置計算局部
    墨水密度（用積分圖，O(1) 查詢），挑最空的一處；候選順序在密度相同時
    決定偏好（右 → 下 → 上 → 左），並排除超出畫布與與既有標籤重疊者。
    """
    x0, y0, x1, y1 = box
    cands = [
        ("右", (x1 + gap, y0)),
        ("下", (x0, y1 + gap)),
        ("上", (x0, y0 - lh - gap)),
        ("左", (x0 - lw - gap, y0)),
        ("右下", (x1 + gap, y1 + gap)),
        ("右上", (x1 + gap, y0 - lh - gap)),
    ]
    best, best_key = None, None
    for rank, (name, (lx, ly)) in enumerate(cands):
        if lx < 0 or ly < 0 or lx + lw > W or ly + lh > H:
            continue
        if any(not (lx + lw <= o[0] or o[2] <= lx or ly + lh <= o[1] or o[3] <= ly)
               for o in occupied):
            continue
        d = _density(integ, W, H, lx, ly, lx + lw, ly + lh)
        key = (round(d, 4), rank)
        if best_key is None or key < best_key:
            best_key, best = key, (name, lx, ly, d)
    if best is None:                      # 四周都放不下 → 疊在框內左上角
        return ("框內", x0 + 6, y0 + 6, -1.0)
    return best


def annotate_image(im, boxes, width=4, fontsize=22, number=True, threshold=238):
    im = im.convert("RGB")
    W, H = im.size
    integ = _ink_integral(im)
    d = ImageDraw.Draw(im)
    # 把本次所有標籤串起來交給 _font 判定：全英文標籤在無 CJK 字型的環境
    # 仍可以純西文字型繪製；只要有一個中文標籤就必須有 CJK 字型，否則中止。
    f = _font(fontsize, "".join(str(b.get("label", "")) for b in boxes))
    occupied, log = [], []
    for i, spec in enumerate(boxes, 1):
        b = resolve_find(im, spec["find"], threshold)
        pad = spec.get("pad", 6)
        bx = (max(0, b[0] - pad), max(0, b[1] - pad),
              min(W, b[2] + pad), min(H, b[3] + pad))
        color = tuple(spec["color"]) if "color" in spec else (
            C_MARK2 if spec.get("secondary") else C_MARK)
        d.rectangle(list(bx), outline=color, width=width)
        text = spec.get("label")
        if not text:
            log.append((i, bx, None, None))
            continue
        if number:
            text = f"({i}) {text}"
        tb = d.textbbox((0, 0), text, font=f)
        lw, lh = tb[2] - tb[0] + 16, tb[3] - tb[1] + 12
        name, lx, ly, dens = place_label(integ, W, H, bx, lw, lh,
                                         occupied=occupied)
        d.rectangle([lx, ly, lx + lw, ly + lh], fill=color)
        d.text((lx + 8, ly + 6 - tb[1]), text, font=f, fill=C_TEXT)
        occupied.append((lx, ly, lx + lw, ly + lh))
        log.append((i, bx, (name, lx, ly), dens))
    return im, log


def cmd_annotate(a):
    spec = json.load(open(a.spec, encoding="utf-8"))
    jobs = spec if isinstance(spec, list) else [spec]
    base = os.path.dirname(os.path.abspath(a.spec))
    outs = []
    for job in jobs:
        src = job["image"]
        src = src if os.path.isabs(src) else os.path.join(base, src)
        if not os.path.exists(src):
            _die(f"找不到圖檔：{src}")
        im = Image.open(src)
        res, log = annotate_image(im, job.get("boxes", []),
                                  width=job.get("line_width", a.width),
                                  fontsize=job.get("fontsize", a.fontsize),
                                  number=job.get("number", True))
        out = job.get("output") or os.path.splitext(src)[0] + "_annotated.png"
        out = out if os.path.isabs(out) else os.path.join(base, out)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        res.save(out)
        outs.append(out)
        print(f"✔ {os.path.basename(src)} → {out}")
        for i, bx, place, dens in log:
            if place is None:
                print(f"    ({i}) 框 {bx}（無標籤）")
            elif place[0] == "框內":
                print(f"    ({i}) 框 {bx} → 標籤放【框內】"
                      f"——四周都放不下，請確認是否蓋到內容")
            else:
                print(f"    ({i}) 框 {bx} → 標籤放【{place[0]}】"
                      f"（該處墨水密度 {dens:.3f}）")
    if outs and not a.no_preview:
        sheet = os.path.join(os.path.dirname(outs[0]), "_preview_sheet.png")
        make_sheet(outs, sheet, cols=a.cols)
        print(f"\n預覽拼接圖：{sheet}")
        print("→ **請先看過這張再放進簡報**。標註類的錯誤（框錯位置、標籤蓋到既有文字）"
              "在單張看不出來，要看整體與縮放後的樣子。")
    return outs


# ══════════════════════════════════════════════════════════════
# sheet
# ══════════════════════════════════════════════════════════════
def make_sheet(paths, out, cols=3, cell=520, margin=12):
    ims = [Image.open(p).convert("RGB") for p in paths]
    rows = (len(ims) + cols - 1) // cols
    thumbs = []
    for im in ims:
        im = im.copy()
        im.thumbnail((cell, cell))
        thumbs.append(im)
    ch = max(t.height for t in thumbs) + 34
    cw = max(t.width for t in thumbs)
    W = cols * cw + (cols + 1) * margin
    H = rows * ch + (rows + 1) * margin
    sheet = Image.new("RGB", (W, H), (245, 247, 250))
    d = ImageDraw.Draw(sheet)
    f = _font(18)
    for i, (t, p) in enumerate(zip(thumbs, paths)):
        r, c = divmod(i, cols)
        x = margin + c * (cw + margin)
        y = margin + r * (ch + margin)
        sheet.paste(t, (x, y + 26))
        d.rectangle([x, y + 26, x + t.width, y + 26 + t.height],
                    outline=(214, 222, 233))
        d.text((x + 2, y + 4), f"{i+1}. {os.path.basename(p)}", font=f,
               fill=(31, 41, 55))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out)
    return out


def cmd_sheet(a):
    out = make_sheet(a.images, a.out, cols=a.cols)
    print(f"✔ 預覽拼接圖：{out}（{len(a.images)} 張）")


def cmd_manifest(a):
    """登記 PENDING:figprep-鍵值 → 最終產出檔案路徑的對應表，供
    cpet-input-template 的回填腳本讀取。

    設計原則（與其餘六個子命令一致）：不猜測、不自動推斷「哪個中間產物是
    最終版本」——figprep 的工作流程本質含人工確認閘門（sheet 預覽），
    一個素材可能經過 debg/convert/annotate 任意組合與順序，只有使用者
    知道哪一步的輸出才是最終要交回 cpet-yslai-pptx 的版本。因此本命令
    要求明確給出「鍵值:路徑」清單（逐行文字檔或 JSON 陣列皆可），而非
    掃描目錄猜測。

    輸入格式（--from 指定的檔案）：
      每行 "PENDING:figprep-鍵值=路徑"，或整份 JSON 陣列
      [{"id": "figprep-鍵值", "png": "路徑"}, ...]
    """
    entries = []
    with open(a.from_file, encoding="utf-8") as f:
        content = f.read()
    stripped = content.strip()
    if stripped.startswith("["):
        for item in json.loads(stripped):
            key = item["id"]
            if not key.startswith("figprep-"):
                key = f"figprep-{key}"
            entries.append({"id": key, "png": item.get("png") or item.get("path")})
    else:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                _die(f"格式錯誤（缺 '='）：{line}")
            key, path = line.split("=", 1)
            key = key.strip()
            if key.startswith("PENDING:"):
                key = key[len("PENDING:"):]
            if not key.startswith("figprep-"):
                _die(f"鍵值必須以 figprep- 開頭：{key}")
            entries.append({"id": key, "png": path.strip()})

    manifest = {"figures": [], "errors": []}
    for e in entries:
        path = e["png"]
        if not path or not os.path.exists(path):
            manifest["errors"].append({"id": e["id"], "message": f"找不到檔案：{path}"})
            continue
        manifest["figures"].append({"id": e["id"], "png": os.path.abspath(path)})

    out_path = a.out or "manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"✔ manifest：{out_path}（{len(manifest['figures'])} 筆成功，"
          f"{len(manifest['errors'])} 筆錯誤）")
    if manifest["errors"]:
        for err in manifest["errors"]:
            print(f"  ✘ {err['id']}：{err['message']}")


# ══════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="簡報素材前處理工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="檢查尺寸／透明／白邊／有效解析度")
    p.add_argument("images", nargs="+")
    p.add_argument("--width-in", type=float, default=6.0,
                   help="預計置入投影片的寬度（吋），用來估有效 dpi")
    p.add_argument("--threshold", type=int, default=238)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("debg", help="去背＋autocrop＋padding")
    p.add_argument("images", nargs="+")
    p.add_argument("-o", "--out")
    p.add_argument("--outdir")
    p.add_argument("--threshold", type=int, default=238)
    p.add_argument("--pad", type=int, default=6)
    p.add_argument("--no-crop", action="store_true")
    p.set_defaults(func=cmd_debg)

    p = sub.add_parser("convert", help="EMF／WMF／SVG／PDF → PNG")
    p.add_argument("images", nargs="+")
    p.add_argument("--outdir")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("locate", help="查詢目標在圖上的座標")
    p.add_argument("image")
    p.add_argument("--text")
    p.add_argument("--region", help='JSON 陣列，如 "[0.1,0.2,0.5,0.4]"')
    p.add_argument("--threshold", type=int, default=238)
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("annotate", help="依 spec 畫紅框與標籤")
    p.add_argument("spec")
    p.add_argument("--width", type=int, default=4)
    p.add_argument("--fontsize", type=int, default=22)
    p.add_argument("--cols", type=int, default=3)
    p.add_argument("--no-preview", action="store_true")
    p.set_defaults(func=cmd_annotate)

    p = sub.add_parser("sheet", help="產生編號預覽拼接圖")
    p.add_argument("images", nargs="+")
    p.add_argument("-o", "--out", default="preview_sheet.png")
    p.add_argument("--cols", type=int, default=3)
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("manifest", help="登記 PENDING:figprep-鍵值→產出路徑對應表（供回填腳本讀取）")
    p.add_argument("--from", dest="from_file", required=True,
                   help="逐行 'PENDING:figprep-鍵值=路徑' 的文字檔，或 JSON 陣列")
    p.add_argument("-o", "--out", default="manifest.json")
    p.set_defaults(func=cmd_manifest)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
