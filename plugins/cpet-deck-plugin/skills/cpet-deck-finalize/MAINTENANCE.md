# cpet-deck-finalize 維運規範（maintainer: Casey）

> 給維護者（人與 AI）看，不影響 skill 執行。

## 版本紀律
- 功能性變更（新子命令、新的動畫效果類型、manifest schema 改變）+0.1，SKILL.md 標題與 CHANGELOG.md 末條同步。
- 同版 bug 修復不升版，於該版條目附記症狀、根因、修復、驗證方式。
- manifest 的 `schema` 字串（`cpet-deck-manifest/0.1`）只在欄位不相容時改；改了要寫遷移說明。

## 修改 scripts 的流程
1. 在 repo 的 `skill-src/cpet-deck-finalize/` 修改（dist 由 SOP 重建，不直接改 dist）。
2. 跑 `tests/test_finalize.py`，必須全 PASS。新增功能要同時加測試案例。
3. 動到 `anim.py`／`derive.py` 時，另以一份**真實的、PowerPoint 存過的**含動畫簡報跑
   `tests/regress_on_deck.py <Final> <NoAnim> <work_dir>`（在複本上跑；專案檔案不進 repo）。
4. 動到動畫寫入邏輯時，必須請 Casey 在 PowerPoint 實機播放一次——LibreOffice 能開檔不代表
   PowerPoint 的動畫行為正確（D53 的退場失效在 LibreOffice 看不出來）。
5. 刪除 `__pycache__` 後再跑 SkillSpector（測試會在 scripts/ 產生 pycache，觸發 SC8／SC9 誤報）。

## 成對的契約
- `derive.py notes` 的輸入格式＝cpet-talk-prep `talk.py notes` 的輸出（`{"頁碼": "多行文字"}`、`**粗體**`、`__the__`）。
  改任一邊都要同步另一邊，並跑兩邊的測試（`tests/test_finalize.py`、cpet-talk-prep `tests/test_talk.py`）。

## 已知環境風險
- Windows 繁中 cp950 終端機：`pptx_xml.py` 匯入時把 stdout／stderr 設為 UTF-8；新腳本若不匯入它，要自己設。
- 系統 Python 未必有 `python-pptx`／`lxml`；測試用的 venv 由使用者自行準備。

## 安全掃描的已接受項目
- **LP3（MEDIUM）未宣告 allowed-tools**：刻意不宣告。宣告會讓 Bash 下的 python 執行免確認，
  比不宣告的風險大。重新評估時機：Claude Code 若支援「只宣告、不自動核准」的權限欄位。

## 打包檢查清單
□ SKILL.md 標題版本號＝CHANGELOG.md 末條版本
□ `tests/test_finalize.py` 全 PASS
□ `__pycache__` 不入包
□ `evals/evals.json` 存在且案例與 SKILL.md 描述一致
