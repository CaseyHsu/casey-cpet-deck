/**
 * circle-cycle.mjs — 環形循環骨架（通用版）
 *
 * 改寫自先前 SPAL Cycle 案例的硬編碼原型（spal-handcraft.mjs，
 * 當時卡片數、座標、文字皆寫死為4）。此版接受任意數量節點、
 * 任意文字與 icon，座標由節點數動態計算角度分布。
 *
 * 規則：不畫全畫布背景矩形，留白處保持 alpha=0（見 forge-build 硬性規則）。
 */

function lucideInner(refSvgString) {
  // data.icon 已由 icon-resolve.mjs 處理成 "ref:svg:<...>" 格式，取內層路徑
  const raw = refSvgString.replace(/^ref:svg:/, '');
  return raw.replace(/<svg[^>]*>/, '').replace(/<\/svg>/, '');
}

function iconAt(refSvgString, cx, cy, size, color, strokeWidth = 2.2) {
  const inner = lucideInner(refSvgString);
  const s = size / 24;
  const tx = cx - size / 2, ty = cy - size / 2;
  return `<g transform="translate(${tx} ${ty}) scale(${s})" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round">${inner}</g>`;
}

function card({ x, y, w, h, iconSvg, label, desc, navy, navyMid, iconBg }) {
  const icx = x + 52, icy = y + h / 2, textX = x + 96;
  return `
  <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="18" fill="#FFFFFF" stroke="${navy}" stroke-width="2.6"/>
  <circle cx="${icx}" cy="${icy}" r="30" fill="${iconBg}"/>
  ${iconSvg ? iconAt(iconSvg, icx, icy, 34, navyMid) : ''}
  <text x="${textX}" y="${icy - 6}" font-size="30" font-weight="800" fill="${navy}">${label}</text>
  <text x="${textX}" y="${icy + 24}" font-size="18" font-weight="500" fill="#3A4460">${desc}</text>`;
}

function arc(cx, cy, r, a0, a1, navy, navyMid) {
  const rad = (d) => (d * Math.PI) / 180;
  const px = (a) => cx + r * Math.cos(rad(a));
  const py = (a) => cy + r * Math.sin(rad(a));
  const x0 = px(a0), y0 = py(a0), x1 = px(a1), y1 = py(a1);
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
  const tAng = a1 + 90;
  const head = 15, spread = 26;
  const h1x = x1 - head * Math.cos(rad(tAng - spread));
  const h1y = y1 - head * Math.sin(rad(tAng - spread));
  const h2x = x1 - head * Math.cos(rad(tAng + spread));
  const h2y = y1 - head * Math.sin(rad(tAng + spread));
  return `
  <path d="M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}"
        fill="none" stroke="${navy}" stroke-width="4.5" stroke-linecap="round"/>
  <polygon points="${x1.toFixed(1)},${y1.toFixed(1)} ${h1x.toFixed(1)},${h1y.toFixed(1)} ${h2x.toFixed(1)},${h2y.toFixed(1)}" fill="${navy}"/>
  <circle cx="${x0.toFixed(1)}" cy="${y0.toFixed(1)}" r="8" fill="${navyMid}"/>`;
}

/**
 * @param {object} data - { title, subtitle_en?, subtitle_line?, center_callout?, nodes:[{label,desc,icon}] }
 * @param {string[]} palette - 至少2色 [navy, navyMid, ...]
 */
export function renderCircleCycle(data, palette) {
  const NAVY = palette[0] || '#1B2A5E';
  const NAVY_MID = palette[1] || '#2E5AAC';
  const ORANGE = palette[palette.length - 1] || '#F5941E';
  const ICON_BG = '#EDF1F9';

  const nodes = data.nodes || [];
  const n = nodes.length;
  if (n < 2) throw new Error('circle-cycle 至少需要 2 個節點');

  const CANVAS = 1080;
  const CX = CANVAS / 2, CY = 600, R = 246;
  const CARD_W = 320, CARD_H = 128;

  // 動態計算每個節點的卡片位置（均分圓周，從正上方開始順時針）
  const cardPos = nodes.map((_, i) => {
    const angle = -90 + (360 / n) * i; // 度
    const rad = (angle * Math.PI) / 180;
    const cardCx = CX + (R + 130) * Math.cos(rad);
    const cardCy = CY + (R + 130) * Math.sin(rad);
    return { x: cardCx - CARD_W / 2, y: cardCy - CARD_H / 2 };
  });

  const cardsSvg = nodes
    .map((node, i) =>
      card({
        ...cardPos[i],
        w: CARD_W,
        h: CARD_H,
        iconSvg: node.icon,
        label: node.label,
        desc: node.desc || '',
        navy: NAVY,
        navyMid: NAVY_MID,
        iconBg: ICON_BG,
      })
    )
    .join('\n');

  // 每兩個相鄰節點間畫一段弧形箭頭
  const gapDeg = 360 / n;
  const arcsSvg = nodes
    .map((_, i) => {
      const a0 = -90 + gapDeg * i + gapDeg * 0.28;
      const a1 = -90 + gapDeg * (i + 1) - gapDeg * 0.28;
      return arc(CX, CY, R, a0, a1, NAVY, NAVY_MID);
    })
    .join('\n');

  const titleBlock = data.title
    ? `<text x="${CANVAS / 2}" y="90" text-anchor="middle" font-size="52" font-weight="900" fill="${NAVY}">${data.title}</text>`
    : '';
  const subtitleEnBlock = data.subtitle_en
    ? `<text x="${CANVAS / 2}" y="150" text-anchor="middle" font-size="38" font-weight="800" fill="${NAVY}">${data.subtitle_en}</text>`
    : '';
  const subtitleLineBlock = data.subtitle_line
    ? `<text x="${CANVAS / 2}" y="195" text-anchor="middle" font-size="20" font-weight="700" fill="${NAVY}">${data.subtitle_line}</text>`
    : '';

  let calloutBlock = '';
  if (data.center_callout) {
    const lines = data.center_callout.lines || [];
    const boxW = 260, boxH = 60 + lines.length * 30;
    const bx = CX - boxW / 2, by = CY - boxH / 2;
    calloutBlock = `
    <rect x="${bx}" y="${by}" width="${boxW}" height="${boxH}" rx="16" fill="#FDF3E7" stroke="${ORANGE}" stroke-width="2.6"/>
    <text x="${CX}" y="${by + 34}" text-anchor="middle" font-size="20" fill="${ORANGE}">★</text>
    ${lines
      .map(
        (l, i) =>
          `<text x="${CX}" y="${by + 62 + i * 28}" text-anchor="middle" font-size="19" font-weight="800" fill="#C96A0E">${l}</text>`
      )
      .join('\n')}`;
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${CANVAS} ${CANVAS}" font-family="Noto Sans TC, Arial, sans-serif">
  <!-- 無全畫布背景矩形：留白處保持透明，符合硬性規則 -->
  ${titleBlock}
  ${subtitleEnBlock}
  ${subtitleLineBlock}
  ${arcsSvg}
  ${cardsSvg}
  ${calloutBlock}
</svg>`;
}
