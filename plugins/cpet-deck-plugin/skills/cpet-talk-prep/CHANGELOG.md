# cpet-talk-prep 版本履歷（Changelog）

> 維護者文件，skill 執行時不載入。撰寫紀律見 `MAINTENANCE.md`。

- **v1.0**（2026-10-21）：首次建立。

  **源起**：ECCE 2026 口頭報告（D27–D59）。講稿措辭變更 16 次，每次要同步 speech.json、講稿版 pptx（pptxgenjs
  的 build.js）、講稿 md、Final 備忘錄、無動畫版、speech_txt、語音檔，共 5–7 處，全部手工。

  **設計決策**：
  - 單一來源 `talk.json`（schema `cpet-talk/0.1`），由 ECCE 的 speech.json 一般化：陣列改為具名欄位，
    新增 `meta`（wpm、點擊與換頁秒數、核心頁、檢查點、上限、spoken 替換表）、`notes_pre`、`phrases_note`。
  - 講稿版簡報由 pptxgenjs 移植為 python-pptx，與 cpet-deck-finalize 同一技術棧，不再需要 Node。
  - 備忘錄不直接寫 pptx，而是輸出 notes.json 交給 cpet-deck-finalize 的 `derive.py notes`，讓寫入主檔一律經過
    check／snapshot／register 防護。
  - 點擊數 0 的語意沿用 ECCE：第一句為進頁即講；之後的 0 表示「不按鍵，接著講」（文字稿不分段）。
  - 時間：每頁 `round(字數/wpm×60 + 點擊×0.7 + 1)`，`round` 為四捨六入五成雙，與 ECCE 時間表逐頁一致。

  **取捨留痕**：
  - TTS 只做文字稿與參數文件（`references/tts.md`），不內建合成程式：本機未安裝 Kokoro，無法驗證；且 Claude
    無法聽音檔，發音只能由使用者確認。未來在已裝 Kokoro 的環境驗證後再升版加入。
  - 講稿版的字型沿用 ECCE 的 Calibri（講者自用，不受實驗室字型規範約束）。

  **驗證**：
  - `tests/test_talk.py`（合成資料）：18/18 PASS，含交給 cpet-deck-finalize `derive.py notes` 的串接。
  - `tests/regress_on_project.py` 於 ECCE 2026 定稿複本：
    - 匯入後每頁字數、點擊、秒數與專案時間表 21 頁完全一致。
    - 文字稿 22 個檔（21 頁＋_all）與交付的 speech_txt 逐字相同。
    - 備忘錄：27 頁的講稿與 Q&A 行（含哪一行帶 thee 標記）與 Final.pptx 完全相同；`【…】` 標頭行有 5 頁不同，
      是專案內的手工差異（#1 手加發音提示、#23–#26 補充數據只寫進講稿版），工具如實回報，不算錯誤。
    - 講稿版簡報 33 頁，每頁可見文字與交付的 Speech.pptx 相同。
    - 加縮圖後轉 PDF 抽 6 頁目視：版面、紅字重音、橘色點擊標記、藍色底線 the 正常；核心頁（#9、#10）縮圖較窄、頁碼底為橘色。
  - `thumbs` 在 `PYTHONHOME`／`PYTHONPATH` 指向不存在路徑時仍正常產出 27 張縮圖。
  - governance preflight PASS；SkillSpector `--no-llm`：score 20、LOW、CAUTION（LP3、AST4×2，理由見 MAINTENANCE）。
    初版以字典生成式複製 `os.environ` 來移除 PYTHONHOME，被判 E2（HIGH）；改為不動環境變數、以 PDF 是否產出判斷後消失。

  **已知限制**：見 SKILL.md；`thumbs` 依賴 LibreOffice 與 pdftoppm。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：源起段移除投稿編號；`references/tts.md`
  音標表的姓名範例改用虛構拼音。行為未變。
