# cpet-figure-prep 維運規範（maintainer: Casey）

> 給維護者（人與 AI）看，不影響 skill 執行。

## 版本紀律
- 功能性變更（新子命令、演算法改變）+0.1，SKILL.md 標題與 CHANGELOG.md 末條同步。
- 同版 bug 修復不升版，於該版條目附記症狀、根因、驗證方式。

## 修改 `figprep.py` 的流程
1. 複製到 /tmp 修改（不在掛載點直接編輯）。
2. `py_compile` 過編譯。
3. 回寫後 md5 比對。
4. **以會踩到改動路徑的實際素材重跑**——影像處理的失敗多半是靜默的，
   單元層面看不出來，必須目視輸出。最低限度的回歸集：
   - `debg`：白底＋內部鏤空的圖示（斷言內部白保留、四角透明、去背比例 >50%）
   - `annotate`：英文 UI 截圖走 OCR 路徑、中文截圖走 region+snap 路徑，各至少一張
   - 守門：幾乎全白的圖應被 >97% 規則攔下並非零退出
5. `references/pitfalls.md` 若新增一類靜默失敗，必須連同「回歸測試怎麼寫」一起記。
6. CHANGELOG.md 記錄 → 重新打包 .skill。

## 已知環境風險
- Cowork 沙箱無 root：`apt-get` 一律失敗，OCR 中文語言包裝不了（見 pitfalls §4）。
- 掛載點大檔寫入偶發尾端截斷：大檔先寫 /tmp 再 cp，並做 md5 比對。
- 已安裝 skill 目錄唯讀：一律在專案資料夾維護完整結構 → `package_skill` 打包 →
  Save skill 重新安裝。

## 打包檢查清單
□ SKILL.md 標題版本號＝CHANGELOG.md 末條版本
□ 全部 .md 可完整 UTF-8 decode 且尾端正確
□ `figprep.py` 過 `py_compile`，`--help` 可列出全部子命令
□ `tests/test_fig_extract.py` 全 PASS
□ `__pycache__` 不入包
□ 打包後解 .skill 抽驗 SKILL.md 尾端

## `scripts/fig_extract.py`（v1.2 新增）的維護注意事項

- 跑 `tests/test_fig_extract.py`，必須全 PASS；它用 scipy 建構舊格式 .fig，不需要 MATLAB 也不需要專案檔。
- 改讀檔邏輯時，另以一批真實 .fig（在複本上）跑一次解碼統計，確認可解碼數沒有下降、HG2 仍是明確錯誤而非崩潰。
- 軸標籤的角色是靠「文字物件出現順序」推定（舊 .fig 不直接存 XLabel／YLabel 的對應），遇到標籤錯位時先檢查這裡。
- 邊界（Casey 2026-10-20 裁決）：只重繪既有 .fig；要加「重新分析」或「投稿圖」功能前先回頭確認邊界，不要默默擴大。

## `manifest` 子命令（v1.1 新增）的維護注意事項

- 這是本技能唯一「不處理圖片本身、只做記帳」的子命令，測試時不能只用既有的圖片
  回歸集，需額外涵蓋：正常登記、找不到檔案（`errors` 陣列正確記錄）、JSON 陣列
  輸入格式（非純文字行格式）三種情境。
- 輸出的 `manifest.json` 格式（`{figures:[{id,png}], errors:[{id,message}]}`）
  刻意對齊 `cpet-infographic-forge/scripts/forge.mjs` 的既有格式，讓
  `cpet-input-template` 的回填腳本能用同一套邏輯讀兩邊——**修改此格式前，需同步
  確認 `backfill_pending.py` 的 `load_manifest()` 是否也要跟著改**，兩者是成對
  的契約，不是各自獨立演化的。
- 本機 Windows 環境已知：`print()` 輸出 `✔`／`✘` 等符號在 cp950 codepage 終端機
  會拋 `UnicodeEncodeError`（見「已知環境風險」，這是既有六個子命令共有的問題，
  非 `manifest` 獨有）；如某天要修，六個子命令的 print 語句需一併處理，不要只修
  `manifest` 讓問題看起來只發生在新命令上。
