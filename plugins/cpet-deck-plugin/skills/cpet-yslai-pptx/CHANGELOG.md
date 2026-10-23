# cpet-yslai-pptx 版本履歷（Changelog）

> 本檔為**維護者文件**，不在 skill 執行時載入——SKILL.md body 每次技能觸發都會進入
> context，版本沿革對「產生簡報」沒有貢獻，故自 v2.8 起自 SKILL.md 移出（原本佔該檔
> 33% 字元量）。維運規範見 `MAINTENANCE.md`，兩者分開是因為更新節奏不同：規範少動，
> 履歷每次升版都要加一條。
>
> 撰寫紀律見 `MAINTENANCE.md` §1：功能變更 +0.1、同版 bug 修復於該版條目附記、回滾標
> `reverted`、每條必含變更清單／動機／驗證結果。

- **v2**（本履歷補記，原始日期不可考）：plan.json 驅動的確定性建構器架構——八種投影片類型、LaTeX 公式自動渲染內嵌、IguanaTex v3 檔案交換法、三層 QA（內容／schema／像素）、新模板（2026-04 版）視覺規格內建於 `assets/template.pptx`。
- **v2.1**（2026-07-14，未安裝即被 v2.2 取代）：依 9 份舊模板 PDF 樣本抽取模板無關簡報風格規範，新增 `references/lab-style-conventions.md`；SKILL.md 補強步驟 1（routing＋實驗室慣例）、規範 7→11 條、補建版本履歷章節。模板核對（docx 基準）當時未執行。
- **v2.2**（2026-07-14）：Casey 對 v2.1 的候選規則與衝突報告裁決後修訂——(1) 候選裁決：C2 採用（Outline 上限 8 項）、C3 升級硬規則（模擬 vs 實測左右並排，規範第 8 條）、C5 升級硬規則（假設括號註記，規範第 2 條）、C4 教學情境條件採用（Homework 頁）、C7/C8 條件採用（新增規範第 12 條：書面配套用章節式編號＋小節徽章，獨立簡報用流水號）、C1/C6 捨棄（C6 以 icon 圖示標註替代嵌附件，併入規範第 10 條）；(2) 新增**步驟 0.5 使用情境確認**（簡報類型／書面配套／教學情境／語言，未言明必先確認）；(3) 推導取捨定案：理論推導中間步驟移至簡報末 **Remarks 章節**（規範第 9 條、內容映射表 equation 列）；(4) 模板核對改以 `PPT_Example.pptx` 執行**通過**（尺寸／版型／標題副標色／theme 字型／母片固定元素一致；2 附註＋1 粒度限制見 lab-style-conventions.md §6.4），該示例同時證實 running title＋section 頁並存與 Remarks 章節為新時期現行慣例；(5) 依 Casey 裁決補入**章節回訪**規則（conventions §1.7）：每個 Part 開頭以 `section` 頁重放 Part 清單＋`active` 進度（PPT_Example p7/p15/p22 佐證），原 §6.5「Outline 回訪樣本未見」結案。scripts/、assets/、plan schema 零改動。舊版備份：`archive/SKILL.md.v2-bak`。
- **v2.3**（2026-07-14）：依 Casey 對 v2.2 生成結果的回饋，首次修改建構器 `scripts/build_deck.py`（三項功能）＋新增輸入範本：(1) **表格樣式強化**——表頭 navy 底白粗體、第一欄自動視為項目欄（淡藍底 `#DCE6F1`＋粗體，`first_col_item` 可關）、全表細框線（`#8EA9C9`）、儲存格垂直置中、欄位對齊自動判斷（短內容置中／長句靠左，`col_align` 可覆寫）、關閉預設橫紋改由樣板配色落實；(2) **項目符號**第一層 `➢`(U+27A2) → `➤`(U+27A4)，等邊實心三角更貼近 PowerPoint Wingdings 觀感且維持跨平台安全；(3) 新增 **`closing` 頁型**——內容區正中置大字感謝頁（預設 "Thank You for Your Attention" 40pt 標題藍粗體），解決 v2.2 Thanks 頁近空白的 QA 失敗；(4) 新增 `assets/input-templates/`（`input_template.md`／`.docx`／`.tex`）標準化來源文稿範本：簡報資訊宣告區＋版面提示語法（`[layout:]`／`[figure:]`／`[note:]`／`[remarks]`…），並於步驟 0 文件化語法表。驗證：戰鬥營測試簡報重建後像素 QA 10/10 通過、XML well-formed 通過。
- **v2.4**（2026-07-15）：依 Casey 對 v2.3 的 PowerPoint 實機檢視回饋——(1) **項目符號定案**：第一層改回 Wingdings `Ø`（PowerPoint 原生 3D 箭頭式樣），實測 LibreOffice QA 管線可正確映射不產生 tofu，另留 `meta.bullet_unicode` 後備開關（➤/Arial）；(2) **條列縮排規格化**：依模板段落設定（文字之前 1.37 cm、凸排 1.27 cm、後段 10pt、單行間距）取代原 inch 估值，bullets／outline／section 全面一致；(3) 移除 skill 內 `archive/SKILL.md.v2-bak`（Casey 核可；同一份備份保留於專案資料夾 `cpet-yslai-pptx-v2.1-upgrade-package/archive/`）。驗證：戰鬥營測試簡報重建，buChar/buFont 與 marL/indent 之 XML 值逐項核對正確、像素 QA 10/10 通過。**同版修復（2026-07-15）**：`scripts/render_eq.py` 的 pdflatex 路徑補入 `\usepackage{graphicx}`——原缺此套件時 `\scalebox` 靜默失效，所有走 pdflatex 的公式（cases／aligned 等）一律以 12pt 輸出而非指定字級；修復後以 Final Project Report 轉換範例（18 條公式、55 頁）驗證，公式尺寸正確、像素 QA 55/55 通過。
- **v2.5**（2026-07-15）：轉換與維運能力入庫——(1) 新增 `scripts/extract_legacy.py`（舊簡報機械抽取器：文字／表格／圖片全抽，HIDDEN/OMML/GROUP/SPARSE/EMPTY_TABLE 五類旗標＋旗標頁自動渲染；以 49 頁 Demo 實測，21 頁旗標與人工判定一致）；(2) 新增 `references/legacy-conversion.md`（舊簡報→新模板 L1–L4 SOP，自兩個實際轉換案例提煉），步驟 0 加入 routing；(3) 新增 `MAINTENANCE.md`（維護者文件：版本紀律、builder 五步修改流程、規則變更留痕、驗收判準、Cowork 環境風險與打包檢查清單）。plan schema 與既有 builder 行為零改動。
- **v2.6**（2026-07-15）：依 Casey 要求換模板＋致謝頁一律自動附加——(1) **模板更換**：`assets/template.pptx` 換成 Casey 提供的最新樣板（5 頁示例：封面、標題及物件×2、致謝頁），三版型名稱／尺寸／母片固定元素與前版一致，已核對通過（見「模板風格規格」章節）；(2) **致謝頁改為建構器自動附加的硬規則**：新增 `_ensure_closing_slide()`，在 `build()` 存檔前檢查 plan 最後一張是否已是 `closing` 型——是則沿用（視為使用者自訂收尾語），否則自動追加一張標準致謝頁；新增 `meta.no_closing_slide: true` 作為例外關閉開關（單一章節片段等非完整交付情境）。移除舊規則「成果報告型以 Conclusion 收尾、不加 Thanks 頁」，改為**不論簡報類型，一律以致謝頁收尾**；(3) `slide_closing()` 改用封面 layout（layout1／標題投影片）並清空其全部 placeholder，取代原本的 layout2＋部分清理，版式與新模板內建的致謝頁範例逐項比對一致（無殘留提示框、無 body placeholder）。驗證：測試 plan（含手動 closing 與未寫 closing 兩種情況）分別產出 2 頁／4 頁，致謝頁正確附加或沿用自訂文字不重複；schema 驗證與像素 QA 皆通過。SKILL.md 同步更新內容映射表、步驟 2 schema 注意事項、實驗室慣例段落。
- **v2.7**（2026-08-03）：換新版模板＋四項無風險修復（本版不動版面演算法，僅幾何常數同步與環境健壯性）——(1) **模板更換**：`assets/template.pptx` 換成 Casey 提供的新版樣板，母片零差異、layout 層四項變更已逐項核對（見「模板風格規格」章節），建構器 `TITLE_TOP` 0.36→0.25、`SUB_TOP` 1.02→0.91、`BODY_TOP_PLAIN` 1.18→1.07、`BODY_TOP_SUB` 1.62→1.51 同步上移，維持與 placeholder 的既有相對關係；(2) **封面資訊區塊（ph14）改為底端錨定**——原沿用 placeholder 固定 top/height，資訊行數一多（報告人＋CPET＋NTUT＋日期共 4 行）末行日期就會壓到母片底線（7.25in）之外被遮，此為建構器真實 bug；改為依實際行數估高、方框底端固定在底線上方 0.2in、`vertical_anchor=BOTTOM` 文字向下貼齊，並加 `COVER_INFO_TOP_MIN=5.20` 上限保護避免侵入主標 placeholder。同時把主標換行估算寫死的 8.4in 改為讀取 ph13 實際寬度（新模板已加寬至 12.01in，沿用舊值會高估行數而無謂縮小字級）；(3) **新增 `meta.no_proof`（預設 true）**——`_set_font()` 為所有文字 run 寫入 `noProof="1"`，關閉 PowerPoint 編輯畫面對中文字與 CPET／MTPA／SVPWM 等英文專有名詞的拼字檢查紅波浪線（放映與列印本就不受影響，此為編輯體驗改善）；設 `false` 可還原檢查；(4) **`schema_check.py` 去除寫死路徑**——原 `SCHEMA` 硬編 `/mnt/skills/public/pptx/...`，Cowork 實際掛載於 `/sessions/<id>/mnt/.claude/skills/pptx/...` 導致整層 schema QA 靜默失效（症狀是「找不到檔案」易被誤判為環境問題跳過）；改為三段式定位並**把官方 `ISO-IEC29500-4_2016` schema 目錄內建進 `scripts/office/schemas/`**（第一優先），徹底去除對 pptx skill 掛載位置的依賴，SKILL.md 步驟 4 的 QA 指令同步改為直接呼叫 `schema_check.py`；(5) **文件修正**：步驟 3 原寫「低於 16pt 會印出建議拆頁警告」與程式碼 `MIN_BODY_SZ = 18`／`sz <= MIN_BODY_SZ` 的實際觸發條件不符，改為 18pt。驗證：封面 2 行／4 行兩種情況分別重建，日期落點一致且不溢出；全簡報 run 皆帶 `noProof="1"`；`schema_check.py` 自動定位內建 schema 並通過；像素 QA 與逐頁目視通過。
- **v2.8**（2026-08-03）：版面與視覺層改版——依 Casey 提供的實驗室參考簡報（54 頁，PowerPoint 實機產出）反推設計語言，並導入 Okabe-Ito 色盲友善配色。(1) **新增 `bands` 組合式頁型**：一頁 1–3 個水平帶（`text`／`figure`／`cards`／`table`），覆蓋實驗室五種排版式樣中的四種垂直式樣（左右分欄仍用 `two_col`——band 是垂直堆疊模型，加 `split` 會讓實作面積翻倍，取捨為兩套版面模型並存）；原規劃的 `numbered`／`kpi` 獨立頁型**取消**，改由 `cards` 的 `badge`／`kpi` 欄位表達，少兩套幾何程式碼且行為等價。新增 `_card()`／`_draw_badge()` 原語，幾何全取自參考簡報實測（roundRect adj≈1800、底 `#F5F7FA`、框 `#D6DEE9` 0.75pt、內距 0.28/0.16in、卡間距 0.20in、徽章 0.40in）。(2) **配色改採 Okabe-Ito 語意色**：結構色／語意色兩層制，Orange `#E69F00`（結論）、Blue `#0072B2`（對照）、Vermilion `#D55E00`（警示），**綠色自語意層退出**——舊版 takeaway 綠 `#2E6010` 與 section active 紅 `#C00000` 構成紅綠對立，第一／二型色覺異常者（男性約 8%）無法區分。takeaway 改為橙底 `#FBEFD8`＋橙框＋**navy 文字**（對比 12.90:1；橙字在此底上僅 1.98:1 不可用，舊版綠底綠字為 6.29:1，本次為提升）。新增 conventions §2.5 六條配色硬規則（同時約束 infographic-forge 出圖）。(3) **字級由全域 18pt 下限改為分角色下限**（`SZ` 表）：圖說 13pt、來源／註腳 11.5pt、卡片內文 18pt、正文 24/20——輔助資訊壓低正是視覺層次的來源，對齊參考簡報實測字級譜。(4) **三層標題**（章 running title／頁大標／頁副標），由 `section` 欄位啟用；未提供時完全維持 v2.6 行為，既有 plan 零修改。(5) **語意項目符號 `mark`**：`pro`／`con`／`step` 一律用 PowerPoint 內建字型字元（Wingdings U+00FC／U+00FB、Arial U+25BA），新增 `buSzPct` 統一控尺寸（原本未寫此屬性，是「符號忽大忽小」的真正來源）；**刻意避開 U+2714／U+274C／U+25B6** 三個帶 emoji 呈現變體的碼點。takeaway 前綴同步由 U+25B6 改 U+25BA。(6) **`images[].source` 圖片來源標註**（figure band／figure 頁型／two_col 三處）＋`source_shared`，並寫入 conventions §2.6 作為學術誠信要求。(7) **提案 A（table note 重疊）根治**：抽出 `draw_table()` 與 `_table_metrics()`，note 比照 takeaway 先扣空間再定位；更關鍵的是把「`0.42 × 列數` 常數估高」改為**逐格估算換行行數**並把列高明確寫回表格。過程中實測發現「壓縮列高」是無效手段（PowerPoint 依字級強制最小列高，壓了不會變矮，只是讓配置與渲染再度脫鉤、重演同一 bug），最終改為**字級適配**：由 20pt 逐級下探至 18pt 直到放得下，放不下就明確警告要求拆頁。新增 `highlight_rows` 整列橙底強調。(8) **`meta.visual: "v2.6"`** 逃生開關：把配色與字級鎖回舊常數，bug 修復不受影響。(9) `schema_check.py` 新增**具名已知例外機制**：`buSzPct/@val` 在 ISO-IEC29500-4:2016 被宣告為只接受 "85%" 百分比字串，但真實 PowerPoint 寫的是 `val="100000"` 千分之一百分比整數——佐證是 Casey 的參考簡報 112 處全為此形式、且該檔 55 個 part 有 25 個因此被判 FAIL。取捨：以 PowerPoint 實機行為為準（MAINTENANCE.md §4），並把此落差列為具名例外附完整理由，避免它淹沒真正的 schema 錯誤。驗證：六頁綜合測試 plan（目錄徽章頁、雙欄卡片頁、table band＋強調卡頁、step 符號頁、既有 table 頁型相容）＋三頁圖文測試 plan（式樣 4／5／既有 figure 頁型）全部重建，schema 8/8 與 5/5 通過、像素 QA 7/7 與 4/4 通過、逐頁目視通過、灰階去飽和測試層次保留。目視另抓到兩個實作缺陷並修正：figure band 內有／無 `source` 的圖高度參差（改為取同 band 最大值），以及上述表格列高壓縮無效問題。

　**同版修訂（2026-08-03，依 Casey 對 v2.8 輸出圖的目視回饋）**：(a) **takeaway 與 accent 卡無法區分**——兩者原本都是淡橙底＋橙框，視覺重量完全相同。問題本質是層級不是色相：accent 卡是同層元素之一，takeaway 是整頁結論。改為 takeaway＝**全頁唯一的 navy 實心橫幅＋白字**（對比 14.69:1、灰階底 38 vs 卡片 240，分離最大；navy 已是結構色故不增加色數，且與參考簡報 p9 做法一致），前綴箭頭維持橙色保留「橙＝結論」的語意線索；accent 卡續用淡橙底。另兩個備案記錄於此供日後切換：字卡改白底＋橙左粗邊條（靠形狀區分，但遠距投影層級感弱）、takeaway 改深橙 `#8A5A00` 實心＋白字（5.93:1，但投影幕上易偏暗發褐）。(b) **圖片被字卡擠壓**——bands 原本讓非 flex band 取滿自然高度，圖片只拿到剩餘空間，式樣 4 的波形圖小到看不出趨勢。新增**圖片優先的高度分配**：`MIN_FLEX_RATIO=0.52`（有圖時圖片 band 至少取得可用高度 52%）、`CARDS_MAX_RATIO=0.32`／`TEXT_MAX_RATIO=0.24` 上限（表格不設限——列高不可壓），並可用 band 的 `max_h` 個別覆寫；字卡被壓縮時改以**降卡片內文字級**適配（18→16pt）而非硬壓高度（後者只會讓文字溢出卡片邊界），仍不足時夾至邊界並警告，確保絕不侵入 takeaway。KPI 卡的副標改用 caption 字級（它是數值的說明不是正文）、大數值行高係數 1.35→1.22、字級下限 32→28。實測圖片高度由 1.3in 提升至 2.10in（+62%）。(c) **目錄與 Outline 風格不一致**——目錄用 navy 數字圓徽章、Outline 用箭號。改為 **`cards` 的 marker 預設即箭號**（有 `head` 且非 KPI 卡時），要數字徽章須明確給 `badge`。實作上必須走 `buChar`＋`buFont` 這條路徑：第一版把箭號當成一般文字 run 並指定 Wingdings 字型，LibreOffice 直接印出字面 "Ø"——Wingdings 的私有字元映射只在項目符號路徑上被正確處理，這點已寫入程式碼註解避免重蹈。 (d) **`assets/input-templates/` 三份範本升至 v2.0**（`.md`／`.docx`／`.tex`）——v1.0 有兩處已與實作不符：範本寫「takeaway（綠色橫條）」（v2.8 已改 navy 實心橫幅）、`.tex` 版仍寫「成果報告型以 Conclusion 收尾、不加 Thanks 頁」（此規則 v2.6 即已移除）。新增語法：`[sub:]` 頁副標、`[cards: 欄數]`／`[card:]`／`[card-accent:]`／`[card-num:]`／`[kpi:]` 字卡群、條列行首 `(+)`／`(-)`／`(>)` 語意符號、`[figure: … | source: …]` 與獨立行 `[source:]` 圖片出處、`[highlight: 關鍵字]` 表格整列強調。**刻意不新增「式樣編號」宣告語法**——五種排版式樣就是「文字／圖／字卡／表格」四種區塊的排列組合，使用者寫什麼、順序如何，式樣就決定了；要他先判斷「這是式樣 4 還是式樣 5」再宣告，是把工具的內部結構外露給使用者，既增加負擔又容易寫錯（宣告式樣 5 卻只給一張圖）。`[layout:]` 因此退化為「覆寫預設判斷」的例外機制而非必填。SKILL.md 步驟 0 語法表同步擴充並加註 plan 欄位對照。驗證：以範本示例內容手動映射為 plan 做 round-trip 重建（4 頁，涵蓋雙欄字卡＋強調卡、表格＋highlight＋結論卡、圖＋KPI 卡＋觀察卡、三種語意符號條列），schema 6/6、像素 QA 5/5、逐頁目視通過——確認每一個新語法都有可運作的 plan 欄位對應，無空頭承諾。 (e) **文件結構調整**：版本履歷自 SKILL.md 移出至本檔 `CHANGELOG.md`。依 skill-creator 的 Progressive Disclosure 規範，SKILL.md body 在技能每次觸發時都會載入 context，而版本沿革對「產生一份簡報」的貢獻為零——它在 SKILL.md 中佔 33% 字元量（8,753／26,236）純屬 context 浪費。未併入 `MAINTENANCE.md` 的理由是兩者更新節奏不同：維運規範少動、履歷每次升版都要加一條，合併會讓規範被增長的履歷淹沒。SKILL.md 留一行指標，`MAINTENANCE.md` §1／§2／§6 三處引用同步改指向本檔，打包檢查清單新增「SKILL.md 內無殘留履歷章節」一項。SKILL.md 由 26,236 降至 17,586 字元。 (f) **依 Casey 於 Windows PowerPoint 實機驗收的兩項裁定修訂**（2026-08-04，驗收卡逐項核對，其餘全數通過）：**(f-1) `mark: con` 的叉號字元更換**——原 Wingdings `U+00FB` 是細筆畫的 ballot X，實機視覺重量遠低於同組的勾號（`U+00FC`），Casey 反映「太小、希望是正體的 X」。改用 **Arial 的拉丁大寫 `X`**，`buSzPct` 由 88% 回到 100%：字型必定涵蓋無缺字風險、無 emoji 呈現變體、筆畫粗細與內文一致。未採用幾何上更對稱的 `U+2715`（MULTIPLICATION X），因其屬 Dingbats 區塊、Arial 未必涵蓋，有 tofu 風險——與其換一個可能缺字的符號，不如用保證存在的字母。勾號 `U+00FC`／步驟箭號 `U+25BA`／卡片方塊 `U+006E`／預設箭號 `U+00D8` 四者實機驗收通過，維持不變。**(f-2) 頁大標字級 36pt → 32pt**（`SZ["page_head"]` 由 (36, 28) 改為 (32, 26)），Casey 實機判定 36pt 過大；SKILL.md 兩處說明同步。**其餘實機驗收項目全數通過**：13pt 圖說與 11.5pt 註腳可讀、表格與註腳無重疊（提案 A 修復確認生效）、navy takeaway 與淡橙強調卡層級可分、KPI 深橙數值清楚、`noProof` 確實消除紅波浪線、標楷體／微軟正黑體字型分工正確、封面日期未被母片底線遮住、開檔無修復對話框——這些項目自此不再標「待實機確認」。
- **v2.9**（2026-08-04）：QA 工具化第一批——**純附加工具，不改版面演算法**。(1) **新增 `scripts/plan_lint.py`**：plan.json 結構驗證器。錯誤級（非零退出）涵蓋 `type` 白名單、依頁型的必要欄位、圖檔存在性、`bands` 上限 3、`rows` 欄數與 `columns` 一致性、`highlight_rows` 範圍、未知的 `mark`／`marker`／`meta.visual`、空卡；警告級涵蓋外部圖未標 `source`（conventions §2.6）、單頁 bullet >6、outline >8 項、頁大標顯示寬度 >20、公式缺 `note`、同 band 多張 accent 卡（§2.5b.1），以及**未知欄位偵測**（打錯 `takeway`／`txt` 這類會被建構器靜默忽略的拼字錯誤）。必要欄位一律訂為錯誤級而非警告級，依據是兩個實際發生且**三層 QA 全數 PASS** 的靜默失敗：plan 中 6 個圖片路徑失效只印一行 warn 就繼續（當時靠臨時腳本才一次抓到 17 個），以及 `equation` 把公式寫成頂層 `latex`／`note` 而非 `blocks[]` 導致靜默產出只有標題的空白頁。後者已做成專門的錯誤訊息，偵測到頂層 `latex`／`note` 時直接提示正確寫法。(2) **`build_deck.py` 建置前自動執行 lint**，錯誤級問題中止建置、不產出半殘檔案；`--no-lint` 可跳過（僅供除錯）。做成預設執行而非另外記得跑，是因為這兩類失敗的共同點就是「不報錯、檔案也產得出來」——要靠人記得執行的 lint 等於沒有 lint。(3) **新增 `scripts/full_qa.sh`**：三層 QA 單一入口，把原本四段互不知情的命令（schema_check → soffice 轉 PDF → pdftoppm → qa_check）包成一個，並新增**內容層**——輸出全簡報文字稿供掃過漏字錯字，同時攔截「完全空白的投影片」。統一退出碼（0／1／2）與彙總報告，最後印出渲染圖路徑並明確聲明「三層全過不等於 QA 完成」——像素層不做文字框幾何碰撞偵測，v2.8 的三個版面缺陷都是它判 PASS 而由人眼抓到的。(4) SKILL.md 步驟 3／4 同步改寫。**自我檢查**：以兩份刻意破壞的 plan 逐條觸發全部 24 條規則（17＋7 個錯誤、10＋4 則警告）並核對訊息正確；以三份正常 plan 確認不誤報；`build_deck` 三種行為（錯誤中止不產檔／`--no-lint` 強制建置／正常 plan 照常帶警告）逐一驗證；`full_qa.sh` 五種退出路徑（無參數／檔案不存在／非 pptx／空白頁／正常）退出碼全部正確。過程中修掉一個**自製圖誤判**：原本只比對路徑第一層，而實際 plan 常用絕對路徑（`/sessions/<id>/mnt/outputs/figs/...`），導致自製圖全被當成外部素材要求標 source；改為比對路徑的每一層，並把 `screenshots` 納入自製目錄。以本專案 55 頁的真實教學 plan 驗證：修正後由 25 則警告降為 2 則（皆為真實的 bullet 過多），23 個錯誤全數為真陽性——該 plan 的圖片路徑指向已消失的舊 session，今日重建會靜默產出 23 張缺圖投影片。 **同版第二批（2026-08-04）**：新增 `scripts/layout_lint.py` 與 `full_qa.sh` 的**第 4 層版面幾何**。原規劃只是「學術排版 lint 的閾值」，實作時改為對產出的 .pptx 做幾何檢查——因為閾值若只從 plan.json 算就看不到座標，而 v2.8 開發期間三個真實缺陷（table note 與最後一列重疊、figure band 圖高參差、封面資訊區被推出投影片左緣）全部是像素 QA 判 PASS、由人眼目視才抓到的**幾何錯位**，這才是該補的缺口。錯誤級：超出投影片邊界、文字越過母片底線或侵入 header bar、實質重疊、表格內容估算高度超過宣告高度；警告級：內容佔用比 >75%（含圖頁 >85%）、同列圖高不一致、語意色 >3 種、文字低於 10.5pt。**重疊判定的關鍵設計**是「完全包含＝合法容器關係，部分重疊＝缺陷」，但**圖片與表格不得視為容器**——第一版把表格也當容器豁免，回測時直接放過了 table note 重疊這個最重要的案例。**表格高度檢查**是獨立的一條：提案 A 的原始 bug 中，note 畫在「宣告的」表格下緣之下，宣告幾何看起來沒重疊、渲染後才被自動撐開的列高壓到，故單看座標抓不到，必須另外估算內容所需高度。自我檢查：合成 4 個已知缺陷回測全數命中（其中缺陷 1 是修正容器判定後才抓到），對照組的正常 deck 零誤報，寬鬆表格與擠壓表格能正確區辨（2.46in 內容 vs 1.00in 宣告→報錯；vs 3.00in→通過）；`full_qa.sh` 對正常檔退出碼 0、對缺陷檔 1。工具上線後第一次執行即抓到一個既有的小缺陷並修正：`add_caption()` 的框高原本固定 0.35in，在 13pt 圖說時比行進距離 0.31in 還高，導致圖說框與其下的來源框宣告座標重疊 21%——渲染上因文字靠上對齊而看不出來，但只要日後有人把該框改成垂直置中或加底色就會變成可見錯位；已改為依字級推算框高。 **同版修復（2026-08-04，由另一組 eval 抓到）**：`assets/input-templates/` 三份範本的檔頭標示「對應 skill v2.8」，而 SKILL.md 已是 v2.9。查證後確認不只是字串過期，而是三層問題：(a) **字面**——三份範本（.md／.docx／.tex）檔頭版本標示落後一版；(b) **實質**——v2.9 新增的量化上限（一頁區塊數 ≤3 且為錯誤級會中止建置、單頁 bullet ≤6、Outline ≤8、頁大標寬度 ≤20、每頁 accent 卡 ≤1、公式必附 note、外部圖必附 source）全部是**文稿階段就該遵守的填寫指引**，卻一條都沒寫進範本；同時漏了「圖片請用相對路徑」的提醒——這點有實證，一份 55 頁的真實 plan 因存了舊 session 的絕對路徑，重建時會靜默缺 23 張圖；(c) **流程**——`MAINTENANCE.md` 的打包檢查清單只核對 SKILL.md 與 CHANGELOG.md 的版本一致性，未涵蓋 `assets/input-templates/`，所以這個落差不是偶發，是檢查清單本身漏了一項，不補就會重複發生。處置：三份範本升 v2.1、檔頭改標「對應 skill v2.9」、新增「填寫上限」區塊（.docx 由 .md 經 pandoc 重生以確保三份一致）；SKILL.md 語法表下方補指向；`MAINTENANCE.md` 打包清單新增兩項檢查（範本檔頭版本＝SKILL.md 版本且三份語法一致／本版若新增文稿階段規則須寫進範本）。

- **v2.10**（2026-08-17）：QA 工具鏈跨平台修正——`full_qa.sh` 與 `schema_check.py`
  在 Windows 上無法執行的問題已解決，**不改任何版面演算法**。
  (1) **`schema_check.py` 解除 `xmllint` 相依**：原 `_validate_one()` 只走
  `xmllint` 外部指令，Windows 無內建 libxml2 工具鏈故常缺席，導致第 2 層
  schema QA 整層無法執行（症狀為 FileNotFoundError，正是本技能 v2.7 註解
  警告過的「容易被當成環境問題整層跳過」失效模式）。改為拆成
  `_validate_with_lxml()`（優先）與 `_validate_with_xmllint()`（後備），
  以 `lxml.etree.XMLSchema` 做驗證——同一個 libxml2 引擎、判定等價，且
  lxml 本為既有相依（`build_deck.py` 手動 XML 操作即用它），不新增套件。
  schema 編譯結果以 `_LXML_SCHEMA_CACHE` 快取，避免逐張投影片重複解析 XSD。
  (2) **`full_qa.sh` 工具探測改為「尋找可用實作」而非「假設標準名稱」**：
  Python 依序試 `python3`／`py`／`python` 並實際 `import pptx` 驗證
  （Windows 的 `python3.exe` 常是 Microsoft Store 的 App Execution Alias 假
  指令）；LibreOffice 除 PATH 另探測 `C:\Program Files\LibreOffice\program\
  soffice.exe` 等標準安裝路徑，缺席時提示 winget 安裝指令；`pdftoppm` 以
  `-h` 探測是否支援 `-jpeg`，不支援則退回 `-png`（TeX Live 夾帶的 poppler
  0.75.0 即只有 `-png`），檔名 glob 與彙總訊息連動。
  (3) 驗證：`bash full_qa.sh <deck>.pptx` 端到端執行，**四層全過、exit 0**
  （第1層內容 PASS／第2層 schema 4 個 part 全過／第3層像素 3 張全過／
  第4層版面幾何 0 警告）——這是本機環境首次能完整執行此單一入口腳本。
  `schema_check.py` 另做反向測試：故意送違規 PresentationML 確認正確回報
  `SCHEMAV_ELEMENT_CONTENT` 錯誤並判定失敗，非假通過。
  (4) 環境安裝紀錄：本次以 `winget install TheDocumentFoundation.LibreOffice`
  安裝 LibreOffice 26.2.5.2（官方 The Document Foundation 發行、MPL-2.0）。

  **同版修復（2026-08-30，由另一 session 實際產出示範簡報時發現）**：v2.10
  發布時的端到端驗證用的是乾淨 shell，未覆蓋兩種真實情境，此次補上。
  (a) **`qa_check.py` 收到 MSYS 路徑，glob 解不開**——`full_qa.sh` 原本用
  bash 的 `compgen -G` 展開 glob 確認圖檔存在，卻把「未展開的字面 glob
  字串」原樣傳給 `qa_check.py`，由 Python 的 `glob.glob()` 二次展開；此時
  `$OUTDIR` 是 bash/MSYS 形式路徑（如 `/c/Users/.../qa`），Windows 版
  Python 的 `glob` 不認得這種前綴，回傳空 list，誤判為找不到圖檔，第 3
  層像素 QA 假性 FAIL（PDF／PNG 其實都已正確產出）。改為 `full_qa.sh` 用
  `mapfile` 讓 bash 自己展開好 glob、把每個檔案路徑當獨立參數傳給
  `qa_check.py`；`qa_check.py` 的 `main()` 同步改為接受多檔案路徑清單
  （`sys.argv[1:]` 全收），僅當單一參數含 `*`／`?` 時才 fallback 用
  `glob.glob()` 展開以維持舊介面相容。此舉也一併解掉路徑含中文或空格時
  glob pattern 傳遞不可靠的隱性風險。
  (b) **soffice 被繼承的 `PYTHONHOME`／`PYTHONPATH` 污染，回非零 exit**——
  若呼叫端 shell 另外設了這兩個變數（常見於本機已有獨立 Python 環境的情
  況），LibreOffice 內建的 bundled Python 會誤讀它們、找不到自己的
  stdlib，印出 `Could not find platform independent libraries <prefix>`
  並以非零 exit code 結束——即使 PDF 其實已正常產出。原本 `full_qa.sh`
  用 `if ! soffice ...` 判定成功與否，因而整層第 3 層被短路跳過。改為
  `env -u PYTHONHOME -u PYTHONPATH` 呼叫 soffice，並且**一律以「PDF 檔案
  是否存在」而非 exit code 判定成功**（headless 轉檔情境下 soffice 的
  exit code 本就不可靠）。
  驗證：兩處修正皆有實測佐證（分別以 MSYS 路徑字串／Windows 路徑字串直
  接呼叫 `qa_check.py` 對照行為差異；以 `env -u` 清空前後對照 soffice
  的 stderr 與 exit code 差異，確認 PDF 皆正確產出 454KB、pdftoppm 正常
  轉出 9 張 PNG）。與此次修復同時，另一 session 用本技能產出了一份 9 頁
  示範簡報（SPMSM 無差拍預測電流控制），四層 QA 在繞過上述兩個 bug 後
  全綠，佐證修復後行為正確、非僅理論推導。

  **文字修訂（2026-09-20，不升版）**：移除 SKILL.md 寫死的執行環境假設。
  原文以 claude.ai Chat 的容器為預設：素材來源寫 `/mnt/user-data/uploads/`、
  輸出寫 `/mnt/user-data/outputs/`、交付指定用 `present_files`——這三者在
  Claude Code 都不存在。本技能自 v6 職權收斂後主要部署於 Claude Code，
  保留這些路徑會讓執行時嘗試寫入不存在的目錄。改為中性寫法：素材以
  絕對路徑引用但不假設前綴，輸出用 `<輸出目錄>`（未指定則用目前工作目錄），
  交付方式依環境而定（`present_files` 改列為 Chat／Cowork 的例子而非唯一做法）。
  同時統一腳本呼叫寫法：原本 `python scripts/...` 與 `<skill_path>/scripts/...` 混用，
  前者只在「當下工作目錄恰好是技能目錄」時才成立；全改為 `<skill_path>/scripts/...`
  （共 3 處：`extract_legacy.py`、`plan_lint.py`、`build_deck.py`，`full_qa.sh` 原本就是正確寫法）。
  行為未變，僅文件正確性，故不升版。

  **同版修復（2026-10-17，Windows 繁中環境的編碼崩潰）**：
  - 症狀：(1) 在 Windows 繁中環境跑 `full_qa.sh`，第 4 層 `layout_lint.py` 印到「≤」時以
    `UnicodeEncodeError: 'cp950' codec can't encode character '≤'` 崩潰，彙總判為 FAIL
    （第 1 層同樣受影響），等於「簡報沒問題但 QA 說不能交付」。(2) `build_deck.py` 讀
    `plan.json` 時以 `UnicodeDecodeError: 'cp950' codec can't decode byte 0x9d` 失敗，
    含中文的 plan 在 Windows 原生 Python 上**完全無法建置**。
  - 根因：兩者都是依賴系統預設編碼。stdout 接管線（Git Bash、`full_qa.sh` 內呼叫）時，
    Python 用系統 ANSI 碼頁（繁中 Windows 為 cp950），印不出 cp950 以外的字元；
    `open()` 未指定 `encoding` 時也用同一碼頁讀檔。開發與驗證在 Linux 容器（預設
    UTF-8）進行，所以從沒踩到。v2.10 的跨平台修正處理了工具探測與路徑，沒涵蓋編碼。
  - 修復：
    - `full_qa.sh` 開頭 `export PYTHONIOENCODING=utf-8`，涵蓋它呼叫的全部 Python。
    - 七支會印中文或符號的腳本（`build_deck.py`、`extract_legacy.py`、`layout_lint.py`、
      `plan_lint.py`、`qa_check.py`、`render_eq.py`、`schema_check.py`）在 import 後把
      stdout／stderr 重設為 UTF-8，單獨執行時也不會崩潰。
    - `build_deck.py` 讀 plan、`render_eq.py` 寫 `.tex` 改為明確 `encoding="utf-8"`。
      全部四個技能的 Python 已搜過，沒有其他未指定編碼的文字檔 `open()`。
  - 驗證（本機 Windows 11，未設 `PYTHONIOENCODING`）：
    - `layout_lint.py` 經管線執行：修改前重現 cp950 崩潰（以 `git stash` 還原舊版確認），
      修改後正常輸出「版面幾何檢查通過（9 張，3 則警告）」，rc=0。
    - `full_qa.sh` 對 `dist/demo-output` 的示範簡報四層全過。
    - 以 `dist/demo-output/plan.json` 經 `build_deck.py` 重新建置：修改前 cp950 讀檔失敗，
      修改後成功產出 8 張投影片（含 2 條公式 `.tex`），`full_qa.sh` 四層全過，
      渲染圖目視中文與版面正常。示範簡報原檔為 9 張，差一張的原因本次未追查
      （本次修改只動編碼設定，不影響頁數邏輯）。

  **同版修復（2026-10-21，schema_check 對 PowerPoint 存過的檔案誤報）**：
  - 症狀：ECCE 2026 定稿（PowerPoint 存檔、實機播放正常）經 `schema_check.py` 有 25/28 個
    part 判 FAIL，結論是「禁止交付」。
  - 根因：(1) buSzPct 已知例外的 regex 寫成 `element buSzPct`，只吃 xmllint 的訊息格式；
    v2.10 改以 lxml 為優先後端，lxml 的訊息是 `Element '{ns}buSzPct'`，大小寫與命名空間都
    對不上，例外從此失效。本技能自己的示範簡報沒有非 100% 的 buSzPct，所以一直沒有觸發。
    (2) PowerPoint 會寫入 `mc:AlternateContent`（ISO-IEC29500-3 Markup Compatibility），
    pml.xsd 不宣告它，直接驗證必報 strict wildcard 錯誤（2 個 part）。
  - 修復：buSzPct regex 改為不分大小寫、允許命名空間，兩種後端格式都吃；新增具名已知例外
    `mc:AlternateContent`，只比對 MCE 命名空間，並寫明規範依據與佐證。
  - 驗證（本機 Windows 11，lxml 後端）：
    - ECCE 定稿與 `cpet-deck-finalize` 重新寫入動畫的複本：28 個 part 全過，rc=0。
    - 以現版 `build_deck.py` 重建 `dist/demo-output/plan.json`：10 個 part 全過，rc=0。
    - 反向測試：在 ECCE 定稿第 2 頁（同時帶有 buSzPct 例外）插入非法元素，仍判 FAIL 並指出
      `SCHEMAV_ELEMENT_CONTENT`，rc=1——例外沒有遮蔽真錯誤。
  - 流程補強：已知例外新增時必須同時用 lxml 與 xmllint 兩種訊息格式各測一次（xmllint 本機
    未安裝，本次只驗 lxml 格式；regex 已兼容 xmllint 格式但未實測）。

- **v2.11**（2026-10-21）：大會官方模板 profile、備忘錄與備用頁、雙層標題、chevrons／lanes／tint、
  行內重點與結論橫條重點字（ECCE 2026 回顧計畫 P3＋P7）。

  **源起**：ECCE 2026 口頭報告完全在本技能外完成——官方模板只有一個空白版面配置、logo 與頁尾畫在範例頁上，
  只能寫一支專用 build.py 以文字比對與寫死座標處理；之後 Casey 在 PowerPoint 手改的版面語彙（雙層標題、
  chevron 流程、雙泳道對照、淡底卡、紅色重點字、結論橫條黃字）都沒有回到本技能。排版配色審查
  （`提案改善/ECCE2026_排版配色審查_2026-10-20.md`）10 項，Casey 2026-10-21 全數依建議採用。

  **新增內容**：
  - `--profile`（P3）：描述檔指定範例頁角色、標題／頁尾文字框、要刪的範例文字、內容區、封面欄位位置與字級；
    建構器以複製範例頁建頁（含圖片關聯），建置後刪除全部範例頁。第一份描述檔 `assets/profiles/ecce2026_oral.json`。
    說明見 `references/template-profiles.md`。官方模板檔本身不隨技能散佈。
  - plan：每頁 `notes`、`backup`；`meta.title_style`（`two-level`）、`meta.deck_type`、`meta.footer`／`paper_title`／
    `presenter`；卡片 `tint`；band `chevrons`、`lanes`；任何文字 `!!重點!!`；`meta.visual` 新值 `v2.11`（預設）。
  - P7 落地：重點紅單一 token `#C00000`（F1／F2）；結論橫條 16pt＋重點黃 `#FFD54F` +4pt、兩行自動加高（F4／F10）；
    LaTeX 原始碼改寫進備忘錄、不再留在投影片（F3）；雙層標題（F8）；`conference-oral` 每卡 ≤3 點（F11）；
    語意色含淡底與泳道全簡報 ≤3、第 4 色需雙重編碼（F5）；conventions v2.3 收錄 F6（流程圖標籤 ≥12pt 粗體）、
    F9（資料圖可沿用論文配色的例外條件）。
  - QA：`layout_lint.py --profile`、`qa_check.py --generic`、`full_qa.sh` 以 `QA_PROFILE` 環境變數切換；layout_lint 把淡底色
    歸併到本色計數、重點紅與黃字不計入語意色。

  **bug 修正（v2.8 外觀也受影響，依規不受 visual 開關控制）**：
  - 卡片標題換行估算沒扣掉箭號縮排 0.42in，3 欄卡片的長標題被低估一行、換行後壓到第一行內文（新 plan 實測重現）。
  - KPI 大數字在窄卡片（泳道 1.9in）被拆成兩行（「≈57」／「h」）；改為縮到一行（下限 20pt）。
  - 公式圖的替代文字原為暫存檔名（每次建置不同），改為 LaTeX 原始碼——同一份 plan 建置兩次的輸出因此完全相同。
  - 官方模板範例文字常以上標編號開頭，覆寫文字改以「字最多的 run」為格式樣板並移除 baseline。

  **取捨留痕**：
  - 結論橫條基準字級由 20pt 改 16pt 是外觀變更，已交付的簡報以 `meta.visual: "v2.8"` 重出即維持原樣。
  - lanes 不支援每格不同底色、不畫連接線以外的標註；需要更自由的對照圖時仍用 forge 畫一張圖。
  - 封面欄位的字級由描述檔給定起始值後自動縮到行數內，不嘗試自動找最佳位置（ECCE 用 `box` 指定）。

  **驗證**：
  - 回歸：v2.10 程式建置的 demo plan 與一份含 bands／cards／KPI／公式的 plan 作為基準；新程式以 `meta.visual: "v2.8"`
    重建後，每個 part 經 c14n 比對與基準相同，唯一差異是公式圖替代文字（原為暫存檔名，已改為 LaTeX）。
  - `tests/test_v211.py`：18/18 PASS（lint 8 條新規則、建置：備用頁位置、雙層標題字級與 small caps、結論黃字 +4pt、
    卡片紅字、公式原始碼不在投影片而在備忘錄、plan 備忘錄、窄 KPI 縮字、v2.8 外觀保留原始碼）。
  - 實驗室模板 v2.11（新功能 plan）與 ECCE 官方模板 profile 各建置一份，轉 PDF 逐頁目視；四層 QA 皆全過
    （官方模板帶 `QA_PROFILE`）。目視時發現並修掉 4 個問題：雙層標題在實驗室模板靠左會壓到左上校徽（改置中）、
    官方模板未指定角色的範例頁沒刪、封面長標題溢出到作者行、單位行沿用上標格式。
  - DSL 同步：`assets/input-templates/` 三份範本升 v2.2（.docx 由 .md 經 pandoc 重生，註解轉成「【填寫說明】」引言區塊）；
    **已同步** `cpet-input-template/references/translation-rules.md`（見該技能 CHANGELOG 2026-10-21 文字修訂）。
  - 未驗證：PowerPoint 實機開啟官方模板 profile 產出的簡報（本次以 LibreOffice 渲染與 schema 驗證為準）。

  **裁決依據**：Casey 2026-10-21「P7 審查報告 §4 那 10 項：依你建議採用」「其餘事項都可以開始進行」。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：源起段移除投稿編號；SKILL.md 與三份輸入範本的
  `lanes` 範例 KPI 由 ECCE 實際值改為示範值 ≈40 h（.docx 只替換該字串，其餘內容不動）；`assets/template.pptx`
  清空 `lastModifiedBy` 中繼資料，版面與內容不變。
