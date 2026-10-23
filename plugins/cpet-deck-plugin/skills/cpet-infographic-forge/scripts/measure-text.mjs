/**
 * measure-text.mjs — Node 端呼叫 measure-text.py 取得文字寬度
 *
 * 回傳每段文字在「參考字級 100」下的寬度；因 advance width 隨字級
 * 線性縮放，呼叫端可用 width(S) = width100 * S / 100 換算任意字級。
 * 每次渲染只需一次子行程呼叫。
 *
 * 量測失敗時回傳保守估計（CJK 視為 1.0em、其餘 0.5em），確保 recipe
 * 仍能渲染，只是字級貼合精度下降。
 */
import { execFileSync } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const CJK_RE = /[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/;

// 2026-08-17\uFF1AWindows \u4E0A `python3.exe` \u5E38\u662F\u6307\u5411 Microsoft Store \u5B89\u88DD\u63D0\u793A\u7684
// App Execution Alias\uFF08\u975E\u771F\u6B63\u7684 Python\uFF09\uFF0C\u547C\u53EB\u6703\u5931\u6557\u4E14\u932F\u8AA4\u8A0A\u606F\u5177\u8AA4\u5C0E\u6027\u3002
// Windows \u5B98\u65B9 Python launcher `py` \u4E0D\u53D7\u6B64\u554F\u984C\u5F71\u97FF\uFF1BLinux/macOS\uFF08\u542B Chat\uFF0F
// Cowork \u5BB9\u5668\uFF09\u7DAD\u6301\u6163\u7528\u7684 `python3`\uFF0C\u5169\u908A\u4E92\u4E0D\u5F71\u97FF\u3002
const PYTHON_CMD = process.platform === 'win32' ? 'py' : 'python3';

export function measureTexts(texts, family = 'Noto Sans TC, Arial, sans-serif') {
  const uniq = [...new Set(texts.filter(Boolean))];
  if (!uniq.length) return {};
  const script = resolve(dirname(fileURLToPath(import.meta.url)), 'measure-text.py');
  try {
    const out = execFileSync(PYTHON_CMD, [script], {
      input: JSON.stringify({ texts: uniq, family }),
      encoding: 'utf-8',
    });
    return JSON.parse(out).widths || {};
  } catch {
    // 保守回退估計
    const fb = {};
    for (const t of uniq) {
      fb[t] = [...t].reduce((s, ch) => s + (CJK_RE.test(ch) ? 100 : 50), 0);
    }
    return fb;
  }
}
