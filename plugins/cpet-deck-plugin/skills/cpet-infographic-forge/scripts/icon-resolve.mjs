import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const ASSETS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../assets');
const ICON_DIR = `${ASSETS_DIR}/icons`;
const ICON_MAP = JSON.parse(readFileSync(`${ASSETS_DIR}/icon-map.json`, 'utf-8'));

/** 全部語意詞查表攤平成單一 dict：中文詞 → lucide 檔名 */
const semanticMap = ICON_MAP.semantic_zh || {};

export const unresolvedLog = [];

/**
 * 三級 fallback：
 *   1. 中文語意詞查表（icon-map.json .semantic_zh）
 *   2. 直接視為 lucide 檔名，查本地精選子集是否存在
 *   3. 都失敗 → 記入 unresolvedLog，回傳 null（呼叫端需處理，不可靜默忽略）
 */
export function resolveIcon(nameOrWord) {
  const lucideNmae = semanticMap[nameOrWord] || nameOrWord;
  const path = `${ICON_DIR}/${lucideNmae}.svg`;
  if (existsSync(path)) {
    const raw = readFileSync(path, 'utf-8');
    const cleaned = raw.replace(/<!--[\s\S]*?-->/g, '').replace(/\n\s*/g, ' ').trim();
    return `ref:svg:${cleaned}`;
  }
  unresolvedLog.push(nameOrWord);
  return null;
}
