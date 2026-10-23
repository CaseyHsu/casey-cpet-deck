# TTS 語音（選配）

本技能不內建合成程式：本機與 Claude 執行環境都未必裝有 TTS 模型，而且 Claude 無法聽音檔，
發音只能由使用者試聽確認。以下是 ECCE 2026 實際使用、經 Casey 試聽確認過的設定，供在使用者環境合成時照做。

## 文字稿

`talk.py txt` 產生的逐頁文字稿即為合成輸入：
- 段落之間的空行＝一次點擊；`meta.spoken` 已把 LUT 換成 lookup table、非斷行連字號換成一般連字號。
- 縮寫逐字母唸時（MTPA、MTPV）要確認引擎不會把句中的 A 唸成「呃」。

## 引擎與參數（ECCE 2026）

| 項目 | 設定 |
|---|---|
| 引擎 | Kokoro（開源、離線） |
| 講稿聲音 | am_michael（美式男聲） |
| 語速 | 全文平均約 105 wpm（含停頓） |
| 停頓 | 句間 0.25 s、每次點擊 0.8 s、換頁 1.5 s |
| 輸出 | 每頁一檔 `<prefix>_pNN.mp3`＋完整版＋zip |
| Q&A 基本版 | 題目：af_heart（速度 0.90）唸題號與問題 → 停 2 s → 答案：am_michael（速度 0.80）唸短答 |
| Q&A 聽力練習版 | 題目用完整問句、af_heart／af_bella／bm_george／bf_emma 輪流、一般語速，唸完停 3 s；答案同基本版 |

## 合成前要修正的音標（逐字檢查引擎輸出的音標後發現）

| 字 | 問題 | 修正 |
|---|---|---|
| 中文姓名的拼音（例：Hsieh、Jun-Yi） | 被逐字母唸，或 j 唸成 y | 直接指定音標（Hsieh → shyeh） |
| 句中的 MTPA | A 唸成「呃」 | 指定 A 的字母音 |
| use／uses（動詞） | 用了名詞的 s 音 | 改 z 音 |
| envelope | AHN-vuh-lohp | EN-vuh-lohp |
| eta | EE-tuh | AY-tuh |
| Lagrange、comparator | 重音位置錯 | 指定音標 |

做法：合成前把引擎產生的音標表全部列出（ECCE 全文 372 個不同的字），逐字檢查後只修正有問題的字，其餘不動。

## 改稿後

`talk.py diff` 列出的頁，重產該頁的單頁檔，再重產完整版與 zip；Q&A 短答改了就重產對應題目與 Q&A 完整版。
