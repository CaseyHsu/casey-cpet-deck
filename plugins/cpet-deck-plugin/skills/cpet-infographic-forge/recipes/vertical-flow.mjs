import { measureTexts } from '../scripts/measure-text.mjs';
import { solveLayout, verticalFlowCandidates } from '../scripts/layout-solver.mjs';
/**
 * vertical-flow.mjs — 縱向流程骨架
 *
 * 適用場景：時程、階段性流程（研究進度、審稿流程）。
 * 每個節點是一張橫向卡片，由上到下垂直排列並用連接線串接，
 * 左側可選配一條索引數字條。
 *
 * 規則：不畫全畫布背景矩形，留白處保持 alpha=0（forge-build 硬性規則）。
 */

function lucideInner(refSvgString) {
  const raw = refSvgString.replace(/^ref:svg:/, '');
  return raw.replace(/<svg[^>]*>/, '').replace(/<\/svg>/, '');
}

function iconAt(refSvgString, cx, cy, size, color, strokeWidth = 2.2) {
  const inner = lucideInner(refSvgString);
  const s = size / 24;
  const tx = cx - size / 2, ty = cy - size / 2;
  return `<g transform="translate(${tx} ${ty}) scale(${s})" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round">${inner}</g>`;
}

/**
 * @param {object} data - { title?, nodes:[{label,desc,icon}] }
 * @param {string[]} palette - [navy, navyMid, ...]
 */
export function renderVerticalFlow(data, palette, assetsDir, options = {}) {
  const NAVY = palette[0] || '#1B2A5E';
  const NAVY_MID = palette[1] || '#2E5AAC';
  const nodes = data.nodes || [];
  const n = nodes.length;
  if (n < 1) throw new Error('vertical-flow 至少需要 1 個節點');

  const titleH = data.title ? 80 : 20;

  // 依目標長寬比求解版面；未提供時退回原本的固定版面。
  // 卡片內容以 icy = y + CARD_H/2 定位，本就垂直置中，故 CARD_H 變動
  // 不需重新排版。
  let CARD_W = 640, CARD_H = 80, GAP = 32;
  if (options.targetAspect) {
    const solved = solveLayout({
      targetAspect: options.targetAspect,
      candidates: verticalFlowCandidates({
        n, titleH, base: { CARD_W: 640, CARD_H: 80, GAP: 32, SIDE_PAD: 50, BOTTOM_PAD: 40 },
      }),
    });
    if (solved) ({ CARD_W, CARD_H, GAP } = solved.params);
  }

  const canvasW = CARD_W + 100;
  const canvasH = titleH + n * CARD_H + (n - 1) * GAP + 40;

  // 自動貼合字級：卡片高度會隨版面求解結果變動（實測 70~190），
  // 固定字級在高卡片中顯得過小。作法與 grid-matrix 一致——以「最長文字
  // 佔可用寬度的目標比例」反推字級，並以不溢出為硬上限。
  // 文字自 textX = x + ICON_ZONE 起算，故可用寬度需扣除 icon 區與右內距。
  const ICON_ZONE = 84, RIGHT_PAD = 20;
  const availW = CARD_W - ICON_ZONE - RIGHT_PAD;
  const labels = nodes.map((d) => String(d.label ?? '')).filter(Boolean);
  const descs = nodes.map((d) => String(d.desc ?? '')).filter(Boolean);
  const widths100 = measureTexts([...labels, ...descs]);

  const fitSize = (texts, baseSize, fill, kind) => {
    const widest = Math.max(0, ...texts.map((t) => widths100[t] || 0));
    if (!widest) return baseSize * 1.6;
    const ideal = (availW * fill / widest) * 100;
    const hardMax = (availW * 0.98 / widest) * 100;
    const size = Math.min(Math.max(ideal, baseSize * 0.8), baseSize * 1.8, hardMax);
    if (size < 11) {
      const longest = texts.reduce((a, b) => ((widths100[b] || 0) > (widths100[a] || 0) ? b : a), texts[0]);
      console.warn(
        `  [警示] vertical-flow：${kind}「${longest}」過長，為避免溢出字級已降至 `
        + `${size.toFixed(1)}px（低於可讀下限 11px）；建議縮短文字或改用較寬的 slot`
      );
    }
    return size;
  };

  // 垂直可用空間也需納入：label + 間距 + desc 不得超過卡片高的 62%
  let labelSize = fitSize(labels, 20, 0.62, 'label');
  let descSize = fitSize(descs, 15, 0.58, 'desc');
  const vNeeded = labelSize + 8 + descSize;
  if (vNeeded > CARD_H * 0.62) {
    const k = (CARD_H * 0.62) / vNeeded;
    labelSize *= k; descSize *= k;
  }

  const nodesSvg = nodes
    .map((node, i) => {
      const x = 80, y = titleH + i * (CARD_H + GAP);
      const color = palette[i % palette.length] || NAVY_MID;
      const icx = x + 40, icy = y + CARD_H / 2, textX = x + ICON_ZONE;
      // icon 圓心距卡片左緣 40px、文字自 ICON_ZONE(84) 起算，故半徑同時受
      // 「不可超出卡片左緣」與「不可壓到文字」兩項約束，取最嚴者
      const iconR = Math.min(
        24 * (labelSize / 20),   // 隨字級放大
        CARD_H * 0.32,           // 不超過卡片高度比例
        40 - 6,                  // 不超出卡片左緣（圓心在 x+40）
        ICON_ZONE - 40 - 8       // 不壓到文字起點
      );

      let connector = '';
      if (i < n - 1) {
        const lineY0 = y + CARD_H, lineY1 = y + CARD_H + GAP;
        connector = `
        <line x1="${icx}" y1="${lineY0}" x2="${icx}" y2="${lineY1}" stroke="${NAVY}" stroke-width="3"/>
        <polygon points="${icx},${lineY1} ${icx - 6},${lineY1 - 10} ${icx + 6},${lineY1 - 10}" fill="${NAVY}"/>`;
      }

      return `
      <circle cx="${x - 40}" cy="${icy}" r="${(18 * Math.min(labelSize / 20, 1.4)).toFixed(1)}" fill="${color}"/>
      <text x="${x - 40}" y="${(icy + 6 * Math.min(labelSize / 20, 1.4)).toFixed(1)}" text-anchor="middle" font-size="${(16 * Math.min(labelSize / 20, 1.4)).toFixed(1)}" font-weight="800" fill="#FFFFFF">${i + 1}</text>
      <rect x="${x}" y="${y}" width="${CARD_W}" height="${CARD_H}" rx="14" fill="#FFFFFF" stroke="${color}" stroke-width="2.4"/>
      <circle cx="${icx}" cy="${icy}" r="${iconR.toFixed(1)}" fill="#EDF1F9"/>
      ${node.icon ? iconAt(node.icon, icx, icy, iconR * 1.08, color) : ''}
      <text x="${textX}" y="${(icy - descSize * 0.35).toFixed(1)}" font-size="${labelSize.toFixed(1)}" font-weight="800" fill="#1B2A5E">${node.label}</text>
      <text x="${textX}" y="${(icy + labelSize * 0.72 + descSize * 0.5).toFixed(1)}" font-size="${descSize.toFixed(1)}" font-weight="500" fill="#3A4460">${node.desc || ''}</text>
      ${connector}`;
    })
    .join('\n');

  const titleBlock = data.title
    ? `<text x="${canvasW / 2}" y="46" text-anchor="middle" font-size="34" font-weight="900" fill="${NAVY}">${data.title}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasW} ${canvasH}" font-family="Noto Sans TC, Arial, sans-serif">
  <!-- 無全畫布背景矩形：留白處保持透明 -->
  ${titleBlock}
  ${nodesSvg}
</svg>`;
}
