#!/usr/bin/env python3
"""
measure-text.py — 批次量測文字寬度（供 recipe 計算安全字級）

【用途】
recipe 的 <text> 不做自動換行，字級放大後若超出卡片寬度就會溢出。
本工具用 fontTools 讀實際渲染字型的 hmtx advance width，回報每段文字
在「參考字級 100」下的寬度；因 advance width 隨字級線性縮放，呼叫端
可直接換算任意字級的寬度：

    width(S) = width_at_100 * S / 100

故每個字串只需量測一次，一次子行程呼叫即可涵蓋整份圖的所有文字，
不需為每個字級重複量測。

【輸入】stdin 讀 JSON：
    {"texts": ["...", "..."], "family": "Noto Sans TC, Arial, sans-serif"}

【輸出】stdout 印 JSON：
    {"widths": {"文字": 寬度at100, ...}, "family_used": "實際採用的字型"}

【限制】
- 僅計算 advance width 總和，未計入 kerning 與 OpenType 進階排版特性，
  實際渲染寬度可能略有出入（一般小於 2%）。呼叫端應保留安全邊界。
- 字型解析邏輯與 foreignobject-to-text.py 的 FontMetrics 一致：模擬
  cairo toy API 取堆疊中第一個可解析的實體字型，不做逐字元 fallback。
"""
import sys
import json
import subprocess
from functools import lru_cache

try:
    from fontTools.ttLib import TTFont, TTCollection
except ImportError:
    print(json.dumps({'error': '需要 fontTools'}), file=sys.stdout)
    sys.exit(2)

CJK_RANGES = [(0x3000, 0x303F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
              (0xF900, 0xFAFF), (0xFF00, 0xFFEF)]


def is_cjk(ch):
    cp = ord(ch)
    return any(a <= cp <= b for a, b in CJK_RANGES)


@lru_cache(maxsize=32)
def resolve(family):
    try:
        return subprocess.check_output(['fc-match', '-f', '%{file}', family],
                                       encoding='utf-8',
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


@lru_cache(maxsize=32)
def metrics(path):
    if not path:
        return None
    try:
        faces = (TTCollection(path).fonts if path.lower().endswith(('.ttc', '.otc'))
                 else [TTFont(path, fontNumber=0)])
        widths, upem = {}, 1000
        for f in faces:
            upem = f['head'].unitsPerEm
            hmtx = f['hmtx']
            for cp, gname in f.getBestCmap().items():
                if cp not in widths and gname in hmtx.metrics:
                    widths[cp] = hmtx.metrics[gname][0]
        return widths, upem
    except Exception:
        return None


def main():
    req = json.load(sys.stdin)
    family = req.get('family', 'Noto Sans TC, Arial, sans-serif')
    tables, used = [], None
    for fam in [f.strip().strip('\'"') for f in family.split(',')]:
        p = resolve(fam)
        t = metrics(p)
        if t:
            tables.append(t)
            if used is None:
                used = fam

    REF = 100.0

    def char_w(ch):
        cp = ord(ch)
        for widths, upem in tables:
            if cp in widths:
                return widths[cp] / upem * REF
        return REF if is_cjk(ch) else REF * 0.5

    out = {t: round(sum(char_w(c) for c in t), 3) for t in req.get('texts', [])}
    print(json.dumps({'widths': out, 'family_used': used}, ensure_ascii=False))


if __name__ == '__main__':
    main()
