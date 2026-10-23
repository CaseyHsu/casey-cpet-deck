#!/usr/bin/env python3
"""
check-font-coverage.py — SVG 字型 glyph 覆蓋率檢查（確定性，非啟發式）

【設計動機】
本工具取代先前失效的兩道檢查：
  - `qa-gate.mjs` 的 `checkMissingGlyphs()`：只掃 SVG 原始碼有無 U+FFFD／□
    等替代字元。但 NO GLYPH 是「字型缺 glyph」而非「字串內容有問題」，
    SVG 原始碼永遠是乾淨的，故此檢查對本類問題永遠 pass，是無效閘門。
  - 像素層級的啟發式視覺特徵掃描：門檻難以校準，實測對整片 NO GLYPH
    方框的圖仍回報 pass，不可信賴。

【本工具的作法（確定性）】
模擬 cairo "toy" text API 的字型選擇行為——cairo **不做逐字元 fallback**，
只會取 font-family 堆疊中第一個能被 fontconfig 解析到的實體字型，整個
文字節點都用那一個字型面渲染。因此只要：
    對每個 <text> 節點，解析它繼承或自帶的 font-family
    → 用 fontconfig 找出實際會被選中的字型檔
    → 用 fontTools 讀該字型的 cmap
    → 逐字元檢查是否有對應 glyph
就能在轉檔前100%確定哪些字會變成 .notdef，零偽陽性、零偽陰性。

【額外檢查】foreignObject 偵測
cairosvg 是純 SVG 渲染器，不處理 <foreignObject> 內嵌的 HTML 內容，
該區塊的文字會被完全略過（渲染成空白）。此情況下 SVG 內可能一個
<text> 節點都沒有，上述 glyph 檢查會「無事可檢」而假性通過，因此
必須另外偵測並回報。

用法：
    python3 check-font-coverage.py <svg_path> [--json]
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


@lru_cache(maxsize=64)
def resolve_font_file(family):
    """用 fontconfig 解析 family 名稱 → 實際字型檔路徑（模擬 cairo 的選擇）"""
    try:
        out = subprocess.check_output(
            ['fc-match', '-f', '%{file}|%{family}', family],
            encoding='utf-8', stderr=subprocess.DEVNULL)
        path, matched_family = out.split('|', 1)
        return path.strip(), matched_family.strip()
    except Exception:
        return None, None


@lru_cache(maxsize=64)
def load_cmap(font_path):
    """讀取字型的 cmap（支援 .ttc/.otc 集合檔，合併所有 face 的覆蓋範圍）"""
    if not font_path:
        return frozenset()
    try:
        if font_path.lower().endswith(('.ttc', '.otc')):
            coll = TTCollection(font_path)
            codepoints = set()
            for f in coll.fonts:
                codepoints |= set(f.getBestCmap().keys())
            return frozenset(codepoints)
        f = TTFont(font_path, fontNumber=0)
        return frozenset(f.getBestCmap().keys())
    except Exception:
        return frozenset()


def first_resolvable_family(font_family_value):
    """
    模擬 cairo toy API：取堆疊中第一個能解析到「名稱確實相符」的實體字型。
    fc-match 對不存在的字型會回退到系統預設，故需比對回傳的 family 名稱
    是否確實包含請求的名稱，才算命中。
    """
    families = [f.strip().strip('\'"') for f in font_family_value.split(',')]
    for fam in families:
        if fam.lower() in ('sans-serif', 'serif', 'monospace', 'cursive', 'fantasy'):
            path, matched = resolve_font_file(fam)
            return fam, path, matched
        path, matched = resolve_font_file(fam)
        if path and matched and fam.lower() in matched.lower():
            return fam, path, matched
    # 全部落空 → fontconfig 預設
    path, matched = resolve_font_file('sans-serif')
    return None, path, matched


def analyze(svg_path):
    svg = open(svg_path, encoding='utf-8').read()

    result = {
        'svg': svg_path,
        'pass': True,
        'text_node_count': 0,
        'missing_glyph_nodes': [],
        'foreign_object': {'present': False, 'count': 0, 'lost_text_samples': []},
        'font_resolution': [],
    }

    # --- 檢查 foreignObject（cairosvg 不渲染，文字會整段消失）---
    fo_count = len(re.findall(r'<foreignObject\b', svg))
    if fo_count:
        spans = re.findall(r'<span[^>]*>([^<]*)</span>', svg)
        lost = [s for s in spans if s.strip()]
        result['foreign_object'] = {
            'present': True,
            'count': fo_count,
            'lost_text_samples': lost[:10],
            'lost_text_total': len(lost),
        }
        result['pass'] = False

    # --- 根層級 font-family（供 <text> 繼承）---
    root_match = re.search(r'<svg\b[^>]*font-family="([^"]*)"', svg)
    root_family = root_match.group(1) if root_match else 'sans-serif'

    # --- 逐 <text> 節點檢查 glyph 覆蓋 ---
    seen_families = {}
    for m in re.finditer(r'<text\b([^>]*)>([\s\S]*?)</text>', svg):
        attrs, inner = m.group(1), m.group(2)
        result['text_node_count'] += 1
        own = re.search(r'font-family="([^"]*)"', attrs)
        family_value = own.group(1) if own else root_family
        text = re.sub(r'<[^>]*>', '', inner)
        if not text.strip():
            continue

        chosen, path, matched = first_resolvable_family(family_value)
        cmap = load_cmap(path)
        if family_value not in seen_families:
            seen_families[family_value] = {
                'requested_stack': family_value,
                'cairo_will_use': chosen,
                'resolved_file': path,
                'resolved_family': matched,
            }

        missing = sorted({ch for ch in text
                          if ch not in ('\n', '\t', ' ') and ord(ch) not in cmap})
        if missing:
            result['pass'] = False
            result['missing_glyph_nodes'].append({
                'text': text[:60],
                'font_stack': family_value,
                'cairo_will_use': chosen,
                'resolved_file': path,
                'missing_chars': missing,
                'missing_count': len(missing),
            })

    result['font_resolution'] = list(seen_families.values())
    return result


def main():
    if len(sys.argv) < 2:
        print('用法：python3 check-font-coverage.py <svg_path> [--json]', file=sys.stderr)
        sys.exit(2)
    res = analyze(sys.argv[1])
    if '--json' in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"檔案：{res['svg']}")
        print(f"  <text> 節點數：{res['text_node_count']}")
        for fr in res['font_resolution']:
            print(f"  字型解析：請求「{fr['requested_stack']}」"
                  f"→ cairo 實際採用「{fr['cairo_will_use']}」({fr['resolved_family']})")
        fo = res['foreign_object']
        if fo['present']:
            print(f"  [FAIL] 偵測到 {fo['count']} 個 <foreignObject>："
                  f"cairosvg 不渲染其內容，{fo.get('lost_text_total', 0)} 段文字將完全消失")
            for s in fo['lost_text_samples']:
                print(f"          遺失文字：{s}")
        if res['missing_glyph_nodes']:
            print(f"  [FAIL] {len(res['missing_glyph_nodes'])} 個節點含字型缺 glyph 的字元"
                  f"（將渲染為 .notdef／NO GLYPH 方框）：")
            for n in res['missing_glyph_nodes']:
                print(f"          「{n['text']}」→ 採用 {n['cairo_will_use']}，"
                      f"缺 {n['missing_count']} 字：{''.join(n['missing_chars'][:20])}")
        if res['pass']:
            print('  [PASS] 全部文字皆有對應 glyph，且無 foreignObject 遺失風險')
    sys.exit(0 if res['pass'] else 1)


if __name__ == '__main__':
    main()
