# H3 Colab 送件協定（給 agent 讀）

筆記本不開公網。agent 與 Colab 之間只透過 Google Drive 的 `h3-queue` 資料夾交換檔案。
Colab 端的「代理模式」cell 必須正在執行，agent 才拿得到結果。

## 資料夾（在 My Drive 根目錄，筆記本啟動時自動建立）

```
h3-queue/
  inbox/    agent 把工作單放這裡
  running/  筆記本認領後移到這裡（agent 不要碰）
  done/     <id>.json（完成標記）+ <id>.mp4 + <id>.settings.json
  failed/   <id>.json（含 error 訊息）
  heartbeat.json   筆記本每輪更新；每約 5 分鐘更新；alive_at 超過約 10 分鐘沒動 = 筆記本已停
  STOP      （選用）建立此檔可讓筆記本的代理迴圈結束
```

## 怎麼存取這個資料夾（優先順序）

1. **本機有 Google Drive 桌面版同步（這台電腦是 `G:\我的雲端硬碟`）：直接當一般檔案讀寫**，
   例如寫入 `G:\我的雲端硬碟\h3-queue\inbox\`、讀取 `...\done\`。mp4 幾 MB 到幾十 MB，這條路最穩。
2. 遠端 agent 才用 Google Drive MCP：只拿來丟小的 JSON / 圖片、查完成標記。**不要用 `download_file_content` 抓 mp4**
   （會把 base64 整包塞進對話，放不下）；改成回報檔案 ID 或連結，讓使用者或本機端取。

兩個方向的同步都是非同步的，檔案可能「先看到標記、後看到內容」，所以一律用下面的規則防呆。

## 送件（順序很重要）

1. 選一個 id：只能用英數、`-`、`_`，最長 64 字，必須唯一（例如 `clip-20261022-001`）。
2. 若有參考圖，**先**放到 `inbox/`：`<id>.first_frame.png`、`<id>.last_frame.png`（選用），
   並在工作單裡用 `"images": ["first_frame"]` 宣告。筆記本會等宣告的圖片都到齊才開始（最多等 10 分鐘，逾時算失敗），
   不會悄悄變成純文字生影片。
3. **最後**才放 `inbox/<id>.json`（筆記本只掃 .json）。

用 Drive MCP 的 `create_file` 時：`parentId` = inbox 資料夾 ID、`title` = `<id>.json`、
`contentMimeType` = `application/json`，**必須設 `disableConversionToGoogleType: true`**，否則會被轉成 Google 文件。
圖片用 `base64Content` + `image/png`。

## 工作單欄位

```json
{
  "prompt": "integrated_multimodal_description: ...\noverall_soundscape: ...\nnon_diegetic_music: N/A",
  "size": "landscape",
  "seconds": "5",
  "mode": "turbo",
  "seed": -1,
  "images": ["first_frame"]
}
```

| 欄位 | 值 |
|---|---|
| prompt | 必填，16000 字內 |
| size | `p480`(832x480，草稿) `p480v`(480x832) `landscape`(960x544) `portrait`(544x960) `square`(768x768) `native`(1344x768) |
| seconds | `"5"` `"8"` `"10"` `"15"` |
| mode | `omni_hd`（Omni 草稿加二次取樣，輸出 1280×720，至少 1 張參考圖；`size` 只能 `p480` 或 `p480v`，預設 `p480`；可選 `refine_steps` 2～6，預設 4）`ref4`（Ref2VA 4 步，參考圖專用）`turbo`（8 步，預設）`turbo4`（4 步，最快；LoRA 為 768p 調校，建議配 `native` 或 `square` 比較）`omni`（FastH3 Omni，8 步，參考圖生成，**至少 1 張參考圖**）`quality`（20 步起，品質優先）`ref2va`（官方非蒸餾 Ref2VA，單階段，參考圖專用）`ref2va_hd`（Ref2VA 草稿加尾段二次取樣，輸出 1280×720，參考圖專用） |
| steps | 只有 `quality` 有效：16 / 20 / 25 / 30。`ref2va` 與 `ref2va_hd`：12～30，預設 20 |
| refine_steps | 只有 `ref2va_hd` 用：2～12，預設 8，必須小於 `steps`（尾段取樣的步數）。`omni_hd` 的設定見上表 mode 列 |
| seed | -1 隨機，或 0–4294967295 |
| images | 宣告隨附的圖片：一般模式 `first_frame`、`last_frame`；`omni` 模式 `ref_1`…`ref_9`（依序對應提示詞裡的 `<Picture 1>`…`<Picture 9>`） |
| sampler | 選用：`res_multistep+simple`（預設）或 `euler+beta`。兩者實測畫質相近、速度相同，用預設即可 |

其他欄位一律忽略；LoRA 不能自選。

## 取件

1. 輪詢 `done/<id>.json`（每 30–60 秒一次）。出現後讀 `video_bytes`，
   **等 `done/<id>.mp4` 的檔案大小等於 `video_bytes` 才算完成**（同步可能先送標記）。
2. 同時輪詢 `failed/<id>.json`；有的話讀 `error` 欄位，修正後換新 id 重送。
3. 逾時判斷：`heartbeat.json` 約每 5 分鐘更新一次；`alive_at` 超過約 10 分鐘沒動，就表示筆記本已停。
4. 筆記本中斷（■ 或 Colab 斷線）時，執行中的工作會退回 `inbox/` 等下次啟動重跑，不需要重送。

## Omni 模式（FastH3 Omni 參考圖生成）

- 圖片檔 `<id>.ref_1.png`…`<id>.ref_9.png`，工作單 `"mode": "omni"`、`"images": ["ref_1","ref_2"]`。
- 提示詞用 `<Picture 1>`、`<Picture 2>` 引用對應的圖；`ref_N` 對應 `<Picture N>`，編號必須從 1 開始連續（跳號會被拒絕）。
- 目前只支援圖片參考；影片／音訊參考尚未接上。
- 模型已蒸餾成 8 步，不要再疊 turbo LoRA（筆記本也不會疊）。
- 需要 ① 勾選「download_omni」下載模型（INT8 約 +22GB），否則工作單會進 `failed/`。

## 草稿再精修（omni_hd）與完成後的檔案

- 一個工作內完成：Omni 8 步草稿（480p）→ 解碼、放大到 1280×736 → 用同一個模型只跑排程尾段的二次取樣 → 裁成 1280×720。
- 想「抽卡」：先用 `omni` 搭配 `size: p480` 與不同 seed 快速出草稿（`seconds` 可 5／10／15），挑到喜歡的 seed 後，用同一個 seed、同一份提示詞與參考圖改 `mode: omni_hd` 重跑；同 seed 的草稿是否完全重現，以實測為準（見測試結果）。
- `done/<id>.settings.json` 內有 `timeline`（每個節點開始的秒數）與 `min_vram_free_gib`（工作期間最低剩餘顯存），`omni_hd` 另有 `done/<id>.draft.mp4`（無聲的草稿，用來和精修後比對）。
