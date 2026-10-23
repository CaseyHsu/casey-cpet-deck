# 輸出格式範本

## 1. `input_template.md` 骨架

直接沿用讀取到的 `cpet-yslai-pptx` 當下 `assets/input-templates/input_template.md`
作為填寫骨架（含檔頭註解、簡報資訊宣告區）。以下示範轉譯後長什麼樣子（節錄）：

```markdown
<!-- ============================================================
CPET-YS Lai Lab 簡報來源文稿（Markdown 版）
由 cpet-input-template 於 2026-08-04 轉譯產出，來源：doc-coauthoring 共創草稿
============================================================ -->

# 簡報資訊（必填）

- 簡報類型：SOP
- 書面報告配套：否
- 教學情境：是
- 語言：zh-TW
- 標題（英）：...
- 標題（中）：...
- 報告人：...
- 指導教授：Y.S. Lai
- 日期：2026/08/04

## 階段 0：環境與觀念準備

### 開始前要備妥的東西

一個工作資料夾、內容文稿、圖檔、skill 檔案，四項缺一不可。

[figure: PENDING:forge-prep-items | 圖：開始前要備妥的四個物件]

### [layout: two_col] 建立 Project 畫面

左側 Projects 清單，點「New project」新增專案；填好名稱後點「Create project」建立。

[figure: PENDING:figprep-screenshot-01 | ① Projects 清單與新增按鈕]
```

**`two_col` 右欄若是公式而非圖片**（例如「文字先建立物理直覺、公式後驗證」的頁面），
右欄改用 `[eq-right:]`，不要誤路由成 forge 示意圖：

```markdown
### 電磁轉矩組成
[layout: two_col]

左欄先用文字段落說明磁鏈轉矩與磁阻轉矩兩個分量的物理來源。

[eq-right: T_e = \frac{3P}{4}[\lambda_{pm} i_q + (L_d-L_q) i_d i_q]]
[note: 電磁轉矩由磁鏈轉矩項與磁阻轉矩項組成，IPMSM 因 Ld≠Lq 才有第二項]
```

## 2. 素材處理清單.md 骨架

兩個區段，各自條目格式固定，方便下游技能或人工逐條核對：

```markdown
# 素材處理清單

> 由 cpet-input-template 於 2026-08-04 產出，對應 input_template.md 同日版本。
> forge 區段交給 cpet-infographic-forge 手動觸發處理；figprep 區段交給
> cpet-figure-prep 手動觸發處理。處理完成後，回填實際路徑到 input_template.md
> 對應的 PENDING: 標記（相對路徑）。

## Forge 區段（需新產出圖表）

### PENDING:forge-prep-items

- **概念**：開始前要備妥的四個物件
- **項目與關係**：平行清單——工作資料夾／內容文稿／圖檔／skill 檔案，四者並列、無先後
- **配色**：語意色用 Orange 標主強調項（若有），其餘走結構色 navy/灰
- **建議長寬比／解析度**：接近 16:9 全版寬，投影用途 ≥110dpi

## Figprep 區段（需前處理既有圖片）

### PENDING:figprep-screenshot-01

- **原始素材**：使用者提供的螢幕截圖（新增 Project 畫面）
- **需要的處理**：截圖紅框標註＋文字標籤
- **要框住的元素（文字描述，不猜座標）**：「New project」按鈕
- **置入投影片預計寬度**：約全版寬的一半（two_col 右欄）
```

**若某個 PENDING 條目在轉譯完成時判斷不需要圖（例如原本以為要配圖，重新讀過草稿後發現
文字已經夠清楚），不要留下孤兒佔位鍵**——回頭刪掉 `input_template.md` 裡對應的
`[figure: PENDING:...]` 標記，同時從素材處理清單.md 移除對應條目，避免下游技能對著
根本沒被引用的鍵值處理，或使用者疑惑「這個鍵值是什麼」。

## 2.5 數據查核表.md 骨架（v1.5 新增）

先跑 `scripts/claim_check.py suggest input_template.md` 取得候選列，再補欄位。表格第一列的欄名不可改
（`claim_check.py check` 依欄名讀取）；`labels` 以分號分隔。

```markdown
# 數據查核表

> 由 cpet-input-template 於 2026-10-21 產出，對應 input_template.md 同日版本。
> 改了任何數字，先改這張表，再改簡報與講稿；改完跑 claim_check.py check。

| id | anchor | value | unit | kind | labels | source | pages | status |
|---|---|---|---|---|---|---|---|---|
| T9_cmd | 9 000 rpm | 40 | Nm | command | command;LUT;命令 | LUT .mat 檔 Te_max 最後一點（39.6，取整） | #3；#7 | 已查證 |
| T9_meas | 9 000 rpm | 42.5 | Nm | measured | measured;實測 | 測功機最大轉矩紀錄 | #7 | 已查證 |
| T9_err | 9 000 rpm | 2.9 | Nm | calculated | error;誤差 | T9_meas − 39.6 | Q&A Q4 | 已查證 |
| CAL_time | after the model is available | 120 | s | measured | 待填 | 待填 | #2；#5；#9 | 待查證 |
```

（以上數值皆為示範用的合成資料。）

**status**：`已查證`（來源已核對）／`待查證`（數字來自素材但來源未核對）／`待填`（素材裡找不到）。

## 3. 決策摘要格式（初次生成）

技能執行完，兩份文件之後，直接在對話中列出（不是另開檔案）：

```
## 轉譯決策摘要

**簡報資訊**：SOP 型／無書面配套／教學情境／中文。

**版面決策**（僅列有特殊判斷的頁面，一般 bullets 頁不逐一列出）：
- 「開始前要備妥的東西」：two_col，因四個物件適合並列文字＋示意圖對照
- 「建立 Project 畫面」：two_col，因截圖需要與操作步驟文字對照呈現
- ...

**素材路由**：
- fig-prep-items → forge（概念性示意圖，尚無實體檔案）
- figprep-screenshot-01～05 → figprep（使用者提供的操作截圖，需標紅框）
- ...

**數據查核表**：共 N 個數字；同一條件有兩種性質、簡報上必須標明的：T9（命令 40 Nm／實測 42.5 Nm）。
**來源待填**：CAL_time（120 s 的計時起點）、…——請補來源後再建置。

**待你確認**：以上版面與路由判斷是否符合預期？確認後我不會自動繼續，需要你手動觸發
cpet-yslai-pptx（建構簡報）與對應的 forge／figprep（產出視覺素材）。
```

## 4. 決策摘要格式（修訂模式）

```
## 轉譯決策摘要（修訂）

**本次改動**：
- 「情境四問先想好」頁：由 table 改回 bullets，因你反饋「這頁資訊量少，不需要表格」
- 新增一頁「附錄D」：因你要求補充 FAQ

**其餘頁面**：維持原判斷，未變動。

**待你確認**：...
```
