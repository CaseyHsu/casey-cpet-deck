# Recipe route 使用說明

5 個自帶 recipe，版面可依 slot 自動求解、字級自動貼合。適合需要精確控制版面或塞進特定 slot 的情境。

## 資料結構

### grid-matrix — 矩陣並列

多角色／多維度對照。每個 cell 是一張卡片（icon + 標題 + 說明）。

```yaml
- id: fig-matrix
  route: recipe
  recipe: grid-matrix
  slot: twocol
  data:
    title: 五專才助理矩陣
    cols: 3                    # 選填；未指定時由求解器決定
    cells:
      - {label: Albert, desc: IEEE 審稿工房, icon: search-check}
      - {label: RikaKyo, desc: 產業研究, icon: chart-bar}
```

### vertical-flow — 垂直流程

帶序號與連接箭頭的縱向步驟。

```yaml
  recipe: vertical-flow
  data:
    title: 投稿時程
    nodes:
      - {label: 修訂稿定案, desc: 整理審稿意見, icon: file-search}
```

### circle-cycle — 循環

首尾相接的循環流程。

```yaml
  recipe: circle-cycle
  data:
    title: 迭代循環
    nodes:
      - {label: 設計}
      - {label: 實作}
```

> `circle-cycle` 尚未接入版面求解器與字級貼合（天生 1.0 正方形，twocol 下偏差 0.180 仍合格，但其他 slot 未最佳化）。

### data-table — 二維矩陣表格（v1.2 新增）

多方法／多維度結構性比較矩陣。與 `grid-matrix` 的本質差異：`grid-matrix.cells` 是一維卡片陣列（每格只有 label+desc+icon），無法表達「列×欄→交叉格值」的二維語意；`data-table.cells` 是真正的二維陣列，且支援整列／整欄高亮。

```yaml
- id: fig-compare
  route: recipe
  recipe: data-table
  slot: full
  data:
    title: 電流估測方法比較
    cols: [Proposed, LUT-based, Reg.-based, KKT-based, FEM-based]
    rows: [Model basis, Solver required, Optimality, Online cost, Accuracy, Robustness, Implementation]
    cells:
      - [混合模型, 查表, 正則化, KKT條件, 有限元素]
      - [輕量迭代, 無, 迭代, QP求解器, FEM求解器]
      # ... 每列一個陣列，長度須與 cols 相同
    highlightCol: 0   # 整欄高亮（此例強調 Proposed）；亦可用 highlightRow
```

**欄標題長度差異大時**（例如方法全名 vs 簡稱），建議用簡稱或編號（比照論文比較表慣例）。實測：5 欄方法名稱若用全名（如 `Regularization-based`，20 字元），會把該欄字級壓到 10.2px 觸底；改用簡稱（`Reg.-based`）後全部欄標題字級 19px 以上。

### dual-line-panel — 雙面板折線圖（v1.2 新增）

單一或雙面板並列的折線圖，各面板可有多條 series、各自獨立 y 軸範圍、參考線、關鍵資料點標註。

```yaml
- id: fig-error-compare
  route: recipe
  recipe: dual-line-panel
  slot: full
  data:
    title: 電流估測誤差分析：絕對誤差 vs 相對誤差
    panels:
      - label: 絕對誤差 (A)
        series:
          - {name: Proposed, points: [{x: 0, y: 0.42}, {x: 1, y: 0.38}]}
          - {name: Conventional LUT, points: [{x: 0, y: 0.68}, {x: 1, y: 0.72}]}
        yAxis: {min: 0, max: 1.0, unit: A}
        referenceLine: {value: 0.5, label: 全域 MAPE 門檻}
        annotations: [{x: 2, y: 0.85, label: 峰值誤差}]
      - label: 相對誤差 (%)
        series: [...]
        yAxis: {min: 0, max: 6.0, unit: "%"}
```

`panels.length` 為 1（單面板）或 2（雙面板並列）；超過 2 個會拋錯。

## 版面求解器

`layout-solver.mjs` 依目標 slot 的長寬比反解版面參數，使畫布比例貼合 slot，避免大量留白。

**問題背景**：原本版面常數寫死，長寬比是「項目數的副產品」。`vertical-flow` n=3 得 1.745（不合格）、n=5 得 1.142（合格）——同一 recipe 換個項目數就在合格與不合格之間跳動。

**效果**：留白由約 40% 降至 7～10%。

| 圖 | 偏差（前→後） | 未使用高度（前→後） |
|---|---|---|
| grid-matrix | 0.428 → 0.016 | 38.6% → 7.1% |
| vertical-flow | 0.479 → 0.013 | 41.3% → 10.1% |

**設計要點**：評分對「縮窄」施加 2.5 倍懲罰。因為 recipe 的 `<text>` 不做自動換行，縮窄卡片有文字溢出風險，而加高沒有——安全方向優先。

**使用者明確指定 `cols` 時一律尊重**，僅在該欄數下求解卡片尺寸。

**實作註記**：同分判定的容差初設為 `1e-6` 過嚴，導致求解器為了多命中 0.0001 的偏差而選擇大幅縮窄卡片的解。改為 0.02 容差後，兩個 recipe 的解皆不再縮窄。

## 字級自動貼合

字級不能寫死放大——安全上限取決於**輸入文字有多長**，而 recipe 的 `<text>` 不換行，溢出無法自我修正。

**作法**：`measure-text.py` 用 fontTools 讀 advance width，回報文字在**參考字級 100** 下的寬度。因寬度隨字級線性縮放（`width(S) = width100 × S / 100`），每個字串只需量測一次，整份圖一次子行程呼叫即可。

字級決定流程：
1. **目標**：讓最長的一段文字佔可用寬度的目標比例（label 0.72、desc 0.68），據此反推
2. **硬上限**：不得超過可用寬度的 0.98
3. **垂直檢查**：內容總高不得超過卡片高的 0.86（grid-matrix）／0.62（vertical-flow）

> 為何不依卡片尺寸等比縮放：卡片常只有高度變大（寬度受欄數約束不變），此時等比縮放完全放不大字級，即使寬度還有大量餘裕。

**結果**：

| recipe | label（前→後） | desc（前→後） |
|---|---|---|
| grid-matrix | 22 → 37.2 | 15 → 21.2 |
| vertical-flow | 20 → 36.0 | 15 → 27.0 |

### 兩個曾犯的錯（已修，勿重蹈）

**可讀性下限破壞防溢出保證**：初版無條件套用 `0.8×基準` 下限，導致極長文字（`Field Weakening Control`）被硬拉回 22.4px 而**溢出 130%**。已改為：可讀性下限只在不致溢出時適用；防溢出優先（溢出比字小更糟）。字級被壓到 11px 以下才發警示。

**icon 圓超出卡片邊界**：`vertical-flow` 的圓半徑初版只依字級放大，算出 43.2 而圓心距卡片左緣僅 40px，**戳出左邊界 3.2px**。已加入雙重夾制（不可超出左緣、不可壓到文字起點）。

**通則**：任何隨字級縮放的幾何元素，都要同時受「容器邊界」約束，不能只看字級比例。

## 調整字級大小

改 `recipes/grid-matrix.mjs` 的 `TARGET_FILL`（現為 label 0.72、desc 0.68）。0.8 左右仍安全，再高會開始貼邊。
