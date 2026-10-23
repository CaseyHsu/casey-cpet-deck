---
name: cpet-talk-prep
description: CPET／YS Lai Lab 口頭報告的講稿與試講準備——把逐頁講稿、點擊分組、中文提示、Q&A 短答集中在一份 talk.json，再由它產生：講者備忘錄（交給 cpet-deck-finalize 寫入簡報）、講稿版簡報（左縮圖＋中文提示、右逐字稿，點擊標 [n]、重音紅字、要唸 thee 的 the 標藍色底線）、TTS／練習用逐頁文字稿、依 wpm 估算的時間表與檢查點，以及改稿後該重產哪些檔的清單。使用者說「寫講稿」「講稿要配動畫點擊」「試講太長要刪」「估一下幾分鐘」「做講稿版投影片」「把講稿寫進備忘錄」「準備 Q&A」「審稿意見整理成問答」「產生語音稿／TTS 文字」「改了一句講稿要同步哪些檔」，或要為研討會口頭報告、口試、實驗室報告準備英文講稿時，一定要使用本技能。不適用：做投影片本身（cpet-yslai-pptx）、修改已定稿的 pptx 版面或動畫（cpet-deck-finalize）、一般文章寫作。
---

# CPET Talk Prep（v1.0 — 講稿、試講、Q&A）

講稿會一改再改，而每改一句，備忘錄、講稿版簡報、文字稿、語音、時間表都要跟著動。本技能的做法是
**只改 talk.json，其他全部由它產生**，並用 `diff` 告訴你哪些檔要重產。

## 流程

1. **建立 talk.json**：格式見 `scripts/talk.py` 檔頭。舊專案的 ECCE 式 `speech.json` 可用 `import-speech` 轉換。
   撰寫原則見 `references/speech-writing.md`（一次點擊講一句、句子 ≤15 字、固定轉折句、不唸符號下標）。
2. **估時間**：`talk.py timing talk.json`。超過 `meta.limit_sec` 回 1。落後時依刪句順序刪，不要靠加快語速。
3. **Q&A**：依 `references/qa-template.md` 整理（每題：30 秒口答、好唸短答、補充數據、禁語、對應備用頁），
   短答放進 talk.json 的 `backup`／`other`。
4. **產出**（都從同一份 talk.json）：

| 產物 | 指令 |
|---|---|
| 備忘錄 | `talk.py notes talk.json notes.json` → cpet-deck-finalize `derive.py notes <deck> notes.json <out>` |
| 講稿版簡報 | `talk.py thumbs <無動畫版.pptx> thumbs/` → `talk.py deck talk.json speech.pptx --thumbs thumbs/` |
| 文字稿（練習／TTS） | `talk.py txt talk.json speech_txt/ --prefix <專案>_Speech` |
| 時間表 | `talk.py timing talk.json`（貼進專案的講稿文件） |

5. **改稿後**：先把舊版存成 `talk_prev.json`，改完跑 `talk.py diff talk_prev.json talk.json`，依清單重產；
   寫入主檔備忘錄一律走 cpet-deck-finalize 的 check → snapshot → 寫入 → register。

所有指令在 `<skill_path>/scripts/`，依賴 `python-pptx`、`lxml`；`thumbs` 另需 LibreOffice 與 `pdftoppm`。

## talk.json 的幾個約定

- `lines` 的點擊數 `k`：`k>0` 表示按第 k 下之後講；第一句的 `0` 是進頁就講；之後的 `0` 表示「不按鍵，接著講」。
  點擊數必須與投影片的動畫點擊數一致（用 cpet-deck-finalize `anim.py check` 對照）。
- `**…**` 是重音，講稿版顯示為紅色粗體；備忘錄不加粗（簡報者檢視裡太搶眼）。
- `thee_before`：後面接母音發音的單字（小寫）。縮寫依**唸法**判斷：MTPA 唸 em-tee… 要列；LUT 若唸成 lookup table 就不列。
- `meta.spoken`：只影響文字稿（TTS），例如 `"LUT": "lookup table"`；投影片與備忘錄保留原字。
- `notes_pre`：要放在備忘錄講稿上方的提示行（例如 `【發音】` 主席姓名唸法）。

## 驗收

- `timing` 的點擊數與 `anim.py check` 的每頁點擊數一致。
- 講稿版簡報：轉 PDF 逐頁目視，文字不得溢出（字級由程式依字數自動縮小，下限 18 pt）。
- TTS 語音的發音**必須由使用者試聽確認**；Claude 無法聽音檔，不得宣稱發音正確。

## TTS（選配）

本技能只產生 TTS 用的文字稿與參數；合成步驟見 `references/tts.md`（Kokoro 離線模型、聲音與停頓參數、
音標修正清單）。需要合成時依該文件在使用者環境安裝與執行。
