# cpet-input-template 維運規範（maintainer: Casey）

> 給維護者（人與 AI）看，不影響 skill 執行。

## 版本紀律

- 功能性變更（新的轉譯規則、輸出格式改變、路由邏輯調整）+0.1，SKILL.md 標題與
  CHANGELOG.md 末條同步。
- 同版 bug 修復不升版，於該版條目附記症狀、根因、驗證方式。
- `references/translation-rules.md` 的版本快照標註（檔頭「對應 cpet-yslai-pptx
  vX.X」）**必須與實際核對過的 cpet-yslai-pptx 版本一致**——這份文件的過時風險是本技能
  最主要的維護負債，見下方「校正紀律」。

## cpet-yslai-pptx 升版時的校正紀律（最重要的維護動作）

`cpet-yslai-pptx` 每次升版，若涉及 DSL 語法或 `input_template.md` 相關規則變更，本技能
的 `references/translation-rules.md` 都需要對應校正，否則會重演 v1.0 打包當下就已經
在示範的問題（v3 工作流指引寫死複製了 v2.6 時期語法，兩個 session 後就已經是錯的）。

校正流程：
1. 取得該次升版的交接文件（若對方 session 有產出）或直接 diff `cpet-yslai-pptx` 的
   `SKILL.md` 步驟0/0.5/1 與 `cpet-yslai-pptx/assets/input-templates/input_template.md`。
2. 逐條核對 `translation-rules.md` §1–§11，比照本次 v1.0 撰寫時的做法：**不要只轉述
   交接文件的敘述，實際打開 `cpet-yslai-pptx` 的原始碼（`build_deck.py`／
   `plan_lint.py`）核對關鍵主張**（例如顏色、量化上限、路徑處理邏輯），交接文件本身
   也可能有轉述誤差。
3. **版本標示改了不等於內容已經對齊**——v1.1 校正的實際案例：對方只是把範本檔頭版本
   標示從「v2.8」修成「v2.9」，但重新通讀範本全文後另外抓到兩個先前就漏收錄的語法
   （`[eq-right:]`、`[first_col_item:]`），跟這次的版本標示變動本身無關，是舊版就有
   而 v1.0 撰寫時沒抓全。每次校正都要通讀一次範本全文逐段比對 §4 語法表，不能只看
   版本號有沒有變就結案。
4. 更新 `translation-rules.md` 檔頭的版本快照標註與 `output-templates.md` 若涉及格式
   變更的部分。
5. CHANGELOG.md 記錄本次校正對應哪個 `cpet-yslai-pptx` 版本、修正了哪些條目。
6. 因為 SKILL.md 本身已設計為「執行時讀取即時語法，不依賴快照」，校正
   `translation-rules.md` 的急迫性低於 `cpet-yslai-pptx` 或 `cpet-figure-prep` 這類
   直接執行腳本的技能——但**轉譯判斷邏輯**（§3 排版式樣觀念、§10 路由判斷）若隨新版
   有結構性變化（例如未來又新增第四個下游技能），仍必須校正，不能只靠「執行時讀語法」
   彌補判斷邏輯本身的過時。

## 測試與驗證

本技能核心是「轉譯判斷」而非確定性腳本執行，無法像 `figprep.py`／`build_deck.py` 那樣
用固定回歸集驗證輸出位元組相同。驗證方式改為：

1. 用 `evals/evals.json` 裡的測試案例（散文草稿或素材檔案 + 需求描述），跑過一次完整
   流程，人工檢查輸出的 `input_template.md` 是否語法正確、量化上限有沒有守住、路由
   判斷是否合理。
2. 特別檢查修訂模式：先跑一次初次生成，再模擬「使用者提出局部修改意見」，確認輸出是
   整份重跑且決策摘要只列差異，沒有變成局部 patch 或全部重列。
3. 若之後 `cpet-yslai-pptx` 或 `cpet-figure-prep` 的介面變化（新增子命令、路由條件
   改變），連動更新 evals 測試案例，不只是改 `translation-rules.md`。

## 已知環境風險

- ~~Cowork 沙箱無法在單一 session 內完整端對端驗證~~——**v1.1 更新：已用 skill-creator
  eval 流程實測證偽**。2 組 with-skill subagent 測試中，`Skill` 工具確實成功呼叫了
  `doc-coauthoring`（Stage 3 讀者測試甚至真的另外 spawn 了一個子代理跑冷讀者測試），也
  確實讀到已安裝 `cpet-yslai-pptx` 的即時語法並回報版本號。保留但縮小範圍的真實限制：
  eval 是自動化 subagent 執行，`doc-coauthoring` 的 Stage 1-2（脈絡收集／逐段共創）需要
  的真人多輪對話，在無真實使用者的測試情境下由執行者以工程判斷替代，這部分的保真度沒有
  被驗證到，正式使用時（有真人在互動迴圈中）行為可能與 eval 記錄不同。
- 已安裝 skill 目錄唯讀：一律在專案資料夾維護完整結構 → `package_skill` 打包 →
  Save skill 重新安裝。
- 掛載點大檔寫入偶發尾端截斷：大檔先寫暫存區再複製，並做 md5 比對。

## `scripts/backfill_pending.py`（v1.2 新增）的維護注意事項

- 本技能第一次擁有 `scripts/`，且是本技能唯一的確定性腳本（其餘工作流程全是轉譯
  判斷）。修改時比照 `figprep.py`／`build_deck.py` 的紀律：複製到可寫路徑改、
  `py_compile` 過編譯、用會踩到改動路徑的實際案例重跑（含「有鍵值未被 manifest
  涵蓋」「manifest 標記失敗」兩種邊界情況，不能只測正常路徑）。
- 這是機械式字串取代，**刻意不做任何語意判斷**——不檢查「這個路徑指到的圖片內容
  是否合理」，不檢查「這個鍵值的用途是否符合本技能第5步當初的判斷」。若未來有人
  想在這支腳本裡加判斷邏輯，先確認為什麼不是加在第5步的轉譯規則裡——判斷邏輯的
  正確位置是轉譯階段，不是回填階段，混在一起會讓兩件性質不同的工作互相干擾除錯。
- 與 `cpet-infographic-forge` 的 `forge.mjs`、`cpet-figure-prep` 的 `manifest`
  子命令共用 `manifest.json` 格式契約（`{figures:[{id,png}], errors:[...]}`）。
  三方任一改動此格式，需同步確認其餘兩方是否受影響。

## `scripts/claim_check.py`（v1.5 新增）的維護注意事項

- 唯讀工具，不修改任何輸入檔；若有人想讓它「自動修正數字」，那屬於 cpet-deck-finalize 的寫入流程，不放這裡。
- 查核表欄名（`id | anchor | value | unit | kind | labels | source | pages | status`）是契約：
  `references/output-templates.md` §2.5、`suggest` 的輸出、`parse_ledger` 三者要一致。
- 讀 talk.json 依賴 cpet-talk-prep 的 schema `cpet-talk/0.1`（pages／backup／other）；該 schema 改版時同步。
- 不可見字元（千分位窄空白、非斷行連字號、負號）一律用 `chr()` 定義，不直接寫在原始碼裡。
- 修改後跑 `tests/test_claim_check.py`，並以一份真實定稿簡報（在複本上）確認 D49 型情境仍被抓到。

## 打包檢查清單

□ SKILL.md 標題版本號＝CHANGELOG.md 末條版本
□ 全部 .md 可完整 UTF-8 decode 且尾端正確
□ `references/translation-rules.md` 檔頭版本快照標註與實際核對過的 cpet-yslai-pptx
  版本一致
□ 版本標示核對過**不代表內容核對過**——`cpet-yslai-pptx` 範本升版時，除了比對版本號，
  另外通讀一次範本全文逐段比對 `translation-rules.md` §4 語法表有沒有遺漏（v1.1 教訓：
  `[eq-right:]`／`[first_col_item:]` 兩個語法存在已久，只是 v1.0 撰寫時沒抓到，不是
  這次升版才新增的）
□ evals/evals.json 測試案例存在且至少涵蓋一次初次生成、一次修訂模式
□ `backfill_pending.py` 過 `py_compile`，端到端測試涵蓋正常回填／鍵值未涵蓋／
  manifest標記失敗三種情境
□ `tests/test_claim_check.py` 全 PASS
□ `__pycache__` 不入包
□ 打包後解 .skill 抽驗 SKILL.md 尾端
