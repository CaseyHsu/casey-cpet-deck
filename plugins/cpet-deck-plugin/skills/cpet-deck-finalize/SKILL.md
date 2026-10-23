---
name: cpet-deck-finalize
description: CPET／YS Lai Lab 簡報「定稿後」的維護工具——簡報已經在 PowerPoint 裡手動微調過（改位置、換配色、插 IguanaTeX 公式），不能再從 plan.json 或 build 腳本重建時使用：寫入前檢查檔案有沒有被手動改過或正開在 PowerPoint、改前自動快照到 99_封存、寫入點擊動畫（出現／消失）、由動畫版產生無動畫版、把講稿寫進備忘錄、追蹤哪些衍生版本過期。使用者說「定稿後要改一頁」「幫我加動畫」「動畫照講稿點擊分組」「產生無動畫版／上傳版」「把講稿寫進備忘錄」「Final 被我手動改過了」「這幾個版本要同步」「改之前先備份」，或要直接修改一份已交付、含動畫或手動調整的實驗室簡報 pptx 時，一定要使用本技能，不要直接用 python-pptx 覆寫檔案。不適用：從零建立簡報或大改版面（用 cpet-yslai-pptx）、還沒有 input_template（用 cpet-input-template）、撰寫講稿或估算試講時間（用 cpet-talk-prep）。
---

# CPET Deck Finalize（v1.0 — pptx 主檔期工具）

簡報一旦經過 PowerPoint 手動微調，主檔就從 plan.json 變成 pptx 本身：重跑建置腳本會蓋掉那些手改。
從這一刻起，每次修改都面對同一組風險，本技能把它們變成可檢查的步驟：

| 風險 | 處置 |
|---|---|
| 寫入前檔案已被手動微調，覆寫會吃掉 | `deck_guard.py check` 逐頁列出改了哪個形狀（文字／位移／格式） |
| 檔案正開在 PowerPoint | `check` 回 3（LOCKED）→ 停下請使用者關檔，**不要另存他名**（之後還得手動合併） |
| 改前要備份 | `deck_guard.py snapshot` 自動命名封存夾並產生 README |
| 動畫退場失效 | `anim.py` 讓同一形狀的每個效果用不同 grpId；`check` 會抓出共用 |
| 無動畫版要從動畫版重做 | `derive.py noanim`（移除動畫與 `EntryPrompt*` 進頁提示框） |
| 衍生版本忘了重產 | `deck_guard.py stale` |

## 主檔切換

1. plan.json／build 腳本是主檔，直到**第一次**有人在 PowerPoint 手動修改並決定保留。
2. 切換時登錄：`deck_guard.py register <deck> --manifest deck_manifest.json --note "主檔切換"`，
   並在專案的決策紀錄記一筆。之後 cpet-yslai-pptx 只用來產生**新頁**，再手動貼入主檔。
3. `deck_manifest.json` 放在 deck 旁邊，取代手寫的 md5 版本表（它的 `history` 就是版本表）。

## 每次寫入主檔的固定流程

```
check ──0──▶ snapshot ──▶ 修改 ──▶ register ──▶ 重產衍生檔 ──▶ register --role derived --from 主檔
  │1  向使用者列出被手改的地方；使用者確認保留 → register 接受，再從 check 重來
  │3  檔案鎖定：請使用者關檔後重跑，不要另存
```

修改本身只動必要的投影片與物件；動完用 `derive.py verify-noanim` 或 `anim.py check` 確認沒有連帶改到別處。

## 工具（`<skill_path>/scripts/`，依賴 `python-pptx`、`lxml`）

| 指令 | 作用 | 回傳碼 |
|---|---|---|
| `deck_guard.py check <deck> --manifest M` | 與上次登錄比對 | 0 未變／1 有變（印逐頁差異）／2 未登錄／3 鎖定 |
| `deck_guard.py register <deck> --manifest M [--role derived --from MASTER] [--note …]` | 登錄目前狀態 | 0 |
| `deck_guard.py snapshot <deck> --archive <封存根目錄> --action <slug> [--reason …]` | 改前快照到 `<日期>_before_<slug>/` | 0 |
| `deck_guard.py stale --manifest M` | 列出過期的衍生檔 | 0／1 |
| `anim.py extract <deck> spec.json` | 把現有動畫讀成點擊分組 | 0 |
| `anim.py inject <deck> spec.json <out>` | 依分組寫入動畫並自我檢查 | 0／1 |
| `anim.py check <deck>` | 每頁點擊數＋grpId 檢查 | 0／1 |
| `derive.py noanim <final> <out> [--drop-prefix EntryPrompt]` | 產生無動畫版 | 0 |
| `derive.py verify-noanim <final> <noanim>` | 既有無動畫版是否仍與動畫版一致 | 0／1 |
| `derive.py notes <deck> notes.json <out>` | 寫入備忘錄 | 0／1（有頁被跳過） |

輸出一律寫到新檔，確認無誤後才取代原檔；取代後立刻 `register`。

### 動畫 spec

```json
{"slides": {"9": [
  [{"shape": "EntryPrompt2", "effect": "appear"}],
  [{"shape": "EntryPrompt", "effect": "exit"}, {"shape": "EntryPrompt2", "effect": "exit"},
   {"shape": "Picture 5", "effect": "appear"}]
]}}
```

- 每個內層陣列是一次點擊：第一個效果「按一下時」，其餘「與前一個同時」。
- 只用「出現／消失」、不設轉場：動畫的用途是提詞——按下去出現什麼，就講什麼。
- 卡片的框、標題、內文放在同一次點擊；結論橫條放在該頁最後一次點擊。
- 形狀名稱不唯一時改用 `"spid"`（用 `extract` 看現有編號）。
- 進頁就顯示、第一下才消失的提示框，命名為 `EntryPrompt*`，無動畫版會自動移除它們。

### 備忘錄 notes.json

`{"<投影片序號>": "第一段\n第二段"}`。行內 `**粗體**`；`__the__` 會變成藍色加底線，用來提醒「這個 the 要唸 thee」。
沒有備忘錄頁的投影片會被跳過並回報——先在 PowerPoint 點一下該頁的備忘錄窗格建立它。

## 驗收

- 動畫：`anim.py check` 0 問題，每頁點擊數與講稿的 `[n]` 標記一致；**請使用者在 PowerPoint 從頭按一次**
  （LibreOffice 能開檔不代表 PowerPoint 的動畫行為正確）。
- 無動畫版：`derive.py verify-noanim` 回 0。
- schema：用 cpet-yslai-pptx 的 `schema_check.py`，必須回 0。

## 已知限制

- 不新增備忘錄頁；動畫只支援出現／消失（其他效果 `extract` 會警告並降級）。
- 鎖定偵測靠 `~$檔名` 與寫入開檔測試；網路磁碟上的鎖可能偵測不到。
