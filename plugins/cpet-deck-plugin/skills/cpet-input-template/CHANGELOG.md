# cpet-input-template 版本履歷（Changelog）

> 維護者文件，skill 執行時不載入。撰寫紀律見 `MAINTENANCE.md`。

- **v1.0**（2026-08-04）：首次打包。源起於 CPET 簡報自動生成教學 SOP 簡報製作過程中
  反覆踩到的坑——`cpet-yslai-pptx` 的「文稿→plan.json」映射是建置當下即時、隱性完成的，
  沒有留下可版控的中介產物；當時實測 plan.json 手動改了六輪後即與任何來源文件脫鉤，
  必須反向考古重建一份 input_template.md 才補回追溯性。經過同一 session 內多輪工作流
  設計討論（v1 指引文件方案→v2 獨立技能但 doc-coauthoring 分開觸發→v3 內部編排呼叫
  doc-coauthoring，定名 cpet-input-template）確定架構，並在另一 session 將
  `cpet-yslai-pptx` 升級到 v2.9（新增字卡群、語意項目符號、highlight、Okabe-Ito 配色
  規則、`plan_lint.py`/`layout_lint.py`/`full_qa.sh` 四層 QA、`cpet-figure-prep` 技能）
  後，依交接文件校正轉譯規則，寫成本技能。

  設計核心決策：(1) **不複製 doc-coauthoring 方法論**，改為內部編排呼叫，避免與其本體
  維護兩份易漂移；(2) **不內建 DSL 語法靜態複本**，執行時讀取 `cpet-yslai-pptx` 當下
  安裝版本作單一事實來源，`references/translation-rules.md` 明確標註為快照而非真相；
  (3) 修訂鐵律採**整份重跑，不做局部 patch**，理由是版面/素材判斷涉及跨頁一致性（章節
  編號、Part 清單同步、running title、視覺語言一致），局部編輯容易破壞全局狀態；
  (4) 素材路由拆兩軌（`PENDING:forge-`／`PENDING:figprep-`），對應 `cpet-yslai-pptx`
  v2.9 期間新增的三方分工（forge 生成／figure-prep 整理既有／yslai-pptx 組裝）；
  (5) 技能執行完必須停下來列決策摘要交人審查，不自動觸發任何下游技能——這是整條
  pipeline 唯一設計了人工審查點的環節，也是本技能存在的核心理由。

  已知限制：本技能規格文件階段經過多輪工作流設計討論但**尚未經過實機測試**（無法在
  Cowork 沙箱內部呼叫另一個技能做端對端驗證，doc-coauthoring 的編排呼叫與轉譯輸出品質
  需要之後實際使用時持續校正）。`references/translation-rules.md` 的語法快照對應
  `cpet-yslai-pptx` v2.9／`input_template` v2.0（2026-08-04），未來 `cpet-yslai-pptx`
  升版時需要人工比對交接文件校正此快照，校正紀律見 `MAINTENANCE.md`。

- **v1.1**（2026-08-05）：實機測試＋校正兩件事。

  **實機測試（skill-creator 標準流程）**：以 2 組 eval（各含 with-skill／baseline 對照）
  跑過完整流程——真的透過 `Skill` 工具呼叫 `doc-coauthoring`、真的讀取已安裝
  `cpet-yslai-pptx` 的即時語法並回報版本號、情境四問處理（未講明時標假設值待確認／已講明
  時不重問）、forge/figprep 路由判斷、遺失素材誠實標記為阻塞項、決策摘要後停下不觸發下游
  技能——七項／六項驗證點在 with-skill 組全數通過，baseline（無本技能）組多數項目失敗
  （通過率 24%），對照結果印證上一版「已知限制」段落所述的「尚未實機測試」已補上；上一版
  該段文字保留作為歷史記錄，不回頭修改。

  **同版校正**（由 eval-1 實機測試發現，`translation-rules.md` 遺漏兩個真實存在的語法）：
  Casey 在另一 session 把 `cpet-yslai-pptx` 的 `assets/input-templates/input_template.md`
  升到 v2.1（同版修復，skill 本身仍是 v2.9），修正內容之一正是**修補範本檔頭版本標示落後
  一版**的問題——這正是 eval-1 測試時被本技能執行者揪出的落差（範本自報「對應 skill
  v2.8」，但 SKILL.md 已是 v2.9），對方的 CHANGELOG 明確記載「同版修復，由另一組 eval
  抓到」。核對新版範本全文（而非只信版本標示改了就結案）時，額外發現
  `translation-rules.md` §4 語法表本身有兩處遺漏：(1) **`[eq-right: LaTeX]`**——
  `two_col` 右欄若是公式而非圖片時的寫法，對應 `plan.json` 的 `two_col.right.latex`／
  `.note`，先前只知道右欄可以放圖，沒收錄公式版；(2) **`[first_col_item: false]`**——
  表格第一欄預設視為項目欄（淡藍底＋粗體）的關閉開關，先前 §8 只收錄了 `[highlight:]`。
  兩者都已核對過確實是 `input_template.md` 檔內文件化的方括號標籤（非憑 `plan.json`
  schema 反推杜撰），已補進 §3／§4／§8，並在 §8 明確註記 `col_align`（欄位對齊逐欄覆寫）
  **沒有**對應的方括號標籤、只存在於 `plan.json` 層級，避免下一版維護者看到
  `first_col_item` 有標籤就誤以為 `col_align` 也有、自行發明一個下游不認得的語法。
  `references/translation-rules.md` 版本快照標註同步改為
  `cpet-yslai-pptx v2.9／input_template v2.1（2026-08-05）`；`references/output-templates.md`
  新增 `[eq-right:]` 的骨架範例。SKILL.md 標題升至 v1.1。

- **v1.2**（2026-08-16）：CPET 簡報工作流整備任務段2a——新增 `PENDING:` 佔位鍵回填
  自動化（`scripts/backfill_pending.py`，本技能首次擁有 `scripts/` 目錄）。動機：
  v4 工作流指引 §4 原記載「回填方式手動 vs 自動化，尚未定案」；Casey 於本次任務段1
  裁決事項回覆時明確要求本階段納入（原 D1 建議是「不納入，維持人工回填」，Casey
  裁決推翻此建議）。設計上明確劃清界線：回填腳本只做機械式字串取代（讀
  forge／figprep 的 `manifest.json` → 找 `PENDING:` 字串 → 換成相對路徑），**不涉及
  任何轉譯判斷**——決定「這頁該用哪個佔位鍵」仍是第5步的職責，未變動。回填前自動
  備份原檔為 `.bak`；manifest 未涵蓋或標記失敗的鍵值維持原樣並於執行結果列出，避免
  誤判為已全部處理完成。`cpet-figure-prep` 同步新增 `manifest` 子命令（見該技能
  CHANGELOG v1.1）供本腳本讀取；`cpet-infographic-forge` 既有的 `manifest.json`
  格式不變，直接沿用。驗證：端到端測試（含一個未涵蓋鍵值、一個 manifest 標記失敗
  鍵值的情境）皆正確處理，見 D2 技能更新異動報告。SKILL.md 標題升至 v1.2。
- **v1.3**（2026-08-30）：新增「快照模式」作為與「動態模式」並列的**正常**運作情況。
  動機：`簡報內容共創工作流指引_v6.md` §6.3 職權收斂決策——`cpet-yslai-pptx` 等三
  技能收斂為 Code 專屬部署後，本技能在 Chat／Cowork 環境永遠找不到已安裝的
  `cpet-yslai-pptx`，而「環境準備」與步驟3原文字面上把「找不到就依賴
  `references/translation-rules.md`」定性為需要提醒使用者的落差情況，與 v6 新設計
  矛盾——快照模式在 Chat／Cowork 是**預期且唯一可行**的運作方式，不是異常。修正
  「環境準備」章節，明確區分兩種皆屬正常的模式（動態模式：定位到已安裝
  `cpet-yslai-pptx` 即動態讀取；快照模式：找不到則依
  `references/translation-rules.md`），決策摘要僅需照常標註採用哪一種模式，不再用
  警告語氣呈現快照模式；「動態模式下讀到的版本與快照不一致」才維持記錄提醒（這才是
  真正代表快照需要同步的訊號）。步驟3標題與內文、交付前自我檢查第2條同步改寫。
  快照本身的同步依賴由 `cpet-yslai-pptx/MAINTENANCE.md` 打包檢查清單新增的同步
  紀律把關，本技能不自行驗證快照時效性。**附帶查證**：本次修訂時確認
  `references/translation-rules.md` 檔頭標示對應 `cpet-yslai-pptx v2.9`，現況已是
  v2.10——查核 v2.10 CHANGELOG 確認該版僅為 QA 工具鏈跨平台修正、不涉及 DSL 語法或
  版面演算法變動，故快照**內容**不需要修改，僅檔頭版本標示字串需更新（見下方同版
  修復）。SKILL.md 標題升至 v1.3。
  **同版修復（2026-08-30）**：`references/translation-rules.md` 檔頭版本標示由
  「對應 cpet-yslai-pptx v2.9 / input_template v2.1」更新為「對應 cpet-yslai-pptx
  v2.10 / input_template v2.1」，僅字面更新、規則內容不變（原因見上）。

  **文字修訂（2026-09-20，不升版）**：解除快照模式與特定執行環境的綁定。
  v1.3 原文寫「典型為 Chat／Cowork，這兩個環境依 v6 裁決不部署該技能」，
  該前提已過時——Cowork 現在可以把 Git repo 加成 marketplace 來安裝 plugin，
  包含 `cpet-yslai-pptx`，故「Cowork 一定是快照模式」不再成立。**模式判定邏輯
  本身未改**（依舊是「找不找得到已安裝的 `cpet-yslai-pptx`」），只拿掉環境名稱
  的預設，並明寫「判定依據只有找不找得到這件事」、不要以環境名稱推論結果。
  `references/translation-rules.md` 檔頭同步修改。行為未變，故不升版。
- **v1.4**（2026-10-17）：**版號區隔升版，SKILL.md 本文與 v1.3 末版（含 2026-09-20
  文字修訂）相同。**
  - 源起：claude.ai 某帳號／組織同步的是 2026-08-30 的 v1.3 原版（仍寫「典型為
    Chat／Cowork」的環境預設），本 repo 的 v1.3 則已含 2026-09-20 文字修訂（判定依據
    只看實際探測結果）。兩者標題同為 v1.3、內容卻不同，無法從版號判斷手上是哪一份，
    覆蓋上傳時也無從核對。
  - 設計決策：升為 v1.4，讓 repo 版與已散佈的舊 v1.3 在標題上可區分。SKILL.md 只改
    標題版號；`references/translation-rules.md` 快照內容與檔頭不變（仍對應
    `cpet-yslai-pptx v2.10 / input_template v2.1`）。
  - 取捨留痕：資安修補計畫（`casey-cpet-deck_修改計畫_20261017.md`）原提議 v1.3.1。
    本規範的版號只有兩位（功能變更 +0.1／不升版），引入第三位會與其他技能不一致，
    故改採 +0.1。2026-09-20 的修改本身仍屬文字修訂、行為未變，本次升版的理由只是
    「與已散佈版本區隔」，不是追認為功能性變更。
  - 驗證：本次未動 `scripts/` 與流程步驟，只改標題版號。governance `preflight.py`
    （已裝 OpenCC）結果與修改前完全相同，無新增項目：F4「v1.4 vs 首條 v1.0」是檢查器
    誤報（本檔條目由舊到新排列，未修改的 `cpet-yslai-pptx`、`cpet-figure-prep` 也報
    同樣錯誤）；F6 兩筆 `assets/input-templates/input_template.md` 指的是
    `cpet-yslai-pptx` 底下的路徑，屬跨技能引用；F6／W3 的 `evals/evals.json` 是既有的
    幽靈引用。後兩項都不是本次造成的，另列待辦，不在本次處理。
  - 裁決依據：Casey 拍板（2026-10-17，選 v1.4 而非 v1.3.1 或不升版）。
  - 已知限制：claude.ai 上的舊 v1.3 仍需 Casey 以本版重新上傳覆蓋或刪除，本 repo 無法
    代為處理。（2026-10-17 補記：已查證兩個同步來源的 claude.ai 技能清單都沒有
    cpet-input-template，舊版已不存在，此項結案。）

  **同版修復（2026-10-17，補建 evals）**：`MAINTENANCE.md`「測試與驗證」與打包清單
  都要求 `evals/evals.json`，但這個檔案從未進版控（repo 歷史與其他資料夾都找不到），
  preflight 報 F6／W3 幽靈引用。依治理規範選擇補檔而非刪描述，因為清單描述的驗證
  流程（初次生成＋修訂模式）本身是對的。新增三個案例：口頭需求初次生成、散文草稿
  初次生成、接續案例 2 的修訂模式，每案附人工檢查用的 expectations。
  驗證：preflight 的 F6／W3 evals 項目消失；JSON 可解析。案例本身尚未實際跑過一輪
  （需 doc-coauthoring 與人工判讀），下次修改本技能時依 MAINTENANCE 流程執行。

  **文字修訂（2026-10-17，不升版）**：`SKILL.md`「環境準備」兩處與 `MAINTENANCE.md`
  校正流程一處，把 `assets/input-templates/input_template.md` 寫成
  `cpet-yslai-pptx/assets/input-templates/input_template.md`。原寫法讀起來像本技能自己的
  路徑（實際在 cpet-yslai-pptx 底下），preflight F6 也因此報「引用不存在的路徑」。
  搜尋目標加上技能目錄名後更精確，行為不變。修訂後 governance preflight（含本日 F4
  修正）對本技能 PASS，上方 v1.4 驗證段所列的 F4／F6／W3 三項均已消失。

- **v1.5**（2026-10-21）：新增第三份產出「數據查核表.md」與 `scripts/claim_check.py`（第 6、9 步）。

  **源起**：ECCE 2026 口頭報告有 6 次內容事實更正（D22、D23、D35、D45、D49、D51），其中 D49 是典型：
  同一轉速下，#13 的轉矩是 LUT 命令值、#19 的是測功機實測值，卡片沒標性質，前後看似矛盾；
  Q&A 也因此用錯數字。數字的性質與來源原本只散在計畫書的決策紀錄裡，沒有一處能查。

  **設計決策**：
  - 查核表在轉譯當下建立（數字第一次進入簡報的時刻），以 `suggest` 從 input_template.md 列出候選，
    `anchor`／`kind`／`source` 由 Claude 依素材填，找不到來源一律「待填」並列入決策摘要（不推測）。
  - `check` 是唯讀檢查，可在建置後、定稿期每次修改後執行；讀 pptx（文字框＋最近鄰文字框組合，處理 KPI 磚
    「數字在上、條件在下」的版面）、備忘錄、talk.json（逐頁定位）與一般文字檔。
  - 只在「同一條件、同一單位有兩種以上性質」時要求標註，避免對所有數字都要求標籤。

  **取捨留痕**：
  - 本技能原則是「不碰下游產物」；查核是唯讀，故列為明文例外（SKILL.md 分工段）。
  - 不判斷主張的統計強度（D45 的偏心量比較），只比對數字；統計判斷保留人工。
  - 原型在 `skill-src/_drafts/p4-claim-check/`，搬入時改以 `chr()` 定義千分位空白等不可見字元，避免原始碼含
    肉眼看不見的字；並加入 `suggest` 子命令與非數值列容錯。

  **驗證**：
  - `tests/test_claim_check.py`（合成資料）：11/11 PASS，含 D49 型（未標實測值）、錯值、talk.json 逐頁定位、
    非數值列略過、suggest 抽取與跨頁合併、「3 steps」不誤判為秒。
  - ECCE 2026 定稿複本回歸：模擬 D49 前的 #19 文字時抓到 #13（命令值未標）與 #19（實測值 2 處未標）；
    現行定稿只剩 #13 一處未標（屬實）；#13 改錯數值判 MISMATCH。加上 talk.json 時，Q&A 中文備註裡的
    命令值取整前的原始值與誤差值被判 MISMATCH——符合設計：衍生量要在查核表另開一列，
    中文標籤要寫進 labels。
  - `suggest` 對 ECCE input_template.md 抽出 59 個數字並正確合併跨頁出現位置。
  - governance preflight PASS。

  **已知限制**：唸法數字（forty）不解析；anchor 是純文字比對，同一條件換說法（9 krpm）需另列 anchor。

  **文字修訂（2026-10-21，不升版）**：`references/translation-rules.md` 快照同步到 cpet-yslai-pptx v2.11／
  input_template v2.2——§1 加標題樣式與模板兩問、§4 加 `!!重點!!`、`[card-tint:]`、`[chevron:]`、`[lane…]`、
  `[notes:]`、`[backup]` 與何時用 chevrons／lanes 的判斷、§9 加三條新上限。轉譯流程本身未變。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：`references/output-templates.md` 查核表範例、
  `scripts/claim_check.py` docstring 與註解、`evals/evals.json` 第 4 案、`tests/test_claim_check.py` 的 suggest 測資、
  SKILL.md anchor 舉例與本檔 v1.5 源起段，原用 ECCE 實際數值，全部改為合成值（9 000 rpm／40、42.5 Nm 等），
  並移除投稿編號與對個人的描述。程式邏輯未變；`tests/test_claim_check.py` 10 項檢查全部 PASS（v1.5 驗證段寫的 11/11 為當時筆誤，檢查數一直是 10）。
