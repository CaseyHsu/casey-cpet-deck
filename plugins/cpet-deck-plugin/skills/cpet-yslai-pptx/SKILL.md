---
name: cpet-yslai-pptx
description: "用於 CPET / YS Lai Lab 實驗室簡報——當使用者提及實驗室相關語境時觸發，例如「實驗室模板」、「CPET template」、「YSLai」、「實驗室簡報」；或要求將文件（Markdown／HTML／Word／LaTeX／會議記錄）轉成實驗室風格簡報（如「轉成投影片」、「用實驗室模板輸出」）；或提供舊 .pptx 要求更新成實驗室風格的新模板。支援嵌入使用者提供的圖片與 LaTeX 公式。實驗室成員的研討會口頭報告要套**大會官方模板**（如 ECCE、IECON 的 Oral Presentation Template）時也使用本技能（以模板描述檔 --profile 建置）。**不要**用於非實驗室用途的一般簡報（如個人用途、對外提案、或未指定模板的請求）。"
---

# CPET-YS Lai Lab 簡報技能（v2.11 — 文稿轉簡報建構器）

以 CPET-YS Lai Lab 標準模板（`assets/template.pptx`）生成簡報。v2 的核心是 **slide-plan 驅動的確定性建構器**：不再逐頁手寫 XML，而是把來源文稿整理成一份 `plan.json`，由 `scripts/build_deck.py` 一次生成整份簡報。修訂時只改 plan 再重建，不動 pptx 內部。

**LaTeX 公式與使用者提供的圖檔都由建構器自動內嵌**：公式經 `scripts/render_eq.py` 渲染為高解析透明 PNG（mathtext 為主、pdflatex 為 fallback），圖片自動等比縮放置入版面格位。

---

## 技術研究文稿 → 簡報：完整 Workflow

### 步驟 0：解析來源文稿

| 來源格式 | 讀取方式 |
|---|---|
| Markdown / 純文字 | 直接 `view` 閱讀 |
| HTML | 直接 `view` 閱讀（必要時去除樣式雜訊） |
| Word (.docx) | `pandoc input.docx -t markdown --extract-media=media_dir -o doc.md`——**會同時把內嵌圖片抽到 `media_dir/`、把 OMML 公式轉回 LaTeX**，一次取得三種素材 |
| LaTeX 文稿 (.tex) | 直接閱讀；公式原樣保留給 plan 使用 |

使用者另外提供的圖檔，在 plan 中以**絕對路徑**引用（來源依執行環境而異：Claude Code 為使用者指定的本機路徑，Chat／Cowork 為上傳區，不要假設固定前綴）。EMF/WMF 向量圖建議先以 LibreOffice 轉為 PNG（`soffice --headless --convert-to png`）再引用。

**標準化來源文稿範本**：`assets/input-templates/` 提供三種格式的填寫範本（`input_template.md`／`.docx`／`.tex`），內含簡報資訊宣告區（對應步驟 0.5 的四項情境）與版面提示語法。使用者若想事先規劃簡報結構，提供這些範本給他填寫。範本語法約定（來源文稿中出現時依此解讀，全部選填）：

| 語法 | 意義 | 對應 plan |
|---|---|---|
| `## 一級標題` | 一章 → running title（藍 40pt 置中） | `section` |
| `### 三級標題` | 章內一頁 → **頁大標**（navy 32pt，前置箭號） | `title` |
| `[sub: …]` | 頁副標（灰 16pt，v2.8 新增） | `subtitle` |
| `[layout: 類型]` | 覆寫版面判斷（bullets/equation/figure/two_col/table/closing） | `type` |
| `[section: Part-I: … \| Part-II: …]` | 宣告多 Part 方法章，每 Part 開頭自動放進度回訪 section 頁 | `section` 頁 |
| `[intro: …]`／`[note: …]`／`[assumption: …]` | 公式的開場句／物理意義／假設 | `equation.blocks[]` |
| `[figure: 路徑 \| caption \| source: … \| takeaway: …]` | 圖＋說明＋**出處**＋量化結論 | `images[]` |
| `[source: …]` | 同區塊多圖共用出處（單獨一行） | `source_shared` |
| `[cards: 欄數]` | 宣告接下來的字卡排成幾欄（1–4，v2.8） | `bands[].cols` |
| `[card: 標題 \| 內文]` | 一般字卡（淺灰底，v2.8） | `cards[]` |
| `[card-accent: 標題 \| 內文]` | 強調字卡（淡橙底，一頁最多一張，v2.8） | `cards[].accent` |
| `[card-num: 編號 \| 標題 \| 內文]` | 數字圓徽章字卡（順序帶訊息時才用，v2.8） | `cards[].badge` |
| `[kpi: 數值 \| 標籤 \| 說明]` | 大數值卡（v2.8） | `cards[].kpi` |
| 條列行首 `(+)`／`(-)`／`(>)` | 語意符號：勾／叉／箭號（v2.8） | `bullets[].mark` |
| `[highlight: 關鍵字]` | 表格中該列整列橙底強調（v2.8） | `highlight_rows` |
| `[takeaway: …]` | 該頁一句話結論（navy 實心橫幅＋白字） | `takeaway` |
| `[remarks]…[/remarks]` | 收錄至簡報末 Remarks 章節的推導與補充 | Remarks 章 |
| `[closing: 自訂感謝詞]` | 自訂結尾頁文字 | `closing` |
| `!!片語!!` | 行內重點（紅 `#C00000` 粗體；結論橫條內為黃字 +4pt）。每卡 1–2 個、每條結論 ≤3 個（v2.11） | 任何文字欄位 |
| `[card-tint: 色 \| 標題 \| 內文]` | 淡底字卡，色＝blue／orange／vermilion／green（v2.11） | `cards[].tint` |
| `[chevron: 標題 \| 說明]`／`[chevron-accent: …]` | 一列流程階段箭頭，連續 3–5 行成一組；accent 為橙底（v2.11） | `chevrons` band |
| `[lane: 標籤 \| 色]` ＋ `[lane-item: 圖路徑或文字 \| 圖說]` ＋ `[lane-kpi: 數值 \| 說明]` | 並列對照泳道（傳統 vs 本文），2–3 條（v2.11） | `lanes` band |
| `[notes: …]` | 該頁備忘錄（講稿另由 cpet-talk-prep 管理時可省略，v2.11） | `notes` |
| `### [backup] 頁名` | 備用頁：建置時放到致謝頁之後（Q&A 用，v2.11） | `backup: true` |

**排版式樣由區塊順序決定，使用者不必宣告**（v2.8 的關鍵設計）：一頁由「文字／圖／字卡／表格」四種區塊依文稿中出現的順序垂直堆疊，映射為 `bands` 頁型。實驗室的五種式樣全部是它們的排列組合——上文＋下圖＝`[text, figure×1]`、上文＋左右兩圖＝`[text, figure×2]`、上文＋圖＋字卡＝`[text, figure, cards]`、上文＋兩圖＋兩卡＝`[text, figure×2, cards×2]`；只有「左文右圖」需要明確寫 `[layout: two_col]`（那是左右分欄，與垂直堆疊正交）。**不要要求使用者宣告式樣編號**——那是把工具的內部結構外露給使用者，既增加負擔又容易寫錯（宣告式樣 5 卻只給一張圖）。寫什麼就排什麼，`[layout:]` 只在要覆寫預設判斷時才用。

未標註提示時，一律依 `references/lab-style-conventions.md` 的骨架與硬規則自動判斷。

範本（v2.1 起）另附**填寫上限**——一頁區塊數 ≤3（超過會中止建置）、單頁 bullet ≤6、Outline ≤8 項、頁大標寬度 ≤20、每頁 accent 卡 ≤1 張、公式必附 `[note:]`、外部圖必附 `source`、圖片一律用相對路徑。這些與 `plan_lint.py` 的檢查一致，文稿階段就遵守可以少一輪修訂。

**舊簡報轉新模板**：使用者提供舊 .pptx 要求「更新成新模板／實驗室風格」時，先跑 `python <skill_path>/scripts/extract_legacy.py 舊簡報.pptx workdir/` 完成機械抽取與旗標判定，再依 `references/legacy-conversion.md` 的 L1–L4 SOP 執行（隱藏頁排除、OMML 公式視讀轉錄 LaTeX、拼貼頁內容區裁切、模糊值標「待補」不杜撰）。

### 步驟 0.5：使用情境確認（必做）

若使用者未在需求中言明，**開始內容映射前先確認使用情境**（一次問完，不要分批追問）：

1. **簡報類型**：研究成果／期末報告型｜講義／weekly report 型｜短篇數據／SOP 型 → 決定敘事骨架分流。
2. **是否為書面報告的配套簡報** → 是：圖表用章節式編號（圖 2.7）＋頁面小節編號徽章；否：圖表與公式以流水號編號（圖 1、式 (1)…）。
3. **是否為教學情境** → 是：講義結尾 Thanks 前加 Homework 頁。
4. **語言與對外程度**（實驗室內部／口試／會議）→ 決定中英文分工或全英文。

從對話脈絡已能明確判定的項目不必重問，只確認判不出來的。

### 步驟 1：內容映射（文稿結構 → 投影片類型）

> **撰寫 plan.json 前，先參考 `references/lab-style-conventions.md` 之 §0（情境確認）、§1–§2（實驗室簡報風格硬規則）與 §4（MUST-NOT 清單）。**

依下表把文稿內容映射為 plan 中的投影片，**這一步是降低修訂次數的關鍵——先把內容裁剪成簡報密度，再進建構器**：

| 文稿元素 | 投影片類型 | 裁剪規則 |
|---|---|---|
| 文件標題／作者 | `cover` | 英文主標＋中文副標；報告人＋指導教授 |
| 章節目錄 | `outline` | 4–8 項；當前重點章節加 `"em": true` |
| 多階段方法的章首 | `section` | Part 清單＋`active` 索引，作為章節分隔頁 |
| 敘述段落 | `bullets` | **每段濃縮成 1–2 條 bullet，一頁一訊息**；一頁最多 6 條主 bullet，超過就拆頁 |
| `$$…$$`／`\begin{equation}` | `equation` | 一頁最多 3 條公式；**每條公式必附 `note`（物理意義）**；理論推導中間步驟不進正文，只留「起點 → 假設 → 結果」，完整推導移至簡報末 **Remarks 章節**，正文頁註記「詳見 Remarks」 |
| 圖片（文稿內嵌或使用者上傳） | `figure` | 每圖必附 caption；結果圖必附 `takeaway`（量化結論句） |
| 「原理文字＋一條公式／一張圖」的組合 | `two_col` | 左文右圖（或右公式），對應 Casey 偏好的「文字先、公式後」順序 |
| 規格表／比較表 | `table` | 超過 12 列拆成兩頁或移除次要列 |
| 結論／未來工作 | `bullets` | 最多 4 條，附 takeaway |
| 結尾感謝頁 | `closing` | **建構器自動附加，plan 不必列出此列**；預設 "Thank You for Your Attention" 置中大字，僅在需要自訂收尾語時才手動加一張 |

**學術發表敘事骨架**（若使用者未指定順序，依此排列）：
`cover → outline → motivation(bullets/figure) → section(Part 分隔) → method(equation/two_col/bullets) → verification(figure/table) → conclusions(bullets)`。每個方法章節開頭放一張 `section` 頁並更新 `active`，讓聽眾隨時知道位置。

**實驗室慣例補強**（依 `references/lab-style-conventions.md` §1，自 9 份實驗室簡報樣本抽取、經 Casey 裁決修訂）：

- **簡報類型分流**：研究成果／期末報告型在 outline **前**加 Summary 章（動詞開頭的目標句 3–5 條：Address…／Show…／Present…，可附 1–2 頁代表性結果圖作開場證據），以 Conclusion 收尾；講義／weekly report 型在簡報前段放 Gantt 進度頁（封面後或 Outline 後皆有先例），教學情境可在致謝頁前加 Homework 頁。**不論何種類型，簡報最後一律以 "Thanks for your attention" 致謝頁收尾**（`closing` 頁型，v2.6 起由建構器自動附加，plan 不必手動加）。
- **Remarks 章節**：理論推導的完整過程、冗長步驟與補充材料集中放在簡報末的 Remarks 章節（Conclusion／Future Works 之後、Thanks 頁之前）。
- **頁標題採 running title**：同一章的每一頁 `title` 一律用章節名（如連續多頁都是 "Experiment Results"、"Proposed Method (Part-I: …)"），頁面自身主題放 `subtitle` 或首條 bullet。與 `section` 分隔頁並存：section 頁負責換章，running title 負責章內延續。
- **章節回訪**：多 Part 的方法章，每個 Part 開頭都放一張 `section` 頁重放完整 Part 清單並更新 `active`（當前 Part 強調、其餘灰階）——不重放整份 Outline，以 section 頁完成進度回訪。
- **驗證章比重**：模擬＋實驗章合計佔全簡報 20–45%；一頁一測項，測試條件不同即拆頁。

### 步驟 2：撰寫 `plan.json`

Schema 與範例（欄位皆為選填，除 `type` 外）：

```json
{
  "meta": {
    "language": "zh-TW",
    "eq_preamble": "\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage{bm}",
    "eq_show_source": true,
    "eq_source_size": 11
  },
  "slides": [
    {"type":"cover","title_en":"英文主標題","title_zh":"中文副標題",
     "presenter":"姓名","advisor":"Y.S. Lai","date":"2026.07.05",
     "extra_lines":["CPET – Center for Power Electronics Technology","National Taipei University of Technology"]},

    {"type":"outline","title":"Outline",
     "items":["Motivation",{"text":"Proposed Method","em":true},"Verification"]},

    {"type":"section","title":"Proposed Method","lead":"方法總名稱（可省略）",
     "parts":["Part-I: ...","Part-II: ...","Part-III: ..."],"active":0},

    {"type":"bullets","title":"標題","subtitle":"(Part-I: 副標，深紅)","size":24,
     "bullets":[{"text":"主要論點","bold":true},
                {"text":"子項目","level":1},
                "純字串等同 {\"text\": ...}"],
     "takeaway":"本頁一句話結論（綠色橫條，選填）"},

    {"type":"equation","title":"標題","subtitle":"(Part-I: ...)",
     "intro":"公式前的一句話說明（選填）",
     "blocks":[{"latex":"T_e = \\frac{3P}{4}[\\lambda_{pm} i_q + (L_d-L_q) i_d i_q]",
                "note":"物理意義說明——必填，禁止只放符號"}],
     "takeaway":"..."},

    {"type":"figure","title":"標題",
     "bullets":[{"text":"圖上方的重點說明（選填）","bold":true}],
     "images":[{"path":"fig1.png","caption":"圖 1. 說明文字"},
               {"path":"/abs/path/to/fig2.png","caption":"圖 2. ..."}],
     "takeaway":"量化結論句"},

    {"type":"two_col","title":"標題","left_bullets":[...],
     "right":{"image":{"path":"...","caption":"..."}}},
    {"type":"two_col","title":"標題","left_bullets":[...],
     "right":{"latex":"P_{fe}=K_h\\omega_e\\lambda^2+K_e\\omega_e^2\\lambda^2","note":"物理意義"}},

    {"type":"table","title":"標題","columns":["Description","Value","Unit"],
     "rows":[["Rated Power","60","kW"]],"note":"表下註解（選填）",
     "first_col_item":true,"col_align":["center","center","center"]},

    {"type":"closing","text":"Thank You for Your Attention","size":40}
  ]
}
```
（上例的 `closing` 一行僅示範自訂收尾語的寫法；一般情況不需要在 plan 中列出，建構器會自動附加，見下方注意事項。）

注意事項：
- `images[].path` 相對路徑以 plan.json 所在目錄為基準；建議直接用絕對路徑。
- LaTeX 在 JSON 內反斜線要跳脫（`\\frac`）。**不要**加 `$`（腳本會自動處理）。
- 支援 `cases`、`aligned`、`matrix` 等 amsmath 環境（自動走 pdflatex）；`align`/`equation` 這類完整環境不支援，改寫成 `aligned` 內嵌形式。
- `figure` 一頁 1 張圖置中、2 張並排、3–4 張 2×2；超過 4 張拆頁。
- `table` 樣式由建構器自動落實：表頭 navy 底白粗體置中、**第一欄視為項目欄**（淡藍底＋粗體，`"first_col_item": false` 可關閉）、全表細框線、儲存格垂直置中；欄位對齊自動判斷（整欄皆短內容→置中、含長句→靠左），`"col_align": ["center","left",…]` 可逐欄覆寫。
- **`bands`（v2.8 新增，組合式版面）**：一頁由 1–3 個「水平帶」垂直堆疊，覆蓋實驗室的四種垂直式樣（上文下圖／上文＋左右兩圖／上文＋圖＋字卡／上文＋兩圖＋兩卡）。band 有四種 `kind`：`text`（bullets）、`figure`（cols 1–3 ＋ images）、`cards`（cols 1–4 ＋ cards）、`table`（欄位同 `table` 頁型）。卡片支援 `head`／`body`／`bullets`／`badge`（navy 圓徽章）／`accent`（橙底強調）／`kpi`（大數值）六個欄位——**原本規劃的 `numbered` 與 `kpi` 頁型不存在**，它們分別是 `cards(cols=1)+badge` 與 `cards+kpi` 的特例。高度分配：text／cards／table 依內容估自然高度，`figure` 為 flex 吃剩餘空間；無 figure band 時剩餘空間留在底部，這就是結構性留白。**左右分欄不走 bands**（band 是垂直堆疊模型），用既有的 `two_col`。band 超過 3 個會警告並只取前 3 個——這是刻意的密度閘門。
- **`images[].source`（v2.8 新增）**：外部圖片來源標註，渲染於圖說下方 11.5pt 灰字，前綴「來源：」。同一區塊多圖共用時用 band／頁層的 `source_shared`。適用 `figure` band、`figure` 頁型、`two_col.right.image`。
- **bullet 的 `mark`（v2.8 新增）**：`pro`（Wingdings 勾，Blue）／`con`（Wingdings 叉，Vermilion）／`step`（U+25BA 箭頭，navy）。全部使用 PowerPoint 內建字型字元、由 `buSzPct` 統一控尺寸，**不使用 U+2714／U+274C／U+25B6 這三個帶 emoji 呈現變體的碼點**（Windows 會由 Segoe UI Emoji 接手渲染成彩色、尺寸不受控）。使用邊界見 `references/lab-style-conventions.md` §2.7。
- **`table` 的 `highlight_rows`（v2.8 新增）**：整列橙底強調，用於「本文」列與最佳結果列。
- `closing` 為結尾感謝頁：內容區正中置大字，`text` 預設 "Thank You for Your Attention"、`size` 預設 40pt。**v2.6 起，建構器一律在簡報最後自動附加一張致謝頁**（不論簡報類型），plan 不需要、也不必手動加這一頁——若 plan 最後一張已自訂 `closing`（例如想換一句收尾語），建構器沿用該自訂內容不重複附加；若想關閉此自動行為（例如只交付單一章節片段），設 `meta.no_closing_slide: true`。
- `meta.language`：`"zh-TW"`（預設）或 `"en"`，控制固定標籤（報告人/Presenter、指導教授/Advisor、物理意義/Physical meaning）；**投影片內容本身的語言由撰寫 plan 時決定**——使用者指定全英文簡報時，plan 內所有 title/bullets/note/takeaway 一律以英文撰寫，不要中英混雜。
- `meta.eq_preamble`：自訂公式編譯 preamble（例如使用者有自己的 my_latex_packages.tex 內容時，把套件清單填入此欄），同時影響渲染與輸出的 .tex 檔案。
- `meta.eq_show_source`（v2.11 起預設 `false`）：是否在每張公式圖下方顯示 LaTeX 原始碼小字。v2.11 起原始碼改寫進**該頁備忘錄**（簡報者檢視看得到、可複製貼進 IguanaTex）與 `equations/*.tex`，投影片上不再出現灰色小字；工作草稿想直接在投影片上看到時設 `true`。
- **v2.11 新欄位**：
  - 任何頁都可加 `notes`（備忘錄字串，`\n` 分行）與 `backup: true`（放到致謝頁之後；第一張備用頁未寫 `section` 時自動用 `Backup`）。
  - `meta.title_style`：`"three-level"`（預設）或 `"two-level"`——章名 32pt small caps＋頁名 16pt 粗體 navy 同一行，省下一整行給內容（研討會口頭報告建議用）。
  - `meta.deck_type`：`research`／`lecture`／`weekly`／`sop`／`conference-oral`；`conference-oral` 時 lint 檢查每卡 ≤3 點。
  - 卡片 `tint`：`blue`／`orange`／`vermilion`／`green` 淡底＋本色框（`green` 是第 4 語意色，只在有 ✓／✗ 或文字標籤等雙重編碼時用）。
  - band `chevrons`：`{"kind":"chevrons","steps":[{"head":"…","body":"…"}],"accent":索引}`，3–5 個階段，第一個為五邊形。
  - band `lanes`：`{"kind":"lanes","lanes":[{"label":"Conventional\nmanual","tint":"blue","items":[{"image":"…","caption":"…"},{"text":"…"}],"kpi":{"value":"≈40 h","body":"…"}}]}`；與 `figure` 一樣吃剩餘高度。
  - `meta.visual: "v2.8"`：鎖回 v2.10 以前的外觀（結論橫條 20pt、公式原始碼留在投影片上、無公式備忘錄），已交付簡報小改重出時用。
  - 官方模板（`--profile`）另用 `meta.paper_title`／`meta.presenter`（組頁尾）或 `meta.footer`（直接指定頁尾）；封面可用 `authors`、`affiliation`。
- `meta.eq_source_size`（預設 `11`）：原始碼小字標註的字級。此標註屬於中繼資料用途（供複製，不是正式呈現內容），預設不受全簡報 18pt 正文下限管轄；若想在編輯階段看得更清楚，可設為 `18` 或更高，但公式較密集的頁面版面會更緊繃，建議先用預設值，需要再調整。

### 步驟 3：建構

```bash
python <skill_path>/scripts/plan_lint.py plan.json   # 建置前結構檢查（build_deck 會自動跑，可單獨執行）
python <skill_path>/scripts/build_deck.py plan.json <輸出目錄>/簡報名稱.pptx
```

`<輸出目錄>` 依使用者指定；未指定時用目前工作目錄。不要寫死特定環境的路徑。

**研討會官方模板**（v2.11）：官方模板通常把 logo、線條、頁尾畫在範例投影片上，不能用版面配置建頁。改用描述檔：

```bash
python <skill_path>/scripts/build_deck.py plan.json out.pptx --template <官方模板.pptx> --profile <skill_path>/assets/profiles/ecce2026_oral.json
```

描述檔指定哪張範例頁當封面／內容頁／致謝頁、標題與頁尾在哪個文字框、哪些範例文字要刪、內容區範圍。
新會議的模板依 `references/template-profiles.md` 寫一份新的描述檔。官方模板檔本身不隨本技能散佈。

**`build_deck.py` 自 v2.9 起在建置前自動執行 `plan_lint.py`，發現錯誤級問題直接中止、不產出半殘檔案**（除錯時可加 `--no-lint` 跳過，正常流程不要用）。這是刻意做成「預設執行」而非「另外記得跑」——缺圖與缺欄位這兩類靜默失敗的共同點是「不報錯、檔案也產得出來」，一個要靠人記得執行的 lint 等於沒有 lint。錯誤級涵蓋：`type` 不在白名單、依頁型缺必要欄位（例如 `equation` 沒有 `blocks`）、圖檔不存在、`bands` 超過 3 個、`rows` 欄數與 `columns` 不符、未知的 `mark`／`marker`／`meta.visual`。警告級涵蓋：外部圖未標 `source`、單頁 bullet >6、頁大標過長、未知欄位（打錯字偵測）、同 band 多張 accent 卡。

建構器行為：
- 自動清除模板中的範例頁，只保留母片與版型（header bar、校訓、底線、頁腳、頁碼皆由母片提供，不需處理）。
- 條列字級自動適配：由指定字級（預設 24pt）逐步下修至可容納，**降到 18pt（`MIN_BODY_SZ` 全域下限）就會印出「建議拆頁」警告——看到警告就回 plan 拆頁，不要接受過小字級**。（v2.7 修正：本行原誤寫為「低於 16pt」，與程式碼的 `MIN_BODY_SZ = 18` 及 `sz <= MIN_BODY_SZ` 觸發條件不符。）
- 公式圖以實際 pt 大小置入（2 條內 24pt、3 條 20pt），過寬會自動縮小並警告。
- 圖片等比縮放置中於格位，絕不變形裁切。
- **配色（v2.8）**：結構色／語意色兩層制。結構色 navy `#14274E`（頁大標／表頭／徽章／卡片標題）、`#1F2937`（正文）、`#6B7280`（副標／圖說／註腳）、`#F5F7FA`／`#D6DEE9`（卡片底／框）；語意色一律取自 **Okabe-Ito 色盲友善色票**——Orange `#E69F00`（結論／takeaway／KPI）、Blue `#0072B2`（對照／強調）、Vermilion `#D55E00`（警示／進度 active）。**綠色自語意層退出**（舊版綠 takeaway ＋ 紅 active 構成紅綠對立，第一／二型色覺異常者無法區分）。六條配色硬規則見 `references/lab-style-conventions.md` §2.5。
- **字級（v2.8）**：單一 `MIN_BODY_SZ = 18` 全域下限改為**分角色下限**（見 `SZ` 表）：頁大標 32/下限 26、正文 24/下限 20、卡片內文 18/16、圖說 13/12、來源與註腳 11.5/11、頁副標 16、KPI 44。輔助資訊刻意壓低正是視覺層次的來源（對齊實驗室參考簡報 54 頁實測字級譜）。個案可用 `meta.caption_size` 覆寫。
- **三層標題（v2.8）**：plan 提供 `section` 時啟用——章 running title（40pt 藍置中，母片 placeholder）→ 頁大標（32pt bold navy 靠左，前置箭頭）→ 頁副標（16pt 灰）。同章連續多頁只需第一頁寫 `section`。**未提供 `section` 時完全維持 v2.6 行為**，既有 plan 不需修改。
- **`meta.visual: "v2.6"`**：把配色與字級鎖回舊常數（已交付簡報要小改一頁重出的情境）。bug 修復（封面錨定、noProof、table note 幾何）不受此開關影響。
- **v2.11（ECCE 2026 回饋，conventions §2.5c）**：行內重點 `!!…!!` 統一用 `#C00000`（全簡報只有這一種重點紅）；結論橫條基準 16pt、重點片語黃 `#FFD54F` +4pt，兩行時橫條自動加高到 0.85in；KPI 數字在窄卡片會自動縮到一行；卡片標題換行估算扣除箭號縮排（修正長標題壓到內文）；公式圖的替代文字改為 LaTeX 原始碼。
- **表格樣式（v2.3）**：表頭 navy（#003781）底白粗體置中、第一欄項目欄淡藍底（#DCE6F1）＋粗體、全表細框線（#8EA9C9）、儲存格垂直置中、關閉預設橫紋——配色全部落實在建構端，與模板樣板色系一致。
- **IguanaTex 相容（v3 檔案交換法）**：經兩輪實測確認，透過 OOXML User Defined Tags Part 模擬 IguanaTex 的 `Shape.Tags.item("LATEXADDIN")` 判斷邏輯**無法成功**——這個判斷發生在 PowerPoint 的 VBA 物件模型執行期，只有真正載入 IguanaTex 增益集的 PowerPoint 應用程式才能將檔案中的 Tags Part 正確映射回 VBA 集合，這一步無法在檔案生成端驗證或保證，屬於架構性限制（Cowork 環境同樣受限，因為背後操作 pptx 的方式同樣是直接讀寫 OOXML，而非驅動真正的 PowerPoint 應用程式執行 VBA 巨集）。因此改採「檔案交換法」：
  1. **每張公式圖正下方**附一行等寬字型（Consolas）、灰階、斜體的 LaTeX 原始碼純文字（例如 `LaTeX: \lambda_d(i_d,i_q) = ...`），可直接在 PowerPoint 中反白複製，貼進 IguanaTex「New LaTeX Display」對話框的 Input code 欄位重新生成。
  2. 建構完成後，**同步輸出獨立的 `.tex` 檔案**至輸出目錄的 `equations/` 子資料夾（每條公式一個檔案，含完整 `\documentclass`/`\usepackage`/`\begin{document}` preamble），可直接用 IguanaTex 官方支援的「Read from File」功能開啟，不必手動複製貼上。
  3. 同時輸出 `equations_index.md` 對照表（投影片序號、`.tex` 檔名、LaTeX 原始碼），方便在多條公式的簡報中快速定位。
  4. 所有輸出的 `.tex` 檔案皆已用 `pdflatex` 實際編譯驗證可成功產出 PDF（含 `cases`/`aligned` 等 amsmath 環境），確保拿給 IguanaTex 使用時不會因語法問題失敗。
  這個方案只依賴「正確寫文字到投影片」與「正確寫檔案到磁碟」，兩者都能在生成端完全驗證，不涉及對 PowerPoint 或 IguanaTex 內部行為的任何猜測。
- **項目符號（v2.4 定案）**：第一層預設 **Wingdings `Ø`**（buFont=Wingdings、buChar=Ø）——即 PowerPoint 原生的 3D 箭頭式樣，與實驗室模板完全一致（Casey 裁定以 PowerPoint 觀感為準；v2.2 的 U+27A2 與 v2.3 的 U+27A4 觀感皆有差異故棄用）。第二層 `●`（U+25CF，Arial）。顏色 #0000FF。實測 LibreOffice（QA 轉圖管線）可正確映射 Wingdings Ø 為同款箭頭字形，不產生 tofu；若目標環境確認無 Wingdings 字型，plan 可設 `meta.bullet_unicode: true` 退回跨平台安全的 `➤`（U+27A4，Arial）。
- **條列縮排（v2.4）**：依實驗室模板段落設定落實——文字之前（marL）1.37 cm、特別凸排（hanging indent）1.27 cm、段後間距 10pt、單行間距；第二層 marL 遞增 1.27 cm。outline 項目與 section 頁同規格，全簡報縮排一致。
- **字級下限**：全簡報文字（含條列主層/副層、公式物理意義說明、圖表 caption、表格內容、takeaway、封面次要資訊）皆遵守 `MIN_BODY_SZ = 18` 全域下限，不會出現低於 18pt 的文字；第二層條列在版面允許時維持 22–24pt 區間，僅在空間嚴重不足時才降到 18pt 下限，絕不繼續往下降。

### 步驟 4：QA（必做，四層）

```bash
bash <skill_path>/scripts/full_qa.sh 簡報名稱.pptx [輸出目錄]
QA_PROFILE=<同一份 profile.json> bash <skill_path>/scripts/full_qa.sh 簡報名稱.pptx   # 官方模板建置的簡報
```

官方模板的簡報一定要帶 `QA_PROFILE`：否則第 3、4 層會拿實驗室母片元素（header bar、7.25in 底線、左下頁腳）當通過條件而全部誤判。

一個入口跑完四層並輸出彙總（v2.9 起）：

1. **內容層**——輸出全簡報文字稿供掃過漏字／錯字／順序，並攔截「完全空白的投影片」（通常代表 plan 欄位寫錯導致內容沒被畫上去）。
2. **schema 層**——`schema_check.py` 以官方 ISO/IEC 29500 schema 驗證每張 slide XML。這是 PowerPoint 實際會做的嚴格檢查；LibreOffice 的解析器容錯度遠高於 PowerPoint，**僅靠 LibreOffice 能開啟／轉圖不能代表 PowerPoint 能正常開啟**（實測：`<a:latin>` 被重複寫入兩次，LibreOffice 完全無視，PowerPoint 開啟時跳出修復對話框）。schema 檔已內建於本 skill，腳本自動定位。
3. **像素層**——LibreOffice 轉 PDF → `pdftoppm` 轉圖 → `qa_check.py` 檢查母片元素、空白頁、溢出。
4. **版面幾何層**（`layout_lint.py`，v2.9 第二批）——直接讀形狀座標，補上像素層抓不到的類別。錯誤級：形狀超出投影片邊界、文字越過母片底線或侵入 header bar、**實質重疊**（完全包含＝合法容器關係，部分重疊＝缺陷；圖片與表格不視為容器）、**表格內容估算高度超過宣告高度**（PowerPoint 會自動撐開列高壓到下方元素——這是提案 A 的原始症狀，單看座標看不出來）。警告級：內容佔用比 >75%／含圖頁 >85%、同列圖高不一致、語意色 >3 種、出現低於 10.5pt 的文字。

退出碼：0＝四層全過、1＝有層未過、2＝環境或參數問題。

**四層全過仍不等於 QA 完成。** 自動化只驗幾何與統計，不驗觀感——版面好不好看、論證清不清楚、圖片夠不夠清晰，只有人眼能判斷。腳本最後會印出渲染圖路徑，**務必逐張看過**。

**修正一律回到 plan.json 改內容後重跑 `build_deck.py`**，不要直接改 pptx——這是修訂能收斂在一兩輪內的原因。
例外：使用者已在 PowerPoint 手動微調並決定保留（插 IguanaTeX 公式、調位置）之後，主檔就換成 pptx 本身，
重跑會蓋掉那些修改。從那時起改用 cpet-deck-finalize（寫入前檢查、快照、動畫、衍生版本），本技能只用來產生要補進去的新頁。

### 步驟 5：交付

交付最終 `.pptx`（位於上一步指定的輸出目錄）——交付方式依執行環境：Claude Code 告知使用者檔案路徑即可，Chat／Cowork 則用該環境的檔案呈現工具（如 `present_files`）。若簡報含公式，**一併交付 `equations/` 資料夾與 `equations_index.md`**（`build_deck.py` 已自動輸出至 `.pptx` 同目錄），並告知使用者：每條公式的原始碼在該頁備忘錄裡（v2.11；`meta.visual: "v2.8"` 或 `eq_show_source: true` 時在公式下方小字），若想用 IguanaTex「Read from File」功能，可直接指向 `equations/eqNN.tex`。若建構過程有警告，向使用者說明哪幾頁做了自動縮字或拆頁建議。

---

## 內容密度與學術發表規範（撰寫 plan 時強制遵守）

1. **一頁一訊息**：每頁只論證一件事；來源文稿一個段落塞不進一頁時，拆頁而不是縮字。
2. **公式三件套**：公式本體＋物理意義（`note`）＋成立假設；假設可獨立成一頁 `bullets`（A1、A2…編號），短註記可直接以括號附在計算標題後（例「計算銅損（未考慮鄰近效應與溫升）」）。
3. **圖是論證工具**：結果圖必附量化 `takeaway`（有數字），禁止「results look good」式空話；圖檔本身缺座標軸或單位時提醒使用者補圖。
4. **文字先、公式後**：方法頁優先用 `two_col`（左原理文字、右公式/圖）或 `equation` 的 `intro` 欄位，先講設計目的再上數學。
5. **條列上限**：主 bullet 每頁 ≤ 6 條、每條 ≤ 2 行；目錄 4–8 項。
6. **語言規則**：預設中文說明＋英文專有名詞/變數；使用者指明對外發表（會議、口試）時整份改英文。**章節標題與技術章節名慣用英文**（中文簡報亦然），變數、單位、專有名詞一律英文。
7. **每個方法章節收尾**放 `takeaway`，全份簡報的 Conclusions ≤ 4 條。
8. **實驗結果頁固定結構**：測試條件 bullet（含激勵訊號公式，如 `ω*_m=30sin(2π·454t) rpm`）→ 波形圖 → 通道定義（CH 對應 dq 變數符號，正式報告附刻度如 2A/div）；量化結論優先直接標註在圖上（來源圖已含標註時，takeaway 引用該數值）。驗證章第一頁交代受測系統：規格表與（或）測試環境照片＋設備標註。**模擬與實測有同條件數據時，以左右並排比較呈現**（左模擬、右實測，各附通道清單；測試條件一條 bullet 全量化交代）。
9. **設計參數計算頁例外**：控制器增益、磁性元件、snubber 等「設計程序」頁（非理論推導）保留規格 → 公式 → 數值代入 → 最終參數值的完整鏈，並以一句設計決策句收尾（例「為確保工作於 DCM，取激磁電感 35μH」）；公式頁一律以條件／目的句開場（`intro` 欄位）。**理論推導**則相反：正文只留「起點 → 假設 → 結果」，完整推導移至簡報末 Remarks 章節。
10. **出處與可重現性**：取材自 app note／datasheet 的頁面，頁尾附 `Reference：廠商 "文件標題"`；模擬／程式結果頁在頁面上標對應檔名（`.m`／`.psimsch`）；軟體 SOP 頁寫完整選單路徑。需指出引用檔案本身時，以小圖示＋檔名標註（圖片形式），**不**將附件嵌入 pptx。
11. **變數定義與比較呈現**：方程組出現 ≥3 個新符號時，同頁附變數定義清單（中文簡報用中文物理名）；比較內容同頁並列＋對照標籤（方法一／方法二、理想／實際）。
12. **編號規則依使用情境分流**（步驟 0.5 確認）：書面報告的配套簡報 → 圖表用章節式編號（圖 2.7、圖 5.3）＋頁面顯示小節編號徽章（2.3、4.1）；獨立簡報 → 圖表與公式以流水號編號（圖 1、圖 2、式 (1)…）。

---

## 模板風格規格（由母片與建構器自動落實，僅供核對）

- 尺寸 16:9（13.33" × 7.5"）。三個版型：封面（layout1）、標題及物件（layout2）、自訂版面（layout3）；建構器內容頁一律基於 layout2。
- 色彩：標題 `#0000FF` 粗體、副標/物理意義標籤 `#9B423D`、內文 `#1F1F6E`、強調 `#2D2D8A`、section 當前項 `#C00000`、takeaway 綠 `#2E6010`/底 `#E2EFDA`、表頭 `#003781`、表格項目欄底 `#DCE6F1`、表格框線 `#8EA9C9`。
- 字型：標題 Times New Roman／標楷體；內文 Arial／微軟正黑體（建構器已於 run 層級明確指定，不依賴繼承——模板 theme 的內文預設是 Times New Roman／標楷體，繞過建構器直接打字會退回 theme 預設）。
- 固定元素（母片提供）：頂部藍色漸層 header bar＋校訓、右上角 `Goal, Method, Progress, Results` 導覽、底部藍色分隔線、左下 `CPET-Y.S. Lai Lab`、右下頁碼。
- 本節已於 2026-07-14 以 `PPT_Example.pptx`（新模板 42 頁示例）逐項核對通過，核對明細與附註見 `references/lab-style-conventions.md` §6.4。
- **2026-08-03（v2.7）**：`assets/template.pptx` 更換為 Casey 提供的新版樣板。**母片完全一致**（header bar、TAIPEI TECH 與校訓圖片、底線 7.25in、`CPET-Y.S. Lai Lab` 頁尾、`SLIDE`／頁碼、右上 `Goal, Method, Progress, Results` 逐項比對相同），差異全部在 layout 層：(a) 標題 placeholder top 0.40in → **0.29in**、內容版面配置區 top 1.15in → **1.07in**（建構器 `TITLE_TOP`／`SUB_TOP`／`BODY_TOP_PLAIN`／`BODY_TOP_SUB` 已同步上移）；(b) 封面主標 ph13 由 (2.39, 2.16, 8.54×3.19) 加寬為 **(0.76, 2.16, 12.01×2.97)**；(c) 封面資訊區 ph14 由 (2.69, 5.92, 7.95×0.91) 上移加高為 **(2.02, 5.25, 9.37×1.73)**；(d) **新增第四個版型 `1_自訂版面配置`**（三張圖片版面配置區，各 3.54×5.51in，x = 0.33／4.75／9.19），原三版型名稱與尺寸不變。13.333×7.5in 寬螢幕、五頁示例結構與 v2.6 相同。
- **2026-07-15（v2.6）**：`assets/template.pptx` 再次更換為 Casey 提供的最新樣板（5 頁示例，含標題頁、標題及物件頁、致謝頁範例）。尺寸／三版型名稱／母片固定元素與前版一致，逐頁核對通過；範例中的致謝頁（"Thank You for Your Attention"，layout1／標題投影片、置中大字、無殘留 placeholder）已對照落實為建構器 `slide_closing()` 的標準輸出版式。

---

## 特殊版面（建構器不涵蓋時）

需要建構器九種類型以外的自由排版（例如複雜方塊圖疊字、跨頁動畫）時，先用 build_deck.py 生成全份，再對個別頁面用公版 pptx skill 的 unpack/pack 流程手動編輯；XML 範本與版位座標見 `references/xml_recipes.md`。**不要**為了少數特殊頁放棄建構器改全手寫。

## 相依套件

python-pptx、matplotlib、Pillow（渲染公式）、pandoc（docx 解析）、pdflatex + amsmath（公式 fallback）、LibreOffice + pdftoppm（QA 轉圖）。缺 python-pptx 時：`pip install python-pptx --break-system-packages`。

---

## 版本履歷

完整版本沿革見 skill 根目錄的 `CHANGELOG.md`（維護者文件，執行時不需讀取）。
維運規範、builder 修改流程與打包檢查清單見 `MAINTENANCE.md`。
