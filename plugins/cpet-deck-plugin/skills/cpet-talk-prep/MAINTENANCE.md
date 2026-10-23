# cpet-talk-prep 維運規範（maintainer: Casey）

> 給維護者（人與 AI）看，不影響 skill 執行。

## 版本紀律
- 功能性變更（新子命令、talk.json 欄位、講稿版版面）+0.1，SKILL.md 標題與 CHANGELOG.md 末條同步。
- 同版 bug 修復不升版，於該版條目附記症狀、根因、修復、驗證方式。
- talk.json 欄位不相容時改 schema 字串（`cpet-talk/0.1`），並在 `import-speech` 或新子命令提供轉換。

## 修改 scripts 的流程
1. 在 repo 的 `skill-src/cpet-talk-prep/` 修改。
2. 跑 `tests/test_talk.py`，必須全 PASS（串接測試需要 `cpet-deck-finalize` 在同層目錄）。
3. 動到 `notes`／`txt`／`deck`／timing 時，以一份已交付專案跑
   `tests/regress_on_project.py <speech.json> <speech_txt> <Final.pptx> <Speech.pptx> <work_dir>`（在複本上跑）。
4. 動到講稿版版面時，轉 PDF 逐頁目視。
5. 刪除 `__pycache__` 後再跑 SkillSpector。

## 成對的契約
- `notes` 輸出的 notes.json 格式＝cpet-deck-finalize `derive.py notes` 的輸入格式（`{"頁碼": "多行文字"}`、
  `**粗體**`、`__the__`）。改任一邊都要同步另一邊，並跑兩邊的測試。

## 已知環境風險
- Windows cp950 終端機：`talk.py` 匯入時把 stdout／stderr 設為 UTF-8。
- `thumbs` 以「PDF 是否產出」判斷 soffice 成功，不看 exit code（繼承 `PYTHONHOME`／`PYTHONPATH` 時 soffice 會回非零但
  PDF 正常）。刻意**不**複製或改寫環境變數：那會被 SkillSpector 判為 E2（環境變數蒐集，HIGH）。
  已實測在 `PYTHONHOME`／`PYTHONPATH` 指向不存在路徑時仍正常產出 27 張縮圖。

## 安全掃描的已接受項目
- **LP3（MEDIUM）**：同 cpet-deck-finalize，不宣告 allowed-tools。
- **AST4（MEDIUM）×2**：`thumbs` 呼叫 soffice 與 pdftoppm；參數為固定清單（無 `shell=True`，使用者輸入只作為單一路徑參數）。

## 打包檢查清單
□ SKILL.md 標題版本號＝CHANGELOG.md 末條版本
□ `tests/test_talk.py` 全 PASS
□ `__pycache__` 不入包
□ `evals/evals.json` 存在且案例與 SKILL.md 描述一致
