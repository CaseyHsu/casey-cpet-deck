/**
 * safe-write.mjs — 因應 cpet-yslai-pptx/MAINTENANCE.md §5 記載之
 * Cowork 掛載點大檔寫入偶發尾端截斷風險（SKILL.md 曾三次尾段損毀）。
 *
 * 紀律：一律先寫系統暫存目錄 → cp 到目標路徑 → md5 比對 → 不符則重試。
 *
 * 2026-09-20：暫存路徑原本寫死 `/tmp/...`。該路徑在 Linux／macOS 正確，但在
 * Windows 原生 Node 上會被 path 解析成「目前磁碟機根目錄 + 	mp」（實測在 I:
 * 磁碟下為 `I:	mp`），該目錄不存在，writeFileSync 直接以 ENOENT 失敗——而本
 * 模組正是為了防資料截斷而存在，它自己失敗等於防線失效。改用 os.tmpdir()
 * 取得各平台正確的暫存目錄。同時補上 finally 清除暫存檔（原本從未刪除，
 * 每次寫入都會遺留一個檔案）。
 */
import { writeFileSync, copyFileSync, readFileSync, mkdirSync, unlinkSync } from 'fs';
import { createHash } from 'crypto';
import { dirname, join } from 'path';
import { tmpdir } from 'os';

function md5(buf) {
  return createHash('md5').update(buf).digest('hex');
}

export function safeWrite(targetPath, content, { maxRetries = 3 } = {}) {
  const tmpPath = join(tmpdir(), `safe-write-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const buf = Buffer.isBuffer(content) ? content : Buffer.from(content);

  try {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      writeFileSync(tmpPath, buf);
      const tmpMd5 = md5(readFileSync(tmpPath));

      mkdirSync(dirname(targetPath), { recursive: true });
      copyFileSync(tmpPath, targetPath);
      const targetMd5 = md5(readFileSync(targetPath));

      if (tmpMd5 === targetMd5) {
        return { success: true, attempts: attempt, md5: targetMd5 };
      }
      // 不符，下一輪重試
    }
    return { success: false, attempts: maxRetries };
  } finally {
    try { unlinkSync(tmpPath); } catch { /* 暫存檔可能未建立或已被清除，忽略 */ }
  }
}
