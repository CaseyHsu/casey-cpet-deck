---
name: cpet-figure-prep
description: 簡報素材前處理——處理「既有的點陣圖」讓它能安全放進投影片：白底去背與自動裁邊、EMF／WMF／SVG 轉 PNG、螢幕截圖加紅框與文字標註（標籤自動避開既有內容）、解析度與白邊體檢、批次處理與預覽確認。當使用者要求「這張圖有白框」「幫我把截圖標重點」「框住某個按鈕」「圖片去背」「截圖標註」「這張圖放進簡報會不會糊」「EMF 轉 PNG」「教學簡報的操作截圖」，或提供外部 AI 生成圖／網路抓圖／螢幕截圖要放進簡報時，一定要使用本技能。**也**負責把**既有的 MATLAB .fig 圖**（論文、實驗已畫好的曲線圖）不開 MATLAB 讀出資料、照論文配色重繪成投影片格位的尺寸——使用者說「這張 .fig 放進簡報」「論文的圖重畫成簡報大小」「把 .fig 的資料抓出來」「換掉第 N 頁的圖但尺寸不變」時使用。**不要**用於從資料生成示意圖（那是 cpet-infographic-forge），也不要用於製作投影片本身（那是 cpet-yslai-pptx），更不要用於新的統計分析或論文投稿圖（走 IEEE-PlotOps／MATLAB SOP）。
---

# CPET Figure Prep（v1.2 — 簡報素材前處理）

把**既有的點陣圖**與**既有的 MATLAB .fig 圖**整理成可以安全放進投影片的素材。核心價值不在「能處理圖片」，而在
**擋掉一整類會靜默失敗的坑**——這些坑的共同特徵是「不報錯、圖也產得出來，但結果是
錯的」，靠事後看縮圖抓不到。

## 與鄰近技能的分工

| 技能 | 職責 |
|---|---|
| `cpet-infographic-forge` | **從資料生成**向量圖（流程圖、矩陣、時程） |
| **`cpet-figure-prep`（本技能）** | **整理既有圖**（去背、裁邊、轉檔、標註、體檢；既有 .fig 重繪到投影片尺寸） |
| `cpet-yslai-pptx` | 把素材**組裝**進投影片 |
| IEEE-PlotOps／MATLAB SOP | 新的統計分析與論文投稿圖 |

生成／整理／組裝三分。素材若是要「無中生有畫一張圖」，走 forge，不要用本技能。
.fig 重繪的界線：**資料與圖型都已經在 .fig 裡**，只是要換成簡報尺寸與字級——走本技能；要重新分析數據、改圖型、
出投稿用的圖——不屬本技能。

## 為什麼需要這個技能：五個靜默失敗

| 失敗模式 | 表現 | 本技能的處置 |
|---|---|---|
| 全域白轉透明把圖挖爛 | 放大鏡鏡片、機器人眼白、流程圖填色一起被挖空 | 只從邊界 flood-fill，保留內部白 |
| 白底 PNG 直接置入 | 圖周圍一圈白框、有效內容被壓小 | `debg` 去背＋autocrop |
| 低解析度圖放大 | 投影時糊掉，簡報做完才發現 | `inspect` 依置入寬度算有效 dpi |
| 紅框框錯位置 | 座標靠肉眼估，切到文字或框到隔壁元素 | `locate` 兩條定位路徑，先查再框 |
| 標籤蓋到截圖既有文字 | 單張看不出來，嵌入簡報縮放後才發現 | 標籤自動避讓＋強制預覽拼接圖 |

**細節與實證見 `references/pitfalls.md`——動手前先讀，可省下重複排查。**

## 環境準備

```bash
pip install pillow numpy pytesseract --break-system-packages
```

`soffice`（LibreOffice）用於 `convert` 子命令；tesseract 用於 OCR 定位。

**重要環境限制**：Cowork 沙箱只裝得到 tesseract 的 `eng` 語言包，`chi_tra` 需要 root
（`apt-get` 會被拒）。因此**以中文字串定位在 Cowork 不可用**，請改走 region 路徑
（見下）。在 Claude Code／本機環境可 `apt-get install -y tesseract-ocr-chi-tra` 後啟用。

## 工作流程

### 1. 先體檢

```bash
python scripts/figprep.py inspect 素材/*.png --width-in 6
```

`--width-in` 是這張圖預計在投影片上佔的寬度（吋），用來估有效 dpi。輸出會標出
「四邊全白建議去背」「有效解析度不足會糊」「原圖偏小」三類提醒。**先看過再決定要不要
處理**，不要對所有圖無差別跑去背。

### 2. 去背與裁邊（只對需要的圖）

```bash
python scripts/figprep.py debg 素材/gemini_圖.png --outdir figs
```

適用：外部生圖工具（Gemini／DALL·E）的近白底 PNG、示意圖、圖示。
**不適用**：照片、示波器截圖、實驗設備照——去了會破圖或產生鋸齒。

參數：`--threshold`（預設 238，判定「近白」的門檻）、`--pad`（預設 6px 留白）、
`--no-crop`（保留原尺寸不裁）。

兩道守門：去背比例 >97% 直接中止（多半是門檻設錯，會把整張圖清空）；<1% 印警告
（邊界可能不是白色，這張其實沒被改到）。

### 3. 格式轉換

```bash
python scripts/figprep.py convert 圖.emf --outdir figs
```

EMF／WMF／SVG／PDF → PNG，透過 LibreOffice。Word 文稿裡抽出來的向量圖多半是 EMF，
直接餵給 python-pptx 會失敗。

**注意**：LibreOffice 會把圖包成整頁輸出——實測一張 300×200 的 EMF 轉出來是
794×1123（A4）帶大量白邊。所以 `convert` 之後幾乎一定要接 `debg` 裁掉白邊：

```bash
python scripts/figprep.py convert 圖.emf --outdir tmp
python scripts/figprep.py debg tmp/圖.png --outdir figs
```

### 4. 標註：先定位、再下框

**不要憑肉眼猜座標。** 先用 `locate` 查，確認位置對了再寫進 spec：

```bash
# 路徑 A：以文字內容定位（英文介面，需 OCR）
python scripts/figprep.py locate shots/01.png --text "Create a project"

# 路徑 B：以粗略區域＋吸附定位（中文介面、任何環境都可用）
python scripts/figprep.py locate shots/01.png --region "[0.05,0.30,0.95,0.42]"
```

路徑 B 的 `snap` 會把粗略框吸附到框內實際內容的邊界，**不依賴 OCR**，對圖示、輸入框、
色塊一樣有效。中文截圖一律走這條。

確認後寫 spec（可以是單一物件或陣列，陣列＝批次）：

```json
[
 {"image": "shots/01.png", "output": "figs/01_annotated.png", "boxes": [
   {"find": {"text": "Create a project"}, "label": "建立專案對話框"},
   {"find": {"region": [0.05,0.29,0.94,0.40], "snap": true}, "label": "填寫專案名稱"},
   {"find": {"region": [0.68,0.80,0.94,0.92]}, "label": "送出", "secondary": true}
 ]}
]
```

```bash
python scripts/figprep.py annotate spec.json
```

`find` 三選一：`text`（OCR）／`region`（0–1 正規化或絕對像素，預設 `snap: true`）／
`px`（絕對像素，不做任何處理）。`secondary: true` 改用藍色（次要標註），
`pad` 調整框與目標的間距，`color` 可直接指定 RGB。

框的編號自動加上（`(1)`、`(2)`…），標籤位置由工具在框的四周挑**墨水密度最低**的一處，
並避開先前已放的標籤。執行記錄會印出每個標籤放在哪一側與該處密度——若看到
「標籤放【框內】」代表四周都放不下，八成需要調整框的大小或換位置。

### 5. 預覽閘門（不要跳過）

`annotate` 會自動產生 `_preview_sheet.png` 編號拼接圖。也可單獨產：

```bash
python scripts/figprep.py sheet figs/*.png -o figs/_preview.png
```

**看過這張再放進簡報。** 標註類的錯誤在單張全尺寸下往往看不出來，要看整體、看縮放後
的樣子——實測經驗是紅框座標平均要修 2 次、標籤重疊要到嵌入簡報後才會發現。

### 6. 交回 cpet-yslai-pptx

處理好的 PNG 放進 plan 的 `images[].path`。**若素材取自網路或文獻，記得同時填
`images[].source`**——那是學術誠信要求，`plan_lint.py` 會檢查。

若素材是透過 `cpet-input-template` 產生的 `PENDING:figprep-鍵值` 觸發本技能處理，
**在完成第5步的預覽拼接圖確認之後**，登記鍵值與最終產出路徑的對應表供回填腳本使用：

```bash
python scripts/figprep.py manifest --from 鍵值對應.txt -o figprep_manifest.json
```

`鍵值對應.txt` 每行格式 `PENDING:figprep-鍵值=最終產出路徑`（v1.1 新增，見 CHANGELOG）。
**只在確認過預覽拼接圖、確定這是最終版本後才登記**——manifest 不做任何自動推斷，只是
機械記錄，登記錯了一樣會被機械地回填錯。

### 7. 既有 MATLAB .fig 重繪（v1.2）

論文或實驗的曲線圖多半存成 .fig。直接截圖放進簡報，字會太小或被縮放糊掉；本技能不開 MATLAB 讀出資料，
照原圖配色（論文一致，conventions §2.5.5 例外條款）在**投影片格位的實際尺寸**重繪，置入時 1:1、不縮放，字級就是實際的 9–11pt。

```bash
python scripts/fig_extract.py summary 圖.fig                       # 看結構：有哪些線、名稱、資料點數
python scripts/fig_extract.py slot 簡報.pptx 11                    # 要換掉既有的圖：列出該頁圖片的實際尺寸
python scripts/fig_extract.py replot 圖.fig figs/圖.png --slot 4.93 2.47
python scripts/fig_extract.py lines 圖.fig figs/圖_data/            # 只要資料（CSV），在專案裡自己畫
```

- `--slot` 的寬高：替換既有圖時用 `slot` 列出的尺寸；新頁面用 yslai 建置後同一頁圖片的尺寸，或依版面估的格位大小。
- 只解得出**舊格式**的 .fig；新版 MATLAB 存的（HG2）會明確回報格式錯誤並結束（回傳 2）——請在 MATLAB 匯出各條線的
  XData／YData 再畫，**不要**改用截圖充數。
- 曲面與等高線圖 `summary` 列得出來，但不重繪（只重繪折線類）。
- 重繪後照第 5 步產生預覽拼接圖目視；有 legend 的圖確認沒有蓋到曲線。

依賴：`numpy`、`scipy`、`matplotlib`（`slot` 另需 `python-pptx`）。

## 交付前的自我檢查

- [ ] `inspect` 的提醒都處理過或確認可忽略
- [ ] 去背過的圖：內部白（圖示鏤空、色塊填色）沒有被挖空
- [ ] 每個紅框都是先 `locate` 確認過座標，不是憑估的
- [ ] 預覽拼接圖看過，沒有標籤蓋到既有文字
- [ ] 外部素材已備妥出處字串，準備填進 plan 的 `source`
- [ ] 若素材源自 `PENDING:figprep-鍵值`，已在預覽確認後才登記 `manifest`，不是處理到一半就登記
- [ ] .fig 重繪的圖：`--slot` 等於投影片上的實際格位尺寸，置入時沒有再縮放；灰階下各條線靠線型或標記分得開
