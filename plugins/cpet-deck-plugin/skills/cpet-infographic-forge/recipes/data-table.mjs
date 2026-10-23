import { measureTexts } from '../scripts/measure-text.mjs';
import { solveLayout, dataTableCandidates } from '../scripts/layout-solver.mjs';
/**
 * data-table.mjs — 二維矩陣表格骨架（v1.2 新增，缺口一）
 *
 * 適用場景：多方法/多維度結構性比較矩陣（例：5 個方法 × 7 個比較維度）。
 * 與既有 grid-matrix.mjs 的本質差異：grid-matrix 的 cells 是一維卡片陣列
 * （每格只有 label+desc+icon 三欄資訊），無法表達「列標籤 × 欄標籤 →
 * 交叉格值」的二維語意；本 recipe 的 cells 是 rows×cols 的二維陣列，
 * 每個 cell 是「這一列方法」在「這一欄維度」下的值，且支援整列／整欄
 * 高亮（實際需求：Proposed 方法整列強調，或某比較維度整欄強調）。
 *
 * 規則：不畫全畫布背景矩形，留白處保持 alpha=0（forge-build 硬性規則）。
 */

/**
 * @param {object} data - {
 *   title?: string,
 *   rows: string[],           // 列標籤，如 ["Conventional LUT", ...]
 *   cols: string[],           // 欄標籤，如 ["Model basis", ...]
 *   cells: string[][],        // cells[rowIdx][colIdx]
 *   highlightRow?: number,    // 整列高亮的列索引
 *   highlightCol?: number,    // 整欄高亮的欄索引
 * }
 * @param {string[]} palette
 * @param {string} assetsDir
 * @param {object} options - { targetAspect }
 */
export function renderDataTable(data, palette, assetsDir, options = {}) {
  const rowLabels = data.rows || [];
  const colLabels = data.cols || [];
  const cells = data.cells || [];
  const rows = rowLabels.length;
  const cols = colLabels.length;
  if (rows < 1 || cols < 1) throw new Error('data-table 至少需要 1 列與 1 欄');
  if (cells.length !== rows) {
    throw new Error(`data-table cells 列數（${cells.length}）與 rows 標籤數（${rows}）不符`);
  }
  for (let r = 0; r < rows; r++) {
    if ((cells[r] || []).length !== cols) {
      throw new Error(`data-table cells[${r}] 欄數（${(cells[r] || []).length}）與 cols 標籤數（${cols}）不符`);
    }
  }

  const NAVY = palette[0] || '#1B2A5E';
  const HEADER_BG = palette[0] || '#1B2A5E';
  const HIGHLIGHT_BG = palette[1] || '#2E5AAC';
  const titleH = data.title ? 70 : 16;

  let labelColW, cellColW, rowH, GAP, solved = null;
  if (options.targetAspect) {
    const candidates = dataTableCandidates({ rows, cols, titleH });
    solved = solveLayout({ targetAspect: options.targetAspect, candidates });
  }
  if (solved) {
    ({ labelColW, cellColW, rowH, GAP } = solved.params);
  } else {
    labelColW = 200; cellColW = 130; rowH = 56; GAP = 2;
  }
  const headerH = 64;
  const PAD = 20;

  const canvasW = labelColW + cols * cellColW + cols * GAP + 2 * PAD;
  const canvasH = titleH + headerH + rows * rowH + rows * GAP + PAD;

  // 字級自動貼合：欄標題／列標籤／格值三種文字獨立量測，各自以「最長文字佔
  // 可用寬度的目標比例」反推字級（與 grid-matrix/vertical-flow 同一手法），
  // 因為 cell 文字不做自動換行，欄過窄時必須靠縮字避免溢出而非讓文字裁切。
  const widths100 = measureTexts([
    ...colLabels.map(String),
    ...rowLabels.map(String),
    ...cells.flat().map(String),
  ]);

  // 逐文字獨立貼合字級（而非統一取最長字串反推套用全體）。
  // 統一字級策略在欄標題長度差異大時會讓短字串被迫縮到與最長字串同樣小
  // （實測：5欄方法名稱長度 8~20 字元，若統一字級，全部欄標題被壓到
  // 10.2px 低於可讀下限，即使多數欄標題遠短於最長者，「Proposed」8字元
  // 也被迫和「Regularization-based」20字元用同一個字級）。改為每個文字
  // 各自依「不超過 baseSize、且不溢出自己所在欄寬」反推字級——短字串
  // 用較大字級、長字串用較小字級但不低於各自能撐住不溢出的下限，兩者
  // 互不拖累。回傳陣列與該組文字裡的最小值（供計算儲存格垂直置中基準）。
  const fitSizePerText = (texts, baseSize, availW, fill, kind) => {
    const sizes = texts.map((t) => {
      const w = widths100[String(t)] || 0;
      if (!w) return baseSize;
      const ideal = (availW * fill / w) * 100;
      const hardMax = (availW * 0.96 / w) * 100;
      return Math.min(Math.max(ideal, baseSize * 0.6), baseSize * 1.3, hardMax);
    });
    const tooSmallIdx = sizes
      .map((s, i) => (s < 10 ? i : -1))
      .filter((i) => i >= 0);
    if (tooSmallIdx.length) {
      const names = tooSmallIdx.map((i) => texts[i]).join('、');
      console.warn(
        `  [警示] data-table：${kind}「${names}」過長，為避免溢出字級已降至可讀下限`
        + `以下；建議縮短文字、減少欄數或改用較寬的 slot`
      );
    }
    return sizes;
  };

  const headerSizes = fitSizePerText(colLabels, 17, cellColW - 16, 0.85, '欄標題');
  const labelSizes = fitSizePerText(rowLabels, 16, labelColW - 24, 0.85, '列標籤');
  const cellSizesFlat = fitSizePerText(cells.flat(), 15, cellColW - 16, 0.85, '格值');
  const cellSizes = [];
  for (let r = 0; r < rows; r++) cellSizes.push(cellSizesFlat.slice(r * cols, (r + 1) * cols));

  const highlightRow = Number.isInteger(data.highlightRow) ? data.highlightRow : -1;
  const highlightCol = Number.isInteger(data.highlightCol) ? data.highlightCol : -1;

  // ── 標頭列：左上角空白角 + 欄標題 ──
  let headerSvg = `<rect x="0" y="${titleH}" width="${labelColW}" height="${headerH}" fill="${HEADER_BG}"/>`;
  for (let c = 0; c < cols; c++) {
    const x = labelColW + c * (cellColW + GAP);
    const isHl = c === highlightCol;
    const bg = isHl ? HIGHLIGHT_BG : HEADER_BG;
    const sz = headerSizes[c];
    headerSvg += `
    <rect x="${x}" y="${titleH}" width="${cellColW}" height="${headerH}" fill="${bg}"/>
    <text x="${x + cellColW / 2}" y="${titleH + headerH / 2 + sz * 0.35}" text-anchor="middle" font-size="${sz.toFixed(1)}" font-weight="800" fill="#FFFFFF">${colLabels[c]}</text>`;
  }

  // ── 資料列：列標籤 + 各欄格值，整列/整欄高亮疊加淺色底 ──
  let bodySvg = '';
  for (let r = 0; r < rows; r++) {
    const y = titleH + headerH + r * (rowH + GAP) + GAP;
    const rowIsHl = r === highlightRow;
    const labelBg = rowIsHl ? '#EAF0FC' : (r % 2 === 0 ? '#F7F9FC' : '#FFFFFF');
    const lsz = labelSizes[r];
    bodySvg += `
    <rect x="0" y="${y}" width="${labelColW}" height="${rowH}" fill="${labelBg}"/>
    <text x="12" y="${y + rowH / 2 + lsz * 0.35}" font-size="${lsz.toFixed(1)}" font-weight="700" fill="${NAVY}">${rowLabels[r]}</text>`;
    for (let c = 0; c < cols; c++) {
      const x = labelColW + c * (cellColW + GAP);
      const colIsHl = c === highlightCol;
      const cellIsHl = rowIsHl || colIsHl;
      const bg = cellIsHl ? '#EAF0FC' : (r % 2 === 0 ? '#F7F9FC' : '#FFFFFF');
      const textColor = cellIsHl ? HIGHLIGHT_BG : '#3A4460';
      const csz = cellSizes[r][c];
      bodySvg += `
      <rect x="${x}" y="${y}" width="${cellColW}" height="${rowH}" fill="${bg}"/>
      <text x="${x + cellColW / 2}" y="${y + rowH / 2 + csz * 0.35}" text-anchor="middle" font-size="${csz.toFixed(1)}" font-weight="${cellIsHl ? 700 : 500}" fill="${textColor}">${cells[r][c]}</text>`;
    }
  }

  // 高亮列/欄的邊框（描邊，不只是底色，確保灰階測試下仍可辨識——
  // 規格§0.2配色硬規則要求雙重編碼，不能只靠顏色區分語意）
  let highlightBorder = '';
  if (highlightRow >= 0) {
    const y = titleH + headerH + highlightRow * (rowH + GAP) + GAP;
    highlightBorder += `<rect x="0" y="${y}" width="${canvasW}" height="${rowH}" fill="none" stroke="${HIGHLIGHT_BG}" stroke-width="2.5"/>`;
  }
  if (highlightCol >= 0) {
    const x = labelColW + highlightCol * (cellColW + GAP);
    highlightBorder += `<rect x="${x}" y="${titleH}" width="${cellColW}" height="${canvasH - titleH}" fill="none" stroke="${HIGHLIGHT_BG}" stroke-width="2.5"/>`;
  }

  const titleBlock = data.title
    ? `<text x="${canvasW / 2}" y="${titleH * 0.68}" text-anchor="middle" font-size="30" font-weight="900" fill="${NAVY}">${data.title}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasW} ${canvasH}" font-family="Noto Sans TC, Arial, sans-serif">
  <!-- 無全畫布背景矩形：留白處保持透明 -->
  ${titleBlock}
  ${headerSvg}
  ${bodySvg}
  ${highlightBorder}
</svg>`;
}
