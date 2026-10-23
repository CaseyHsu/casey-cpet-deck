/**
 * svg-to-png.mjs — SVG → PNG 轉檔（playwright 驅動既有瀏覽器）
 *
 * 【為什麼不用 cairosvg】
 * 原實作為 `python3 -c "import cairosvg; cairosvg.svg2png(...)"`，有兩個問題：
 *   1. `cairosvg` 需要底層 C 函式庫 `libcairo-2.dll`（Windows）／`libcairo.so.2`
 *      （Linux）。`pip install cairosvg` 只裝 Python 綁定層，裝不到原生函式庫，
 *      Windows 上通常缺席（實測本機確實缺，`import cairosvg` 直接 OSError）。
 *   2. 原本用 `execSync` 字串拼接組 `python -c "..."` 指令，Windows 路徑的反斜線
 *      會被 Python 解析器誤判為 unicode escape（`C:\Users\...` 的 `\U`）而拋
 *      SyntaxError——這是拼接式呼叫的固有脆弱性。
 *
 * 【改用 playwright 的理由】
 * `playwright` 本來就是本技能 package.json 宣告的相依（原為 screenshot 類功能），
 * 不新增任何外部相依；且可用 `channel` 驅動系統既有的 Edge／Chrome，**不需要
 * 下載 playwright 自帶的 chromium 二進位檔**（省下約 150MB 與一次網路下載）。
 * 瀏覽器的 SVG 渲染器對字型 fallback、CSS、tspan 換行的支援也比 cairo toy API
 * 完整——cairo 不做逐字元 font fallback，那正是既有 NO GLYPH 問題的根源之一。
 *
 * 【透明底】
 * `omitBackground: true` 使留白處保持 alpha=0，符合 forge-build 硬性規則
 * （qa-gate 的 checkTransparentCorners 會驗四角 alpha 必須為 0）。
 */
import { readFileSync } from 'fs';

/** 依序嘗試的瀏覽器 channel；皆失敗才退回 playwright 自帶 chromium */
const CHANNELS = ['msedge', 'chrome', 'chromium'];

/**
 * 把 SVG 檔轉成 PNG。
 *
 * @param {string} svgPath 來源 SVG 路徑
 * @param {string} pngPath 目標 PNG 路徑
 * @param {object} [opts]
 * @param {number} [opts.width]  目標寬（px）；未給則用 SVG viewBox 尺寸
 * @param {number} [opts.height] 目標高（px）
 * @returns {Promise<{channel: string, width: number, height: number}>}
 */
export async function svgToPng(svgPath, pngPath, opts = {}) {
  const { chromium } = await import('playwright');
  const svg = readFileSync(svgPath, 'utf-8');

  // 由 viewBox 取得原生尺寸，作為 viewport 與縮放基準
  const vb = svg.match(/viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"/);
  const natW = vb ? parseFloat(vb[1]) : 1200;
  const natH = vb ? parseFloat(vb[2]) : 800;

  // 目標解析度：呼叫端給了就用，否則用原生尺寸。以 deviceScaleFactor 放大而非
  // 改 viewport，可避免 SVG 內部依 viewport 做的相對佈局被改變。
  const outW = opts.width || natW;
  const outH = opts.height || natH;
  const scale = Math.max(outW / natW, outH / natH, 1);

  let browser = null;
  let usedChannel = null;
  let lastErr = null;
  for (const channel of CHANNELS) {
    try {
      // chromium 為 playwright 自帶（需 npx --no-install playwright install），不指定 channel
      browser = channel === 'chromium'
        ? await chromium.launch()
        : await chromium.launch({ channel });
      usedChannel = channel;
      break;
    } catch (e) {
      lastErr = e;
    }
  }
  if (!browser) {
    throw new Error(
      '找不到可用的瀏覽器（已嘗試 msedge／chrome／playwright chromium）。'
      + '請安裝 Microsoft Edge 或 Google Chrome，或執行 `npx --no-install playwright install chromium`。'
      + `最後錯誤：${lastErr?.message?.split('\n')[0] ?? '未知'}`
    );
  }

  try {
    const page = await browser.newPage({
      viewport: { width: Math.ceil(natW), height: Math.ceil(natH) },
      deviceScaleFactor: scale,
    });
    // margin:0 避免 body 預設邊距讓截圖多出白邊
    await page.setContent(
      `<!doctype html><html><body style="margin:0">${svg}</body></html>`,
      { waitUntil: 'load' }
    );
    const el = await page.$('svg');
    if (!el) throw new Error(`SVG 根節點找不到：${svgPath}`);
    // 對 <svg> 元素本身截圖（非整頁），確保輸出邊界與圖形邊界一致
    await el.screenshot({ path: pngPath, omitBackground: true });
    return { channel: usedChannel, width: Math.round(natW * scale), height: Math.round(natH * scale) };
  } finally {
    await browser.close();
  }
}
