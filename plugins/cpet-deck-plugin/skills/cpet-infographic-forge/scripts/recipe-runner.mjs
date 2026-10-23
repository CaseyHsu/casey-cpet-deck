import { renderCircleCycle } from '../recipes/circle-cycle.mjs';
import { renderGridMatrix } from '../recipes/grid-matrix.mjs';
import { renderVerticalFlow } from '../recipes/vertical-flow.mjs';
import { renderDataTable } from '../recipes/data-table.mjs';
import { renderDualLinePanel } from '../recipes/dual-line-panel.mjs';

const REGISTRY = {
  'circle-cycle': renderCircleCycle,
  'grid-matrix': renderGridMatrix,
  'vertical-flow': renderVerticalFlow,
  'data-table': renderDataTable,
  'dual-line-panel': renderDualLinePanel,
};

export async function runRecipe(name, data, palette, assetsDir, options = {}) {
  const fn = REGISTRY[name];
  if (!fn) {
    throw new Error(
      `recipe "${name}" 尚未實作。目前可用: ${Object.keys(REGISTRY).join(', ')}`
    );
  }
  return fn(data, palette, assetsDir, options);
}
