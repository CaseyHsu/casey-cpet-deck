# 架構與資料流

## 產圖流程

```
job.yaml
   │
   ├─→ validate-input.mjs     ← 渲染前攔截（必須在 renderToString 之前）
   │      查 template-registry.json：模板名合法性、data_key、desc 支援度
   │
   ├─→ engine route: @antv/infographic SSR → SVG（含 foreignObject）
   │   recipe route: recipes/*.mjs（含 layout-solver + measure-text）→ SVG
   │
   ├─→ postprocess.mjs
   │      1. 剝除外連 xml-stylesheet
   │      2. foreignobject-to-text.py：foreignObject → 原生 <text>
   │      3. 字型堆疊改 CJK 優先，純西文節點覆寫回 Inter 優先
   │
   ├─→ cairosvg → PNG（解析度由 fit.mjs 依 slot 決定）
   │
   └─→ qa-gate.mjs → manifest.json
          fontCoverage / aspect / textOverflow / externalRefs / glyphs
```

## 各檔案職責

### scripts/

| 檔案 | 職責 |
|---|---|
| `forge.mjs` | 主流程：讀 job、分派 route、寫檔、彙整 manifest |
| `validate-input.mjs` | **渲染前**輸入驗證（依 template-registry） |
| `postprocess.mjs` | SVG 後處理：外連剝除、foreignObject 轉寫、字型堆疊修正 |
| `foreignobject-to-text.py` | foreignObject → 原生 text，含中英混排斷行 |
| `qa-gate.mjs` | 五道 QA 檢查與整合判定 |
| `check-font-coverage.py` | **確定性**字型 glyph 覆蓋率檢查（主閘門） |
| `layout-solver.mjs` | 依目標長寬比反解 recipe 版面參數 |
| `measure-text.py` / `.mjs` | 文字寬度量測（參考字級 100，線性換算） |
| `fit.mjs` | slot → 輸出解析度；長寬比偏差評估 |
| `recipe-runner.mjs` | recipe 分派 |
| `icon-resolve.mjs` | icon 名稱 → SVG 內容解析 |
| `safe-write.mjs` | 檔案寫入 |
| `emit-input-template.mjs` | 產生 job YAML 範本 |

### assets/

| 檔案 | 內容 |
|---|---|
| `template-registry.json` | **276 模板的 `data_key` 與 `supports_desc`**（全量調查產出） |
| `template-catalog.json` | 42 家族的長寬比實測與推薦 slot |
| `icon-map.json` / `icons/` | lucide icon 對照與 SVG |
| `palette.yaml` | CPET 色盤定義 |

## 關鍵設計決策

**驗證必須在 `renderToString` 之前**——不合法資料鍵會使 SSR hang 10 秒且不報錯，事後偵測無法補救。

**QA 用確定性檢查而非啟發式**——啟發式門檻在未見過的輸入上會失效且不會有徵兆。詳見 `pitfalls.md` 附錄。

**recipe 與 engine 的長寬比處置不同**——recipe 的版面由我方控制，可用求解器主動貼合；engine 的版面由第三方模板決定、無法調整，只能給 `recommendedSlot` 建議。

**postprocess 的順序有意義**——foreignObject 轉寫必須在字型堆疊修正之前，轉寫產生的 `<text>` 才會一併套用 CJK 優先規則。
