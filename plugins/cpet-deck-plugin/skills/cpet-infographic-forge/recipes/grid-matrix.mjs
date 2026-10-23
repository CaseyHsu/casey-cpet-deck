import { measureTexts } from '../scripts/measure-text.mjs';
import { solveLayout, gridMatrixCandidates } from '../scripts/layout-solver.mjs';
/**
 * grid-matrix.mjs — 矩陣並列骨架
 *
 * 適用場景：多角色/多維度矩陣（例：五專才矩陣、能力對照表）。
 * 每個 cell 是一張卡片（icon + 標題 + 說明），依 cols 參數自動換行。
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
 * 單一卡片。內容區塊（icon 圓 + label + desc）在卡片內垂直置中，
 * 使卡片高度隨版面求解結果變動時不會頭重腳輕。
 *
 * 字級與 icon 尺寸由呼叫端依卡片大小與實測文字寬度決定（見
 * resolveTypography），此處只負責依給定尺寸排版。
 */
function contentHeight(t) {
  return t.iconR * 2 + t.gapIconLabel + t.labelSize + t.gapLabelDesc + t.descSize;
}

function cell({ x, y, w, h, iconSvg, label, desc, borderColor, iconBg, iconColor, typo }) {
  const t = typo;
  const top = (h - contentHeight(t)) / 2;
  const icx = x + w / 2;
  const icy = y + top + t.iconR;
  const labelBaseline = icy + t.iconR + t.gapIconLabel + t.labelSize * 0.78;
  const descBaseline = labelBaseline + t.gapLabelDesc + t.descSize * 0.95;
  return `
  <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="16" fill="#FFFFFF" stroke="${borderColor}" stroke-width="2.4"/>
  <circle cx="${icx}" cy="${icy}" r="${t.iconR}" fill="${iconBg}"/>
  ${iconSvg ? iconAt(iconSvg, icx, icy, t.iconSize, iconColor) : ''}
  <text x="${icx}" y="${labelBaseline.toFixed(1)}" text-anchor="middle" font-size="${t.labelSize.toFixed(1)}" font-weight="800" fill="#1B2A5E">${label}</text>
  <text x="${icx}" y="${descBaseline.toFixed(1)}" text-anchor="middle" font-size="${t.descSize.toFixed(1)}" font-weight="500" fill="#3A4460">${desc || ''}</text>`;
}

/**
 * 依卡片尺寸與實測文字寬度決定字級（自動貼合，盡量放大）。
 *
 * 動機：版面求解器會依目標 slot 調整卡片尺寸（實測範圍 150~360 寬、
 * 140~300 高）。固定字級在大卡片中顯得過小、在小卡片中則會溢出，而
 * recipe 的 <text> 不做自動換行，溢出無法自我修正。
 *
 * 作法（以填充比例反推，而非綁定卡片尺寸比例）：
 *   1. 目標：讓「最長的一段文字」佔可用寬度的 TARGET_FILL，據此反推字級。
 *      直接依卡片尺寸等比縮放會在「卡片只有高度變大」時完全放不大字級，
 *      即使寬度還有大量餘裕；以填充比例為目標可自然用盡可用空間。
 *   2. 以 MIN/MAX 倍率夾住，避免字數極少時字級異常巨大、或極長時過小。
 *   3. 垂直檢查：內容總高不得超過卡片高的 MAX_V_FILL，超過則整體等比縮小。
 *
 * 量測值取自 fontTools 的 advance width，未計 kerning，故 TARGET_FILL
 * 本身即保留了安全邊界（不追求 100% 填滿）。
 */
function resolveTypography({ CW, CH, widths100, labels, descs }) {
  const BASE = { label: 28, desc: 19, iconR: 30, iconSize: 32 };
  const TARGET_FILL = { label: 0.72, desc: 0.68 };
  const BOUNDS = { min: 0.8, max: 1.9 };
  const HARD_FILL = 0.98;   // 絕不允許超過的寬度佔用率
  const READABLE_MIN = 11;  // 低於此字級視為不可讀，發出警示
  const MAX_V_FILL = 0.86;
  const availW = CW - 24;

  const sizeForFill = (texts, baseSize, fill, kind) => {
    const widest = Math.max(0, ...texts.map((t) => widths100[t] || 0));
    if (!widest) return baseSize * BOUNDS.max;
    const ideal = (availW * fill / widest) * 100;
    // 可讀性下限只在不致溢出時才適用。
    // 先前版本無條件套用 BOUNDS.min，導致極長文字（如
    // "Field Weakening Control"）被硬拉回 0.8×基準而溢出達 130%——
    // recipe 的 <text> 不換行，溢出無法自我修正，故防溢出必須優先於
    // 可讀性下限；真正過小時改以警示告知使用者縮短文字或換版面。
    const hardMax = (availW * HARD_FILL / widest) * 100;
    const clamped = Math.min(Math.max(ideal, baseSize * BOUNDS.min), baseSize * BOUNDS.max);
    const size = Math.min(clamped, hardMax);
    if (size < READABLE_MIN) {
      const longest = texts.reduce((a, b) => ((widths100[b] || 0) > (widths100[a] || 0) ? b : a), texts[0]);
      console.warn(
        `  [警示] grid-matrix：${kind}「${longest}」過長，為避免溢出字級已降至 `
        + `${size.toFixed(1)}px（低於可讀下限 ${READABLE_MIN}px）；`
        + `建議縮短文字、減少欄數或改用較寬的 slot`
      );
    }
    return size;
  };

  let labelSize = sizeForFill(labels, BASE.label, TARGET_FILL.label, 'label');
  let descSize = sizeForFill(descs, BASE.desc, TARGET_FILL.desc, 'desc');

  // icon 與間距跟隨 label 的放大倍率，維持視覺比例一致
  let k = labelSize / BASE.label;
  const build = () => ({
    labelSize,
    descSize,
    iconR: BASE.iconR * k,
    iconSize: BASE.iconSize * k,
    gapIconLabel: 14 * k,
    gapLabelDesc: 8 * k,
  });

  let typo = build();
  const vFill = contentHeight(typo) / CH;
  if (vFill > MAX_V_FILL) {
    const shrink = MAX_V_FILL / vFill;
    labelSize *= shrink;
    descSize *= shrink;
    k = labelSize / BASE.label;
    typo = build();
  }
  return typo;
}

/**
 * @param {object} data - { title?, cols?, cells:[{label,desc,icon}] }
 * @param {string[]} palette - 用於循環指派每個cell的色彩（依index取模）
 * @param {string} assetsDir
 * @param {object} options - { targetAspect } 目標長寬比；提供時自動求解版面
 */
export function renderGridMatrix(data, palette, assetsDir, options = {}) {
  const cells = data.cells || [];
  const n = cells.length;
  if (n < 1) throw new Error('grid-matrix 至少需要 1 個 cell');

  const titleH = data.title ? 80 : 20;
  const PAD = 20;

  // 版面決定：
  //  - data.cols 明確指定時一律尊重使用者設定，僅在該欄數下求解卡片尺寸
  //  - 否則連同欄數一併求解，以最貼近 targetAspect
  //  - 未提供 targetAspect 時退回原本的固定版面（cols=ceil(sqrt(n))、220x150）
  let cols, CELL_W, CELL_H, GAP, solved = null;
  if (options.targetAspect) {
    let candidates = gridMatrixCandidates({ n, titleH, base: { CW: 220, CH: 150, GAP: 24, PAD } });
    if (data.cols) candidates = candidates.filter((c) => c.params.cols === data.cols);
    solved = solveLayout({ targetAspect: options.targetAspect, candidates });
  }
  if (solved) {
    ({ cols, CW: CELL_W, CH: CELL_H, GAP } = solved.params);
  } else {
    cols = data.cols || Math.ceil(Math.sqrt(n));
    CELL_W = 220; CELL_H = 150; GAP = 24;
  }
  const rows = Math.ceil(n / cols);

  const canvasW = cols * CELL_W + (cols - 1) * GAP + 2 * PAD;
  const canvasH = titleH + rows * CELL_H + (rows - 1) * GAP + PAD;

  // 量測所有文字在參考字級 100 下的寬度（一次子行程呼叫），
  // 供 resolveTypography 計算不溢出的字級上限
  const labels = cells.map((c) => String(c.label ?? '')).filter(Boolean);
  const descs = cells.map((c) => String(c.desc ?? '')).filter(Boolean);
  const widths100 = measureTexts([...labels, ...descs]);
  const typo = resolveTypography({ CW: CELL_W, CH: CELL_H, widths100, labels, descs });

  const cellsSvg = cells
    .map((c, i) => {
      const col = i % cols, row = Math.floor(i / cols);
      const x = 20 + col * (CELL_W + GAP);
      const y = titleH + row * (CELL_H + GAP);
      const color = palette[i % palette.length] || '#2E5AAC';
      return cell({
        x, y, w: CELL_W, h: CELL_H,
        iconSvg: c.icon, label: c.label, desc: c.desc,
        borderColor: color, iconBg: '#EDF1F9', iconColor: color, typo,
      });
    })
    .join('\n');

  const titleBlock = data.title
    ? `<text x="${canvasW / 2}" y="46" text-anchor="middle" font-size="34" font-weight="900" fill="#1B2A5E">${data.title}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasW} ${canvasH}" font-family="Noto Sans TC, Arial, sans-serif">
  <!-- 無全畫布背景矩形：留白處保持透明 -->
  ${titleBlock}
  ${cellsSvg}
</svg>`;
}
