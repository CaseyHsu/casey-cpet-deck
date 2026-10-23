# 官方模板描述檔（template profile）

研討會的官方簡報模板常見兩種結構：

| 結構 | 例 | 建置方式 |
|---|---|---|
| logo、線條、頁尾放在**母片／版面配置** | 實驗室模板 | `build_deck.py`（預設，用 `slide_layouts` 建頁） |
| logo、線條、頁尾畫在**範例投影片**上，只有一個空白版面配置 | ECCE 2026 Oral Template | `--profile`：複製範例頁再填內容 |

第二種模板無法用版面配置建頁，ECCE 2026 當時是在 build.py 裡寫死文字比對與座標處理。描述檔把這些差異集中成一份 JSON，建構器其餘部分（卡片、圖、表、結論橫條）完全共用。

## 建立新描述檔的步驟

1. 列出模板內容（每張範例頁的形狀名稱、位置、文字）：

   ```bash
   python -c "from pptx import Presentation; import sys
   p=Presentation(sys.argv[1])
   for i,s in enumerate(p.slides,1):
       print('slide',i)
       for sh in s.shapes:
           t=sh.text_frame.text[:40] if sh.has_text_frame else ''
           print('  ',sh.name,round(sh.left/914400,2),round(sh.top/914400,2),round(sh.width/914400,2),round(sh.height/914400,2),repr(t))" 模板.pptx
   ```

2. 依下表填 JSON（以 `assets/profiles/ecce2026_oral.json` 為範本）。
3. 用一份含封面、bands、公式、致謝、備用頁的小 plan 建置，轉 PDF 逐頁目視；再以 `QA_PROFILE=… full_qa.sh` 跑四層 QA。

## 欄位

| 欄位 | 說明 |
|---|---|
| `slides` | `{"cover": n, "content": n, "closing": n}`：擔任各角色的範例頁序號（1 起算）。模板其他範例頁建置後一律刪除 |
| `title_style` | 預設標題樣式；plan 的 `meta.title_style` 可覆寫。官方模板多半只有一行標題列，建議 `two-level` |
| `body` | `margin_x`、`top`、`bottom`（吋）：內容區。`top` 取標題列下緣＋約 0.2in，`bottom` 取頁尾線上方約 0.15in |
| `cover.fields` | 封面欄位 → 範例文字框。鍵：`title`（取 `title_en`，沒有就 `title_zh`）、`authors`（取 `authors`，沒有就 `presenter`）、`affiliation`、`date`。每個值：`{"text": 範例文字開頭}` 或 `{"name": 形狀名稱}`；可加 `box: [x,y,w,h]` 重新定位、`size` 起始字級、`max_lines` 最多行數（超過就縮字，下限 18pt） |
| `content.title` | 內容頁的標題文字框（清空後寫入章名＋頁名，沿用其字型與顏色） |
| `content.remove` | 要刪除的範例文字框（例如 "Sample Text"），同一條規則會刪掉所有符合的形狀 |
| `content.footer` | `match`：頁尾文字框；`format`：以 meta 欄位組字串（如 `"{paper_title}  -  {presenter}"`）；可加 `box`、`size`。plan 有 `meta.footer` 時直接用它 |
| `closing.text` | 致謝頁上要換成 `closing.text` 的文字框；plan 沒寫就保留模板原文 |
| `page_number` | `{x,y,w,h,size}`：模板母片**沒有**頁碼時才加；母片已有頁碼時不要設（會出現兩個號碼） |
| `lint` | `header_bottom`、`rule_y`：給 layout_lint 用的保留區；`structural_colors`：模板自帶、不該計入語意色數的顏色 |

## 已知限制

- 文字框以「範例文字開頭」比對，模板改了範例文字就要更新描述檔。
- 範例頁上的動畫、備忘錄不會被複製。
- 封面長標題靠 `size`／`max_lines` 縮字；若模板標題框本身太矮，用 `box` 重新定位（ECCE 2026 即如此）。
