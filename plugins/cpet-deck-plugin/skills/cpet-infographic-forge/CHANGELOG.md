# cpet-infographic-forge 版本履歷（Changelog）

> 維護者文件，skill 執行時不載入。撰寫紀律見 `MAINTENANCE.md`。

- **v1.0**（2026-08-02）：首次打包。276 個 engine 模板＋3 個 recipe（circle-cycle／
  grid-matrix／vertical-flow），四道 QA 閘門（fontCoverage／aspect／textOverflow／
  textLegibility），長寬比自動求解（`layout-solver.mjs`）與 slot 對齊（`fit.mjs`）。

- **v1.1**（2026-08-16）：CPET 簡報工作流整備任務段2a——套用兩項已驗證修復＋補齊本檔案。
  (1) **新增第五道 QA 閘門 `textCollision`**（`scripts/check-text-collision.mjs`，新檔案）：
  既有四道閘門僅檢查「單一文字區塊內部」問題（缺字、溢出、字級過小），從未檢查跨區塊
  之間是否互相疊壓——實測案例（另一任務的 `fig-scope-placement.svg`）顯示主標題與雙欄
  標題垂直重疊糊字，四道既有閘門全數 PASS，只有人工看 PNG 才發現。新閘門用 tag walker
  追蹤 SVG `<g transform="translate()">` 巢狀平移取得每個 `<text>` 節點絕對座標，依
  CJK≈1em／拉丁≈0.55em 估算 bounding box，兩兩比對交集面積，超過兩者中較小者 8% 判定
  碰撞。已掛載於 `scripts/qa-gate.mjs`（僅新增 1 行 import＋5 行掛載程式碼）。
  (2) 動機：這是規格 `archived/提案改善/技能改善分析_build_deck與forge_2026-08-12.md` 第二節
  記載的已實作修復，本次套用回技能原始碼並成為打包基準；門檻（8% 面積交集）尚未大規模
  校準，僅用兩個歷史樣本驗證方向正確，詳見 `MAINTENANCE.md`「已知限制」。
  (3) 補建本檔案與 `MAINTENANCE.md`——v1.0 打包時缺漏，經
  `2026-08-13_software-architecture_cpet-deck-workflow-overhaul_v2.md` 查證確認後補齊。
  (4) **段2a重跑驗證時發現並修正 `check-text-collision.mjs` 的 `extractTextBoxes()`
  邏輯缺陷**：原實作只在文字被 `<tspan>` 包裹時才讀取內容，若 `<text>純文字</text>`
  （無 tspan，直接文字）該節點的 `lines` 是空陣列、bounding box 寬度算成 0——形同
  「這個文字節點永遠不會被判定碰撞」。這不是 edge case：既有三個 recipe
  （`grid-matrix.mjs`／`circle-cycle.mjs`／`vertical-flow.mjs`）的短標題與 desc
  文字全部是純文字、不用 tspan 包裹，是 recipe route 的主流格式，代表此閘門套用
  修補檔當下對 recipe 產出的單行文字節點形同虛設。原分析文件驗證只用了兩個 engine
  route 的 SVG 樣本（皆恰好用 tspan），未覆蓋到這個 recipe route 常態情況。已修正
  `extractTextBoxes()`：`</text>` 關閉時若期間未遇到任何 `<tspan>`，回頭取出
  `<text>` 開始標籤結束位置到 `</text>` 之間的原始文字當作一行。修正後在真實
  `grid-matrix.mjs` 輸出上找到 3 組 label/desc 的估算重疊（`overlapRatio 0.148`），
  核算為 `textCollision` 估算公式（`fontSize*0.85`／`fontSize*1.4`）與
  `grid-matrix.mjs` 實際排版間距（`gapLabelDesc: 8*k`）之間的落差，非
  `grid-matrix.mjs` 本身有問題——這正是門檻尚未校準的實例，記入
  `MAINTENANCE.md`「門檻校準」一節，供未來累積樣本後調整。
  驗證：見 D2 技能更新異動報告（`提案改善/技能更新異動報告_2026-08-13.md`）之回歸驗證
  記錄。

- **v1.2**（2026-08-16）：CPET 簡報工作流整備任務段2b——新增兩個 recipe 補齊模板庫
  結構性缺口，皆為 Casey 2026-08-13 裁決之 in-scope 項目。
  (1) **`data-table`**（缺口一：二維矩陣表格）：`recipes/data-table.mjs` 新檔案，
  資料結構 `cols`(欄) × `rows`(列) × `cells`(二維陣列)，支援 `highlightRow`／
  `highlightCol` 整列／整欄高亮（雙重編碼：底色＋描邊，符合規格配色硬規則的
  灰階可辨識要求）。與既有 `grid-matrix` 的本質差異：後者 `cells` 是一維卡片
  陣列，無法表達列×欄的二維語意。字級貼合採「逐文字獨立反推」而非統一取最長
  字串套用全體——開發過程中實測發現統一策略會讓短欄標題（如「Proposed」）被
  最長欄標題（如「Regularization-based」）拖累觸底，修正後短字串各自使用能
  撐住的字級。`scripts/layout-solver.mjs` 新增 `dataTableCandidates()` 候選
  產生器。
  (2) **`dual-line-panel`**（缺口二：雙軸折線圖）：`recipes/dual-line-panel.mjs`
  新檔案，支援多 series、各自獨立 y 軸範圍、參考線（含標籤）、關鍵資料點標註，
  單面板或雙面板並列皆可。`scripts/layout-solver.mjs` 新增
  `dualLinePanelCandidates()` 候選產生器。
  (3) 兩者皆註冊進 `scripts/recipe-runner.mjs` 的 `REGISTRY`。
  (4) 驗收案例：`references/acceptance-cases/` 下留檔兩組輸入 JSON 與產出 SVG
  （5方法×7維度比較矩陣、絕對誤差vs相對誤差雙面板折線圖）。兩案例皆通過四道
  可執行的 QA 閘門（`aspect`／`textLegibility`／`textCollision`／`glyphs`+
  `externalRefs`）；第五道 `fontCoverage` 因本機環境限制未能驗證（見
  `MAINTENANCE.md`「已知環境風險」，非 recipe 本身缺陷）。
  (5) 驗收案例的矩陣方向（方法橫向排列為欄、比較維度縱向排列為列，Proposed
  整欄高亮）依 Casey 提供的實際論文比較表慣例確認——原規格文字「Proposed整欄
  強調」與改善建議文件「方法橫向對比維度」的描述初看有落差，經確認兩者實為
  一致描述（方法=欄、維度=列），已釐清。
  驗證：見 D2 技能更新異動報告之段2b章節。

- **v1.3**（2026-08-17）：`fontCoverage` 閘門本機環境未驗證問題已解決——改用
  跨平台皆有的具名字型，並將字型分流由「含不含中文」二分擴充為「標題／內文
  × 中／西」四象限，對齊 `cpet-yslai-pptx` 實驗室簡報規範。
  (1) **根因查明**：三支腳本（`check-font-coverage.py`／`measure-text.py`／
  `foreignobject-to-text.py`）呼叫 `fc-match` 做字型解析，但 Windows 原生無
  fontconfig，本機唯一來源是 **TeX Live 2019** 隨附的最小化版本（僅為排版
  數學公式安裝，未定義 `sans-serif` 等泛用族），技能被動撿到此殘缺設定，
  導致泛用族查詢落到不相關的 `Garamond-Math`。技能本身與 TeX Live 無任何
  關聯，此為 Windows 環境意外，非設計如此——Chat／Cowork 的 Linux 容器有
  完整 fontconfig，故同一份程式碼在該環境運作正常。
  (2) **`postprocess.mjs` 由二參數擴充為四參數**（`cjkFont`／`latinFont`／
  `titleCjkFont`／`titleLatinFont`／`titleWeightMin`），依 `font-weight`
  是否 >=800（既有 recipe 慣例：900/800=標題、700/500=內文）疊加標題/內文
  判定，形成四象限：標題西文 Times New Roman、標題中文 Noto Serif TC、
  內文西文 Arial、內文中文 Noto Sans TC。既有 CJK-first 防 NO GLYPH 判定
  原則不變，僅追加 weight 維度。
  (3) `scripts/measure-text.mjs`／`measure-text.py` 預設 `family` 同步更新
  為 `Noto Sans TC, Arial, sans-serif`；五個 recipe 檔案內寫死的佔位字型
  字串（會被 postprocess 覆蓋，僅供閱讀，見 MAINTENANCE.md 說明）一併更新，
  避免誤導維護者。
  (4) **與實驗室規範的已知偏離**：規範中文標題應為標楷體（DFKai-SB），
  但實測其字型名稱在本機 fontconfig（中文名「標楷體」與英文名皆查無）技術
  無解，改用風格最接近的 Noto Serif TC（襯線體）。已嘗試 Casey 提供的
  `字體/kaiu.ttf`（與系統 `C:/Windows/fonts/kaiu.ttf` md5 相同，非檔案
  缺失問題）與 3 種 fontconfig 系統層級修正方案，皆已窮盡仍無解，詳細
  除錯記錄見 `MAINTENANCE.md`。
  (5) 驗證：段2b兩個驗收案例（`data-table`／`dual-line-panel`）與既有三個
  recipe（`grid-matrix`／`vertical-flow`／`circle-cycle`）各一代表案例，
  逐節點核對四象限分流確實生效（weight>=800+中文→Noto Serif TC、
  weight>=800+西文→Times New Roman、weight<800+中文→Noto Sans TC、
  weight<800+西文→Arial）。**注意**：此版驗證是繞過 `qa-gate.mjs`、
  直接以 `python`（非 `python3`）手動呼叫 `check-font-coverage.py` 取得
  `pass=True`——證實字型分流邏輯正確，但透過正式 `qa-gate.mjs` 管線呼叫
  仍因 `python3` 指令問題回傳 `pass: null`，此落差已於 v1.4 訂正並解決。
  `aspect`／`textLegibility`／`textCollision` 三道既有閘門重跑確認未
  因字型變更而回歸破壞。PNG 產出仍受阻於 libcairo 原生函式庫缺失
  （獨立環境問題，不受本次字型變更影響，維持未驗證）。

- **v1.4**（2026-08-17）：`fontCoverage` 透過正式 `qa-gate.mjs` 管線仍回傳
  `pass: null` 的問題已解決（v1.3 遺留落差，Casey 要求訂正）。
  (1) **`measure-text.mjs`／`postprocess.mjs`／`qa-gate.mjs`／`forge.mjs`
  四支腳本**新增 `const PYTHON_CMD = process.platform === 'win32' ? 'py' :
  'python3'`，所有 `execFileSync('python3', ...)`／`execSync('python3 ...')`
  呼叫改用此常數。根因：Windows 上 `python3.exe` 常是指向 Microsoft Store
  安裝提示的 App Execution Alias（非真正 Python），Windows 官方 launcher
  `py`（`C:\Windows\py.exe`）不受此問題影響；Linux/macOS（含 Chat／Cowork
  容器）維持 `python3` 不變，兩邊互不影響。
  (2) 驗證：透過**正式 `qa-gate.mjs` 的 `runQaGate()`**（非繞道測試）對
  段2b兩驗收案例與既有三個 recipe 共五案例逐一測試，`fontCoverage` 全數
  `pass: true`、`missingGlyphNodes: []`；`measureTexts()` 亦確認不再落入
  保守回退估計（實際呼叫 fontTools 量測），字級貼合精度連帶提升。
  (3) **PNG 產出仍未解決，且與本次修正無關**：`forge.mjs` 的
  `cairosvg.svg2png()` 呼叫改用 `py` 後，暴露出另一個獨立問題——
  `execSync` 字串拼接組出的 `python -c "..."` 指令中，Windows 路徑的
  反斜線被 Python 解析器誤判為 unicode escape 序列而拋
  `SyntaxError`；即使修掉此路徑轉義問題，`cairosvg` 仍需要
  `libcairo-2.dll` 原生函式庫（已用 `py -c "import cairosvg"` 直接驗證
  該函式庫確實不存在）。PNG 產出有兩層獨立障礙，本次未處理，維持未驗證。
  (4) `schema_check.py`（`xmllint` 缺失）與像素層QA（`soffice` 缺失）
  兩項與 Python 呼叫無關，本次未受影響、仍未驗證，詳見 D1／段2a紀錄。
  驗證：見本次 session 之 `qa-gate.mjs` 正式管線測試紀錄。

- **v1.5**（2026-08-17）：PNG 產出改用 `playwright` 取代不可用的 `cairosvg`，
  本技能全部環境相依缺口清空。
  (1) **新增 `scripts/svg-to-png.mjs`**：以 `playwright`（本技能 package.json
  既有相依，非新增外部套件）驅動系統既有瀏覽器做 SVG→PNG，依序嘗試
  `msedge`→`chrome`→playwright 自帶 `chromium`。**不需下載瀏覽器二進位檔**
  （實測本機 Edge 直接可用，省約 150MB 與一次網路下載），也不需要任何原生
  函式庫。`forge.mjs` 改呼叫此模組，並移除已無用的 `execSync` import 與
  `PYTHON_CMD` 常數。
  (2) **汰換理由**（取代 v1.4 (3) 所述的未解決狀態）：`cairosvg` 需要底層
  `libcairo-2.dll`（`pip install` 裝不到，本機確實缺席），且原本
  `execSync` 拼接的 `python -c "..."` 指令會讓 Windows 路徑反斜線被 Python
  誤判為 unicode escape 而拋 `SyntaxError`——兩層障礙皆因改用 playwright
  而一併消除。附帶好處：瀏覽器 SVG 渲染器對字型 fallback／CSS／tspan 換行的
  支援優於 cairo toy API（後者不做逐字元 fallback，是既有 NO GLYPH 問題根源
  之一）。`omitBackground: true` 維持透明底，符合 forge-build 硬性規則。
  (3) 驗證：`node scripts/forge.mjs <job>.yaml` 端到端「1 張成功，0 張失敗」，
  manifest 顯示 `qa.pass: True`、**七項檢查全綠**（`aspect`／`externalRefs`／
  `glyphs`／`textLegibility`／`textCollision`／`fontCoverage`／`transparency`）
  ——其中 `transparency`（PNG 四角 alpha 檢查）是本版首次能實際執行，因先前
  無 PNG 可驗。PNG 實測 2040×896 RGBA、四角 alpha 全 0、135 萬非透明像素
  （確認內容有實際渲染而非空白圖）。五個 recipe 回歸測試 `fontCoverage` 全數
  `pass: true`、缺字 0，無回歸。

  **同版修復**（2026-09-20）：
  - 症狀：在 Windows 原生 Node 上，`safe-write.mjs` 的寫入一律以 ENOENT 失敗；
    `postprocess.mjs` 的 foreignObject→text 轉寫則**靜默跳過**（例外被既有的
    `catch` 收進 `foStats.error`），使 engine route 產出的 PNG 文字全部消失而
    不報錯。
  - 根因：兩處暫存路徑都寫死 `/tmp/...`。該字串在 Linux／macOS 正確，但在 Windows
    上會被 path 解析成「目前磁碟機根目錄 + \tmp」——本機實測 `path.resolve('/tmp/x')`
    在 I: 磁碟下得到 `I:\tmp\x`，而 `I:\tmp` 並不存在（`fs.existsSync('/tmp')`
    為 false，寫入回報 `ENOENT`）。`safe-write.mjs` 正是為了防止掛載點大檔寫入
    尾端截斷而存在，它自己在 Windows 上必定失敗，等於該防線完全失效。
  - 修復：兩處改用 `os.tmpdir()` + `path.join()` 取得各平台正確的暫存目錄
    （本機實測為 `C:\Users\<user>\AppData\Local\Temp`）。另補
    `safe-write.mjs` 的暫存檔清除——原實作從未刪除 `/tmp/safe-write-*`，每次寫入
    都會遺留一個檔案；改以 `try/finally` 包住重試迴圈，確保各種結束路徑都會清掉。
    （`postprocess.mjs` 原本已有 `finally { unlinkSync }`，本次未動該行為。）
  - 驗證：本機 Windows 11（Node，win32）對 `safeWrite()` 做往返測試，寫入含中英混排
    的 500 行內容至巢狀目錄，回傳 `success: true, attempts: 1`，讀回內容與原字串
    完全相同，且 `os.tmpdir()` 內 `safe-write-*` 檔案數在呼叫前後皆為 0（確認已清除）。
    兩支檔案均過 `node --check`。
  - 未涵蓋：engine route 的 foreignObject 端到端產圖未在本機重跑（需 `npm install`
    與瀏覽器，見「已知限制」），本次僅修正路徑並以語法檢查與 safeWrite 往返測試佐證。

  **文字修訂（2026-09-20，不升版）**：修正 `package.json` 的占位字串名稱
  `"infographic-test"`（開發初期的測試專案殘留）→ `"cpet-infographic-forge"`，
  並補上 `description`、`private: true`、`license`，移除無意義的 `main`／`keywords`／`author`
  空欄位。**`package-lock.json` 的兩處 `name` 必須同步改**——`npm ci` 會比對兩者，
  只改 `package.json` 會讓 `npm ci` 直接失敗；已一併修正並以 `npm ci --dry-run`
  驗證通過（exit 0，20 套件解析正常）。另於 SKILL.md「環境準備」段補上：
  npm 相依不隨 plugin 發佈（已在 .gitignore 排除），每次 session 重建的環境
  （典型為 Cowork 雲端容器）需先確認 `node_modules/` 是否存在，建議用
  `[ -d node_modules ] || npm ci`。行為未變，故不升版。

  **同版修復（2026-10-17，資安掃描後修補）**：安裝前的 SkillSpector 靜態掃描
  （`--no-llm`）判定整個 plugin 為 DO_NOT_INSTALL，其中屬於本技能的真實問題如下。
  - 症狀：(1) `npm audit` 報 2 筆——`source-map-js 1.2.1` HIGH（GHSA-68fv-2mgg-jv7q，
    indexed source-map 的 section offset 可造成 event-loop DoS）、`js-yaml 5.3.0`
    MODERATE（GHSA-r3ph-w7gj-g6xm，`maxTotalMergeKeys` 對空 merge 來源不設 CPU 上限）。
    (2) 文件與腳本內 6 處 playwright 安裝指令沒加 `--no-install`，`npx` 在本地找不到套件時
    會改從 registry 抓最新版（實測在技能目錄外執行會要求安裝 `playwright@1.64.1`，
    而 lock 內為 1.62.1）。
  - 根因：`source-map-js` 是間接相依（`@antv/infographic` → `postcss 8.5.26` →
    `source-map-js ^1.2.1`），lock 停在 1.2.1；`js-yaml` 直接相依宣告 `^5.2.2`，
    lock 停在 5.3.0。`playwright` 宣告為 `^1.62.1`，`npx` 指令也沒限制只用本地套件。
  - 修復：
    - `package.json` 新增 `"overrides": { "source-map-js": "1.2.2" }`（1.2.2 為上游
      2026-09-30 發布的修補版），不動 `@antv/infographic`／`postcss` 版本。
    - `js-yaml` 升到 5.4.3（宣告見下一項的精確版）。刻意不取 5.5.0：修補只需
      ≥5.4.1，5.5.0 為兩天前（2026-10-15）的新 minor，先不跟進。
    - 六個直接相依全部改為精確版（`playwright` 1.62.1、`@antv/infographic` 0.2.19、
      `@fontsource/inter` 5.3.0、`js-yaml` 5.4.3、`lucide-static` 1.31.0、`pngjs` 7.0.0），
      與 lock 內已解析的版本相同，實際安裝的套件樹不變；目的是讓 `package.json` 本身
      不留浮動範圍（SkillSpector SC1）。
    - `SKILL.md` 第 44、47 行、`MAINTENANCE.md` 第 68、96 行、`scripts/svg-to-png.mjs`
      第 59 行（註解）與第 72 行（錯誤訊息）的 playwright 安裝指令一律加上
      `--no-install`（`npx --no-install playwright install`），只用 lock 內的版本，
      本地沒有就直接失敗、不從網路抓。
  - 驗證（本機 Windows 11，Node／npm 11.16.0）：
    - `npm install` 後 `npm audit` 回報 `found 0 vulnerabilities`；`npm ls` 確認
      `source-map-js@1.2.2 overridden`、`js-yaml@5.4.3`、`playwright@1.62.1`。
    - `npx --no-install playwright --version` 在技能目錄內回 `Version 1.62.1`（rc=0）；
      在目錄外以「missing packages」錯誤中止（rc=1），確認不會偷抓新版。
    - 改精確版後重跑 `npm install`：`npm ls --depth=0` 六個版本與修改前相同，
      `package-lock.json` 只有根節點的宣告字串改變。
    - 回歸：同一份 job（engine `list-grid-badge-card` ＋ recipe `grid-matrix` 各一張）
      分別以修補前相依（舊 lock，`npm ci`）與修補後相依跑 `forge.mjs`，皆「2 張成功，
      0 張失敗」，兩邊 SVG 與 PNG **逐位元組相同**，PNG 已目視確認中文字形正常。
      兩張圖的 QA 各有一項 FAIL（engine 圖 `aspect`：測試資料只有 3 項、長寬比 4.44
      超出 slot 範圍；recipe 圖 `textCollision` 0.386：見 MAINTENANCE「門檻校準」），
      修補前後結果一致，與本次相依變更無關。
  - 文字修訂：修正兩處簡體字——本檔 v1.5 文字修訂段「殘留」、`SKILL.md`
    `dual-line-panel` 段「導致」原誤用簡體（OpenCC 掃描抓出）。
  - 打包前檢查（governance `preflight.py`，已裝 OpenCC）：F4「SKILL.md v1.5 vs
    CHANGELOG 首條 v1.0」判定為**檢查器誤報**——本檔條目由舊到新排列，檢查器取的是
    第一個 `**vX.Y**`。對照組：未修改的 `cpet-yslai-pptx`（v2.10 vs v2.1）、
    `cpet-figure-prep`（v1.1 vs v1.0）跑同一項都報同樣錯誤。F7「斗」（漏斗）是 OpenCC
    把正體「斗」誤判成簡體，不改。檢查器待修項已回報 Casey。

  **description 修訂（2026-10-22，不升版）**：補一句分流——曲線已在 MATLAB .fig 裡、只要換成簡報尺寸時走
  cpet-figure-prep v1.2 的 `fig_extract.py`，不用 `dual-line-panel` 重描。對應 ECCE 2026 回顧計畫 P5
  （figure-prep 邊界放寬時，兩邊的觸發描述一起調整，避免互搶觸發）。行為未變。
  preflight 對三個 assets JSON 與兩個驗收 SVG 報 WARN「尾端無換行」：這些檔案自 git 基線（`252d1e9`）以來未改，
  三個 JSON 皆可完整解析、兩個 SVG 以 `</svg>` 結尾，屬產生器不寫結尾換行，非截斷；接受此 WARN。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：`references/recipes.md` 的 vertical-flow 範例節點
  原為個人投稿進度，改為中性範例。行為未變。
