# cpet-yslai-pptx 維運規範（maintainer: Casey）

> 本文件給維護者（人與 AI）看，不影響 skill 執行。由 v2 → v2.5 的實際維運過程提煉（2026-07）。

## 1. 版本號紀律

- 版本履歷寫在 skill 根目錄的 `CHANGELOG.md`（v2.8 起自 SKILL.md 移出——SKILL.md body
  每次技能觸發都會載入 context，履歷對執行無貢獻卻佔該檔 33% 字元量）。
- 功能性變更（新規則、新頁型、builder 行為改變）：**+0.1**，SKILL.md 標題版本號與
  `CHANGELOG.md` 末條同步。
- 同版 bug 修復：不升版，於該版履歷條目**附記**（例：v2.4 的 graphicx 修復），寫明症狀、根因、驗證方式。
- 回滾：還原備份後，履歷補記該版標 `reverted`——回滾也要留痕。
- 每條履歷必含：變更清單、變更動機、驗證結果（QA 通過數）。

## 2. Builder（scripts/）修改流程——五步，缺一不可

1. **複製到 /tmp 修改**（不在掛載點直接編輯——見 §5 環境風險）。
2. `py_compile` 過編譯。
3. 回寫後 **md5 比對** /tmp 版與掛載版一致。
4. **以實際範例重建驗證**——挑會踩到改動路徑的範例（改公式管線就用含 cases 公式的 plan；改表格就用多表 plan），跑三層 QA＋目視。graphicx 這類「靜默失效」bug 只有實例渲染能抓到，單元層面看不出來。
5. `CHANGELOG.md` 記錄 → 重新打包 .skill。

## 3. 規則變更紀律（references/lab-style-conventions.md）

- 新觀察 → 依裁決協議分級：≥2 樣本一致＝硬規則、單樣本＝候選（§3）、與既有矛盾＝既有為準記 §6。
- 候選升級／捨棄必須由 Casey 裁決，結果記入 §3 裁決紀錄表（留痕格式已固定）。
- 視覺層（字型/色碼/版面值）永不進 conventions 規則區——只允許出現在 §6.4 模板核對紀錄。

## 4. 驗收判準（每次升版後）

以一份未用於規則抽取的文稿生成 5–8 頁，核對四項：
(1) 骨架與比重符合 §1；(2) 公式／圖表邏輯命中 §2；(3) 無 §4 違規；
(4) **視覺層仍為新模板**——此項不過直接回滾。
最終觀感以 **Windows PowerPoint 實機**為準（LibreOffice 渲染僅供 QA，字型／符號映射可能有差異——Wingdings 箭頭即為一例）。

## 5. 已知環境風險（Cowork）

- **掛載點大檔寫入偶發尾端截斷**：SKILL.md 曾三次尾段損毀。對策：大檔一律 `/tmp` 直寫 → `cp` → md5＋尾端斷言驗證；讀回時發現 UnicodeDecodeError／JSON "Extra data" 即為此症狀。
- **已安裝 skill 目錄唯讀**：Cowork 不能直接改安裝版；一律在專案資料夾維護本結構 → `package_skill` 打包 → Save skill 重新安裝。
- 掛載點偶發 `Permission denied`／`Operation not permitted`：先重試，仍失敗時 `rm`（需開啟刪除權限）後重 cp。

### 5.1 Windows／跨平台工具相依（2026-08-17 強化）

`full_qa.sh` 原本假設 PATH 上有 `python3`／`soffice`／`pdftoppm` 三個標準名稱，
缺一即 `exit 2`。實測在 Windows 上三者都會踩坑，已改為「逐項尋找可用實作」：

- **Python**：Windows 的 `python3.exe` 常是指向 Microsoft Store 安裝提示的
  App Execution Alias（假指令，錯誤訊息為「Python was not found」而非「找不到
  指令」，極易誤判為未安裝）。現依序嘗試 `python3`／`py`／`python`，並實際
  `import pptx` 驗證可用性後才採用（存為 `$PY_BIN`）。
- **LibreOffice**：安裝後預設不加入 PATH（需重開 shell）。現除了 PATH，另外
  探測 `C:\Program Files\LibreOffice\program\soffice.exe` 等標準安裝路徑
  （存為 `$SOFFICE_BIN`）。缺席時的錯誤訊息附上
  `winget install TheDocumentFoundation.LibreOffice`。
- **pdftoppm 格式**：TeX Live 夾帶的 poppler 0.75.0 **不支援 `-jpeg`**（只有
  `-png`／`-mono`／`-gray`）。現以 `pdftoppm -h` 探測後決定用 `-jpeg` 或 `-png`
  （存為 `$PDFTOPPM_FMT`／`$IMG_EXT`），檔名 glob 與彙總訊息一併連動。
  `qa_check.py` 用 PIL 讀圖，兩種格式皆可，不影響檢查結果。

**`schema_check.py` 的 `xmllint` 相依已解除**：原僅走 `xmllint` 外部指令，
Windows 無內建 libxml2 工具鏈故常缺席，導致第 2 層 schema QA 整層無法執行
（症狀是 FileNotFoundError，正是本檔案警告過的「容易被當環境問題跳過」的
失效模式）。現改為優先用 **`lxml`**（`etree.XMLSchema`，同一個 libxml2 引擎、
判定等價；schema 編譯結果快取避免逐張投影片重複解析），僅在 `ImportError`
時退回 `xmllint`。lxml 本為本技能既有相依（`build_deck.py` 的手動 XML 操作
即用它），不新增任何套件。已用反向測試確認會正確攔截違規 XML，非假通過。

**編碼（2026-10-17）**：繁中 Windows 的系統碼頁是 cp950，Linux 容器測不出來。
新增或修改 `scripts/` 時遵守兩條：(1) 文字檔 `open()`／`read_text()`／`write_text()`
一律明確寫 `encoding="utf-8"`；(2) 會印中文或符號（✔、≤、→）的腳本，在 import 後
保留把 stdout／stderr 重設為 UTF-8 的區塊（現有七支腳本已有，照抄即可）。
`full_qa.sh` 另外 `export PYTHONIOENCODING=utf-8` 作為外層保險。

## 5.2 v2.11 新增的維護事項

- **visual 開關**：外觀變更一律綁在 `meta.visual` 新值上，舊值（`v2.8`）必須能重現上一版輸出。改 builder 後，
  以上一版程式建置的基準 pptx 和新程式 `meta.visual: "v2.8"` 的輸出逐 part c14n 比對；有差異就要能逐條說明是 bug 修正。
- **官方模板 profile**：改 `clone_slide`／`new_slide`／`load_profile` 時，至少用一份真實官方模板（ECCE 2026 模板在
  Casey 的專案素材區，不進 repo）建置含封面、bands、公式、致謝、備用頁的 plan，轉 PDF 逐頁目視，並以
  `QA_PROFILE` 跑四層 QA。
- **測試**：`tests/test_v211.py` 必須全 PASS。
- **.docx 範本重生**：`input_template.md` 的 `<!-- -->` 註解先轉成 `> 【填寫說明】` 引言區塊再交給 pandoc，
  否則 pandoc 會丟掉所有填寫說明。

## 6. 打包檢查清單

□ SKILL.md 標題版本號＝`CHANGELOG.md` 末條版本　□ SKILL.md 內無殘留履歷章節
□ `assets/input-templates/` 三份範本（.md／.docx／.tex）檔頭標示的「對應 skill 版本」
　＝ SKILL.md 版本，且三份語法一致（.docx 由 .md 經 pandoc 重生，不手改）
□ 若本版新增了使用者在文稿階段就該遵守的規則（例如 lint 的量化上限），已寫進範本
□ 全部 .md 可完整 UTF-8 decode 且尾端正確
□ scripts 全部過 py_compile　□ template.pptx zip 完整
□ archive/、__pycache__ 不入包　□ 打包後解 .skill 抽驗 SKILL.md 尾端
□ **（2026-08-30 新增，見`簡報內容共創工作流指引_v7.md`§6.3，原 v6 §6.3）**：若本版異動了 DSL 語法
　（`assets/input-templates/input_template.md` 或 SKILL.md 步驟 0／0.5／1），已同步檢查
　`cpet-input-template/references/translation-rules.md` 是否需要跟進更新，並在**本技能**
　的 CHANGELOG.md 記錄「已同步」或「本次變更不影響轉譯規則、無需同步」——這是因為
　`cpet-input-template` 在 Chat／Cowork 環境已收斂為依賴該快照運作（不再動態讀取本技能
　當下權威語法），忘記同步會讓 Chat／Cowork 版轉譯出的 `input_template.md` 使用過期
　語法，導致本技能建構時解析失敗或行為不符預期
