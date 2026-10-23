# cpet-figure-prep 版本履歷（Changelog）

> 維護者文件，skill 執行時不載入。撰寫紀律見 `MAINTENANCE.md`。

- **v1.0**（2026-08-04）：首次打包。合併原本規劃的兩個獨立提案——「screenshot-annotator」（截圖紅框標註）與「圖片去背＋autocrop」（cpet-yslai-pptx 改善提案 3）。合併的理由是兩者技術棧相同（Python + Pillow）、輸入輸出型別相同（點陣圖 → 可直接置入投影片的 PNG）、在真實流程中是串接的（外部圖 → 去背裁邊 → 標紅框 → 進簡報），且**失敗模式屬同一家族**（不報錯、產得出來、結果是錯的），因而可以共用同一道閘門：輸出前強制產生預覽拼接圖。單一入口 `scripts/figprep.py`，六個子命令：`inspect`（尺寸／透明／白邊／依置入寬度估有效 dpi）、`debg`（邊界 flood-fill 去背＋autocrop＋padding）、`convert`（EMF／WMF／SVG／PDF → PNG）、`locate`（兩條定位路徑）、`annotate`（spec 驅動批次標註）、`sheet`（預覽拼接圖）。**定位刻意設計成雙路徑**：OCR 路徑（英文 UI，實測 Casey 的截圖辨識信心 92–96）與 region+snap 路徑（把粗略框吸附到框內實際內容邊界，不依賴 OCR）——因為 Cowork 沙箱無 root、`chi_tra` 語言包裝不了，中文截圖必須有一條不靠 OCR 的路。標籤避讓以積分圖計算候選位置的局部墨水密度，O(1) 查詢，並排除超出畫布與與先前標籤重疊者。開發過程中踩到並記入 `references/pitfalls.md` 的靜默失敗：`Image.fromarray()` 建立的影像其 `ImageDraw.floodfill()` 寫入會被**靜默丟棄**（0 ms 返回、無例外、遮罩完全沒變，下游算出「去背 0%」而圖看起來正常），改用 `Image.frombytes()` 後正確。驗證：白底＋內部鏤空的圖示去背後內部白保留、四角透明、去背 75%；幾乎全白的圖被 >97% 守門攔下並非零退出；三張真實截圖批次標註（OCR 與 region 兩路徑並用、中英文標籤、次要色）目視通過，標籤分別被自動放到右／下／上的空白處。 驗證時另發現並記入文件：LibreOffice 的 `convert` 會把圖包成整頁輸出（實測 300×200 的 EMF 轉出為 794×1123 A4 帶大量白邊），故 `convert` 之後幾乎一定要接 `debg`，SKILL.md 已補上串接範例。

- **v1.1**（2026-08-16）：CPET 簡報工作流整備任務段2a——新增第七個子命令
  `manifest`，登記 `PENDING:figprep-鍵值` 與最終產出路徑的對應表，供
  `cpet-input-template` 的 `backfill_pending.py` 讀取。動機：`cpet-infographic-forge`
  已有 `manifest.json` 集中輸出（`forge.mjs` 內建），但本技能六個子命令各自獨立
  輸出，沒有對應機制，回填自動化在本技能側原本做不到。設計上刻意不做自動推斷——
  本技能的工作流程含明確的人工確認閘門（第5步預覽拼接圖），一個素材可能經過
  `debg`/`convert`/`annotate` 任意組合，只有使用者知道哪一步的輸出才是最終版本，
  故要求明確輸入「鍵值=路徑」清單而非掃描目錄猜測，與既有六個子命令「不猜測、
  要求明確輸入」的設計一致。SKILL.md 新增第6步的登記時機說明（**須在預覽確認之後
  才登記**）。驗證：端到端測試含正常登記與找不到檔案兩種情境，皆正確輸出
  `manifest.json` 與對應錯誤訊息，見 D2 技能更新異動報告。SKILL.md 標題升至 v1.1。

  **同版修復**（2026-09-20）：
  - 症狀：在 Windows／macOS 上執行 `annotate`／`sheet`，中文標籤全部變成空心方框
    （tofu），程式只在 stderr 印一行「找不到 CJK 字型」警告，**照常產出圖並以 0
    退出**。屬於本技能 SKILL.md 開宗明義要擋的那一類靜默失敗，卻發生在本技能自己
    身上。
  - 根因：`FONT_CANDIDATES` 只列了四條 Linux 容器路徑（`/usr/share/fonts/...`），
    在非 Linux 平台一條都命中不了，`_font()` 於是退到 `ImageFont.load_default()`
    的點陣字型——該字型不含 CJK 字符。本技能開發與驗證都在 Cowork Linux 容器內
    進行，此路徑從未被走到。
  - 修復：`FONT_CANDIDATES` 擴充為三平台並列（Linux Noto CJK、Windows 微軟正黑體
    `msjhbd.ttc`／`msjh.ttc`／Noto Sans TC／微軟雅黑、macOS PingFang／Songti）；
    另拆出 `FONT_CANDIDATES_LATIN` 供純西文標籤退路。`_font()` 新增選用參數
    `text`：標籤含 CJK（或未指定）而找不到 CJK 字型時，改為呼叫 `_die()` 中止並
    列出已嘗試路徑與各平台安裝指令，不再以方框輸出；標籤確定為純西文時才允許退到
    西文字型。`annotate_image()` 把本批全部標籤字串串接後傳入，讓「全英文標註」在
    無 CJK 字型的環境仍可運作。
  - 驗證：本機 Windows 11（Python 3.13）以 900×600 合成截圖跑 `annotate`，兩個
    標註框、中文標籤「中文標籤測試」與「次要區塊」（含 secondary 藍色）；實際選中
    `C:\Windows\Fonts\msjhbd.ttc`，繪製測試中文字串產生 1026 個深色像素（非空白），
    **輸出 PNG 經目視確認中文為真實字形、非方框**，框線／編號／次要色皆正確。負向
    測試：把 `FONT_CANDIDATES` 指向不存在路徑後，中文標籤以 exit 1 中止且訊息正確，
    純英文標籤正確退到 `arialbd.ttf`。
  - 一併記錄（未修）：`cmd_annotate` 最後的 `print(f"✔ ...")` 在 cp950 終端機仍會
    拋 `UnicodeEncodeError`——這是 MAINTENANCE.md「已知環境風險」既載的問題，六個
    子命令共有，不在本次範圍；本次驗證是在該例外之前完成圖檔輸出。要修須六個子命令
    的 print 一併處理，不應只修 annotate 讓問題看起來只發生在單一命令上。

- **v1.2**（2026-10-22）：新增 `scripts/fig_extract.py`——既有 MATLAB .fig 的讀取與投影片尺寸重繪（第 7 步），
  並放寬技能邊界（Casey 2026-10-20 裁決：放進 figure-prep，不放 IEEE-PlotOps）。

  **源起**：ECCE 2026 口頭報告的 14 張資料圖在技能外以專案腳本重繪（`figio.py`＋「figsize＝投影片格位」規則），
  另寫了一份從未執行的 MATLAB 版，等於重工兩次。這兩個做法與專案無關，可重用。

  **設計決策**：
  - 獨立腳本，不併入 `figprep.py`：依賴 scipy／matplotlib，處理點陣圖的六個子命令不該因此多背依賴。
  - 四個子命令：`summary`（看結構）、`lines`（匯出 CSV）、`slot`（列出投影片上圖片的實際尺寸，替換既有圖時當 `--slot`）、
    `replot`（以格位尺寸 300 dpi 重繪，保留原圖的顏色、線型、標記、名稱與軸範圍）。
  - 邊界：只做「資料與圖型都已在 .fig 裡、換成簡報尺寸」；新的分析與投稿圖仍走 IEEE-PlotOps。
  - 新版 MATLAB（HG2）的 .fig 明確回報格式錯誤並回 2，不嘗試猜解；曲面／等高線只列不畫。

  **取捨留痕**：
  - 原型的錯誤訊息建議「用 hgsave -v7 重存成舊格式」，這個說法沒有查證，移入時刪除，改為建議在 MATLAB 匯出 XData／YData。
  - ECCE 原腳本的像素校準疊圖（在既有 PNG 上疊圓）屬專案專用且脆弱，不收。

  **驗證**：
  - `tests/test_fig_extract.py`（以 scipy 建構舊格式 .fig 結構，無專案資料）：8/8 PASS——讀線名、軸標籤與範圍、
    線型標記、CSV 匯出、重繪像素尺寸＝格位 × 300 dpi（3.94×2.75 in → 1182×825）、HG2 回報錯誤、`slot` 列出圖片。
  - ECCE 2026 素材區全部 114 個 .fig（唯讀掃描）：84 個可解碼（其中 8 個為曲面／等高線），抽出 668 條線；30 個為 HG2，皆明確回報。
  - ECCE 定稿 #11：`slot` 列出內容圖 4.93 × 2.47 in（排在模板 logo 之前），以此尺寸重繪 FW／MTPV 轉矩軌跡圖並目視：
    論文配色、圓點／方塊標記、軸標籤與 legend 正確。

  **已知限制**：HG2 .fig 不支援；曲面／等高線不重繪；子圖（subplot）一律直向排列。

  **文字修訂（2026-10-23，不升版，公開發佈前去識別化）**：源起段移除投稿編號；`tests/test_fig_extract.py`
  的合成軸範圍改為 2000–9000 rpm、0–300 Nm，不再貼近 ECCE 實驗馬達的規格。8/8 PASS。
