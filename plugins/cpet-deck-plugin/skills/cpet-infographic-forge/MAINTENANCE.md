# cpet-infographic-forge 維運規範（maintainer: Casey）

> 給維護者（人與 AI）看，不影響 skill 執行。

## 版本紀律

- 功能性變更（新 recipe、新 QA 閘門、演算法改變）+0.1，SKILL.md 標題與
  CHANGELOG.md 末條同步。
- 同版 bug 修復不升版，於該版條目附記症狀、根因、驗證方式。
- 新增 recipe 時，`references/recipes.md` 與 `references/architecture.md`
  須同步補上該 recipe 的資料結構契約與擴充點說明，避免文件與程式碼分歧。

## 修改 `scripts/` 的流程

1. 複製到可寫路徑修改（不在唯讀掛載點直接編輯）。
2. Node 語法檢查（`node --check <檔案>`）。
3. 回寫後以 `node scripts/forge.mjs <job>.yaml` 跑一次既有測試 job，確認未破壞既有模板。
4. **以會踩到改動路徑的實際案例重跑**——渲染失敗多半是靜默的（見 SKILL.md「五個靜默
   失敗」），單元層面看不出來，必須實際產圖並過五道 QA 閘門：
   - `fontCoverage`：確認中文字型無 `NO GLYPH`
   - `aspect`：確認長寬比落在目標 slot 容許偏差內
   - `textOverflow`：確認 foreignObject 統計無溢出（engine route）
   - `textLegibility`：確認字級未低於可讀下限
   - `textCollision`（v1.1 新增第五道閘門）：確認跨區塊文字無重疊，正例
     （已知重疊案例）應 fail、反例（正常案例）應 pass，且無誤判
5. `references/pitfalls.md` 若新增一類靜默失敗，必須連同「怎麼用既有閘門或新增閘門
   偵測」一起記。
6. 新增 recipe 時，同步在 `scripts/recipe-runner.mjs` 的 `REGISTRY` 註冊，並確認
   `scripts/layout-solver.mjs` 若需要新的候選產生器已一併補上。
7. CHANGELOG.md 記錄 → 重新打包 .skill。

## `textCollision` 閘門的門檻校準（v1.1 新增機制的已知限制）

- 目前 8% 面積交集門檻只用少量樣本驗證方向正確，**尚未大規模校準**。若未來套用到
  更多模板／案例後發現誤判（正常版面被判定碰撞）或漏判（明顯重疊未攔截）比例偏高，
  應在 `check-text-collision.mjs` 的 `areaRatioThreshold` 調整前，先累積至少 10-20
  組已知正確答案的樣本記錄實際 `overlapRatio`，避免憑單一案例調參。
- **已知一筆疑似誤判樣本（2026-08-16 段2a驗證發現）**：`grid-matrix.mjs` 的預設
  label/desc 間距（`gapLabelDesc: 8*k`）在真實輸出上被 `textCollision` 判定為
  `overlapRatio 0.148`（超過 8% 門檻），但這是 recipe 原本設計的正常緊湊間距，
  非實際重疊。根因是本閘門的幾何估算公式（`top = y - fontSize*0.85`、
  `lineHeight = fontSize*1.4`）比 `grid-matrix.mjs` 實際使用的字型渲染更保守，
  兩個獨立系統的間距假設沒有互相校準。**這筆樣本本身不代表 `grid-matrix.mjs` 需要
  修改**，是門檻校準未來需要納入考量的具體案例，可作為第一批累積樣本之一。
- 只處理 `<g transform="translate()">` 造成的座標平移，不處理 `rotate()`／`scale()`。
  若未來模板庫新增旋轉文字，此檢查需要相應擴充，且擴充前的估算結果對含旋轉文字的
  模板不具參考價值（會低估或誤判重疊範圍）。
- 未處理刻意重疊的裝飾性元素（例如某些模板讓 icon 與文字輕微疊加當視覺效果）。若
  擴大套用到全部 276 個既有模板做批次回歸測試，遇到此類版面時需要加入排除規則。

## 字級自動貼合：逐文字獨立反推（v1.2 教訓，`data-table` 開發中發現）

`grid-matrix`／`vertical-flow`／`data-table` 皆用「文字佔可用寬度的目標比例」反推
字級，但**同一組文字（如一整列欄標題）若統一取最長字串反推、套用同一字級給全體**，
短字串會被長字串拖累——實測 `data-table` 5 欄方法名稱（8~20 字元）用統一字級策略時，
全部欄標題被壓到 10.2px（低於 11px 可讀下限），即使多數欄標題遠短於最長者。已在
`data-table.mjs` 修正為「逐文字獨立反推字級，不互相拖累」（見 `fitSizePerText()`）。
**`grid-matrix.mjs`／`vertical-flow.mjs` 目前仍是統一字級策略，未受此次修正影響**——
若未來這兩個既有 recipe 也遇到同類問題（同一組文字長度差異大導致集體縮字），可參考
`data-table.mjs` 的 `fitSizePerText()` 寫法修正，但不要不經查證就全面套用，因為
`grid-matrix`／`vertical-flow` 的統一字級目前是刻意的視覺一致性選擇（同一批卡片的
label 字級理應一致），與 `data-table` 欄標題各自獨立的情境不同。

## 已知環境風險

- Node 相依（`@antv/infographic`／`playwright`／`js-yaml`／`lucide-static`／`pngjs`）
  需要 `npm install` 才能執行；`playwright` 的 `view screenshot` 類功能另需瀏覽器
  二進位檔（`npx --no-install playwright install`）。**新環境／新 session 首次使用前務必確認
  `node_modules/` 已安裝**，否則整條 forge pipeline（`forge.mjs`／`qa-gate.mjs`／
  `recipe-runner.mjs`）無法執行。
- **相依鎖版與漏洞修補（2026-10-17 起）**：`package.json` 的直接相依一律寫精確版、
  不用 `^`／`~`（升版時改數字並重跑 `npm install`）；文件與腳本內的
  `npx` 一律加 `--no-install`，只用 lock 內版本。間接相依有漏洞時，用 `package.json`
  的 `overrides` 拉到上游修補版，不降級、不動上層套件版本；`package.json` 的
  `overrides` 目前只有 `source-map-js`。升級 `@antv/infographic` 或 `postcss` 時，
  先確認上游已自帶 ≥1.2.2 的 `source-map-js`，是的話就移除這筆 override。每次動
  相依都要跑 `npm audit`，並以同一份 job 比對修補前後的 SVG／PNG。
- 字型異動的中間狀態曾疑似造成渲染異常——環境準備一次到位安裝，不要中途增刪字型。
- 已安裝 skill 目錄唯讀：一律在專案資料夾維護完整結構 → 打包 → 重新安裝。
- 掛載點大檔寫入偶發尾端截斷：大檔先寫暫存區再複製，並做 md5 比對。
- **`python3` 指令名稱相依（2026-08-17 已解決，見下方）**：`measure-text.mjs`／
  `postprocess.mjs`／`qa-gate.mjs`／`forge.mjs` 原皆用 `execFileSync('python3', ...)`
  （或 `execSync` 拼接字串）呼叫 Python。部分環境只有 `python` 可執行檔、沒有
  `python3`，且 Windows 上若存在指向 Microsoft Store 重定向器的 `python3.exe`
  App Execution Alias，呼叫會失敗並印出「Python was not found」而非乾淨的
  「找不到指令」錯誤，容易誤導成「python3 完全沒裝」。`measure-text.mjs` 失敗時
  有保守回退估計（CJK 1em／拉丁 0.5em），不會中止渲染，但字級貼合精度下降；
  `checkFontCoverage` 失敗時回傳 `pass: null`（非 `false`），需視為「未驗證」而非
  「未過關」。**修法**：四支腳本改為 `const PYTHON_CMD = process.platform ===
  'win32' ? 'py' : 'python3'`，依平台選擇指令——Windows 用官方 launcher `py`
  （`C:\Windows\py.exe`，不受 App Execution Alias 影響），Linux/macOS（含
  Chat／Cowork 容器）維持 `python3`，兩邊互不影響。實測修正後 `measureTexts()`
  不再落入回退估計、`checkFontCoverage` 透過正式 `qa-gate.mjs` 管線可正確回傳
  `pass: true`（五個 recipe 代表案例皆已驗證，缺字 0）。
- **PNG 產出（2026-08-17 已解決：改用 playwright 取代 cairosvg）**：原
  `forge.mjs` 用 `execSync` 拼接 `python3 -c "import cairosvg; ..."` 做 SVG→PNG，
  有兩層獨立障礙：(a) `cairosvg` 需要底層原生函式庫 `libcairo-2.dll`，
  `pip install cairosvg` 只裝 Python 綁定層裝不到，本機確實缺席；(b) 字串拼接
  的 `python -c "..."` 指令中，Windows 路徑（`C:\Users\...`）的反斜線被 Python
  解析器誤判為 unicode escape（`\U`）而拋 `SyntaxError`。**修法**：新增
  `scripts/svg-to-png.mjs`，用 `playwright`（本技能 package.json 既有相依，
  非新增）驅動系統既有的 Edge／Chrome 做轉檔，依序嘗試 `msedge`→`chrome`→
  playwright 自帶 `chromium`。**不需要 `npx --no-install playwright install` 下載瀏覽器
  二進位檔**（省約 150MB），也不需要任何原生函式庫。瀏覽器的 SVG 渲染器對字型
  fallback／CSS／tspan 換行的支援亦優於 cairo toy API（後者不做逐字元 fallback，
  正是既有 NO GLYPH 問題根源之一）。`omitBackground: true` 維持透明底，符合
  forge-build 硬性規則。實測 `forge.mjs` 端到端 `qa.pass: True`、七項檢查全綠
  （含只有在 PNG 存在時才會跑的 `transparency` 四角 alpha 檢查）。
- **CJK 字型與 fontconfig 解析（2026-08-16 段2b發現、2026-08-17 已解決，見下一節）**：
  段2b階段 `check-font-coverage.py` 要求的字型堆疊確切名稱是 `"Noto Sans CJK TC"`，
  在本機環境查無此名（名稱不匹配讓 cairo fallback 到不相關字型），嘗試三種
  fontconfig 系統層級規則修正皆未成功（詳見下一節根因與嘗試記錄），段2b當時將
  `fontCoverage` 標示為未驗證。**2026-08-17 已透過改用本機/跨平台皆有的具名字型
  （Noto Sans TC／Noto Serif TC／Arial／Times New Roman）解決**，不再需要任何
  fontconfig 系統層級修改。以下記錄根因與已淘汰方案的除錯過程，供理解為何最終
  方案是「換字型名稱」而非「修 fontconfig」。

### 【已解決】CJK 字型 NO GLYPH 問題根因與最終方案（2026-08-17）

**根因**：`check-font-coverage.py`／`measure-text.py`／`foreignobject-to-text.py`
三支腳本呼叫 `fc-match` 做字型名稱解析，但 **Windows 原生無 fontconfig**，本機
唯一的 `fc-match` 來自 **TeX Live 2019** 隨附的最小化版本（僅為排版數學公式安裝，
`conf.d` 只有 1 個規則檔，未定義 `sans-serif` 等泛用族——標準 Linux fontconfig
此類規則有 40+ 個檔案）。技能本身與 TeX Live 無任何關聯，純粹是 Windows 缺乏
系統字型服務、被動撿到 TeX Live 提供的殘缺版本，導致泛用族查詢隨機落到
`Garamond-Math`（TeX Live texmf 樹內的數學符號字型，零中文 glyph）。這解釋了
為何同一份程式碼在 Chat／Cowork 的 Linux 容器上運作正常（有完整 fontconfig），
僅本機 Windows 環境異常。

**已淘汰方案**（按嘗試順序）：
1. `FONTCONFIG_FILE` 環境變數指向自製規則檔，補上缺失的泛用族定義——`fc-match`
   層級可修正大部分查詢，但 `sans-serif` 因 TeX Live fonts.conf 在 `<include>
   conf.d</include>` **之後**才套用 sans 改寫規則、優先序蓋過自訂規則而修不了；
   更根本的是即使 `fc-match` 修好，`check-font-coverage.py` 的
   `first_resolvable_family()` 仍用嚴格字串包含比對（`fam.lower() in
   matched.lower()`）判定命中，請求名與 fontconfig 實際回傳名不同（例如請求
   `Noto Sans CJK TC`、回傳 `Microsoft JhengHei,微軟正黑體`）一律判定未命中，
   單純 `<alias><accept>` 或 `FONTCONFIG_FILE` 覆寫無法通過此比對。
2. 安裝額外中文字型套件——`winget` 官方庫僅字型工具與商業字庫商管理程式，無
   可直接安裝的 Noto CJK 套件；`scoop`／`choco` 皆未安裝。不可行且無必要。
3. 標楷體（`DFKai-SB`，含 Casey 提供的 `字體/kaiu.ttf`，經 md5 比對與系統
   `C:/Windows/fonts/kaiu.ttf` 為同一檔案）——字元覆蓋完整（22,185 glyphs，
   中西文零缺字），但名稱在本機 fontconfig 查詢中文名「標楷體」與英文名
   「DFKai-SB」皆失敗（PostScript 名 `DFKaiShu-SB-Estd-BF` 同樣查無），問題
   在名稱解析而非字型檔或連字號轉義（對照實驗證實：假字型名不論有無連字號皆
   同樣 fallback，連字號非根因）。**技術上無解，非未試出**——複製檔案到專案
   內不改變結果，因 `fc-match` 查詢的是系統字型庫，不是專案資料夾；唯一解法
   是放寬 `check-font-coverage.py` 的嚴格比對，但那正是防止「fontconfig 亂
   fallback 卻假性通過」的核心設計，不建議為此犧牲。`字體/kaiu.ttf` 予以保留
   （規格禁止刪除），僅此處註記已評估結果。

**最終方案**：改用具名字型直接命中，繞過整個殘缺的泛用族解析鏈——查詢
`Noto Sans TC`／`Noto Serif TC`／`Arial`／`Times New Roman` 這類**具名、非
泛用**的字型，`fc-match` 對它們的解析在本機完全正常（不依賴 `sans-serif` 這
類需要規則集才能運作的泛用族）。四象限架構詳見 `postprocess.mjs` 檔頭註解與
下一節。

**可移植性**：Noto Sans TC／Noto Serif TC 為 Google 開源家族，Windows 11 內建，
Linux 由 `fonts-noto-cjk` 套件提供同名字型，Chat／Cowork 容器與本機 Windows
名稱一致。Arial／Times New Roman 為業界標準西文字型，各平台普遍內建。換執行
環境（例如未來在 Linux/macOS 執行 Claude Code）理論上不需調整，但**仍建議
重新跑 `checkFontCoverage` 驗證**，不假設「文件說可移植就一定沒事」。

## 四象限字型架構（v1.2 起，2026-08-17 由二分擴充為四分）

`postprocess.mjs` 的字型分流原僅二分「含不含中文」，現疊加「標題／內文」一層，
對齊 `cpet-yslai-pptx/references/lab-style-conventions.md` 的實驗室簡報規範
（標題用襯線體、內文用無襯線體）：

| | 西文 | 中文 |
|---|---|---|
| 標題（`font-weight >= 800`） | Times New Roman | Noto Serif TC |
| 內文（`font-weight < 800`） | Arial | Noto Sans TC |

判定依據是 recipe 產出 SVG 既有的 `font-weight` 慣例（900=主標題、800=次級
標題如欄標題/面板標題；700=強調格值、500=一般內文），**不需新增語意欄位**。
根層級 `<svg font-family="...">` 沒有 weight 可讀，一律視為內文（它只是
`<text>` 節點未自帶 `font-family` 時的最終 fallback）。

**與實驗室規範的已知偏離**：規範原文中文標題應為標楷體，但如上節所述技術
無解，改用風格最接近的 Noto Serif TC（襯線體）。若未來標楷體的名稱解析問題
獲得解決（例如換到有完整 fontconfig 的環境），可考慮改回，但需重新驗證
`fontCoverage` 而非直接沿用本文件的判斷——判斷本身是環境相依的。

**新增 recipe 時的字型注意事項**：`postprocess.mjs` 會覆蓋所有 `<text>` 的
`font-family`，故 recipe 內寫死的字型字串（如 SVG 根層級 `font-family="..."`）
僅為佔位，實際生效值以 `postprocess()` 呼叫端傳入或其預設值為準；但仍建議
recipe 內佔位字串與 `postprocess.mjs` 預設值保持一致（`Noto Sans TC, Arial,
sans-serif`），避免誤導未來維護者以為那才是實際生效的字型。

## 打包檢查清單

□ SKILL.md 標題版本號＝CHANGELOG.md 末條版本
□ 全部 .md 可完整 UTF-8 decode 且尾端正確
□ `node --check` 過全部 `scripts/*.mjs`
□ `node_modules/` 不入包（`.gitignore`／打包腳本皆排除，相依由使用端 `npm install`）
□ `__pycache__` 不入包
□ 五道 QA 閘門（含 `textCollision`）皆有至少一組正例/反例驗證紀錄可查
□ `data-table`／`dual-line-panel` 兩個 recipe 已在 `recipe-runner.mjs` 註冊，
  對應 `layout-solver.mjs` 候選產生器已補齊
□ 四象限字型（標題/內文 × 中/西）皆有實測 `checkFontCoverage` 通過紀錄
□ 打包後解 .skill 抽驗 SKILL.md 尾端
