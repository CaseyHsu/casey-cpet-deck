/**
 * qa-gate.mjs — 圖檔品質閘門
 *
 * 整合先前對話中以手動一次性指令驗證過的三項檢查，
 * 正式封裝成可重複呼叫的閘門函式：
 *   1. 長寬比偏差（對照 catalog 建議 slot）
 *   2. 透明底檢查（PNG 四角 alpha 須為 0）
 *   3. 外連殘留檢查（SVG 不得含外部 URL）
 */
import { readFileSync } from 'fs';
import { execFileSync } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { checkTextCollision } from './check-text-collision.mjs';

// 2026-08-17：Windows 上 `python3.exe` 常是指向 Microsoft Store 安裝提示的
// App Execution Alias（非真正的 Python），呼叫會失敗且錯誤訊息具誤導性。
// Windows 官方 Python launcher `py` 不受此問題影響；Linux/macOS（含 Chat／
// Cowork 容器）維持慣用的 `python3`，兩邊互不影響。
const PYTHON_CMD = process.platform === 'win32' ? 'py' : 'python3';

export const SLOT_AR = {
  full: 2.31,
  'full-tw': 2.63,
  half: 1.29,
  quad: 2.94,
  twocol: 1.18,
};

/** 長寬比偏差檢查（面積浪費比） */
export function checkAspect(actualAspect, slot, threshold = 0.25) {
  const target = SLOT_AR[slot];
  if (!target) return { pass: true, reason: `未知 slot「${slot}」，略過此項檢查` };
  const deviation = Math.max(actualAspect, target) / Math.min(actualAspect, target) - 1;
  const result = {
    pass: deviation <= threshold,
    deviation: +deviation.toFixed(3),
    target,
    actual: actualAspect,
  };

  // 不合格時直接給出最適 slot 建議，讓結果可行動。
  // recipe route 可透過 layout-solver 主動貼合目標長寬比；engine route 的
  // 版面由第三方模板決定、無法調整，此時唯一的補救就是換用比例相符的 slot。
  if (!result.pass) {
    const best = Object.entries(SLOT_AR)
      .map(([name, ar]) => ({
        slot: name,
        deviation: +(Math.max(actualAspect, ar) / Math.min(actualAspect, ar) - 1).toFixed(3),
      }))
      .sort((a, b) => a.deviation - b.deviation)[0];
    result.recommendedSlot = best.deviation <= threshold ? best : null;
    if (!result.recommendedSlot) {
      result.note = `實際長寬比 ${actualAspect} 超出所有 slot 的容許範圍`
        + `（最接近者 ${best.slot} 偏差仍達 ${best.deviation}），`
        + `建議改用比例較接近的模板或拆分內容`;
    }
  }
  return result;
}

/** 外連殘留檢查：SVG 原始碼不得含任何 http(s):// URL
 *  （排除 SVG/XHTML/XLink 等規範必需的命名空間宣告，避免誤報） */
const NAMESPACE_ALLOWLIST = [
  'http://www.w3.org/2000/svg',
  'http://www.w3.org/1999/xhtml',
  'http://www.w3.org/1999/xlink',
  'http://www.w3.org/XML/1998/namespace',
];
export function checkNoExternalRefs(svgString) {
  const all = svgString.match(/https?:\/\/[^\s"'<>]+/g) || [];
  const urls = all.filter((u) => !NAMESPACE_ALLOWLIST.includes(u));
  return { pass: urls.length === 0, foundUrls: urls };
}

/**
 * 透明底檢查：需要實際像素資料（PNG buffer 經 decode），
 * 這裡用輕量 PNG 頭部+像素掃描避免引入完整影像處理套件依賴。
 * 若環境有 sharp/pillow 等更完整工具，可替換此函式實作。
 */
export async function checkTransparentCorners(pngPath) {
  const { PNG } = await import('pngjs');
  const buf = readFileSync(pngPath);
  const png = PNG.sync.read(buf);
  const corners = [
    [1, 1],
    [png.width - 2, 1],
    [1, png.height - 2],
    [png.width - 2, png.height - 2],
  ];
  const alphas = corners.map(([x, y]) => {
    const idx = (png.width * y + x) << 2;
    return png.data[idx + 3];
  });
  return { pass: alphas.every((a) => a === 0), alphas };
}

/** 缺字檢測：簡易版，檢查 SVG text 節點是否含常見缺字替代符號（tofu / □ / ?)
 *  限制：只查 SVG 原始碼，抓不到轉檔後才出現的 PNG 層級渲染異常
 *  （如 cairosvg 字型查找失敗時繪出的「NO GLYPH」方框）——
 *  這類異常須用 checkFontCoverage() 檢查，見下方。 */
export function checkMissingGlyphs(svgString) {
  const texts = [...svgString.matchAll(/<text[^>]*>([^<]*)<\/text>/g)].map((m) => m[1]);
  const suspicious = texts.filter((t) => /\uFFFD|□|�/.test(t));
  return { pass: suspicious.length === 0, suspiciousTexts: suspicious };
}

/**
 * PNG 層級缺字渲染檢查：呼叫 check-glyph-render.py 做視覺特徵掃描，
 * 偵測轉檔引擎（如 cairosvg）字型查找失敗時繪出的「深色矩形＋白色
 * 線條」NO GLYPH 特徵方塊。這是 SVG 原始碼層級檢查（checkMissingGlyphs）
 * 的必要補充，因為 SVG 乾淨不保證轉檔後的 PNG 乾淨。
 *
 * 啟發式偵測，非 OCR，可能有偽陽性（需人工複核 suspiciousRegions）。
 * 詳見 check-glyph-render.py 內文件註解。
 */
/*
 * 註：此處原有 checkPngGlyphRender()（PNG 像素啟發式偵測 NO GLYPH 方框），
 * 已於 v1.0 移除。原因：門檻無法校準，實測對「整片都是 NO GLYPH 方框」的圖
 * 仍回報 pass（方框內含白色文字，深色連通區填充率達不到判定門檻），
 * 是不可信賴的假保護。改由下方確定性的 checkFontCoverage() 承擔此職責。
 * 詳見 references/pitfalls.md 附錄「失效的檢查方法」。
 */

/**
 * 【主閘門】SVG 字型 glyph 覆蓋率檢查（確定性，取代上述啟發式偵測）
 *
 * 模擬 cairo toy text API 的字型選擇（不做逐字元 fallback，只取堆疊中
 * 第一個可解析的實體字型），再用 fontTools 讀該字型 cmap 逐字比對，
 * 於轉檔前100%確定哪些字會落到 .notdef（即 NO GLYPH 方框）。
 * 同時偵測 <foreignObject>——cairosvg 不渲染其內嵌 HTML，該區塊文字
 * 會整段消失，且此時 SVG 內可能一個 <text> 都沒有而假性通過。
 *
 * 這道檢查是 NO GLYPH 類問題的正確閘門；
 * checkMissingGlyphs()（只掃替代字元）已證實對本類問題無效——SVG 原始碼
 * 永遠乾淨，故該檢查永遠 pass；保留僅為偵測真正的替代字元，不作為
 * NO GLYPH 類問題的判定依據。
 */
export function checkFontCoverage(svgPath) {
  const scriptPath = resolve(dirname(fileURLToPath(import.meta.url)), 'check-font-coverage.py');
  const parse = (buf) => {
    const p = JSON.parse(buf.toString());
    return {
      pass: p.pass,
      textNodeCount: p.text_node_count,
      missingGlyphNodes: p.missing_glyph_nodes,
      foreignObject: p.foreign_object,
      fontResolution: p.font_resolution,
    };
  };
  try {
    return parse(execFileSync(PYTHON_CMD, [scriptPath, svgPath, '--json'], { encoding: 'utf-8' }));
  } catch (e) {
    if (e.stdout) {
      try { return parse(e.stdout); } catch { /* fallthrough */ }
    }
    return { pass: null, reason: `無法檢查（${e.message}），需確認 fontTools 已安裝` };
  }
}

/** 整合閘門：回傳整體 pass/fail 與各項細節 */
/**
 * 文字溢出檢查：轉寫器以真實字型度量斷行後，若總文字高度超過引擎為該
 * foreignObject 預留的框高，代表輸入文字量超出此模板的設計容量。
 *
 * 【判定依據，非渲染錯誤】
 * 引擎對 foreignObject 同時設定 overflow="visible" 與 CSS overflow:visible，
 * 設計上允許文字超出框顯示，故溢出不會被裁切、文字不會遺失；但過度溢出
 * 會壓到相鄰元件而破壞版面。實測短/中長度文字溢出率 0%、長句 41.5%，
 * 證明模板對合理長度有足夠容量，溢出是「內容與模板不匹配」的訊號。
 *
 * 因此本檢查預設以警示（pass=true + warn）呈現，僅在嚴重溢出（超過框高
 * 2 倍）時判為 fail，避免把可接受的輕微溢出當成阻擋性錯誤。
 */
export function checkTextOverflow(foStats, severeRatio = 2.0) {
  const overflow = foStats.overflow || [];
  const widthOverflow = foStats.width_overflow || [];
  const severe = overflow.filter((o) => o.overflow_ratio >= severeRatio);
  return {
    pass: severe.length === 0,
    converted: foStats.converted || 0,
    overflowCount: overflow.length,
    severeCount: severe.length,
    widthOverflowCount: widthOverflow.length,
    worst: overflow.length
      ? overflow.reduce((a, b) => (b.overflow_ratio > a.overflow_ratio ? b : a))
      : null,
    note: overflow.length
      ? '文字量超出模板設計容量；引擎設 overflow:visible 故文字不會遺失，但可能壓到相鄰元件，建議縮短文字或改用容量較大的家族'
      : undefined,
  };
}

/**
 * 字級可讀性檢查（確定性）
 *
 * 補的是一個實測發現的盲區：recipe route 的字級自動貼合為避免溢出，
 * 會在文字過長時持續縮小字級。此機制確實防住了溢出（實測 0.0px），
 * 但可能把字級壓到 8px 這種簡報上根本讀不到的程度——而溢出檢查
 * (textOverflow) 只吃 engine route 的 foreignObject 統計，字級縮小
 * 又不算溢出，導致 QA 全綠卻產出不可用的圖。
 *
 * 縮字時 recipe 雖會 console.warn，但該訊息不進 manifest，批次產圖
 * 時會被完全錯過，故必須有一道進得了 manifest 的檢查。
 *
 * 【門檻依 route 而異，理由】
 * 抽樣 30 個 engine 模板發現 6 個（20%）原生就使用 10px 字級——那是模板
 * 本身的設計選擇，並非縮字病徵。若對兩條 route 套用同一門檻，engine route
 * 會產生約 20% 的誤報，使用者很快就會學會忽略這道檢查，反而讓它失去作用。
 *   - recipe route：門檻 11px。字級由本技能控制，低於此值即代表內容量
 *     超出版面容納能力，是需要處理的訊號。
 *   - engine route：門檻 10px。尊重模板既有設計，只攔明顯異常。
 */
export function checkTextLegibility(svgString, route = 'engine') {
  const minSize = route === 'recipe' ? 11 : 10;
  const sizes = [...svgString.matchAll(/font-size="([\d.]+)"/g)]
    .map((m) => +m[1])
    .filter((n) => Number.isFinite(n) && n > 0);
  if (!sizes.length) return { pass: true, reason: '無顯式 font-size，略過此項檢查' };
  const tooSmall = sizes.filter((s) => s < minSize);
  return {
    pass: tooSmall.length === 0,
    minSize,
    smallest: Math.min(...sizes),
    tooSmallCount: tooSmall.length,
    route,
    note: tooSmall.length
      ? `有 ${tooSmall.length} 處字級低於可讀下限 ${minSize}px（最小 ${Math.min(...sizes)}px）`
        + (route === 'recipe'
          ? '，通常肇因於文字過長觸發自動縮字；建議縮短文字、減少欄數或改用較寬的 slot'
          : '；此為模板既有設計，若簡報上讀不清請改用字級較大的模板')
      : undefined,
  };
}

export async function runQaGate({
  svgString, svgPath, pngPath, aspect, slot, threshold, foreignObjectStats, route,
}) {
  const results = {
    aspect: checkAspect(aspect, slot, threshold),
    externalRefs: checkNoExternalRefs(svgString),
    glyphs: checkMissingGlyphs(svgString),
    textLegibility: checkTextLegibility(svgString, route),
    // 第五道閘門（新增）：跨區塊文字碰撞。既有四道閘門都只檢查「單一文字區塊
    // 內部」的問題（缺字、溢出、字級過小），從未檢查標題／副標／欄位之間是否
    // 互相疊壓——這正是 fig-scope-placement.svg 實測案例的失效模式：四道閘門
    // 全綠，但標題與雙欄標題在渲染後直接糊成一團，只有人工看 PNG 才發現。
    textCollision: checkTextCollision(svgString),
  };
  if (svgPath) {
    results.fontCoverage = checkFontCoverage(svgPath);
  }
  if (foreignObjectStats && !foreignObjectStats.error) {
    results.textOverflow = checkTextOverflow(foreignObjectStats);
  }
  if (pngPath) {
    try {
      results.transparency = await checkTransparentCorners(pngPath);
    } catch (e) {
      results.transparency = { pass: null, reason: `無法檢查（${e.message}），需安裝 pngjs` };
    }
  }
  const overallPass = Object.values(results).every((r) => r.pass !== false);
  return { pass: overallPass, checks: results };
}
