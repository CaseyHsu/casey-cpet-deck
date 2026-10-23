# 新電腦安裝手冊：cpet-deck-plugin（給 Claude Code 照做）

- 版本：v1.2（2026-10-23），對應 cpet-deck-plugin **1.3.1**（v1.1 對應 1.3.0，v1.0 對應 1.2.1）
- 對象：新電腦上的 Claude Code session（由 Casey 開啟並授權）
- 用法：Casey 在新電腦開 Claude Code，說「請讀 INSTALL-NEW-MACHINE.md 並照步驟安裝 cpet-deck-plugin」

> **給執行的 Claude**：照順序做，每一步都有「通過條件」。沒通過就停下來，把指令與完整輸出回報給 Casey，
> 不要跳步、不要改用別的做法繞過。要求 Casey 按允許或親自操作的地方，本文會標 **【Casey】**。
> 回覆用台灣繁體中文。

---

## 步驟 0：確認前提

這台電腦應已依 `casey-skillspector-kit` 的 `INSTALL.md` 裝好 **SkillSpector 安裝前資安閘門**。

```powershell
& "$HOME\.claude\tools\skillspector-venv\Scripts\skillspector.exe" --version
claude --version
git --version
```

**通過條件**：SkillSpector 印出 `SkillSpector v2.12.0`；`claude` 與 `git` 都有版本號。

- SkillSpector 不存在 → **停下來**，請 Casey 先完成 skillspector-kit 安裝。依 Casey 的規則，沒有掃描不得安裝任何 plugin。
- 閘門 hook 已啟用時，下面幾個步驟會跳出確認或被阻擋，這是預期行為，各步驟已註明。

---

## 步驟 1：安裝前資安掃描（必做，不可省略）

先把 repo clone 到暫存目錄，**帶 baseline** 掃描：

```powershell
$T = Join-Path $env:TEMP "cpet-deck-scan"
Remove-Item -Recurse -Force $T -ErrorAction SilentlyContinue
git clone --depth 1 https://github.com/CaseyHsu/casey-cpet-deck.git $T
$env:PYTHONUTF8 = "1"
& "$HOME\.claude\tools\skillspector-venv\Scripts\skillspector.exe" scan $T --no-llm --baseline "$T\.skillspector-baseline.yaml" --format json --output "$env:TEMP\cpet-deck-scan.json"
(Get-Content "$env:TEMP\cpet-deck-scan.json" -Raw -Encoding UTF8 | ConvertFrom-Json) | Select-Object -ExpandProperty risk_assessment
(Get-Content "$env:TEMP\cpet-deck-scan.json" -Raw -Encoding UTF8 | ConvertFrom-Json).issues.Count
```

**通過條件**（2026-10-23 在原電腦以 1.3.1 公開版目錄實測）：

| 欄位 | 預期 |
|---|---|
| `score` | 0 |
| `severity` | LOW |
| `recommendation` | **CAUTION**（不是 DO_NOT_INSTALL） |
| `issues.Count` | 0（22 筆已由 baseline 壓制） |

為什麼是 CAUTION 而不是 SAFE：有 16 個檔案（forge 的 recipe／腳本與 ISO schema 檔）超過掃描器靜態解析上限或被判為疑似混淆文字，
只做了部分檢查（覆蓋率約 95%，1.3.1 實測 95.1%），不是發現了問題。這 16 個檔案自 1.2.1 起未改程式邏輯，已人工檢查過，
沒有網路存取、eval、shell 執行或讀取憑證的寫法。

- 結果是 DO_NOT_INSTALL，或 `issues` 不是 0 → **停下來**，把 `issues` 每筆的 `id`、`severity`、`location.file` 列給 Casey。
  可能是 repo 有新改動但 baseline 沒更新。
- 符合預期 → 把上表的實際數值回報給 Casey，**【Casey】確認 CAUTION 可接受後**再進步驟 2。

**沒帶 `--baseline` 會得到 DO_NOT_INSTALL**（22 筆已知誤判全被計入），這是正常的，不代表 repo 有問題。

---

## 步驟 2：安裝系統相依

先檢查，缺什麼再裝什麼：

```powershell
node -v                 # 需 ≥ 18
python --version        # 需 3.12 以上
py -0p                  # 列出可用的 Python
soffice --version       # LibreOffice；不在 PATH 時見下方說明
pdftoppm -v             # poppler
```

| 項目 | 用途 | 缺少時 |
|---|---|---|
| Node.js ≥ 18 | `cpet-infographic-forge` 產圖 | `winget install OpenJS.NodeJS.LTS` |
| Python 3.12+ | `cpet-yslai-pptx`、`cpet-figure-prep`、QA 腳本 | `winget install Python.Python.3.13` |
| LibreOffice | 投影片轉圖 QA、EMF 轉 PNG | `winget install TheDocumentFoundation.LibreOffice`；不加入 PATH 也可以，`full_qa.sh` 會自動找 `C:\Program Files\LibreOffice\program\soffice.exe` |
| poppler（`pdftoppm`） | QA 把 PDF 轉成逐頁圖 | TeX Live／MiKTeX 內附；或另裝 Windows 版 poppler 並把 `bin` 加入 PATH |
| Microsoft Edge 或 Google Chrome | `svg-to-png.mjs` 轉 PNG（Windows 內建 Edge 即可） | 兩者都沒有才需要 `npx --no-install playwright install chromium`（須在 forge 技能目錄內執行） |
| pdflatex（選用） | 複雜公式（`cases`、`aligned`）的備援渲染 | TeX Live 或 MiKTeX；沒有時一般公式仍可用 matplotlib 渲染 |
| tesseract（選用） | `cpet-figure-prep` 以文字定位標註 | 沒有時改用座標區域標註 |
| 中文字型 | 圖中文字 | Windows 內建微軟正黑體即可；建議另裝 Noto Sans TC |

Python 套件（裝在 `full_qa.sh` 會用到的那個 Python；它依序找 `python3`、`py`、`python`，並以能 `import pptx` 的為準）：

```powershell
py -m pip install python-pptx matplotlib fonttools pillow lxml numpy
py -m pip install pytesseract      # 選用，配合 tesseract
py -c "import pptx, matplotlib, fontTools, PIL, lxml, numpy; print('python deps ok')"
```

**通過條件**：最後一行印出 `python deps ok`；`node -v` ≥ 18；`soffice` 與 `pdftoppm` 能執行（`soffice` 不在 PATH 時，確認上述標準安裝路徑存在即可）。

---

## 步驟 3：確認 doc-coauthoring 技能

`cpet-input-template` 第一步會呼叫 `doc-coauthoring`，它**不隨本 plugin 發佈**。

- 帳號已啟用 claude.ai 技能同步時，`~/.claude/skills/synced/<...>/doc-coauthoring/` 通常已經存在。
- 檢查方式：在 session 內問「目前可用的技能有沒有 doc-coauthoring」，或查看該目錄。

**通過條件**：找得到 `doc-coauthoring`。找不到時**不擋安裝**，但要告訴 Casey：`cpet-input-template` 的內容共創步驟會缺這一塊，
需改用一般對話先確認內容（見 README「doc-coauthoring 的取得方式」）。

---

## 步驟 4：安裝 plugin

```powershell
claude plugin marketplace add CaseyHsu/casey-cpet-deck
claude plugin install cpet-deck-plugin@cpet-deck-marketplace
claude plugin list
```

- **【Casey】** 閘門 hook 會把 `claude plugin marketplace add`／`install` 判為「沒有可掃描的來源」並跳出確認。
  步驟 1 已帶 baseline 掃過，請在確認視窗按允許。
- **不要**改寫成完整網址 `https://github.com/...`：閘門會對網址重新掃描但**不帶 baseline**，結果必定是 DO_NOT_INSTALL 而被阻擋。
- Claude 的工具呼叫若被權限擋下，也可以請 Casey 在互動 session 自己輸入斜線指令：
  `/plugin marketplace add CaseyHsu/casey-cpet-deck`，再 `/plugin install cpet-deck-plugin@cpet-deck-marketplace`。

**通過條件**：`claude plugin list` 出現 `cpet-deck-plugin@cpet-deck-marketplace`，版本 `1.3.1`，狀態 `✔ enabled`。

---

## 步驟 5：安裝 cpet-infographic-forge 的 npm 相依（一次性）

npm 套件不隨 plugin 發佈，要在 plugin 安裝位置裡裝一次。先找路徑：

```powershell
Get-ChildItem "$HOME\.claude\plugins\cache" -Recurse -Directory -Filter "cpet-infographic-forge" | Select-Object -ExpandProperty FullName
```

應找到類似 `...\.claude\plugins\cache\cpet-deck-marketplace\cpet-deck-plugin\1.3.1\skills\cpet-infographic-forge` 的路徑。
在該目錄執行（用 `npm ci`，會完全照 `package-lock.json` 安裝，所有直接相依都是精確版）：

```powershell
Set-Location "<上一步找到的路徑>"
npm ci
npm audit
npx --no-install playwright --version
```

**通過條件**：`npm ci` 成功；`npm audit` 顯示 `found 0 vulnerabilities`；playwright 印出 `Version 1.62.1`。

找到多個版本目錄時，用版本號最大的那個（應為 1.3.1）。

---

## 步驟 6：功能驗證

### 6.1 技能都有掛載

開一個**新的** Claude Code session，問：「列出目前載入的 cpet 相關技能」。

**通過條件**：看得到 `cpet-input-template`、`cpet-yslai-pptx`、`cpet-infographic-forge`、`cpet-figure-prep`、
`cpet-deck-finalize`、`cpet-talk-prep` 六個（1.3.0 起；1.2.1 為前四個）。

### 6.2 產一張資訊圖

在暫存目錄建一份 job（`output_dir` 用絕對路徑）：

```yaml
meta:
  deck_title: "安裝驗證"
  output_dir: "<暫存目錄>/forge-out"
  palette: cpet-vivid
figures:
  - id: fig-01-flow
    route: engine
    template: list-grid-badge-card
    slot: full
    data:
      title: 控制策略開發流程
      lists:
        - label: 時間延遲補償
          desc: 補償一拍半延遲避免振盪
        - label: 參數鑑別
          desc: 線上估測電感與磁鏈
```

```powershell
Set-Location "<步驟 5 的 forge 路徑>"
node scripts/forge.mjs "<job 檔路徑>"
```

**通過條件**：印出「1 張成功，0 張失敗」，產出 PNG。**打開 PNG 目視**中文是正常字形、不是方框。
（QA 的 `aspect` 項可能因測試資料太少而 FAIL，不影響本步驟判定。）

### 6.3 建一份簡報並跑完整 QA

請 Claude 依 `cpet-yslai-pptx` 的 SKILL.md 寫一份 3～4 頁、含中文與一條公式的 `plan.json`，然後：

```bash
python <cpet-yslai-pptx 路徑>/scripts/build_deck.py plan.json test.pptx
bash <cpet-yslai-pptx 路徑>/scripts/full_qa.sh test.pptx
```

**通過條件**：`build_deck.py` 產出 `test.pptx`；`full_qa.sh` 彙總四層（內容、schema、像素、版面幾何）皆 PASS；
抽一張 `slide-*.png` 目視版面與中文正常。

（`build_deck.py` 與 `full_qa.sh` 在 1.2.1 已修正繁中 Windows 的 cp950 編碼問題；若仍出現 `UnicodeEncodeError` 或
`UnicodeDecodeError: 'cp950'`，代表裝到的版本低於 1.2.1，回步驟 4 確認版本。）
（1.3.0 起另可跑各技能的自帶測試確認：`python <技能路徑>/tests/test_*.py`，應印出 `all passed`；需要 python-pptx、lxml、scipy、matplotlib。）

---

## 步驟 7：回報與清理

回報給 Casey：

1. 步驟 1 的 score／severity／recommendation／issues 數。
2. 步驟 2 各相依的版本，以及哪些選用項目沒裝。
3. 步驟 3 doc-coauthoring 是否存在。
4. `claude plugin list` 的那一行。
5. 步驟 6 三項驗證的結果與產出檔路徑。
6. 任何沒通過或被跳過的步驟，以及原因。

清理：

```powershell
Remove-Item -Recurse -Force (Join-Path $env:TEMP "cpet-deck-scan"), "$env:TEMP\cpet-deck-scan.json" -ErrorAction SilentlyContinue
```

---

## 之後更新

```powershell
claude plugin marketplace update cpet-deck-marketplace
claude plugin update cpet-deck-plugin@cpet-deck-marketplace
```

更新後版本號會變，plugin 會裝到新的版本目錄，**要重做步驟 5 的 `npm ci`**。
更新前同樣先做步驟 1 的帶 baseline 掃描。

## 移除

```powershell
claude plugin uninstall cpet-deck-plugin@cpet-deck-marketplace
claude plugin marketplace remove cpet-deck-marketplace
```
