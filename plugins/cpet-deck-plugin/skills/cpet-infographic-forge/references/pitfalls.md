# 靜默失敗實證與排查指南

本文件記錄五個**不會拋出任何錯誤訊息**的失敗模式。它們的共同特徵是：程式回報成功、圖也產得出來、看起來完整，但結果是錯的。每一項都經過實測驗證，並附上判別方法。

**排查任何異常前先讀本文件，可避免重複已排除的假設。**

## 目錄

1. [NO GLYPH：中文全變方框](#1-no-glyph中文全變方框)
2. [engine route 文字完全遺失](#2-engine-route-文字完全遺失)
3. [模板名靜默 fallback](#3-模板名靜默-fallback)
4. [資料鍵錯誤導致 SSR hang](#4-資料鍵錯誤導致-ssr-hang)
5. [29% 模板靜默丟棄 desc](#5-29-模板靜默丟棄-desc)
6. [縮字至不可讀但不溢出](#6-縮字至不可讀但不溢出)
6. [附錄：失效的檢查方法](#附錄失效的檢查方法)
7. [附錄：模板容量參考](#附錄模板容量參考)

---

## 1. NO GLYPH：中文全變方框

### 現象
每一個 CJK 字元渲染成內含 "NO GLYPH" 字樣的直立方框；西文與 icon 正常。方框數量與中文字數精確吻合。

### 根因（三個條件疊加）

1. 字型堆疊把 **Inter 排在第一位**（`font-family="Inter, Noto Sans CJK TC, sans-serif"`）
2. cairosvg 走 cairo 的 **toy text API，不做逐字元 font fallback**——只解析出單一字型面就整段渲染，不會因缺字往堆疊後面找
3. **Inter 完全不含 CJK glyph**，而 **Inter 的 `.notdef` 恰好被設計成內含 "NO GLYPH" 字樣的方框**

### 決定性證據

```bash
# 證據 1：fallback 根本沒發生
# "Inter, Noto Sans CJK TC, sans-serif" 與 "Inter" 渲染輸出 md5 完全相同
# "Noto Sans CJK TC" 與 "Noto Sans CJK TC, Inter, sans-serif" 亦相同

# 證據 2：Inter 不含中文
python3 -c "
from fontTools.ttLib import TTFont
f=TTFont('/usr/share/fonts/opentype/inter/Inter-Regular.otf')
cmap=f.getBestCmap()
print('中' in [chr(c) for c in cmap])   # False
"

# 證據 3：Inter 的 .notdef 是有內容的方框
python3 -c "
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
f=TTFont('/usr/share/fonts/opentype/inter/Inter-Regular.otf')
pen=RecordingPen(); f.getGlyphSet()['.notdef'].draw(pen)
print('輪廓數:', len([o for o,a in pen.value if o=='moveTo']))  # 10（空方框只需 2）
"
```

### 「間歇性」的真相

前一輪排查曾認為此問題間歇出現、懷疑是 cairo 字型快取污染。**該假說錯誤。** 行為是完全確定性的——取決於當下 **Inter 有沒有安裝**：

- 裝了 Inter → 堆疊第一位可解析 → 中文全毀
- 沒裝 Inter → 往後 fallback 到 Noto → 中文正常

所謂「某次正常」是 Inter 尚未安裝時跑的；「icon 單獨測試全正常」是因為那批測試只有英文標籤。

### 修法與驗證

`postprocess.mjs` 將字型堆疊改為 CJK 優先。Noto Sans CJK TC 本身含完整拉丁字母，中英混排不會缺字；純西文節點另行覆寫回 Inter 優先以保留較佳西文字形。

驗證：修正後標題區寬度由 235px 增為 387px，與理論值吻合（7 個全形中文字 × font-size 34 = 238 SVG 單位 × 縮放比 1.634 = 389px；Inter `.notdef` 窄方框約 0.6em ⇒ 233px）。

### 判別方法

```bash
python3 scripts/check-font-coverage.py <輸出>.svg
# FAIL 時會逐節點列出缺 glyph 的字元與實際採用的字型
```

---

## 2. engine route 文字完全遺失

### 現象
產出的 PNG 只有色塊，**一個文字都沒有**。圖形結構完整，容易誤判為「設計如此」。

### 根因
`@antv/infographic` 的 SSR 以 `<foreignObject>` ＋ HTML `<span>` 承載文字，而 cairosvg 是純 SVG 渲染器，**不處理內嵌 HTML**，該區塊被整段略過。

### 決定性證據

```bash
# 文字色像素數為 0
python3 -c "
from PIL import Image
img=Image.open('out/fig.png').convert('RGBA'); w,h=img.size; px=img.load()
n=sum(1 for y in range(h) for x in range(w)
      if px[x,y][3]>128 and all(abs(px[x,y][i]-38)<40 for i in range(3)))
print('文字色像素:', n)   # 修復前為 0
"
```

### 為何不能改用其他渲染引擎

- **Playwright／headless Chromium**：完整支援 foreignObject，但 `cdn.playwright.dev` 不在受限環境的網路 allowlist（403），apt 的 `chromium-browser` 僅為 snap 轉接殼無法執行
- **resvg／rsvg-convert**：皆明確不支援 foreignObject

### 修法
`foreignobject-to-text.py` 將 foreignObject 轉寫為原生 `<text>`／`<tspan>`。

此方案的可行性建立在「foreignObject 內部一律單層 span」這個前提上，**該前提已在全部 276 個模板上驗證**：

| 驗證項 | 結果 |
|---|---|
| `allSingleSpan` 成立 | 276/276，違反 0 |
| 巢狀深度最大值 | 1 |
| 超出已知 15 項的 CSS 屬性 | 無 |
| 轉寫後殘留／略過 | 0 / 0 |

文字承載方式分布：純 foreignObject 230 個、混用 46 個、**完全不用 foreignObject 者 0 個**——即每一個模板都依賴此轉寫。

### 斷行行為
中英混排差異化處理：CJK 逐字斷、西文依單字邊界斷（`beyond`／`injecting` 不會被切開）、超長單詞依 `word-break:break-word` 強制斷。字寬取自 fontTools 的實際字型 advance width，比引擎內部 `measury` 的離線字寬表更貼近真實渲染。

---

## 3. 模板名靜默 fallback

### 現象
打錯模板名或使用家族簡寫，得到一張**完全不相干的圖**，且沒有任何提示。

### 決定性證據

```
resolveTemplateKey('sequence-roadmap')  → 'sequence-pyramid-simple'   # 不同家族！
resolveTemplateKey('list-grid')         → 'list-grid-simple'
resolveTemplateKey('does-not-exist')    → 'compare-swot'              # 任意錯字
```

### 影響範例
一份溢出測試曾使用 `sequence-roadmap`，實際渲染的是 `sequence-pyramid-simple`，導致該案例的框尺寸數據被錯誤歸屬給 roadmap 家族。

### 修法
`validate-input.mjs` 要求必須使用 `template-registry.json` 內的 276 個完整模板名，並在錯誤訊息中**揭露該名稱實際會被解析成什麼**，讓使用者理解後果而非只是被拒絕。

---

## 4. 資料鍵錯誤導致 SSR hang

### 現象
渲染卡住約 10 秒後拋出 `SSR render timeout`。若批次產圖，表現為整份 job 異常緩慢。

### 決定性證據

同一模板、僅資料鍵不同：

| 模板 | 資料鍵 | 結果 |
|---|---|---|
| `hierarchy-tree-curved-line-compact-card` | `lists` | 成功 66ms |
| 同上 | `children` | **timeout 10001ms** |
| `hierarchy-tree-bt-curved-line-badge-card` | `lists` | 成功 59ms |
| `hierarchy-mindmap-colorful-branch-capsule-item` | `lists` | 成功 58ms |

耗時固定在 10.0 秒（10013／10007／10007ms），且**連單一節點 n=1 亦然**——不是複雜度問題，是根本不會完成。

### 合法資料鍵僅五種

依 276 模板全量統計：`lists`(141)、`sequences`(83)、`compares`(23)、`nodes`(18)、`values`(11)。**`children` 不是合法鍵**，儘管 hierarchy 家族的語意會讓人直覺想用它。

### 方法論教訓（值得記住）

初次全量調查曾得出「77 個模板（27.9%）timeout、hierarchy 家族大規模失效」的結論。**該結論錯誤**，成因是調查腳本自身的測量偏差——為加速而加入「timeout 即不再重試其他資料鍵」的優化，導致 hierarchy 模板在第一個猜測鍵（`children`）timeout 後即放棄，永遠試不到正確的 `lists`。修正後重測為 **276/276 全數成功**。

這與[附錄的失效檢查方法](#附錄失效的檢查方法)屬同類問題：**工具本身製造的假象**。驗證工具時，務必先用「已知會失敗的輸入」確認它抓得到，再信任它的通過結果。

---

## 5. 29% 模板靜默丟棄 desc

### 現象
提供了 `desc`，圖看起來完整（title 與 label 都在），但描述文字從未出現，且無任何錯誤訊息。

### 統計
276 個模板中 **196 個（71.0%）支援 desc、80 個（29.0%）靜默丟棄**。

丟棄最多的家族：

| 家族 | 丟棄數 |
|---|---|
| hierarchy-tree | 20 |
| compare-binary | 12 |
| sequence-interaction | 9 |
| hierarchy-mindmap | 6 |
| compare-hierarchy / relation-dagre | 各 4 |

完整清單查 `assets/template-registry.json` 的 `supports_desc` 欄位。

### 為何肉眼難以察覺
圖的視覺結構是完整的——卡片、連線、icon、標題、標籤都在。缺的只是描述文字，而觀看者通常不會逐一比對輸入資料。實際案例：一批展示圖經人工確認「都符合」，後來驗證器才發現其中三張分別丟棄了 5／3／4 筆 desc。

### 判別方法
`validate-input.mjs` 會在渲染前發出警示並記入 `manifest.json` 的 `warnings`。

---

## 6. 縮字至不可讀但不溢出

### 現象
圖產出成功、文字沒有溢出、QA 全綠，但字級只有 8px——簡報投影時完全無法閱讀。

### 根因
recipe route 的字級自動貼合為避免溢出會持續縮小字級。此機制確實防住了溢出（實測 0.0px），
但沒有下限保護時會一路縮到不可讀。

### 為何是盲區
- `textOverflow` 檢查只吃 **engine route** 的 foreignObject 統計，recipe route 不適用
- 字級縮小**不算溢出**，既有檢查都不會觸發
- recipe 雖會 `console.warn`，但該訊息**不進 manifest**，批次產圖時完全錯過

### 判別方法
`checkTextLegibility()` 直接掃 SVG 的 `font-size` 屬性，結果進 manifest。

### 門檻為何依 route 而異

抽樣 30 個 engine 模板發現 **6 個（20%）原生就使用 10px 字級**——那是模板的設計選擇，
非縮字病徵。若兩條 route 套用同一門檻，engine route 會有約 20% 誤報，
**使用者很快就會學會忽略這道檢查，反而讓它失去作用**。故：

| route | 門檻 | 理由 |
|---|---|---|
| recipe | 11px | 字級由本技能控制，低於此值代表內容量超出版面容納能力 |
| engine | 10px | 尊重模板既有設計，只攔明顯異常 |

驗證：極長文字案例正確判 FAIL（8px、9.5px）；engine route 抽樣 25 個模板 PASS 25、FAIL 0，
其中 5 個原生 10px 者正確放行。

> **通則**：加閘門時要同時量測誤報率。一道會頻繁誤報的檢查，比沒有檢查更糟——
> 它會訓練使用者忽略警告。

---

## 附錄：失效的檢查方法

以下方法**曾被採用並證實無效**，不要重蹈：

### `checkMissingGlyphs()`（只掃替代字元）
掃 SVG 原始碼有無 U+FFFD／□ 等替代字元。但 NO GLYPH 是「字型缺 glyph」而非「字串內容有問題」，**SVG 原始碼永遠是乾淨的**，此檢查對該類問題永遠回報 pass。

### PNG 像素啟發式偵測
試圖用「深色矩形＋內部白色線條」的視覺特徵掃描 NO GLYPH 方框。門檻難以校準——實測對**整片都是 NO GLYPH 方框的圖仍回報 pass**（因方框內含白色文字，深色連通區的填充率達不到 0.85 門檻）。

### 正確的作法：確定性檢查
`check-font-coverage.py` 模擬 cairo 的字型選擇（取堆疊中第一個可解析的實體字型），用 fontTools 讀該字型 cmap 逐字比對，於**轉檔前**100% 確定哪些字會落到 `.notdef`。零偽陽性、零偽陰性。

**通則**：能用確定性檢查就不要用啟發式。啟發式的門檻在你沒見過的輸入上會失效，而你不會知道。

---

## 附錄：模板容量參考

### desc 安全字數上限（純中文，保守估計）

以真實字型 advance width 推算，超過則文字高度會溢出容器：

| 家族（代表模板） | n=3 | n=5 | n=8 |
|---|---|---|---|
| list-grid-badge-card | 32 | 32 | 32 |
| list-row | 28 | 28 | 28 |
| sequence-steps | 28 | 28 | 28 |
| sequence-funnel-simple | 20 | 20 | 20 |
| sequence-roadmap | 15 | 17 | 18 |

> 註：此表量測時未使用完整模板名，可能受第 3 節的 fallback 影響，建議重測後再作為嚴格依據。其餘家族未測。

### 溢出行為

批次量測 1062 個 foreignObject（12 家族 × 項目數 3/5/8 × 文字長度短/中/長）：

| 文字長度 | 高度溢出率 | 最大溢出倍率 |
|---|---|---|
| 短標籤 | 0.0% | 1.00x |
| 中等 | 0.0% | 1.00x |
| 長句 | **41.5%** | 1.98x |

**溢出屬於「輸入文字量超出模板設計容量」，非渲染缺陷。** 引擎對 foreignObject 同時設定 `overflow="visible"`，設計上允許文字超出框顯示，故文字不會被裁切或遺失，但過度溢出會壓到相鄰元件。短／中長度 0% 溢出，證明模板對合理長度容量充足。

### slot 長寬比對照

| slot | 尺寸（inch） | 目標長寬比 |
|---|---|---|
| full | 12.57 × 5.45 | 2.306 |
| full-tw | 12.57 × 4.78 | 2.630 |
| half | 6.16 × 4.78 | 1.289 |
| quad | 6.16 × 2.09 | 2.947 |
| twocol | 6.11 × 5.18 | 1.180 |

長寬比偏差門檻 0.25。engine route 的版面無法調整，`aspect` FAIL 時依 `recommendedSlot` 換 slot 即可。曾見長寬比 4.345 的模板，超出所有 slot 容許範圍（最接近的 quad 仍偏差 0.478），只能換模板或拆分內容。
