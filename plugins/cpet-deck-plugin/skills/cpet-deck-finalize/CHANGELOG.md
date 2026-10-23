# cpet-deck-finalize 版本履歷（Changelog）

> 維護者文件，skill 執行時不載入。撰寫紀律見 `MAINTENANCE.md`。

- **v1.0**（2026-10-21）：首次建立。

  **源起**：ECCE 2026 口頭報告（D1–D59）。D22 起 Casey 在 PowerPoint 手改（IguanaTeX 公式、
  位置微調），build.py 凍結、pptx 成為主檔；之後 38 條決策紀錄全部在 skill 外以臨時 lxml 腳本與手工
  完成，腳本沒有留存。具體事故：寫入前才發現已被手改 5 次（D31、D34、D39、D44、D52）；檔案開在
  PowerPoint 只能另存 2 次（D22、D48）；手動快照 13 個；第 9 頁退場動畫因出現／消失共用 grpId 0 而
  在 PowerPoint 失效（D53）；無動畫版自 D35 起未跟著更新（D41 註記）。

  **設計決策**：
  - `deck_guard`：manifest 記錄每頁、每個形狀的 c14n 指紋，`check` 能說出「哪一頁哪個形狀被移動或改字」，
    不只是 md5 不同；鎖定時回 3 並要求關檔，刻意不提供「另存他名」路徑（D48 的另存檔後來要人工合併）。
  - `anim`：只支援出現／消失，依 ECCE 動畫編排規則（動畫即提詞器）；每個效果獨立 grpId＋bldP。
  - `derive`：無動畫版只移除 `p:timing` 與 `EntryPrompt*` 形狀，其他 part 原樣複製，因此可逐 part 比對。

  **取捨留痕**：
  - 沒有宣告 `allowed-tools`。SkillSpector 因此報 LP3（MEDIUM）、整體 CAUTION。宣告的效果是讓這些工具
    免確認執行；本技能需要 Bash 跑 python，宣告 `Bash(python:*)` 等於放寬所有 python 執行的確認，
    比 LP3 本身風險大。Casey 2026-10-21 授權「其餘事項可開始」，此項依安全面判斷不宣告，記入 MAINTENANCE。
  - 不新增備忘錄 part（需要建立 notesSlide 與關聯，PowerPoint 點一下就會建立）。

  **驗證**：
  - `tests/test_finalize.py`（合成簡報，無專案資料）：16/16 PASS。
  - `tests/regress_on_deck.py` 於 ECCE 2026 Final（md5 61b6102c…）複本：
    - `verify-noanim`：重產的無動畫版與交付檔（74adb55f…）193 個 part c14n 完全相同。
    - 動畫往返：18 頁、57 次點擊，逐點擊（目標、類別、節點型別）序列與原檔相同；lint 0 問題。
    - 把第 9 頁全部效果改成 grpId 0（D53 情境），`check` 回 1 並指出 spid 46。
  - PowerPoint 實機播放重新寫入動畫的 ECCE 複本：**Casey 2026-10-21 確認與原簡報一致**。
  - schema：重新寫入動畫的複本經 yslai `schema_check.py`（v2.10 同版修復後）28 個 part 全過。
  - SkillSpector `--no-llm`：score 7、LOW、CAUTION，唯一 finding 為 LP3（見取捨留痕）。

  **裁決依據**：主檔切換規則與觸發描述——Casey 2026-10-21「其餘事項都可以開始進行」，採用草案。

  **已知限制**：見 SKILL.md「已知限制」。

  **文字修訂（2026-10-22，不升版）**：MAINTENANCE.md 補「成對的契約」一節（notes.json 與 cpet-talk-prep），
  對應工作流指引 v7 §6.4。行為未變。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：源起段移除投稿編號。
