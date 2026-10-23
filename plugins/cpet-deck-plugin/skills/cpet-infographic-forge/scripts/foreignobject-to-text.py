#!/usr/bin/env python3
"""
foreignobject-to-text.py — 把 SVG 內的 <foreignObject> 轉寫成原生 <text>/<tspan>

【為什麼需要】
@antv/infographic 的 SSR 產出用 <foreignObject> + HTML <span> 承載文字。
cairosvg 是純 SVG 渲染器，不處理內嵌 HTML，這些文字會被完全略過——
實測 engine route 產出的 PNG 文字色像素數為 0，整張圖只有色塊。

【為什麼可行（抽樣調查結論）】
跨 list/sequence/compare/relation/chart 五大類、12 個代表模板調查，
每個 foreignObject 內部一律是「單層 <span> + 純文字」，巢狀深度為 1，
CSS 屬性全集僅 15 個。且 x/y/width/height 已由引擎算好（絕對定位），
本轉寫器不需要重做版面計算，只需處理「換行 + 對齊 + 樣式映射」。

【字寬來源】
用 fontTools 讀取實際渲染字型的 hmtx advance width，而非 @antv/infographic
內部 measury 的離線字寬表。這比原本的 SSR 度量更貼近真實渲染結果，
可視為對 skill-design-plan §3.5「字型度量脫鉤」限制的部分改善
（僅限本轉寫器處理的 foreignObject 文字；SVG 幾何框仍由引擎算）。

【換行規則】
中英混排採差異化斷行：CJK 字元可在任意字元後斷行；西文依空白邊界斷詞，
單一長詞超出容器寬度時，依 word-break:break-word 語意強制斷開。

【已知限制】
- 只處理「單層 span」結構。若未來版本出現巢狀 HTML，本轉寫器會略過該
  節點並在 stderr 警示，不會靜默產生錯誤版面。
- 垂直對齊依 align-items/align-content 換算基線，flex 的進階行為
  （baseline、stretch、space-between）未實作，遇到時退回 flex-start。
- 不處理 RTL 文字與垂直書寫模式。
"""
import sys
import re
import json
import subprocess
from functools import lru_cache

try:
    from fontTools.ttLib import TTFont, TTCollection
except ImportError:
    print('需要 fontTools：pip install fonttools', file=sys.stderr)
    sys.exit(2)

CJK_RE = re.compile(r'[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]')


@lru_cache(maxsize=32)
def _resolve(family):
    try:
        out = subprocess.check_output(['fc-match', '-f', '%{file}', family],
                                      encoding='utf-8', stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return None


@lru_cache(maxsize=32)
def _metrics(font_path):
    """回傳 (cmap→advance width dict, unitsPerEm, ascent, descent)"""
    if not font_path:
        return None
    try:
        if font_path.lower().endswith(('.ttc', '.otc')):
            faces = TTCollection(font_path).fonts
        else:
            faces = [TTFont(font_path, fontNumber=0)]
        widths, upem, asc, desc = {}, 1000, 800, -200
        for f in faces:
            upem = f['head'].unitsPerEm
            asc = f['hhea'].ascent
            desc = f['hhea'].descent
            cmap = f.getBestCmap()
            hmtx = f['hmtx']
            for cp, gname in cmap.items():
                if cp not in widths and gname in hmtx.metrics:
                    widths[cp] = hmtx.metrics[gname][0]
        return widths, upem, asc, desc
    except Exception:
        return None


class FontMetrics:
    """依 font-family 堆疊解析出 cairo 實際會用的字型，提供字寬查詢"""

    def __init__(self, family_stack):
        self.paths = []
        for fam in [f.strip().strip('\'"') for f in family_stack.split(',')]:
            p = _resolve(fam)
            if p:
                self.paths.append(p)
        self.tables = [t for t in (_metrics(p) for p in self.paths) if t]

    def char_width(self, ch, font_size):
        cp = ord(ch)
        for widths, upem, _, _ in self.tables:
            if cp in widths:
                return widths[cp] / upem * font_size
        # 全部字型都查不到 → 用中日韓全形/西文半形粗估
        return font_size if CJK_RE.match(ch) else font_size * 0.5

    def vmetrics(self, font_size):
        if self.tables:
            _, upem, asc, desc = self.tables[0]
            return asc / upem * font_size, desc / upem * font_size
        return font_size * 0.8, -font_size * 0.2


def parse_style(style_str):
    out = {}
    for part in style_str.split(';'):
        if ':' in part:
            k, v = part.split(':', 1)
            out[k.strip()] = v.strip()
    return out


def wrap_text(text, max_width, fm, font_size):
    """中英混排斷行：CJK 可逐字斷，西文依空白斷詞，超長詞強制斷"""
    lines, cur, cur_w = [], '', 0.0

    def flush():
        nonlocal cur, cur_w
        if cur:
            lines.append(cur)
        cur, cur_w = '', 0.0

    # 先切成 token：CJK 單字元一個 token，西文連續字母一個 token
    tokens = re.findall(r'[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]|\s+|[^\s\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]+', text)

    for tok in tokens:
        if tok == '\n':
            flush()
            continue
        w = sum(fm.char_width(c, font_size) for c in tok)
        if tok.isspace():
            if cur and cur_w + w <= max_width:
                cur += tok
                cur_w += w
            continue
        if cur_w + w <= max_width or not cur:
            # 單一 token 本身就超寬 → 強制逐字斷（word-break:break-word）
            if w > max_width and len(tok) > 1:
                for ch in tok:
                    cw = fm.char_width(ch, font_size)
                    if cur_w + cw > max_width and cur:
                        flush()
                    cur += ch
                    cur_w += cw
                continue
            cur += tok
            cur_w += w
        else:
            flush()
            cur, cur_w = tok, w
    flush()
    return [l.rstrip() for l in lines] or ['']


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def convert(svg, default_stack='Noto Sans CJK TC, Inter, sans-serif'):
    stats = {'converted': 0, 'skipped': 0, 'lines_emitted': 0, 'warnings': [],
             'overflow': [], 'width_overflow': []}

    fo_re = re.compile(r'<foreignObject([^>]*)>([\s\S]*?)</foreignObject>')

    def attr(attrs, name, default=None):
        m = re.search(rf'{name}="([^"]*)"', attrs)
        return m.group(1) if m else default

    def repl(m):
        attrs, inner = m.group(1), m.group(2)

        # 只支援單層 span；其他結構略過並警示（不靜默出錯）
        tags = re.findall(r'<(\w+)', inner)
        if tags.count('span') != 1 or len(tags) != 1:
            stats['skipped'] += 1
            stats['warnings'].append(f'非單層span結構，已略過：{tags}')
            return m.group(0)

        span = re.search(r'<span([^>]*)>([\s\S]*?)</span>', inner)
        if not span:
            stats['skipped'] += 1
            return m.group(0)

        text = re.sub(r'<[^>]*>', '', span.group(2))
        text = (text.replace('&amp;', '&').replace('&lt;', '<')
                    .replace('&gt;', '>').replace('&quot;', '"'))
        if not text.strip():
            stats['skipped'] += 1
            return ''

        box_x = float(attr(attrs, 'x', '0') or 0)
        box_y = float(attr(attrs, 'y', '0') or 0)
        box_w = float(attr(attrs, 'width', '0') or 0)
        box_h = float(attr(attrs, 'height', '0') or 0)

        st = parse_style(re.search(r'style="([^"]*)"', span.group(1)).group(1)
                         if re.search(r'style="([^"]*)"', span.group(1)) else '')

        font_size = float(re.sub(r'[^\d.]', '', st.get('font-size', '14')) or 14)
        font_weight = st.get('font-weight')
        color = st.get('color', '#262626')
        line_height_raw = st.get('line-height', '1.4')
        try:
            lh_factor = float(line_height_raw)
        except ValueError:
            lh_factor = 1.4
        line_h = font_size * lh_factor

        # 依內容選字型堆疊（與 postprocess 的 CJK 優先策略一致）
        stack = default_stack if CJK_RE.search(text) else 'Inter, Noto Sans CJK TC, sans-serif'
        fm = FontMetrics(stack)

        # 換行：只有 flex-wrap:wrap / white-space 允許時才斷行
        nowrap = st.get('white-space') in ('nowrap', 'pre')
        lines = [text] if (nowrap or box_w <= 0) else wrap_text(text, box_w, fm, font_size)

        # 水平對齊
        ta = st.get('text-align') or st.get('justify-content') or 'left'
        if ta in ('center',):
            anchor, tx = 'middle', box_x + box_w / 2
        elif ta in ('right', 'flex-end', 'end'):
            anchor, tx = 'end', box_x + box_w
        else:
            anchor, tx = 'start', box_x

        # 垂直對齊：依 align-items / align-content 換算首行基線
        va = st.get('align-items') or st.get('align-content') or 'flex-start'
        ascent, _ = fm.vmetrics(font_size)
        total_h = len(lines) * line_h
        if va in ('center',):
            top = box_y + (box_h - total_h) / 2
        elif va in ('flex-end', 'end'):
            top = box_y + box_h - total_h
        else:
            top = box_y
        first_baseline = top + (line_h - font_size) / 2 + ascent

        parts = [f'<text x="{tx:.2f}" y="{first_baseline:.2f}" text-anchor="{anchor}"',
                 f' font-size="{font_size}" fill="{color}" font-family="{stack}"']
        if font_weight:
            parts.append(f' font-weight="{font_weight}"')
        parts.append('>')
        for i, ln in enumerate(lines):
            dy = 0 if i == 0 else line_h
            parts.append(f'<tspan x="{tx:.2f}" dy="{dy:.2f}">{esc(ln)}</tspan>')
        parts.append('</text>')

        stats['converted'] += 1
        stats['lines_emitted'] += len(lines)

        # 溢出偵測：引擎用 measury 離線字寬表分配本框的 width/height，
        # 本轉寫器則用 fontTools 真實字寬斷行，兩者不一致時可能斷出
        # 比引擎預留空間更多的行數，導致文字溢出容器（視覺上會壓到
        # 相鄰元件或超出卡片邊界）。此處如實記錄，供 QA 閘門判斷。
        total_h = len(lines) * line_h
        if box_h > 0 and total_h > box_h + 0.5:
            stats['overflow'].append({
                'text': text[:40],
                'lines': len(lines),
                'text_height': round(total_h, 2),
                'box_height': round(box_h, 2),
                'overflow_px': round(total_h - box_h, 2),
                'overflow_ratio': round(total_h / box_h, 3),
            })
        # 單行寬度溢出（nowrap 或無法再斷的長 token）
        widest = max((sum(fm.char_width(c, font_size) for c in l) for l in lines), default=0)
        if box_w > 0 and widest > box_w + 0.5:
            stats['width_overflow'].append({
                'text': text[:40],
                'line_width': round(widest, 2),
                'box_width': round(box_w, 2),
                'overflow_px': round(widest - box_w, 2),
            })
        return ''.join(parts)

    out = fo_re.sub(repl, svg)
    return out, stats


def main():
    if len(sys.argv) < 2:
        print('用法：python3 foreignobject-to-text.py <in.svg> [out.svg] [--stats-json]',
              file=sys.stderr)
        sys.exit(2)
    src = open(sys.argv[1], encoding='utf-8').read()
    out, stats = convert(src)
    dst = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else sys.argv[1]
    open(dst, 'w', encoding='utf-8').write(out)
    if '--stats-json' in sys.argv:
        print(json.dumps(stats, ensure_ascii=False))
    else:
        print(f"轉換 {stats['converted']} 個 foreignObject，"
              f"產生 {stats['lines_emitted']} 行文字，略過 {stats['skipped']} 個")
        if stats['overflow']:
            print(f"  [警示] {len(stats['overflow'])} 段文字高度溢出容器：")
            for o in stats['overflow'][:6]:
                print(f"      「{o['text']}」{o['lines']}行 {o['text_height']}px > 框高 {o['box_height']}px")
        if stats['width_overflow']:
            print(f"  [警示] {len(stats['width_overflow'])} 段文字寬度溢出容器")
        for w in stats['warnings'][:5]:
            print('  警示:', w)


if __name__ == '__main__':
    main()
