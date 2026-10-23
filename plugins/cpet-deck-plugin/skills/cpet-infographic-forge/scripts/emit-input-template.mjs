/**
 * emit-input-template.mjs — cpet-yslai-pptx 銜接契約核心
 *
 * 路徑A（正向）：文稿骨架含 {{figure-id}} 佔位 → 依 manifest 回填真實
 *   PNG 路徑 → 完整 input_template.md
 * 路徑B（反向）：僅有 manifest（無骨架）→ 自動生成可編輯骨架草稿，
 *   供 Chat 階段討論調整後，再走同一個回填邏輯定案
 *
 * 這是先前設計文件中「從未被執行過一次」的核心模組，此次補上並在
 * e2e-test.mjs 中實際跑通。
 */
import { readFileSync, writeFileSync } from 'fs';
import { pathToFileURL } from 'url';

/** 路徑A：骨架 {{id}} 佔位 → 依 manifest 回填真實路徑（PNG，非SVG，因pptx讀點陣圖） */
export function fillTemplate(skeletonMd, manifest) {
  const byId = new Map(manifest.figures.map((f) => [f.id, f]));
  const unresolvedIds = [];

  const filled = skeletonMd.replace(/\{\{([\w-]+)\}\}/g, (match, id) => {
    const fig = byId.get(id);
    if (!fig) {
      unresolvedIds.push(id);
      return match; // 保留原樣，讓後續檢查能抓到
    }
    // pptx 讀取的是 PNG（點陣圖），路徑同名但副檔名替換
    return fig.png || fig.svg.replace(/\.svg$/, '.png');
  });

  return { filled, unresolvedIds };
}

/** 路徑B：manifest → 自動生成可編輯骨架草稿（無骨架時的起點） */
export function draftOutline(manifest, { deckTitle = '未命名簡報' } = {}) {
  let md = `# ${deckTitle}\n\n<!-- 此為自動生成草稿，供 Chat 階段討論調整順序、合併版面、增刪內容後定案 -->\n\n`;

  for (const fig of manifest.figures) {
    md += `### [layout: figure] ${fig.caption || fig.id}\n`;
    const cap = fig.caption || `圖：${fig.id}`;
    const tw = fig.takeaway ? ` | takeaway: ${fig.takeaway}` : '';
    md += `[figure: {{${fig.id}}} | ${cap}${tw}]\n\n`;
  }

  return md;
}

// CLI 入口：支援 fill 與 draft 兩種模式
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [, , mode, manifestPath, skeletonPath] = process.argv;

  if (mode === 'draft') {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    const md = draftOutline(manifest);
    console.log(md);
  } else if (mode === 'fill') {
    if (!skeletonPath) {
      console.error('用法: node emit-input-template.mjs fill <manifest.json> <skeleton.md>');
      process.exit(1);
    }
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    const skeleton = readFileSync(skeletonPath, 'utf-8');
    const { filled, unresolvedIds } = fillTemplate(skeleton, manifest);
    if (unresolvedIds.length) {
      console.error('警告：以下 id 在 manifest 中找不到對應圖檔：', unresolvedIds);
    }
    console.log(filled);
  } else {
    console.error('用法: node emit-input-template.mjs <draft|fill> <manifest.json> [skeleton.md]');
    process.exit(1);
  }
}
