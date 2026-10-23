#!/usr/bin/env node
/**
 * forge.mjs — 批次渲染核心引擎
 *
 * 用法：node forge.mjs <figure-jobs.yaml> [--out <dir>]
 *
 * 讀取 figure-jobs.yaml → 依每張圖的 route 分派 engine（antv/infographic）
 * 或 recipe（手工骨架）路線 → 輸出 <id>.svg 至 output_dir → 產生 manifest.json
 *
 * 本檔案是先前設計文件中「宣稱存在」但從未真正寫出的核心模組，
 * 此次為 Batch A 完整度修正的一部分，端到端驗證見 e2e-test.mjs。
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import * as yaml from 'js-yaml';
import { renderToString } from '@antv/infographic/ssr';
import { validateFigure } from './validate-input.mjs';
import { resolveIcon } from './icon-resolve.mjs';
import { runRecipe } from './recipe-runner.mjs';
import { postprocess } from './postprocess.mjs';
import { evaluateFit } from './fit.mjs';
import { runQaGate, SLOT_AR } from './qa-gate.mjs';
import { svgToPng } from './svg-to-png.mjs';

const ASSETS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../assets');


/** 把 data 物件（JS object，來自 yaml.load）轉成 antv/infographic 語法字串 */
function toSyntaxBlock(obj, indent = 2) {
  const pad = ' '.repeat(indent);
  const lines = [];
  for (const [k, v] of Object.entries(obj)) {
    if (Array.isArray(v)) {
      lines.push(`${pad}${k}`);
      for (const item of v) {
        const sub = toSyntaxBlock(item, indent + 4).split('\n');
        lines.push(`${pad}  - ${sub[0].trim()}`);
        lines.push(...sub.slice(1));
      }
    } else if (v && typeof v === 'object') {
      lines.push(`${pad}${k}`);
      lines.push(toSyntaxBlock(v, indent + 2));
    } else {
      lines.push(`${pad}${k} ${v}`);
    }
  }
  return lines.join('\n');
}

/** 對 data 物件內所有 icon 欄位做語意解析（回填 ref:svg: 內聯字串） */
function resolveIconsDeep(obj) {
  if (Array.isArray(obj)) return obj.map(resolveIconsDeep);
  if (obj && typeof obj === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      out[k] = k === 'icon' && typeof v === 'string' ? resolveIcon(v) : resolveIconsDeep(v);
    }
    return out;
  }
  return obj;
}

async function renderEngine(fig, palette) {
  const dataResolved = resolveIconsDeep(fig.data);
  const dataBlock = toSyntaxBlock(dataResolved);
  const syntax = `infographic ${fig.template}\ndata\n${dataBlock}\ntheme\n  palette ${palette.join(' ')}`;
  const raw = await renderToString(syntax);
  return postprocess(raw);
}

export async function forge(jobPath, outDir) {
  const jobRaw = readFileSync(jobPath, 'utf-8');
  const job = yaml.load(jobRaw);
  const catalog = JSON.parse(readFileSync(`${ASSETS_DIR}/template-catalog.json`, 'utf-8'));
  const paletteYaml = yaml.load(readFileSync(`${ASSETS_DIR}/palette.yaml`, 'utf-8'));

  const resolvedOut = outDir || resolve(dirname(jobPath), job.meta?.output_dir || './figures');
  if (!existsSync(resolvedOut)) mkdirSync(resolvedOut, { recursive: true });

  const paletteName = job.meta?.palette || 'cpet-vivid';
  const paletteColors = (job.meta?.palette_override) ||
    paletteYaml[paletteName]?.colors?.map((c) => c.hex) ||
    ['#2E5AAC', '#6B4FA0', '#0E7C7B', '#2F8F5B', '#C0553A'];

  const manifest = { figures: [], unresolved_icons: [], errors: [], warnings: [] };

  for (const fig of job.figures || []) {
    try {
      // 【渲染前輸入驗證】必須發生在 renderToString 之前才有意義——
      // 不合法資料鍵會使 SSR hang 住 10 秒且不報錯，事後才發現已無法補救。
      const v = validateFigure(fig, ASSETS_DIR);
      if (v.warnings.length) {
        for (const w of v.warnings) {
          console.warn(`  [警示] ${fig.id}: ${w}`);
          manifest.warnings.push({ figure: fig.id, message: w });
        }
      }
      if (v.errors.length) {
        throw new Error(`輸入驗證未通過：\n    - ${v.errors.join('\n    - ')}`);
      }

      let result;
      if (fig.route === 'engine') {
        result = await renderEngine(fig, paletteColors);
      } else if (fig.route === 'recipe') {
        // 傳入目標 slot 的長寬比，讓 recipe 自行求解版面以貼合該 slot，
        // 避免固定版面在不同 slot／項目數下產生大量留白
        const rawSvg = await runRecipe(
          fig.recipe, resolveIconsDeep(fig.data), paletteColors, ASSETS_DIR,
          { targetAspect: SLOT_AR[fig.slot] }
        );
        result = postprocess(rawSvg);
      } else {
        throw new Error(`未知 route: ${fig.route}`);
      }

      const svgPath = `${resolvedOut}/${fig.id}.svg`;
      writeFileSync(svgPath, result.svg);
      const vbMatch = result.svg.match(/viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"/);
      const aspect = vbMatch ? +(vbMatch[1] / vbMatch[2]).toFixed(3) : null;

      // 依 slot + DPI 200 決定輸出解析度，轉 PNG（pptx 讀點陣圖，非 SVG）
      const arrayField = fig.data?.sequences || fig.data?.lists || fig.data?.nodes ||
        fig.data?.compares || fig.data?.values || fig.data?.children || [];
      const itemCount = Array.isArray(arrayField) ? arrayField.length : null;
      const fitResult = fig.slot
        ? evaluateFit(aspect, fig.slot, fig.template || fig.recipe, itemCount)
        : null;
      const pngPath = `${resolvedOut}/${fig.id}.png`;
      const res = fitResult?.resolution;
      // SVG→PNG 由 svg-to-png.mjs（playwright 驅動既有 Edge／Chrome）負責；
      // 原 cairosvg 路徑因 libcairo 原生函式庫缺席與 Windows 路徑轉義問題已汰換，
      // 理由詳見該模組檔頭註解。
      await svgToPng(svgPath, pngPath, res ? { width: res.width, height: res.height } : {});

      const qa = await runQaGate({
        svgString: result.svg,
        svgPath,
        pngPath,
        aspect,
        slot: fig.slot,
        threshold: fig.fit?.allow_deviation ?? 0.25,
        foreignObjectStats: result.foreignObject,
        route: fig.route,
      });

      manifest.figures.push({
        id: fig.id,
        svg: svgPath,
        png: pngPath,
        aspect,
        slot: fig.slot || null,
        caption: fig.caption || null,
        takeaway: fig.takeaway || null,
        route: fig.route,
        template_or_recipe: fig.template || fig.recipe,
        qa,
      });
    } catch (e) {
      manifest.errors.push({ id: fig.id, message: e.message });
    }
  }

  const manifestPath = `${resolvedOut}/manifest.json`;
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  return { manifest, manifestPath };
}

// CLI 入口
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const jobPath = process.argv[2];
  if (!jobPath) {
    console.error('用法: node forge.mjs <figure-jobs.yaml>');
    process.exit(1);
  }
  const { manifest, manifestPath } = await forge(jobPath);
  console.log(`完成：${manifest.figures.length} 張成功，${manifest.errors.length} 張失敗`);
  if (manifest.errors.length) console.log('失敗清單：', manifest.errors);
  console.log('manifest:', manifestPath);
}
