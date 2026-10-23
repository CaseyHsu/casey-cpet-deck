# CPET-YS Lai Lab 模板 — 進階 XML 手冊

以下內容供 **build_deck.py 無法涵蓋的特殊版面** 使用（需手動編輯 slide XML 時參考）。一般情況一律優先使用 scripts/build_deck.py。

---

## 三種投影片版型

### 版型 1：封面投影片（標題投影片）
- Layout：`slideLayout1.xml`（名稱：標題投影片）
- CPET Logo 與機構名稱由 layout 固定提供（上半部）
- **封面標題與報告者資訊必須填入 slide XML 的兩個 placeholder，置中顯示於投影片中央**
- 參考：`assets/template.pptx` 第 1 張

#### 封面 Placeholder 規格

| Placeholder | idx | 位置 (x, y) | 尺寸 (cx, cy) | 用途 |
|---|---|---|---|---|
| 主標題區 | 13 | 2189566, 1970838 | 7812868, 2916324 | 英文主標題 + 中文副標題（各一行），置中，藍色粗體 |
| 報告者資訊區 | 14 | 2459559, 5409220 | 7272882, 828092 | 報告人 + 指導教授 / 機構名稱，置中 |

#### 封面主標題 XML 範本（idx=13，英文標題 + 中文副標題）

```xml
<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="5" name="主標題"/>
    <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
    <p:nvPr><p:ph type="body" sz="quarter" idx="13"/></p:nvPr>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="2189566" y="1970838"/><a:ext cx="7812868" cy="2916324"/></a:xfrm>
  </p:spPr>
  <p:txBody>
    <a:bodyPr anchor="ctr"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <!-- 英文主標題（大字、藍色、粗體） -->
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r>
        <a:rPr lang="en-US" altLang="zh-TW" sz="4400" b="1" dirty="0">
          <a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>
          <a:latin typeface="Times New Roman"/>
          <a:ea typeface="標楷體"/>
        </a:rPr>
        <a:t>英文主標題</a:t>
      </a:r>
    </a:p>
    <!-- 中文副標題（稍小、藍色、粗體） -->
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r>
        <a:rPr lang="zh-TW" altLang="en-US" sz="3200" b="1" dirty="0">
          <a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>
          <a:latin typeface="Times New Roman"/>
          <a:ea typeface="標楷體"/>
        </a:rPr>
        <a:t>中文副標題</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>
```

#### 封面報告者資訊 XML 範本（idx=14）

```xml
<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="6" name="報告者資訊"/>
    <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
    <p:nvPr><p:ph type="body" sz="quarter" idx="14"/></p:nvPr>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="2459559" y="5409220"/><a:ext cx="7272882" cy="828092"/></a:xfrm>
  </p:spPr>
  <p:txBody>
    <a:bodyPr><a:normAutofit/></a:bodyPr>
    <a:lstStyle/>
    <!-- 第一行：報告人 + 指導教授 -->
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r>
        <a:rPr lang="zh-TW" altLang="en-US" sz="2400" b="1" dirty="0">
          <a:latin typeface="Arial"/>
          <a:ea typeface="微軟正黑體"/>
        </a:rPr>
        <a:t>報告人：姓名　　指導教授：Y.S. Lai</a:t>
      </a:r>
    </a:p>
    <!-- 第二行：單位名稱 -->
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r>
        <a:rPr lang="en-US" altLang="zh-TW" sz="2000" b="0" dirty="0">
          <a:latin typeface="Arial"/>
          <a:ea typeface="微軟正黑體"/>
        </a:rPr>
        <a:t>CPET – Center for Power Electronics Technology</a:t>
      </a:r>
    </a:p>
    <!-- 第三行：學校名稱 -->
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r>
        <a:rPr lang="en-US" altLang="zh-TW" sz="2000" b="0" dirty="0">
          <a:latin typeface="Arial"/>
          <a:ea typeface="微軟正黑體"/>
        </a:rPr>
        <a:t>National Taipei University of Technology</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>
```

> **重要**：封面 slide XML 必須同時包含 idx=13 與 idx=14 兩個 `<p:sp>`，才能讓標題與報告者資訊正確顯示在投影片中央。原始空白封面只有空的 placeholder，必須填入實際內容。

### 版型 2：摘要 / 條列式投影片（Summary / Outline style）
- Layout：`slideLayout2.xml`（名稱：標題及物件）
- 頂部置中主標題：`sz="4000"` Bold，色碼 `#0000FF`
- 左側對齊條列項目：`sz="2800"`，使用 `➤` 箭頭符號（`&#x27A4;` 或直接用 `➤`）
- 強調項目以 Bold 顯示，非強調項目維持 Regular
- 參考：`assets/template.pptx` 第 2、3 張

### 版型 3：內容投影片（一般標題 + 內容區）
- Layout：`slideLayout3.xml`（名稱：自訂版面配置）
- 頂部置中主標題：`sz="4000"` Bold，色碼 `#0000FF`
- 內容區域供自由排版（圖表、表格、圖片等）
- 參考：`assets/template.pptx` 第 4 張

---

## XML 複製規則

**新增投影片時，必須：**

1. 以既有的 `slide2.xml` 或 `slide3.xml` 為基礎複製
2. 更新 `_rels/` 中對應的 `.rels` 檔，確保 layout 關係正確
3. 在 `presentation.xml` 的 `<p:sldIdLst>` 中新增投影片 ID（遞增）
4. 新 slide 的 ID 格式：`<p:sldId id="XXX" r:id="rIdX"/>`，ID 從 257 以後遞增

**版位處理原則：**

- **多餘版位必須整個刪除**，不可只清空文字。若某個 `<p:sp>` placeholder 的內容在當前投影片用不到（例如無團隊成員欄位、無副標題），直接從 XML 中移除整個 `<p:sp>` 區塊。保留空文字框會造成版面殘留空白區域，影響排版品質。
- **文字過長時須啟用自動縮小**，避免文字爆出框外。在對應 `<a:bodyPr>` 中使用 `<a:normAutofit/>` 讓 PowerPoint 自動縮放；若字數明顯超過版型設計上限，應主動縮減字級（調低 `sz` 值）而非任其溢出。

**標題文字 XML 範本：**
```xml
<a:r>
  <a:rPr lang="en-US" altLang="zh-TW" sz="4000" b="1" kern="0" dirty="0">
    <a:solidFill>
      <a:srgbClr val="0000FF"/>
    </a:solidFill>
    <a:latin typeface="Times New Roman"/>
    <a:ea typeface="標楷體"/>
  </a:rPr>
  <a:t>標題文字</a:t>
</a:r>
```

**內文條列項目 XML 範本（含字型）：**
```xml
<a:p>
  <a:pPr marL="342900" indent="-342900">
    <a:buFont typeface="Arial" charset="0"/>
    <a:buChar char="➤"/>
  </a:pPr>
  <a:r>
    <a:rPr lang="en-US" altLang="zh-TW" sz="2800" dirty="0">
      <a:latin typeface="Arial"/>
      <a:ea typeface="微軟正黑體"/>
    </a:rPr>
    <a:t>項目文字</a:t>
  </a:r>
</a:p>
```

---

