import { measureTexts } from '../scripts/measure-text.mjs';
import { solveLayout, dualLinePanelCandidates } from '../scripts/layout-solver.mjs';
/**
 * dual-line-panel.mjs — 雙面板折線圖骨架（v1.2 新增，缺口二）
 *
 * 適用場景：兩個物理量綱／視角的對比折線圖（例：絕對誤差 vs 相對誤差），
 * 各面板可有多條 series、各自獨立 y 軸範圍、參考線（含標籤）、關鍵資料點
 * 標註。與既有 chart-line-plain-text（engine 模板）的差異：後者 data_key
 * 為單一 values 陣列、supports_desc:false，不支援多 series、雙面板、
 * 參考線、端點標註的組合需求。
 *
 * 規則：不畫全畫布背景矩形，留白處保持 alpha=0（forge-build 硬性規則）。
 */

function scaleX(x, xMin, xMax, plotW) {
  if (xMax === xMin) return 0;
  return ((x - xMin) / (xMax - xMin)) * plotW;
}
function scaleY(y, yMin, yMax, plotH) {
  if (yMax === yMin) return plotH / 2;
  return plotH - ((y - yMin) / (yMax - yMin)) * plotH;
}

function renderPanel(panel, px, py, panelW, panelH, palette, widths100, axisSize, labelSize) {
  const series = panel.series || [];
  const allPoints = series.flatMap((s) => s.points || []);
  if (!allPoints.length) throw new Error(`dual-line-panel 面板「${panel.label}」至少需要 1 個資料點`);

  const xs = allPoints.map((p) => p.x);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);

  const yAxis = panel.yAxis || {};
  let yMin = yAxis.min, yMax = yAxis.max;
  if (yMin == null || yMax == null) {
    const ys = allPoints.map((p) => p.y);
    const dataMin = Math.min(...ys), dataMax = Math.max(...ys);
    const pad = (dataMax - dataMin) * 0.1 || 1;
    if (yMin == null) yMin = dataMin - pad;
    if (yMax == null) yMax = dataMax + pad;
  }

  // 繪圖區域：扣除軸標籤與面板標題所需空間
  const AXIS_LEFT = 56, AXIS_BOTTOM = 36, TOP_PAD = 34, RIGHT_PAD = 12;
  const plotX = px + AXIS_LEFT, plotY = py + TOP_PAD;
  const plotW = panelW - AXIS_LEFT - RIGHT_PAD;
  const plotH = panelH - TOP_PAD - AXIS_BOTTOM;

  let svg = `<text x="${px + panelW / 2}" y="${py + 22}" text-anchor="middle" font-size="${labelSize.toFixed(1)}" font-weight="800" fill="#1B2A5E">${panel.label}</text>`;

  // 座標軸
  svg += `
  <line x1="${plotX}" y1="${plotY}" x2="${plotX}" y2="${plotY + plotH}" stroke="#8EA9C9" stroke-width="1.5"/>
  <line x1="${plotX}" y1="${plotY + plotH}" x2="${plotX + plotW}" y2="${plotY + plotH}" stroke="#8EA9C9" stroke-width="1.5"/>`;

  // y 軸刻度（5 段）
  for (let i = 0; i <= 4; i++) {
    const v = yMin + ((yMax - yMin) * i) / 4;
    const y = plotY + scaleY(v, yMin, yMax, plotH);
    const unit = yAxis.unit || '';
    svg += `
    <line x1="${plotX - 4}" y1="${y.toFixed(1)}" x2="${plotX}" y2="${y.toFixed(1)}" stroke="#8EA9C9" stroke-width="1"/>
    <text x="${plotX - 8}" y="${(y + axisSize * 0.32).toFixed(1)}" text-anchor="end" font-size="${axisSize.toFixed(1)}" fill="#3A4460">${v.toFixed(1)}${unit}</text>`;
  }
  // x 軸刻度（首尾 + 中點，避免密集重疊）
  const xTicks = xMax === xMin ? [xMin] : [xMin, (xMin + xMax) / 2, xMax];
  for (const v of xTicks) {
    const x = plotX + scaleX(v, xMin, xMax, plotW);
    svg += `
    <line x1="${x.toFixed(1)}" y1="${(plotY + plotH).toFixed(1)}" x2="${x.toFixed(1)}" y2="${(plotY + plotH + 4).toFixed(1)}" stroke="#8EA9C9" stroke-width="1"/>
    <text x="${x.toFixed(1)}" y="${(plotY + plotH + axisSize + 6).toFixed(1)}" text-anchor="middle" font-size="${axisSize.toFixed(1)}" fill="#3A4460">${v}</text>`;
  }

  // 參考線（含標籤）——先畫，讓 series 線疊在上層更清楚
  if (panel.referenceLine) {
    const ry = plotY + scaleY(panel.referenceLine.value, yMin, yMax, plotH);
    svg += `
    <line x1="${plotX}" y1="${ry.toFixed(1)}" x2="${(plotX + plotW).toFixed(1)}" y2="${ry.toFixed(1)}" stroke="#C96A0E" stroke-width="1.5" stroke-dasharray="6,4"/>
    <text x="${(plotX + plotW - 4).toFixed(1)}" y="${(ry - 6).toFixed(1)}" text-anchor="end" font-size="${axisSize.toFixed(1)}" font-weight="700" fill="#C96A0E">${panel.referenceLine.label}</text>`;
  }

  // 各 series 折線 + 資料點
  series.forEach((s, i) => {
    const color = s.color || palette[i % palette.length] || '#2E5AAC';
    const pts = (s.points || [])
      .map((p) => `${(plotX + scaleX(p.x, xMin, xMax, plotW)).toFixed(1)},${(plotY + scaleY(p.y, yMin, yMax, plotH)).toFixed(1)}`)
      .join(' ');
    svg += `
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
    for (const p of (s.points || [])) {
      const cx = plotX + scaleX(p.x, xMin, xMax, plotW);
      const cy = plotY + scaleY(p.y, yMin, yMax, plotH);
      svg += `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="3.5" fill="${color}"/>`;
    }
  });

  // 圖例（series 名稱，面板內右上角垂直排列）
  const legendItems = series.map((s) => String(s.name || ''));
  const legendW = Math.max(0, ...legendItems.map((t) => (widths100[t] || 0) * axisSize / 100)) + 24;
  series.forEach((s, i) => {
    const color = s.color || palette[i % palette.length] || '#2E5AAC';
    const ly = plotY + 4 + i * (axisSize + 6);
    svg += `
    <line x1="${(plotX + plotW - legendW).toFixed(1)}" y1="${ly.toFixed(1)}" x2="${(plotX + plotW - legendW + 14).toFixed(1)}" y2="${ly.toFixed(1)}" stroke="${color}" stroke-width="2.5"/>
    <text x="${(plotX + plotW - legendW + 18).toFixed(1)}" y="${(ly + axisSize * 0.32).toFixed(1)}" font-size="${axisSize.toFixed(1)}" fill="#1B2A5E">${s.name || ''}</text>`;
  });

  // 關鍵資料點標註
  for (const ann of (panel.annotations || [])) {
    const ax = plotX + scaleX(ann.x, xMin, xMax, plotW);
    const ay = plotY + scaleY(ann.y, yMin, yMax, plotH);
    svg += `
    <circle cx="${ax.toFixed(1)}" cy="${ay.toFixed(1)}" r="5" fill="none" stroke="#D55E00" stroke-width="2"/>
    <text x="${ax.toFixed(1)}" y="${(ay - 10).toFixed(1)}" text-anchor="middle" font-size="${axisSize.toFixed(1)}" font-weight="700" fill="#D55E00">${ann.label}</text>`;
  }

  return svg;
}

/**
 * @param {object} data - {
 *   title?: string,
 *   panels: [{
 *     label: string,
 *     series: [{ name, points:[{x,y}], color? }],
 *     yAxis?: { min?, max?, unit? },
 *     referenceLine?: { value, label },
 *     annotations?: [{ x, y, label }],
 *   }]  // panels.length===2 為雙面板情境；1 面板亦可用（單面板折線）
 * }
 * @param {string[]} palette
 * @param {string} assetsDir
 * @param {object} options - { targetAspect }
 */
export function renderDualLinePanel(data, palette, assetsDir, options = {}) {
  const panels = data.panels || [];
  if (panels.length < 1) throw new Error('dual-line-panel 至少需要 1 個面板');
  if (panels.length > 2) throw new Error('dual-line-panel 最多支援 2 個面板並列');

  const NAVY = palette[0] || '#1B2A5E';
  const titleH = data.title ? 60 : 12;

  let panelW, panelH, GAP, solved = null;
  if (options.targetAspect) {
    const candidates = dualLinePanelCandidates({ titleH });
    solved = solveLayout({ targetAspect: options.targetAspect, candidates });
  }
  if (solved) {
    ({ panelW, panelH, GAP } = solved.params);
  } else {
    panelW = 480; panelH = 380; GAP = 40;
  }
  const PAD = 20;

  const nPanels = panels.length;
  const canvasW = nPanels === 1
    ? panelW + 2 * PAD
    : 2 * panelW + GAP + 2 * PAD;
  const canvasH = titleH + panelH + PAD;

  // 字級自動貼合：軸標籤與面板標題文字獨立量測，避免雙面板窄版時軸刻度
  // 數字互相擠壓。與其餘 recipe 一致的填充比例反推手法。
  const allLegendNames = panels.flatMap((p) => (p.series || []).map((s) => String(s.name || '')));
  const allPanelLabels = panels.map((p) => String(p.label || ''));
  const widths100 = measureTexts([...allLegendNames, ...allPanelLabels]);
  const axisSize = 13;
  const labelSize = 18;

  const panelsSvg = panels
    .map((panel, i) => {
      const px = PAD + i * (panelW + GAP);
      const py = titleH;
      return renderPanel(panel, px, py, panelW, panelH, palette, widths100, axisSize, labelSize);
    })
    .join('\n');

  const titleBlock = data.title
    ? `<text x="${canvasW / 2}" y="${titleH * 0.62}" text-anchor="middle" font-size="30" font-weight="900" fill="${NAVY}">${data.title}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasW} ${canvasH}" font-family="Noto Sans TC, Arial, sans-serif">
  <!-- 無全畫布背景矩形：留白處保持透明 -->
  ${titleBlock}
  ${panelsSvg}
</svg>`;
}
