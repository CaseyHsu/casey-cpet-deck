# Third-Party Notices

本 repo 以 MIT License 釋出（見 [LICENSE](LICENSE)），但以下內容的權利屬各自的權利人，依其原授權條款提供。

## Lucide icons

- 位置：`plugins/cpet-deck-plugin/skills/cpet-infographic-forge/assets/icons/*.svg`
- 來源：lucide-static（每個 SVG 檔頭保留 `@license lucide-static … - ISC` 註記）
- 授權：ISC License；部分圖示源自 Feather，為 MIT License

```text
ISC License

Copyright (c) 2026 Lucide Icons and Contributors

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

Icons derived from the Feather project:

```text
The MIT License (MIT)

Copyright (c) 2013-present Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Office Open XML schemas

- 位置：`plugins/cpet-deck-plugin/skills/cpet-yslai-pptx/scripts/office/schemas/ISO-IEC29500-4_2016/`
- 內容：ISO/IEC 29500-4:2016（Office Open XML，Transitional）的 XML schema 檔
- 用途：`schema_check.py` 在本機驗證產出的 `.pptx`，不修改其定義
- 權利：屬 ISO/IEC 與 Ecma International（ECMA-376）。不在本 repo 的 MIT 授權範圍內。

## 標誌

`plugins/cpet-deck-plugin/skills/cpet-yslai-pptx/assets/template.pptx` 內含國立臺北科技大學（Taipei Tech）與
Center for Power Electronics Technology（CPET）的標誌。權利屬原所有者，不在本 repo 的 MIT 授權範圍內。

## 未隨本 repo 散佈的相依套件

`cpet-infographic-forge` 的 npm 套件（如 `@antv/infographic`、`playwright`、`lucide-static`）與各技能的 Python 套件
（如 `python-pptx`、`lxml`、`matplotlib`、`scipy`）由使用者自行安裝，依各套件自己的授權條款使用。
