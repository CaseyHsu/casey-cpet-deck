/**
 * validate-input.mjs — 依 template-registry.json 做渲染前輸入驗證
 *
 * 【為什麼需要在送出 SSR 前擋】
 * 全量 276 模板調查發現兩個 @antv/infographic 的行為，若不事前攔截，
 * 使用者只會得到「無訊息卡住」或「文字莫名不見」，難以自行診斷：
 *
 *   1. **不合法資料鍵會 hang 而非報錯**：例如傳入 `children`，SSR 不會
 *      拋出錯誤，而是 hang 住直到 10 秒 timeout（實測連 n=1 亦然，
 *      耗時固定 10.0 秒）。同一模板改用正確的 `lists` 只需 66ms。
 *   2. **29% 的模板（80/276）會靜默丟棄 desc**：只渲染 title 與 label，
 *      使用者提供的 desc 不顯示且無任何錯誤訊息。
 *
 * 驗證分兩級：
 *   - error：會導致渲染失敗或長時間 hang，直接中止該圖並回報
 *   - warning：不影響渲染成功，但輸出結果與使用者預期不符（如 desc 被丟棄）
 */
import { readFileSync, existsSync } from 'fs';
import { createRequire } from 'module';

// 用引擎自身的解析函式，才能如實揭露「輸入名稱會被靜默解析成什麼」。
// 註：@antv/infographic 的 package.json exports 未開放此子路徑，直接
// require 子路徑會被擋（ERR_PACKAGE_PATH_NOT_EXPORTED），故先解析主入口
// 位置再推導出實體檔案路徑。
const _require = createRequire(import.meta.url);
let _resolveTemplateKey = null;
let _resolveTried = false;
function resolveTemplateKey(name) {
  if (!_resolveTried) {
    _resolveTried = true;
    try {
      const mainPath = _require.resolve('@antv/infographic');
      const pkgRoot = mainPath.slice(0, mainPath.lastIndexOf('/@antv/infographic/') + '/@antv/infographic/'.length);
      const tpl = _require(`${pkgRoot}lib/templates/index.js`);
      _resolveTemplateKey = tpl.resolveTemplateKey;
    } catch { /* 解析不到則放棄此附加資訊，不影響主要驗證 */ }
  }
  if (!_resolveTemplateKey) return null;
  return _resolveTemplateKey(name);
}

let _registry = null;

export function loadRegistry(assetsDir) {
  if (_registry) return _registry;
  const p = `${assetsDir}/template-registry.json`;
  if (!existsSync(p)) {
    _registry = { templates: {}, _missing: true };
    return _registry;
  }
  _registry = JSON.parse(readFileSync(p, 'utf-8'));
  return _registry;
}

/** registry 記錄過的全部合法資料鍵 */
const VALID_KEYS = ['lists', 'sequences', 'compares', 'nodes', 'values'];

/**
 * 已知會導致 SSR hang 的資料鍵。
 * `children` 為實測確認者；其餘為未被任何模板使用、行為未經驗證的鍵，
 * 一併擋下並要求使用者改用正確鍵，避免踩到相同的 hang 行為。
 */
const KNOWN_HANG_KEYS = ['children'];

/**
 * 驗證單張圖的輸入。
 * @returns {{errors: string[], warnings: string[], info: object}}
 */
export function validateFigure(fig, assetsDir) {
  const errors = [];
  const warnings = [];
  const info = {};

  if (fig.route !== 'engine') return { errors, warnings, info }; // recipe route 不適用

  const reg = loadRegistry(assetsDir);
  if (reg._missing) {
    warnings.push('找不到 assets/template-registry.json，已略過輸入驗證');
    return { errors, warnings, info };
  }

  const entry = reg.templates[fig.template];

  // --- 1. 模板名稱是否為 registry 內的 276 個正式模板 ---
  //
  // 【為何必須嚴格擋下】@antv/infographic 的 resolveTemplateKey() 對無法
  // 識別的名稱**不會報錯，而是靜默 fallback 到某個預設模板**。實測：
  //   'does-not-exist'   → compare-swot
  //   'sequence-roadmap' → sequence-pyramid-simple（與名稱暗示的家族不同）
  // 使用者若打錯字或誤用家族簡寫，會拿到完全不相干的圖且毫無提示。
  // 因此此處要求必須使用 registry 內的完整模板名，並在錯誤訊息中揭露
  // 該名稱實際會被解析成什麼，讓使用者理解後果而非只是被拒絕。
  if (!entry) {
    let resolved = null;
    try {
      resolved = resolveTemplateKey(fig.template);
    } catch { /* 解析失敗則不附此資訊 */ }
    const prefix = (fig.template || '').split('-').slice(0, 2).join('-');
    const guess = Object.keys(reg.templates).filter((t) => t.startsWith(prefix)).slice(0, 3);
    errors.push(
      `模板「${fig.template}」不是 registry 的 276 個正式模板之一。`
      + (resolved && resolved !== fig.template
        ? `注意：引擎不會報錯，而會**靜默解析為「${resolved}」**，產出與預期不符的圖。`
        : '')
      + (guess.length ? `同家族可用者例如：${guess.join('、')}` : '')
    );
    return { errors, warnings, info };
  }
  info.expectedDataKey = entry.data_key;
  info.supportsDesc = entry.supports_desc;

  // --- 2. 資料鍵驗證（最重要：避免 10 秒無訊息 hang）---
  const data = fig.data || {};
  const presentKeys = Object.keys(data).filter((k) =>
    Array.isArray(data[k]) || KNOWN_HANG_KEYS.includes(k));

  const hangKeys = presentKeys.filter((k) => KNOWN_HANG_KEYS.includes(k));
  if (hangKeys.length) {
    errors.push(
      `資料鍵「${hangKeys.join('、')}」會使 SSR hang 住直到 10 秒 timeout 且不會報錯；`
      + `此模板應使用「${entry.data_key}」`
    );
  }

  const arrayKeys = presentKeys.filter((k) => !KNOWN_HANG_KEYS.includes(k));
  const unknown = arrayKeys.filter((k) => !VALID_KEYS.includes(k));
  if (unknown.length) {
    errors.push(
      `資料鍵「${unknown.join('、')}」不是已知的合法鍵（合法者：${VALID_KEYS.join('、')}）；`
      + `此模板應使用「${entry.data_key}」`
    );
  }

  if (arrayKeys.length && !arrayKeys.includes(entry.data_key)) {
    errors.push(
      `此模板應使用資料鍵「${entry.data_key}」，但輸入提供的是「${arrayKeys.join('、')}」`
    );
  }
  if (!presentKeys.length) {
    errors.push(`未提供任何項目陣列；此模板應使用資料鍵「${entry.data_key}」`);
  }

  // --- 3. desc 支援度（靜默丟棄警示）---
  const items = data[entry.data_key];
  if (Array.isArray(items) && !entry.supports_desc) {
    const withDesc = items.filter((it) => it && typeof it === 'object' && it.desc != null).length;
    if (withDesc > 0) {
      warnings.push(
        `模板「${fig.template}」不渲染 desc 欄位，輸入中有 ${withDesc} 筆 desc 會被靜默丟棄；`
        + `若需顯示描述文字，請改用支援 desc 的模板`
      );
    }
  }

  return { errors, warnings, info };
}

/** 供 CLI 使用：列出某模板的 registry 資訊 */
export function describeTemplate(name, assetsDir) {
  const reg = loadRegistry(assetsDir);
  return reg.templates[name] || null;
}
