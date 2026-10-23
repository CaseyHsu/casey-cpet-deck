import { writeFileSync, readFileSync, unlinkSync } from 'fs';
import { execFileSync } from 'child_process';
import { resolve, dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { tmpdir } from 'os';

// 2026-08-17：Windows 上 `python3.exe` 常是指向 Microsoft Store 安裝提示的
// App Execution Alias（非真正的 Python），呼叫會失敗且錯誤訊息具誤導性。
// Windows 官方 Python launcher `py` 不受此問題影響；Linux/macOS（含 Chat／
// Cowork 容器）維持慣用的 `python3`，兩邊互不影響。
const PYTHON_CMD = process.platform === 'win32' ? 'py' : 'python3';
/**
 * postprocess.mjs — M1/M2 修正後處理
 *
 * M1修正：剝除 <?xml-stylesheet?> 對 assets.antv.antgroup.com 的外連宣告，
 *         避免 SVG 若被當向量交付物開啟時連向中國網域。
 * M2修正：SSR 版面度量與實際渲染字型天生脫鉤（measury 離線字寬表 vs
 *         cairosvg 實際字型；loadFonts() 在 isNode 為真時直接 return，
 *         此限制無法透過本函式修復，只能緩解）。此函式將 font-family
 *         宣告換成本機已安裝的目標字型堆疊，讓「畫出來的字」使用正確
 *         字型，但版面框仍是用 measury 表算的，不會100%貼合。
 *
 * 【2026-08-17 四象限字型架構】原僅二分「含不含中文」，改為再疊加「標題／
 * 內文」一層，對齊 cpet-yslai-pptx 實驗室規範（lab-style-conventions.md
 * §標題／內文字型）：標題用襯線體、內文用無襯線體。判定依據是 recipe 產出
 * SVG 既有的 font-weight 慣例（900=主標題、800=次級標題如欄標題/面板標題，
 * 皆 >=800；700=強調格值、500=一般內文，皆 <800），不需新增語意欄位。
 *
 * 字型來源與根因記錄：原用 Noto Sans CJK TC（Ubuntu官方套件 fonts-noto-cjk）
 * ／Inter（fonts-inter），在 Chat／Cowork 的 Linux 容器上運作正常，但在
 * Windows 本機環境失敗——根因非字型本身，而是本機唯一的 `fc-match` 來自
 * TeX Live 2019 隨附的最小化 fontconfig（僅為排版數學公式安裝，conf.d 只有
 * 1 個規則檔，未定義 sans-serif 等泛用族），技能被動撿到這份殘缺設定，
 * 導致泛用族查詢落到不相關的 Garamond-Math。改用具名字型直接命中可繞過
 * 此問題。曾嘗試台北黑體但發布通路不可控、標楷體（DFKai-SB）因 fontconfig
 * 名稱查詢失敗技術無解，皆已捨棄，詳見 MAINTENANCE.md。
 *
 * 現用字型（2026-08-17 起）：Noto Sans TC／Noto Serif TC（Windows 11 內建，
 * 與 Linux fonts-noto-cjk 同名，跨平台可移植）＋ Arial／Times New Roman。
 */
export function postprocess(svg, {
  cjkFont = 'Noto Sans TC',
  latinFont = 'Arial',
  titleCjkFont = 'Noto Serif TC',
  titleLatinFont = 'Times New Roman',
  titleWeightMin = 800,
  convertForeignObject = true,
} = {}) {
  let out = svg;

  // M1：剝除全部外連 xml-stylesheet（不論指向何處）
  const before = (out.match(/<\?xml-stylesheet[^>]*\?>\n?/g) || []).length;
  out = out.replace(/<\?xml-stylesheet[^>]*\?>\n?/g, '');

  // M3（2026-07-31 新增）：foreignObject → 原生 <text> 轉寫
  //
  // engine route（@antv/infographic SSR）用 <foreignObject> + HTML <span>
  // 承載文字，而 cairosvg 是純 SVG 渲染器、不處理內嵌 HTML，導致該路線
  // 產出的 PNG 文字全部消失（實測文字色像素數為 0）。此步驟將其轉寫為
  // 原生 <text>/<tspan>，使 cairosvg 能正確渲染。
  //
  // 可行性依據：跨 5 大類 12 個代表模板抽樣調查，foreignObject 內部一律
  // 為「單層 span + 純文字」、巢狀深度 1、CSS 屬性全集僅 15 個，且
  // x/y/width/height 已由引擎算好，轉寫器無須重做版面計算。
  let foStats = null;
  if (convertForeignObject && /<foreignObject\b/.test(out)) {
    // 2026-09-20：原本寫死 `/tmp/...`，在 Windows 原生 Node 上會解析成
    // 「目前磁碟機根目錄 + 	mp」（實測為 `I:	mp`），該目錄不存在。此處的
    // 例外被下方 catch 吞進 foStats.error，foreignObject 轉寫會靜默跳過，
    // engine route 產出的 PNG 文字全部消失而不報錯。改用 os.tmpdir()。
    const tmpIn = join(tmpdir(), `fo-${process.pid}-${Date.now()}.svg`);
    try {
      writeFileSync(tmpIn, out);
      const raw = execFileSync(
        PYTHON_CMD,
        [resolve(dirname(fileURLToPath(import.meta.url)), 'foreignobject-to-text.py'),
         tmpIn, tmpIn, '--stats-json'],
        { encoding: 'utf-8' }
      );
      foStats = JSON.parse(raw);
      out = readFileSync(tmpIn, 'utf-8');
    } catch (e) {
      foStats = { error: e.message };
    } finally {
      try { unlinkSync(tmpIn); } catch { /* ignore */ }
    }
  }

  // M2緩解：替換 font-family 為本地已安裝字型堆疊
  //
  // 【2026-07-31 NO GLYPH 根因，判定原則不變】
  //   1. cairosvg 走 cairo 的 "toy" text API，不做逐字元 font fallback，
  //      只會解析出單一字型面，即堆疊中第一個可解析到的字型。
  //   2. 純西文字型（Inter／Arial／Times New Roman）不含 CJK 字元，若排在
  //      堆疊第一位、又遇到中文節點，該中文會落到 .notdef glyph。
  //   3. 故 CJK 字型必須排在「含中文節點」堆疊的最前面；純西文節點則讓
  //      西文字型排最前面（西文字型的西文字形通常優於 CJK 字型內附的西文）。
  //
  // 【2026-08-17 四象限擴充】在上述「含不含中文」判斷之外，疊加一層
  // 「font-weight 是否達標題門檻」，決定該用襯線體（標題）還是無襯線體
  // （內文）——對齊 cpet-yslai-pptx 實驗室規範的標題／內文字型區分。
  // 根層級 <svg font-family="..."> 沒有 font-weight 可讀，一律視為內文
  // （根層級只作為 <text> 未自帶 font-family 時的 fallback，不影響任何
  // 已標明 weight 的節點）。
  const CJK_RE = /[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/;
  const stackFor = (isCjk, isTitle) => {
    if (isCjk) {
      return isTitle ? `${titleCjkFont}, ${titleLatinFont}, sans-serif`
                      : `${cjkFont}, ${latinFont}, sans-serif`;
    }
    return isTitle ? `${titleLatinFont}, ${titleCjkFont}, sans-serif`
                    : `${latinFont}, ${cjkFont}, sans-serif`;
  };

  // 根層級 <svg font-family="..."> 統一改為內文中文堆疊（未帶 weight，
  // 且是所有節點的最終 fallback，不應假設是標題）。
  out = out.replace(
    /(<svg\b[^>]*\bfont-family=")[^"]*(")/,
    `$1${stackFor(true, false)}$2`
  );

  out = out.replace(/<text\b([^>]*)>([\s\S]*?)<\/text>/g, (full, attrs, inner) => {
    const plain = inner.replace(/<[^>]*>/g, '');
    const isCjk = CJK_RE.test(plain);
    const weightMatch = attrs.match(/font-weight="(\d+)"/);
    const weight = weightMatch ? parseInt(weightMatch[1], 10) : 0;
    const isTitle = weight >= titleWeightMin;
    const stack = stackFor(isCjk, isTitle);
    if (/font-family=/.test(attrs)) {
      return `<text${attrs.replace(/font-family="[^"]*"/, `font-family="${stack}"`)}>${inner}</text>`;
    }
    return `<text${attrs} font-family="${stack}">${inner}</text>`;
  });

  return { svg: out, strippedExternalRefs: before, foreignObject: foStats };
}
