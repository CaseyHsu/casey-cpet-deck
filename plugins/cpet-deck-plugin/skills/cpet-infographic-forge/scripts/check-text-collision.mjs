/**
 * checkTextCollision — 偵測 SVG 中 <text> 區塊彼此是否重疊。
 *
 * 背景：既有四道閘門（aspect／fontCoverage／textOverflow／textLegibility）皆檢查
 * 「單一區塊內部」是否有問題（字級、缺字、溢出），但從未檢查「跨區塊之間」是否
 * 互相疊壓。實測案例（fig-scope-placement.svg）顯示：標題與下方雙欄標題在垂直
 * 方向重疊糊字，四道閘門全數 PASS，只有人工看渲染圖才發現——這代表現有閘門
 * 設計上完全沒有覆蓋「版面碰撞」這一類問題，必須新增第五道閘門補上。
 *
 * 作法：解析每個 <text> 節點（含巢狀 <g transform="translate(x,y)"> 造成的座標
 * 平移）算出絕對座標，用 font-size 與字元寬度估算（CJK≈1em、拉丁≈0.55em，與
 * check-font-coverage.py／build_deck.py 的估寬邏輯同一數量級但獨立實作，因為這裡
 * 面對的是 SVG 座標系而非 pptx 吋制）得到每個 text 區塊的近似 bounding box，
 * 再兩兩比對矩形是否相交。
 *
 * 已知限制：
 *   - 不做真正的字型 metrics 查詢，純粹幾何估算，抓「明顯重疊」比抓「差 1-2px」準確
 *   - text-anchor="middle" 需要用 x 座標當作水平置中點回推左右邊界
 *   - 巢狀 transform 只處理 translate，不處理 rotate／scale（engine 模板目前未使用旋轉文字）
 */
import { readFileSync } from 'fs';
import { pathToFileURL } from 'url';

function estimateTextWidth(text, fontSize) {
  let w = 0;
  for (const ch of text) {
    w += fontSize * (ch.codePointAt(0) > 0x2e7f ? 1.0 : 0.55);
  }
  return w;
}

/** 粗略 XML 解析：抓出每個 <text> 節點的絕對座標與其所有 tspan 行，
 *  透過堆疊追蹤巢狀 <g transform="translate(dx,dy)"> 的累積平移量。
 *
 *  實作分兩階段而非單一 regex 混合匹配（初版曾用單一 alternation 同時抓 <g>／
 *  <text>／<tspan>，結果 tspan 分支從未命中，所有文字寬度算出 0——因為 <text>
 *  與其內部 <tspan> 屬於巢狀結構，混在同一個「掃過整份字串」的 tokenizer 迴圈
 *  裡處理，順序與巢狀關係很容易對不上）。改為：先用 tag walker 依序找出所有
 *  開合標籤與其屬性建立一個扁平事件序列，再依事件序列維護 transform 堆疊與
 *  「目前在哪個 text 節點內」的狀態，分開處理更不容易出錯。 */
function extractTextBoxes(svgString) {
  const boxes = [];
  const stack = [{ dx: 0, dy: 0 }];
  let curText = null;

  const getAttr = (attrs, name) => {
    const r = new RegExp(`${name}="([^"]*)"`).exec(attrs || '');
    return r ? r[1] : null;
  };

  // 掃過所有標籤（開始／結束／自閉合皆比對），依序處理。
  const tagRe = /<(\/?)([\w:-]+)((?:\s+[\w:-]+="[^"]*")*)\s*(\/?)>/g;
  let m;
  let lastIndex = 0;
  while ((m = tagRe.exec(svgString))) {
    const [full, closingSlash, tag, attrs, selfClosingSlash] = m;
    const closing = closingSlash === '/';
    const selfClosing = selfClosingSlash === '/';

    if (tag === 'g') {
      if (closing) {
        if (stack.length > 1) stack.pop();
      } else {
        const transform = getAttr(attrs, 'transform') || '';
        const tr = /translate\(([-\d.]+)[,\s]+([-\d.]+)\)/.exec(transform);
        const top = stack[stack.length - 1];
        stack.push(tr
          ? { dx: top.dx + parseFloat(tr[1]), dy: top.dy + parseFloat(tr[2]) }
          : { ...top });
      }
    } else if (tag === 'text') {
      if (!closing) {
        const top = stack[stack.length - 1];
        const x = parseFloat(getAttr(attrs, 'x') || '0') + top.dx;
        const y = parseFloat(getAttr(attrs, 'y') || '0') + top.dy;
        const fontSize = parseFloat(getAttr(attrs, 'font-size') || '14');
        const anchor = getAttr(attrs, 'text-anchor') || 'start';
        // contentStart 記錄 <text ...> 開始標籤結束的位置，供關閉時若期間未遇到任何
        // <tspan>（純文字直接寫在 <text>純文字</text> 之間，recipe route 的主流格式，
        // 三個既有 recipe 的 label/desc 皆是此寫法）回頭取出這段純文字當作一行。
        curText = { x, y, fontSize, anchor, lines: [], contentStart: m.index + full.length };
      } else if (curText) {
        if (curText.lines.length === 0) {
          const closeIdx = svgString.indexOf('</text>', curText.contentStart);
          const raw = closeIdx >= 0 ? svgString.slice(curText.contentStart, closeIdx) : '';
          const text = raw.trim();
          if (text) curText.lines.push({ text, dy: 0 });
        }
        delete curText.contentStart;
        boxes.push(curText);
        curText = null;
      }
    } else if (tag === 'tspan' && !closing && !selfClosing && curText) {
      // tspan 的文字內容夾在這個開始標籤與對應的 </tspan> 之間，用開始標籤在原始
      // 字串中的結束位置，找到下一個 </tspan> 之前的純文字。
      const contentStart = m.index + full.length;
      const closeIdx = svgString.indexOf('</tspan>', contentStart);
      const text = closeIdx >= 0 ? svgString.slice(contentStart, closeIdx) : '';
      const dy = parseFloat(getAttr(attrs, 'dy') || '0');
      curText.lines.push({ text, dy });
    }
    lastIndex = tagRe.lastIndex;
  }
  return boxes;
}

/** 把 extractTextBoxes 的原始資料轉成 {x0,y0,x1,y1} 矩形。 */
function toRect(box) {
  const lineHeight = box.fontSize * 1.4;
  let maxWidth = 0;
  const lines = box.lines.length ? box.lines : [{ text: '', dy: 0 }];
  for (const ln of lines) {
    maxWidth = Math.max(maxWidth, estimateTextWidth(ln.text, box.fontSize));
  }
  const totalDy = lines.reduce((s, l) => s + l.dy, 0);
  const numLines = lines.length;
  const top = box.y - box.fontSize * 0.85; // baseline -> approx cap-height top
  const bottom = top + Math.max(lineHeight, totalDy + lineHeight);
  let left, right;
  if (box.anchor === 'middle') {
    left = box.x - maxWidth / 2;
    right = box.x + maxWidth / 2;
  } else if (box.anchor === 'end') {
    left = box.x - maxWidth;
    right = box.x;
  } else {
    left = box.x;
    right = box.x + maxWidth;
  }
  return { x0: left, y0: top, x1: right, y1: bottom, numLines };
}

function intersects(a, b) {
  const ix = Math.max(0, Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0));
  const iy = Math.max(0, Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0));
  return ix * iy;
}

export function checkTextCollision(svgString, opts = {}) {
  const areaRatioThreshold = opts.areaRatioThreshold ?? 0.08;
  const boxes = extractTextBoxes(svgString).map(toRect);
  const collisions = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      const interArea = intersects(a, b);
      if (interArea <= 0) continue;
      const areaA = Math.max(1, (a.x1 - a.x0) * (a.y1 - a.y0));
      const areaB = Math.max(1, (b.x1 - b.x0) * (b.y1 - b.y0));
      const ratio = interArea / Math.min(areaA, areaB);
      if (ratio > areaRatioThreshold) {
        collisions.push({ boxA: i, boxB: j, overlapRatio: +ratio.toFixed(3) });
      }
    }
  }
  return {
    pass: collisions.length === 0,
    textNodeCount: boxes.length,
    collisions,
    note: collisions.length
      ? `偵測到 ${collisions.length} 組文字區塊重疊（重疊比例門檻 ${areaRatioThreshold}）——`
        + `這通常代表標題／副標／欄位標題之間的預留高度不足，多發生於多行 tspan 換行時`
      : undefined,
  };
}

// CLI 自我測試
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const path = process.argv[2];
  if (!path) {
    console.error('用法：node checkTextCollision.mjs <svg路徑>');
    process.exit(2);
  }
  const svg = readFileSync(path, 'utf-8');
  const result = checkTextCollision(svg);
  console.log(JSON.stringify(result, null, 2));
}
