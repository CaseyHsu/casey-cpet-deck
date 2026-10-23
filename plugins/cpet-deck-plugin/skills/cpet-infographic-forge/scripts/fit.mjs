/**
 * fit.mjs — 長寬比適配建議（不做補白，理由見下方）
 *
 * 對稱補白在 cpet-yslai-pptx 的 add_picture_fit() 下是 no-op
 * （等比縮放置中，補白後視覺結果與不補白完全相同），故此模組
 * 職責縮減為：
 *   1. 偏差偵測（呼叫 qa-gate.checkAspect）
 *   2. 偏差過大時查 template-catalog.json 給替代模板/recipe建議
 *   3. 依 slot + DPI 計算目標輸出解析度
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { checkAspect } from './qa-gate.mjs';

const ASSETS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../assets');

const SLOT_BOX_INCHES = {
  full: [12.57, 5.45],
  'full-tw': [12.57, 4.78],
  half: [6.16, 4.78],
  quad: [6.16, 2.09],
  twocol: [6.11, 5.18],
};

export function targetResolution(slot, dpi = 200) {
  const box = SLOT_BOX_INCHES[slot];
  if (!box) return null;
  return { width: Math.round(box[0] * dpi), height: Math.round(box[1] * dpi) };
}

/** 依實際項目數查 catalog，回傳當下情境的建議（不可跨項目數套用，見catalog meta.usage_note） */
export function lookupCatalog(family, itemCount) {
  const catalog = JSON.parse(readFileSync(`${ASSETS_DIR}/template-catalog.json`, 'utf-8'));
  const entry = catalog.families?.[family];
  if (!entry) return null;

  // 找最接近的已量測項目數（3/5/8），非精確匹配時標註為推估
  const measured = Object.keys(entry.per_item_count || {}).map(Number);
  if (!measured.length) return null;
  const nearest = measured.reduce((a, b) =>
    Math.abs(b - itemCount) < Math.abs(a - itemCount) ? b : a
  );
  const data = entry.per_item_count[nearest];
  return {
    ...data,
    queriedItemCount: itemCount,
    matchedItemCount: nearest,
    exact: nearest === itemCount,
    stability: entry.stability,
  };
}

/**
 * 主入口：給定實際長寬比、目標 slot、來源家族名與項目數，回傳
 * { pass, deviation, resolution, catalogLookup? }
 */
export function evaluateFit(actualAspect, slot, family, itemCount, threshold = 0.25) {
  const check = checkAspect(actualAspect, slot, threshold);
  const resolution = targetResolution(slot);
  const result = { ...check, resolution };
  if (!check.pass && family) {
    result.catalogLookup = itemCount != null ? lookupCatalog(family, itemCount) : null;
  }
  return result;
}
