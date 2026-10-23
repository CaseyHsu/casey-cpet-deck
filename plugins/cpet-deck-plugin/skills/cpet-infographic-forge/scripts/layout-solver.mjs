/**
 * layout-solver.mjs — 依目標長寬比反解 recipe 版面參數
 *
 * 【問題】
 * 原本各 recipe 的版面常數寫死（grid-matrix 的 CELL_W/CELL_H、
 * vertical-flow 的 CARD_W/CARD_H），長寬比是「項目數的副產品」，
 * 完全不知道目標 slot 是什麼。後果：
 *   - grid-matrix n=5 固定給 3 欄 → aspect 1.685，投到 twocol(1.180)
 *     時上下留白達 38.6%
 *   - vertical-flow n=3 → 1.745（偏差 0.479 不合格），但 n=5 → 1.142
 *     （偏差 0.033 合格）。同一 recipe 換個項目數就在合格與不合格
 *     之間跳動，不是穩定設計。
 *
 * 【作法】
 * 在合理的尺寸界限內搜尋版面參數組合，使畫布長寬比最接近目標值，
 * 並以「偏離基準比例的程度」作為次要評分，避免為了湊長寬比而產生
 * 過度變形的版面。
 *
 * 【安全方向的偏好】
 * 加高（增加 CELL_H／GAP）不會造成文字溢出；縮窄（減少 CELL_W）則
 * 有風險，因為 recipe 的 <text> 不做自動換行。因此評分對「縮窄」
 * 施加額外懲罰，優先以加高達成目標。
 */

/**
 * 在給定界限內搜尋最佳版面。
 *
 * @param {object} opts
 *   targetAspect  目標長寬比（canvasW / canvasH）；null 表示不調整，回傳基準值
 *   candidates    產生候選版面的函式陣列，每個回傳 { W, H, params }
 * @returns {{ params: object, aspect: number, deviation: number, adjusted: boolean }}
 */
export function solveLayout({ targetAspect, candidates }) {
  const evaluated = candidates
    .map((c) => {
      const aspect = c.W / c.H;
      const deviation = Math.max(aspect, targetAspect) / Math.min(aspect, targetAspect) - 1;
      return { ...c, aspect, deviation };
    })
    .filter((c) => Number.isFinite(c.aspect) && c.aspect > 0);

  if (!evaluated.length) return null;

  // 偏差已遠低於門檻（0.25）時，各候選在「長寬比合格」這件事上實質等價，
  // 此時應由變形評分決定，優先選擇不縮窄、貼近基準比例的版面。
  // 若仍以極小的偏差差異排序，會選到「為了多命中 0.0001 而大幅縮窄卡片」
  // 的解，反而提高文字溢出風險。
  const EQUIV_TOLERANCE = 0.02;
  const bucket = (dev) => (dev <= EQUIV_TOLERANCE ? 0 : dev);

  evaluated.sort((a, b) => {
    const d = bucket(a.deviation) - bucket(b.deviation);
    if (Math.abs(d) > 1e-9) return d;
    return (a.distortion ?? 0) - (b.distortion ?? 0);
  });

  return evaluated[0];
}

/**
 * grid-matrix 的候選版面產生器。
 *
 * 搜尋空間：欄數 × 卡片寬 × 卡片高（後兩者在界限內以步進掃描）。
 * 幾何關係：
 *   canvasW = cols·CW + (cols-1)·GAP + 2·PAD
 *   canvasH = titleH + rows·CH + (rows-1)·GAP + PAD
 */
export function gridMatrixCandidates({
  n, titleH, base = { CW: 220, CH: 150, GAP: 24, PAD: 20 }, bounds,
}) {
  const b = bounds || { CW: [150, 360], CH: [140, 300], GAP: [20, 48] };
  const out = [];
  for (let cols = 1; cols <= n; cols++) {
    const rows = Math.ceil(n / cols);
    for (let CW = b.CW[0]; CW <= b.CW[1]; CW += 5) {
      for (let CH = b.CH[0]; CH <= b.CH[1]; CH += 5) {
        const GAP = base.GAP;
        const W = cols * CW + (cols - 1) * GAP + 2 * base.PAD;
        const H = titleH + rows * CH + (rows - 1) * GAP + base.PAD;
        // 變形評分：縮窄（CW < 基準）額外懲罰，因為 recipe 不做文字換行
        const wDev = (CW - base.CW) / base.CW;
        const hDev = (CH - base.CH) / base.CH;
        const distortion = Math.abs(hDev) + Math.abs(wDev) * (wDev < 0 ? 2.5 : 1);
        out.push({ W, H, distortion, params: { cols, rows, CW, CH, GAP } });
      }
    }
  }
  return out;
}

/**
 * data-table 的候選版面產生器（v1.2 新增，缺口一：二維矩陣表格）。
 *
 * 搜尋空間：欄寬（列標籤欄與資料欄分開估）× 列高。與 gridMatrixCandidates
 * 同樣的簡化：不逐欄獨立寬度求解（那需要先知道每欄內容長度分布才能求解，
 * 複雜度遠高於目前需求），改用「列標籤欄寬」與「資料欄統一寬」兩個自由度，
 * 足以覆蓋 5×7 矩陣這類欄數多、欄內容長度相近（皆為簡短技術詞彙／符號）
 * 的實際情境；欄內容長度差異極大的表格不適用此簡化，屬已知限制。
 *
 * 幾何關係：
 *   canvasW = labelColW + cols·cellColW + (cols)·GAP + 2·PAD
 *   canvasH = titleH + headerH + rows·rowH + (rows)·GAP + PAD
 */
export function dataTableCandidates({
  rows, cols, titleH,
  base = { labelColW: 200, cellColW: 130, rowH: 56, headerH: 64, GAP: 2, PAD: 20 },
  bounds,
}) {
  const b = bounds || {
    labelColW: [140, 320], cellColW: [90, 220], rowH: [40, 90],
  };
  const out = [];
  for (let labelColW = b.labelColW[0]; labelColW <= b.labelColW[1]; labelColW += 10) {
    for (let cellColW = b.cellColW[0]; cellColW <= b.cellColW[1]; cellColW += 10) {
      for (let rowH = b.rowH[0]; rowH <= b.rowH[1]; rowH += 5) {
        const GAP = base.GAP;
        const W = labelColW + cols * cellColW + cols * GAP + 2 * base.PAD;
        const H = titleH + base.headerH + rows * rowH + rows * GAP + base.PAD;
        // 變形評分：縮窄資料欄（cellColW < 基準）額外懲罰——表格 cell 文字
        // 不做自動換行，欄過窄比列過矮更容易造成溢出（欄寬影響單行是否
        // 放得下，列高只影響垂直留白，不對稱懲罰比照 grid-matrix 的作法）。
        const wDev = (cellColW - base.cellColW) / base.cellColW;
        const hDev = (rowH - base.rowH) / base.rowH;
        const distortion = Math.abs(hDev) + Math.abs(wDev) * (wDev < 0 ? 2.5 : 1);
        out.push({ W, H, distortion, params: { labelColW, cellColW, rowH, GAP } });
      }
    }
  }
  return out;
}

/**
 * dual-line-panel 的候選版面產生器（v1.2 新增，缺口二：雙軸折線圖）。
 *
 * 搜尋空間：單面板寬 × 單面板高（雙面板並列，兩者共用同一組尺寸——各自
 * 獨立 y 軸範圍是資料語意層面的事，不影響兩面板的畫布幾何對稱性，統一
 * 尺寸也讓左右面板視覺對齊，不需要另外處理不對稱版面）。
 *
 * 幾何關係（雙面板並列，中間留一條分隔間距）：
 *   canvasW = 2·panelW + GAP + 2·PAD
 *   canvasH = titleH + panelH + PAD
 */
export function dualLinePanelCandidates({
  titleH,
  base = { panelW: 480, panelH: 380, GAP: 40, PAD: 20 },
  bounds,
}) {
  const b = bounds || { panelW: [360, 620], panelH: [280, 480] };
  const out = [];
  for (let panelW = b.panelW[0]; panelW <= b.panelW[1]; panelW += 10) {
    for (let panelH = b.panelH[0]; panelH <= b.panelH[1]; panelH += 10) {
      const GAP = base.GAP;
      const W = 2 * panelW + GAP + 2 * base.PAD;
      const H = titleH + panelH + base.PAD;
      // 變形評分：面板過窄比過矮風險更高（軸標籤與圖例需要水平空間），
      // 縮窄懲罰係數比照其餘候選產生器的不對稱慣例。
      const wDev = (panelW - base.panelW) / base.panelW;
      const hDev = (panelH - base.panelH) / base.panelH;
      const distortion = Math.abs(hDev) + Math.abs(wDev) * (wDev < 0 ? 2.0 : 1);
      out.push({ W, H, distortion, params: { panelW, panelH, GAP } });
    }
  }
  return out;
}

/**
 * vertical-flow 的候選版面產生器。
 *
 * 幾何關係：
 *   canvasW = CARD_W + 2·SIDE_PAD
 *   canvasH = titleH + n·CARD_H + (n-1)·GAP + BOTTOM_PAD
 */
export function verticalFlowCandidates({
  n, titleH, base = { CARD_W: 640, CARD_H: 80, GAP: 32, SIDE_PAD: 50, BOTTOM_PAD: 40 }, bounds,
}) {
  const b = bounds || { CARD_W: [420, 760], CARD_H: [70, 190], GAP: [24, 90] };
  const out = [];
  for (let CARD_W = b.CARD_W[0]; CARD_W <= b.CARD_W[1]; CARD_W += 10) {
    for (let CARD_H = b.CARD_H[0]; CARD_H <= b.CARD_H[1]; CARD_H += 5) {
      for (let GAP = b.GAP[0]; GAP <= b.GAP[1]; GAP += 4) {
        const W = CARD_W + 2 * base.SIDE_PAD;
        const H = titleH + n * CARD_H + (n - 1) * GAP + base.BOTTOM_PAD;
        const wDev = (CARD_W - base.CARD_W) / base.CARD_W;
        const hDev = (CARD_H - base.CARD_H) / base.CARD_H;
        const gDev = (GAP - base.GAP) / base.GAP;
        const distortion = Math.abs(hDev) + Math.abs(gDev) * 0.5
          + Math.abs(wDev) * (wDev < 0 ? 2.5 : 1);
        out.push({ W, H, distortion, params: { CARD_W, CARD_H, GAP } });
      }
    }
  }
  return out;
}
