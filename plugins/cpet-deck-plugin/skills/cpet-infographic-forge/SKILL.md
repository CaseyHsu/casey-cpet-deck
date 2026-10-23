---
name: cpet-infographic-forge
description: 產生 CPET／YS Lai Lab 簡報用的資訊圖表（infographic）PNG／SVG，涵蓋流程圖、矩陣、時程、比較、階層、漏斗等 276 種模板與 5 種自訂 recipe（含二維矩陣表格 data-table、雙軸折線圖 dual-line-panel），並自動處理中文字型、版面長寬比與 slide slot 對齊。當使用者要求「畫張圖說明」「做流程圖／架構圖／時程圖／矩陣圖」「多方法比較表」「雙軸／雙曲線對比圖」「簡報插圖」「把這些項目做成圖」「infographic」「示意圖」，或要為 cpet-yslai-pptx 簡報產生配圖時，一定要使用本技能。也適用於把條列資料轉成視覺化圖表、或需要中英混排且不能出現亂碼方框的圖表產出。不要用於統計數據繪圖（那應走 IEEE-PlotOps／MATLAB SOP），也不要用於製作投影片本身（那是 cpet-yslai-pptx 的職責）；曲線已經畫在 MATLAB .fig 裡、只是要換成簡報尺寸重繪時，走 cpet-figure-prep，不要用 dual-line-panel 重新描一次。
---

# CPET Infographic Forge（v1.5 — 中文安全、slot 對齊的簡報資訊圖產生器）

把結構化的條列資料轉成簡報可直接使用的資訊圖 PNG／SVG。核心價值不在「能畫圖」，而在**擋掉一整類會靜默失敗的坑**——這些坑的共同特徵是「不報錯、圖也產得出來，但結果是錯的」，靠肉眼審圖抓不到。

## 為什麼需要這個技能：五個靜默失敗

以下每一項都是實測確認、且**不會拋出任何錯誤訊息**的失敗模式。若不透過本技能的閘門，產出的圖看起來完整、實際上是壞的。

| 失敗模式 | 表現 | 本技能的處置 |
|---|---|---|
| 中文全變 `NO GLYPH` 方框 | 西文正常、中文變直立方框 | 字型堆疊強制 CJK 優先 |
| 文字完全不渲染 | 圖只有色塊，一個字都沒有 | foreignObject 轉原生 `<text>` |
| 模板名靜默 fallback | 打錯字得到完全不相干的圖 | 強制使用 registry 內的完整模板名 |
| 資料鍵錯誤導致 hang | 卡住 10 秒後 timeout，無訊息 | 渲染前驗證資料鍵 |
| 29% 模板靜默丟棄 `desc` | 描述文字不顯示、無提示 | 渲染前依 registry 警示 |
| 縮字至不可讀 | 文字沒溢出但只有 8px | `textLegibility` 閘門 |

**這些坑的細節與實證見 `references/pitfalls.md`——動手前先讀，可省下大量重複排查。**

## 環境準備

依此順序一次到位安裝，**全程不要中途增刪字型**（字型異動的中間狀態曾疑似造成渲染異常）：

```bash
[ -d node_modules ] || npm ci    # 或 npm install（無 lockfile 時）
pip install fonttools pillow --break-system-packages
```

**每次 session 重建的環境（典型為 Cowork 雲端容器）要先確認
`node_modules/` 存不存在**——npm 相依不隨 plugin 發佈（已在 .gitignore
排除），容器重建後必須重裝。已有 `package-lock.json`，用 `npm ci`
比 `npm install` 快且版本鎖定；本機（Claude Code）裝過一次就不需要重跑。

**字型**：中文用 Noto Sans TC／Noto Serif TC、西文用 Arial／Times New Roman
（見下方「字型策略」）。Windows 11 與多數 Linux 桌面發行版已內建 Noto TC；
Linux 若缺，裝 `fonts-noto-cjk`。

**SVG→PNG 轉檔**：由 `scripts/svg-to-png.mjs` 以 `playwright` 驅動系統既有的
Edge／Chrome，**不需 `npx --no-install playwright install` 下載瀏覽器**，也不需 `cairosvg`
（v1.5 起汰換——`cairosvg` 依賴的 `libcairo` 原生函式庫在 Windows 常缺席，
且 cairo toy API 不做逐字元字型 fallback，是舊版 NO GLYPH 問題根源之一）。
若系統無 Edge／Chrome，才需 `npx --no-install playwright install chromium`。

驗證環境正確：

```bash
node scripts/forge.mjs <job>.yaml    # 應回報「N 張成功，0 張失敗」
# manifest.json 的 qa.pass 應為 true，七項檢查全綠
```

## 兩條產圖路線

**engine route** — 用 `@antv/infographic` 的 276 個模板。適合標準結構（流程、時程、比較、階層、漏斗、雷達、網絡等）。模板多、開發成本零，但版面固定、無法微調。

**recipe route** — 用本技能自帶的 5 個 recipe（`grid-matrix`／`vertical-flow`／`circle-cycle`／`data-table`／`dual-line-panel`）。版面可依 slot 自動求解、字級自動貼合，適合需要精確控制版面或塞進特定 slot 的情境。

**`data-table`（v1.2 新增）** — 真二維矩陣表格：`cols`(欄標籤) × `rows`(列標籤) × `cells`(二維陣列)，支援整列／整欄高亮（`highlightRow`／`highlightCol`）。與 `grid-matrix` 的差異：後者 `cells` 是一維卡片陣列，無法表達「列×欄→交叉格值」語意；`data-table` 才是真正的比較矩陣。適用情境：多方法／多維度結構性比較（例：5 個方法 × 7 個比較維度）。**欄標題文字長度差異大時**（例如方法全名 vs 簡稱），建議用簡稱或編號（比照論文比較表慣例，如 `[7]`／`Proposed`），避免最長欄標題把可用欄寬撐爆導致字級觸底。

**`dual-line-panel`（v1.2 新增）** — 雙面板折線圖：每面板可有多條 series、各自獨立 y 軸範圍、參考線（含標籤）、關鍵資料點標註。適用情境：兩個物理量綱／視角的對比折線圖（例：絕對誤差 vs 相對誤差，各含全域 MAPE 參考線）。單面板（`panels.length===1`）與雙面板（`===2`）皆支援，超過 2 個面板會拋錯（設計上不支援三面板以上並列，避免面板過窄導致內容擠壓）。

**預設選 engine route**，除非需要精準的 slot 對齊或 engine 找不到合適結構。

## 工作流程

### 1. 確認資料結構與模板

查 `assets/template-registry.json` 取得該模板的 `data_key` 與 `supports_desc`：

```bash
python3 -c "
import json; r=json.load(open('assets/template-registry.json'))['templates']
t='list-grid-badge-card'; print(t, r[t])"
```

選模板時的兩個硬性要求：

- **必須用完整模板名**（如 `list-grid-badge-card`），不可用家族簡寫（如 `list-grid`）。引擎對無法識別的名稱不報錯，會靜默 fallback 到別的模板——`sequence-roadmap` 會變成 `sequence-pyramid-simple`，任意錯字會變成 `compare-swot`。
- **資料鍵必須與 registry 一致**。全部 276 個模板只用五種：`lists`(141)、`sequences`(83)、`compares`(23)、`nodes`(18)、`values`(11)。**絕不要用 `children`**——它會讓 SSR hang 住 10 秒才 timeout 且不報錯。

若模板 `supports_desc: false`（276 個中有 80 個），使用者提供的 `desc` 會被靜默丟棄。此時要主動告知並建議改用支援 desc 的模板。

### 2. 撰寫 job YAML

```yaml
meta:
  deck_title: "簡報標題"
  output_dir: "./out"
  palette: cpet-vivid

figures:
  - id: fig-01-flow
    route: engine
    template: list-grid-badge-card     # 完整模板名
    slot: full                          # full / full-tw / half / quad / twocol
    data:
      title: 控制策略開發流程
      lists:                            # 需與 registry 的 data_key 一致
        - label: 時間延遲補償
          desc: 補償一拍半延遲避免振盪
```

recipe route 的 `data` 結構不同（`cells`／`nodes`），見 `references/recipes.md`。

### 3. 產圖

```bash
node scripts/forge.mjs <job>.yaml
```

輸出 PNG＋SVG＋`manifest.json`（含每張圖的 QA 結果）。

### 4. 檢查 QA 結果

```bash
python3 -c "
import json
for f in json.load(open('out/manifest.json'))['figures']:
    c=f['qa']['checks']
    print(f['id'], 'overall=', f['qa']['pass'])
    for k,v in c.items():
        if v.get('pass') is False: print('   FAIL', k, v)
"
```

五道閘門：

- **`fontCoverage`（確定性）** — 模擬 cairo 的字型選擇後，用 fontTools 讀 cmap 逐字比對，於轉檔前 100% 確定哪些字會變 `.notdef`。同時偵測未轉換的 foreignObject。零偽陽性／偽陰性。**這是最重要的一道，FAIL 時圖必然是壞的。**
- **`aspect`** — 長寬比與目標 slot 的偏差（門檻 0.25）。FAIL 時會附上 `recommendedSlot` 建議。
- **`textOverflow`** — 文字量超出模板容量。輕微溢出僅警示，超過框高 2 倍才判 FAIL。
- **`textLegibility`** — 字級是否低於可讀下限。recipe 的字級自動貼合為避免溢出會持續縮字，可能壓到 8px 這種簡報上讀不到的程度；此檢查專門攔這種「不溢出但不可讀」的情況。門檻依 route 而異（recipe 11px、engine 10px），因為 20% 的 engine 模板原生就用 10px，套同一門檻會產生大量誤報。
- **`textCollision`（v1.1 新增）** — 跨區塊文字是否互相重疊。前四道閘門都只檢查「單一文字區塊內部」的問題，從未檢查標題／副標／欄位之間是否疊壓——這是實測案例（主標題與雙欄標題垂直重疊糊字）證實的閘門盲區。依 SVG `<g transform="translate()">` 巢狀平移取得每個 `<text>` 節點絕對座標，兩兩比對估算 bounding box 的交集面積，超過兩者中較小者 8% 判定碰撞（門檻尚未大規模校準，見 `MAINTENANCE.md`）。
- **`externalRefs`／`glyphs`** — 外連殘留與替代字元。

### 5. 處理 QA 失敗

**`aspect` FAIL**：
- recipe route → 版面求解器會自動貼合 slot，若仍失敗表示該項目數在該 slot 下無解，改變項目數或換 slot
- engine route → 版面由第三方模板決定、改不了，**照 `recommendedSlot` 換 slot 即可**。若 `recommendedSlot` 為 null，表示該模板長寬比極端，任何 slot 都容不下，只能換模板或拆分內容

> **項目數對 engine 模板的長寬比影響極大**，先調項目數往往比換 slot 有效。實測 `list-grid-badge-card`：3 個項目排成單列 → 長寬比 4.439（無任何 slot 容得下）；5 個項目 → 2.656，套 `quad` 即通過。項目數過少時網格塌成單列是常見主因。

**`fontCoverage` FAIL**：檢查 `missingGlyphNodes` 指出的字元。正常情況不該發生（postprocess 已強制 CJK 優先），若發生表示字型未安裝或字型堆疊被覆寫。

**`textOverflow` FAIL**：縮短文字，或改用容量較大的模板。各家族的 desc 安全字數見 `references/pitfalls.md`。

**`textLegibility` FAIL**：文字過長觸發了自動縮字。縮短文字、減少欄數，或改用較寬的 slot。

**`textCollision` FAIL**：檢查 `collisions` 陣列列出的區塊配對與 `overlapRatio`。通常代表標題／副標／欄位標題之間的預留高度不足，多發生於多行 `tspan` 換行時。縮短標題文字、增加區塊間距，或改用預留高度較大的模板／slot。

## 交付前的自我檢查

產圖後**不要只看 QA 全綠就交付**。以下兩點 QA 抓不到，需人工確認：

1. **desc 是否真的顯示**——若模板 `supports_desc: false`，圖看起來完整（title 與 label 都在）但描述文字從未出現。曾發生產出的展示圖經人工確認「都符合」，實際上 desc 全被丟棄。
2. **語意是否正確**——模板名 fallback 已被驗證器擋下，但選錯模板（如用漏斗圖表達非漏斗語意）閘門不會知道。

## 參考文件

- **`references/pitfalls.md`** — 五個靜默失敗的完整實證、根因與判別方法；各家族 desc 容量表。**排查任何異常前先讀這份。**
- `references/recipes.md` — 3 個 recipe 的資料結構、版面求解器與字級貼合機制
- `references/architecture.md` — 各 script 的職責與資料流

## Changelog

### v1.0（2026-07-31）— 首次打包

本版由一次完整的除錯與驗證 session 沉澱而成，涵蓋以下修正與新增：

**修正的靜默失敗**
- **NO GLYPH 中文亂碼**：根因為 `postprocess.mjs` 將 Inter 排在字型堆疊首位，而 cairosvg 走 cairo toy text API **不做逐字元 fallback**，Inter 又完全不含 CJK glyph，導致每個中文字落到 Inter 的 `.notdef`（該 glyph 本身就是內含 "NO GLYPH" 字樣的方框）。改為 CJK 優先，純西文節點另行覆寫回 Inter 以保留西文字形。
- **engine route 文字 100% 遺失**：`@antv/infographic` SSR 以 `<foreignObject>`＋HTML `<span>` 承載文字，cairosvg 不處理內嵌 HTML。新增 `foreignobject-to-text.py` 轉寫為原生 `<text>`／`<tspan>`，含中英混排差異化斷行（CJK 逐字斷、西文依單字邊界）。全量 276 模板驗證此轉寫的前提（內部一律單層 span、巢深 1、CSS 屬性僅 15 項）成立。

**重建的 QA 閘門**
- 舊有的 `checkMissingGlyphs()`（只掃替代字元）與一度加入的像素啟發式偵測皆證實**對上述問題無效**（後者甚至對整片 NO GLYPH 的圖回報 pass）。改為 `check-font-coverage.py` 確定性檢查。
- 新增 `checkTextOverflow()`、`aspect` 的 `recommendedSlot` 建議。

**新增輸入驗證**
- `validate-input.mjs` 在 `renderToString` **之前**攔截三類 error（hang 資料鍵、非正式模板名、資料鍵不符）與一類 warning（desc 靜默丟棄）。時機是關鍵——問題輸入會 hang 而非報錯，事後偵測無法補救。
- 新增 `assets/template-registry.json`，記錄全部 276 模板的 `data_key` 與 `supports_desc`。

**版面與字級**
- `layout-solver.mjs`：依目標 slot 長寬比反解版面參數。recipe 的留白由約 40% 降至 7～10%。評分對「縮窄」施加 2.5 倍懲罰（recipe 的 `<text>` 不換行，縮窄有溢出風險、加高則無）。
- `measure-text.py`／`.mjs`：以 fontTools advance width 在參考字級 100 下量測，供字級自動貼合。字級較原本放大 40～80%，並以實測寬度為硬上限確保不溢出。

**打包前掃描補上的最後一道閘門**
- `checkTextLegibility()`：實測發現 recipe 的字級自動貼合雖成功防住溢出（0.0px），卻可能把字級壓到 8px 而 QA 全綠——溢出檢查只吃 engine route 的 foreignObject 統計，縮字又不算溢出，recipe 的 console 警示也不進 manifest。門檻依 route 而異（recipe 11px／engine 10px），因抽樣發現 20% 的 engine 模板原生使用 10px。驗證：極長文字案例正確 FAIL，engine 抽樣 25 個零誤報。

**已知限制（未解決，見 `references/pitfalls.md`）**
- `circle-cycle` 尚未接入版面求解器與字級貼合
- 字級貼合僅適用 recipe route；engine route 的字級由第三方模板決定
- 文字寬度以 advance width 計算，未計 kerning，實際渲染可能有 <2% 出入
- 版面求解器界限為經驗值，未針對極端項目數（n>8）驗證
