# CPET 簡報生成工具鏈（cpet-deck-plugin）

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Version](https://img.shields.io/badge/version-1.3.1-informational)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-orange)

給 [Claude Code](https://docs.claude.com/en/docs/claude-code) 用的 plugin，把實驗室簡報從素材整理一路做到口頭報告：
內容轉譯與數據查核、投影片組裝（實驗室模板或大會官方模板）、資訊圖、既有圖片與 MATLAB `.fig` 重繪、
定稿後的動畫與版本管理、講稿與 Q&A 準備。用自然語言描述需求即可，不需要寫程式。

*A Claude Code plugin with six skills for building lab presentation decks in the CPET / YS Lai Lab style,
from source material to finished slides, speaker notes and Q&A. Documentation is in Traditional Chinese.*

## 目錄

- [功能](#功能)
- [需求環境](#需求環境)
- [安裝](#安裝)
- [使用方式](#使用方式)
- [更新與移除](#更新與移除)
- [疑難排解](#疑難排解)
- [安全性](#安全性)
- [維護](#維護)
- [授權與聲明](#授權與聲明)

## 功能

| 階段 | 技能 | 做什麼 |
|---|---|---|
| 建置前 | `cpet-input-template` | 把素材或口頭需求轉成 `input_template.md`，同時產出「素材處理清單」與「數據查核表」 |
| 建置 | `cpet-yslai-pptx` | 依實驗室風格組裝 `.pptx`（也支援大會官方模板 profile），內建四層 QA |
| 建置 | `cpet-infographic-forge` | 產生流程圖、矩陣、時程、比較等資訊圖 PNG／SVG，處理中文字型與投影片格位 |
| 建置 | `cpet-figure-prep` | 既有圖片去背、裁邊、截圖標註；不開 MATLAB 讀出 `.fig` 並依投影片格位重繪 |
| 定稿後 | `cpet-deck-finalize` | 修改手動調整過的簡報前先快照與檢查、寫入點擊動畫、產生無動畫版、寫入備忘錄 |
| 定稿後 | `cpet-talk-prep` | 以一份 `talk.json` 管理逐頁講稿，產生講稿版投影片、時間表、文字稿與 Q&A |

## 需求環境

| 項目 | 用途 | 檢查方式 |
|---|---|---|
| Claude Code CLI | 執行本 plugin | `claude --version` |
| Node.js ≥ 18 | `cpet-infographic-forge` | `node -v` |
| Python 3.12+ 與套件 `python-pptx`、`lxml`、`matplotlib`、`fonttools`、`pillow`、`numpy`、`scipy` | 投影片組裝、QA、`.fig` 讀取、定稿後工具 | `python -c "import pptx, lxml, matplotlib, fontTools, PIL, numpy, scipy"` |
| LibreOffice（`soffice`）與 poppler（`pdftoppm`） | 投影片轉圖的像素層 QA、EMF 轉 PNG | `soffice --version`、`pdftoppm -v` |
| `doc-coauthoring` 技能（選用） | `cpet-input-template` 的內容共創步驟 | 見下方說明 |

- **`doc-coauthoring`** 不隨本 plugin 發佈。Claude.ai 的 Chat／Cowork 已內建；Claude Code CLI 預設沒有，
  需自行安裝到 `~/.claude/skills/`。沒有它時，`cpet-input-template` 的內容共創步驟會缺一塊，可改用一般對話確認內容，
  產出的 `input_template.md` 格式相同。
- **Windows**：`soffice` 不在 PATH 時，QA 腳本會自動尋找 `C:\Program Files\LibreOffice\program\soffice.exe`。
- 選用：pdflatex（複雜公式的備援渲染）、tesseract（以文字定位截圖標註）。

## 安裝

```bash
# 1. 註冊 marketplace
claude plugin marketplace add CaseyHsu/casey-cpet-deck

# 2. 安裝 plugin
claude plugin install cpet-deck-plugin@cpet-deck-marketplace

# 3. 確認
claude plugin list
# 應看到 cpet-deck-plugin@cpet-deck-marketplace，狀態 enabled
```

安裝後重新啟動 Claude Code 才會載入。

**`cpet-infographic-forge` 的 npm 相依**不隨 plugin 發佈，第一次使用前在該技能的安裝目錄執行一次：

```bash
# 路徑通常是 ~/.claude/plugins/cache/cpet-deck-marketplace/cpet-deck-plugin/<版本>/skills/cpet-infographic-forge/
cd <該路徑>
npm ci
```

**Cowork**：側邊欄 Customize → Plugins → Add marketplace，填入 `CaseyHsu/casey-cpet-deck` 後安裝 `cpet-deck-plugin`。
此路徑依官方文件撰寫，尚未在 Cowork 實測；雲端容器每次 session 重建，使用 forge 前要再跑一次 `npm ci`。

## 使用方式

技能由**自然語言**觸發，不是斜線指令。照平常說話描述需求，Claude Code 會依語境選用技能：

| 你說 | 觸發的技能 |
|---|---|
| 「幫我做一份簡報，內容是……」「把這些素材做成簡報」 | `cpet-input-template` |
| 「用這份 input_template.md 建置簡報」「用實驗室模板輸出」「套研討會官方模板」 | `cpet-yslai-pptx` |
| 「畫一張流程圖」「多方法比較表」「雙軸對比圖」 | `cpet-infographic-forge` |
| 「這張圖有白框」「截圖標重點」「這張 .fig 重畫成簡報大小」 | `cpet-figure-prep` |
| 「定稿後要改一頁」「幫我加動畫」「產生無動畫版」 | `cpet-deck-finalize` |
| 「寫講稿」「試講太長要刪」「準備 Q&A」 | `cpet-talk-prep` |

**最短可跑通的路徑**：

1. 準備素材（大綱、圖片、參考文件），說「幫我做一份簡報，內容是……」。先與 Claude 確認內容，再產出
   `input_template.md`、素材處理清單與數據查核表。
2. 依素材處理清單，請 Claude 畫新的示意圖或處理既有圖片。
3. 說「用這份 input_template.md 建置簡報」，產出 `.pptx` 並自動跑 QA（內容、schema、像素、版面幾何）。
4. 要上台報告時，再用 `cpet-talk-prep` 準備講稿，用 `cpet-deck-finalize` 加動畫與產生衍生版本。

各技能的完整語法見安裝目錄下的 `skills/<技能名>/SKILL.md`。

## 更新與移除

```bash
# 更新（版本號改變時會裝到新目錄，forge 要重跑 npm ci）
claude plugin marketplace update cpet-deck-marketplace
claude plugin update cpet-deck-plugin@cpet-deck-marketplace

# 移除
claude plugin uninstall cpet-deck-plugin@cpet-deck-marketplace
claude plugin marketplace remove cpet-deck-marketplace
```

## 疑難排解

| 症狀 | 處理 |
|---|---|
| 改版後技能行為沒變 | 跑上方兩個更新指令，並重新啟動 Claude Code |
| forge 報錯找不到 `@antv/infographic` 等套件 | 在 forge 安裝目錄執行 `npm ci` |
| 圖或投影片的中文變成方框 | 安裝中文字型（Windows 內建微軟正黑體即可，建議另裝 Noto Sans TC） |
| Windows 出現 `UnicodeEncodeError: 'cp950'` | 確認已更新到 1.2.1 以上 |
| `claude plugin validate` 報 `source: Path contains ".."` | 只在改動 `marketplace.json` 時會遇到：plugin 的 `source` 不可指到 marketplace 根目錄之外 |

## 安全性

repo 根目錄的 `.skillspector-baseline.yaml` 記錄了以 SkillSpector 靜態掃描時，逐筆人工確認過的誤判與預期行為
（例如以固定參數呼叫 `soffice`）。安裝前想自行掃描時：

```bash
git clone --depth 1 https://github.com/CaseyHsu/casey-cpet-deck.git cpet-deck-scan
skillspector scan cpet-deck-scan --no-llm --baseline cpet-deck-scan/.skillspector-baseline.yaml
```

不帶 `--baseline` 時，這些已知項目會全部計入，結果必為 DO_NOT_INSTALL。
維護者用的新電腦安裝與驗證步驟見 [INSTALL-NEW-MACHINE.md](INSTALL-NEW-MACHINE.md)。

發現安全問題請開 GitHub issue，不要在 issue 中附上實際的機密資料。

## 維護

- 每個技能有自己的 `CHANGELOG.md` 與 `MAINTENANCE.md`；功能變更升版，bug 修復同版附記。
- 任一技能有異動，`plugins/cpet-deck-plugin/.claude-plugin/plugin.json` 的 `version` 必須跟著升，
  否則使用者端 `plugin update` 會判定版本相同而不更新。
- 打包前確認：`node_modules/`、`__pycache__/` 沒有被帶進 `plugins/`；`claude plugin validate ./plugins/cpet-deck-plugin`
  與 `claude plugin validate .` 都通過；被 baseline 收錄的檔案若有修改，baseline 要重新產生並逐筆核對。

## 授權與聲明

**授權**：本 repo 的程式碼與文件以 [MIT License](LICENSE) 釋出，下列第三方內容與標誌除外。

**第三方內容**（詳見 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)）：

- `cpet-infographic-forge/assets/icons/`：[Lucide](https://lucide.dev) 圖示，ISC License（部分源自 Feather，MIT License）。
- `cpet-yslai-pptx/scripts/office/schemas/`：ISO/IEC 29500-4:2016（Office Open XML）的 XML schema，僅供本機驗證使用，
  權利屬原標準組織。
- npm 與 Python 相依套件不隨本 repo 散佈，由使用者自行安裝，各依其授權。

**商標與標誌**：`cpet-yslai-pptx/assets/template.pptx` 含國立臺北科技大學（Taipei Tech）與
Center for Power Electronics Technology（CPET）的標誌。這些標誌的權利屬原所有者，**不在 MIT 授權範圍內**；
在實驗室以外的場合使用前，請先取得權利人同意，或把模板換成自己的版面。

**非官方聲明**：本專案由個人維護，不是國立臺北科技大學或 CPET 的官方產品，也不代表其立場。

**無擔保**：依 MIT License，本軟體按現況提供。產出的簡報、數據查核結果與講稿都需要使用者自行核對，
特別是數字、引用與研究結論。

**開發方式**：本專案在開發與文件撰寫過程中使用 Claude Code 協作，所有變更由維護者審閱後發佈。
