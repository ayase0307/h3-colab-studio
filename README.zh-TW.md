<p align="center">
  <img src="assets/banner.png" alt="H3 Colab Studio：真實渲染的動畫戰鬥畫面，兩位機械格鬥家、爆炸與拳頭特寫" width="100%">
</p>

<h1 align="center">h3-colab-studio</h1>

<p align="center">
  <b>把 Colab Pro 的 A100 變成 agent 能呼叫的 MiniMax H3 影片渲染服務。</b><br>
  先用 480p 打草稿、用 seed 抽卡，再出 720p 成品。只用參考圖、不開隧道，一個 Google Drive 資料夾就是 API。
</p>

<p align="center">
  <a href="README.md">English</a> · <b>繁體中文</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/code-MIT-blue.svg"></a>
  <img alt="Colab A100" src="https://img.shields.io/badge/Colab-A100%2040GB-F9AB00?logo=googlecolab&logoColor=white">
  <img alt="MiniMax H3" src="https://img.shields.io/badge/MiniMax-H3%20%2F%20FastH3%20Omni-ff5a36">
  <img alt="Agent skill" src="https://img.shields.io/badge/agent-skill-8A2BE2">
  <img alt="Tests" src="https://img.shields.io/badge/tests-5%20scripts%20passing-2ea44f">
  <img alt="Measured" src="https://img.shields.io/badge/%E5%AF%A6%E6%B8%AC-9%20%E6%94%AF%20%C2%B7%209.2%20CU-0a7">
</p>

---

## 成果展示

下面全部由這個儲存庫在一張 Colab A100 上，用兩張參考圖渲染：1280×720、24 fps、含音訊。GIF 是 24 fps 的片段（完整 720p MP4 在 [`assets/videos`](assets/videos)），每支都連到它的提示詞。

<table>
  <tr>
    <td align="center" width="50%">
      <img src="assets/gifs/scrapyard-5s.gif" alt="5 秒廢料場打鬥：兩人躍起、油桶爆開、電纜放電"><br>
      <b>5 秒</b> · 3 鏡 · <a href="assets/videos/scrapyard-5s-720p.mp4">MP4</a> · <a href="benchmarks/prompts/b5-scrapyard-5s.txt">提示詞</a><br>
      <sub>只顯示前 3.4 秒 · 這支實際 355 秒（冷啟動；暖機 133 秒 ¹）· 約 0.18 CU ³</sub>
    </td>
    <td align="center" width="50%">
      <img src="assets/gifs/scrapyard-10s.gif" alt="10 秒廢料場打鬥：貨櫃、橫跨巷道的鎖鏈與火焰"><br>
      <b>10 秒</b> · 5 鏡 · <a href="assets/videos/scrapyard-10s-720p.mp4">MP4</a> · <a href="benchmarks/prompts/b10-scrapyard-10s.txt">提示詞</a><br>
      <sub>378 秒 · 約 0.5 CU</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/gifs/scrapyard-15s.gif" alt="15 秒廢料場打鬥：貨櫃堆炸開，兩人被拋向空中"><br>
      <b>15 秒</b> · 6 鏡 · 五小節提示詞 1,525 字 · <a href="assets/videos/scrapyard-15s-720p.mp4">MP4</a> · <a href="benchmarks/prompts/b15-scrapyard-15s.txt">提示詞</a><br>
      <sub>681 秒 · 0.88 CU</sub>
    </td>
    <td align="center">
      <img src="assets/gifs/combat-part1.gif" alt="太空站貨艙混戰，30 秒戰鬥的第一段"><br>
      <b>30 秒戰鬥・第一段</b> · <a href="assets/videos/combat-30s-720p.mp4">30 秒 MP4</a> · <a href="benchmarks/prompts/a1-combat-part1-15s.txt">提示詞</a><br>
      <sub>h3-combat-impact 範例，15 秒 14 鏡 · 原始參考圖 · 715 秒（新虛擬機）</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/gifs/combat-part2.gif" alt="太空站貨艙混戰第二段：特寫與衝擊"><br>
      <b>30 秒戰鬥・第二段</b> · <a href="benchmarks/prompts/a2-combat-part2-15s.txt">提示詞</a><br>
      <sub>569 秒 · 動作能量 28.3（原流程 28.1）</sub>
    </td>
    <td align="center">
      <img src="assets/gifs/draft-vs-final.gif" alt="左：480p 草稿，右：720p 二次取樣"><br>
      <b>草稿（左）對二次取樣（右）</b><br>
      <sub>同一個 seed、同一批影格 · <a href="docs/benchmarks.md#3-the-30-second-combat-test-two-15-s-segments">數據</a></sub>
    </td>
  </tr>
</table>

Kai 與 Vex 的參考圖不放在這個儲存庫（設計沿用公開的 Seedance 範例，做法跟 [h3-combat-impact](https://github.com/ayase0307/h3-combat-impact) 一樣）。30 秒戰鬥片用的是原始兩張圖；廢料場那幾支用的是依提示詞角色文字生成的兩張圖。

## 為什麼做這個

- 你付費訂閱 Colab Pro、拿得到 A100，卻**沒有 API**，agent 沒辦法呼叫筆記本。
- Colab 條款禁止在執行階段對外提供服務，常見的「在儲存格裡開 ngrok」會讓帳號有被停權的風險。
- H3 需要長而有結構的提示詞與參考圖，而且要先抽幾次卡，才能決定出成品的那一次。

這個儲存庫是一本筆記本加上一個小型客戶端：agent 把工作丟進 Drive 資料夾，筆記本渲染，MP4 回到同一個資料夾。**沒有任何東西在對網際網路監聽。**

## 你會得到什麼

- **Colab A100 40 GB 兩條路**（INT8 主模型＋INT8 文字編碼器、fp16 影片 VAE、euler/simple）：
  - **快速：** Turbo 4 步，960×544，純文字。5 秒：冷 1分38秒／暖 31 秒；10 秒 1分20秒；15 秒 2分25秒。
  - **高清：** FastH3 Omni 8 步，1344×768（H3 原生）單次直出，需至少 1 張參考圖。5 秒：冷 4分56秒／暖 3分28秒；10 秒 7分11秒；15 秒在 40 GB 上顯存不足。
- **極致畫質後製：** 動漫臉部修復（5 秒片約 3.7 分）與 SeedVR2 3B/7B 放大到 1890×1080（臉部＋1080p 每 5 秒片約 11.6 分；40 GB 上 1080p 請控制在約 5 秒）。
- **最多 9 張參考圖**：「+ 新增參考圖」，對應 `<Picture 1>`…`<Picture 9>`（3 張、10 秒高清：8–10 分）。
- **以 Google Drive 為基礎的工作佇列（代理模式）。** 先放圖、最後放 JSON，改名認領，完成標記帶 MP4 大小，`running/` 當機自動退回。
- **命令列與 agent 技能**（`skills/h3-colab-studio`），寫明可選品質、長度、時間與 CU 花費（約 5.3 CU/小時）。
- **繁體中文的筆記本介面**，手動操作用，引擎相同。

舊模式（`omni_hd` 草稿＋精修、`ref4`、`ref2va_hd`、`ayase`）仍可執行但不建議，見 [docs/legacy.md](docs/legacy.md)。

<p align="center">
  <img src="assets/diagram-architecture.svg" alt="agent 把工作寫進 Drive 佇列；Colab A100 筆記本輪詢它，用 ComfyUI（只綁本機位址）渲染，再把 MP4 寫回" width="100%">
</p>

## A100 兩模式配置與實測（2026-10-24）

硬體：Colab **A100-SXM4-40GB**，分支 `fix/a100-quality`，約 **5.3 CU/小時**。第 ① 格（環境準備）約 4.5–5.3 分鐘。整批測試共用掉約 **3.1 CU**（334.44 → 331.34）。

| 路線 | 品質選項 | 輸出 | 模型 | 取樣 |
|---|---|---|---|---|
| **快速出片** | 極速 · Turbo 4 步（768p 調校） | 橫向 960×544，24 fps | INT8 主模型 + INT8 文字編碼器 + fp16 影片 VAE | euler / simple |
| **高清** | Omni · 參考圖生成（8 步） | 橫向・高解析度 1344×768，**單次直出**（不是 `omni_hd` 草稿＋精修） | INT8 主模型 + INT8 文字編碼器 + fp16 影片 VAE | euler / simple，cfg 1.0 |

<table>
  <tr>
    <td align="center" width="33%"><img src="assets/gifs/a100-fast-5s.gif" alt="快速出片 5 秒，960×544"><br><sub>快速出片 · 5 秒 · 960×544</sub></td>
    <td align="center" width="33%"><img src="assets/gifs/a100-hq-5s.gif" alt="高清 Omni 5 秒，九尾狐，1344×768"><br><sub>高清 Omni · 5 秒 · 1344×768</sub></td>
    <td align="center" width="33%"><img src="assets/gifs/a100-hq-10s.gif" alt="高清 Omni 10 秒，1344×768"><br><sub>高清 Omni · 10 秒 · 1344×768</sub></td>
  </tr>
</table>
<sub>GIF 為 480px、12 fps、取前段約 4 秒，畫質遠低於原始 MP4。</sub>

| 路線 | 長度 | 冷啟動（第一支） | 暖機後 | GPU RAM（Colab 面板） |
|---|---:|---:|---:|---:|
| 快速 · Turbo 4 步 960×544 | 5 秒 | 1 分 38 秒 | **31 秒** | 約 37–38 / 40 GB |
| 快速 · Turbo 4 步 960×544 | 10 秒 | – | 1 分 20 秒 | 約 36–38 / 40 GB |
| 快速 · Turbo 4 步 960×544 | 15 秒 | – | 2 分 25 秒 | 約 36–38 / 40 GB |
| 高清 · Omni 8 步 1344×768 | 5 秒 | 4 分 56 秒 | **3 分 28 秒** | 約 37.8 / 40 GB |
| 高清 · Omni 8 步 1344×768 | 10 秒 | – | 7 分 11 秒 | 約 36–38 / 40 GB |
| 高清 · Omni 8 步 1344×768 | 15 秒 | – | ❌ 失敗：約 10 分 37 秒後 Runtime died（GPU RAM 約 39.1 / 40 GB，推測 OOM） | – |
| 參考：Turbo 8 步 1344×768（純文字） | 5 秒 | 5 分 00 秒 | – | – |

<sub>GPU RAM 是任務剛結束時面板的讀數（含 PyTorch 快取），不是精確峰值。</sub>

注意事項：
- **高清 15 秒**在 40 GB 卡上會爆顯存：請改用 A100 80GB（可選「未量化」），或切成每段 ≤10 秒再接起來。
- A100 不支援 FP4，**不要選 NVFP4 文字編碼器**。

## 極致畫質後製（2026-10-24）

在 ① 勾選 `download_facerefine` 和／或 `download_seedvr2`，再用「極致畫質後製（生成後另跑）」或歷史紀錄的「後製」按鈕。輸出：`video_face.mp4`、`video_1080p.mp4`、`video_face_1080p.mp4`。

<p align="center"><img src="assets/gifs/ultra-face-1080p.gif" alt="HQ Omni 5 秒 + 臉部修復 + SeedVR2 1080p" width="480"><br><sub>HQ Omni 5 秒 → 臉部修復（動漫）→ SeedVR2 3B 1890×1080（前 5 秒，縮小）</sub></p>

| 工作（A100 40 GB） | 時間 | 輸出 |
|---|---:|---|
| HQ Omni 5 秒生成 | 328 秒 | 1344×768 |
| 臉部修復（動漫） | 228 秒 | 1344×768 |
| 臉部修復 + SeedVR2 3B INT8 1080p | 219 秒 + 462 秒（UI 共 11分37秒） | 1890×1080 |
| SeedVR2 7B FP16 1080p | 未記錄 | 1890×1080 |
| HQ Omni 10 秒（573 秒）+ 臉部 + 1080p | 臉部完成；**1080p 階段 runtime 崩潰** | - |

40 GB A100 上，1080p 後製請控制在約 5 秒的片段，或改用 80 GB GPU。

## 多張參考圖

按「+ 新增參考圖」最多可放 9 張，第 N 張對應提示詞裡的 `<Picture N>`（從 1 開始、連號）。用《反派擺爛指南》兩個鏡頭實測，各 3 張參考圖、HQ Omni 1344×768、10 秒，兩支合計約 2 CU：

<table><tr>
<td align="center" width="50%"><img src="assets/gifs/multiref-c14.gif" alt="C14 3 張參考圖"><br><sub>C14 · 3 張參考圖 · 9分53秒（冷啟動）</sub></td>
<td align="center" width="50%"><img src="assets/gifs/multiref-c06.gif" alt="C06 3 張參考圖"><br><sub>C06 · 3 張參考圖 · 8分10秒</sub></td>
</tr></table>

## 老實說的限制

- **二次取樣可能讓身份滑掉。** 有一支 15 秒影片（我生成的參考圖）裡，第二位格鬥家有大約一秒變成第一位的複製品，但草稿是對的。`--refine-steps 3` 在那支影片裡解決了（[證據](docs/benchmarks.md#identity-loss-at-the-end-of-part-1-with-my-generated-references-and-the-refine-3-fix)），但那只是一個樣本。
- **參考圖太弱或太像，格鬥家會合併。** 用我生成的參考圖時，草稿本身在一個碰撞鏡頭把兩人都畫成 Kai；原始參考圖就沒有。請用輪廓與顏色差異明顯的參考圖。
- **身份也可能在草稿階段就合併。** 5 秒那支的最後一鏡（廣角、兩人都很小），480p 草稿裡兩個人影就已經都畫成 Kai，二次取樣只是繼承它。上面的 GIF 在那一鏡之前就停了。粗略的紅色像素檢查在其他草稿也標出少數 Vex 偏少的秒數，但那可能只是沒有 Vex 的鏡頭，未經驗證。
- **30 秒的接點是剪接，不是延續。** 兩段獨立的 15 秒渲染：接縫檢查用原始參考圖是 WARN（周圍動作的 64%），用我生成的參考圖是 FAIL（24%）。
- **長提示詞沒有傷害，也沒有明顯幫助。** 四份提示詞最長 1,525 字、8,986 字元，都完整渲染（ComfyUI 的分詞器沒有截斷）；hosted API 的 7,000 字元上限，是它們只能在本機跑的原因。每格只有一個 seed，所以結論不確定。
- 每台新的 Colab 虛擬機都需要**真人點一次 Google Drive 授權**（OAuth 彈窗，任何 agent 都無法代點），外加 6–7 分鐘安裝。
- Colab 不保證給你 A100；G4（96 GB）與 H100 沒有量測。
- 模型權重受 **MiniMax 社群授權**約束（有地區限制）；輸出成品要先確認授權。

## 快速上手

**1. 筆記本。** 在 Colab 開啟 `notebook/MiniMax_H3_Studio.ipynb`（上傳或存進你的 Drive），執行階段類型選 **A100 GPU**。
執行儲存格 ①（兩個下載選項保持勾選），全新虛擬機約 6–7 分鐘。再執行儲存格 ②，點 Drive 授權對話框。若儲存格 ② 因 `mount failed` 停下，再執行一次。

**2. 客戶端。** 在有同步你 Drive 的電腦（Google Drive 桌面版），需要 Python 3.9＋ 與 ffmpeg：

```bash
python skills/h3-colab-studio/scripts/h3q.py status
python skills/h3-colab-studio/scripts/h3q.py submit shot01 --prompt-file prompt.txt --mode omni --size p480 --seconds 15 --seed 7 --ref kai.png --ref vex.png
python skills/h3-colab-studio/scripts/h3q.py wait shot01
python skills/h3-colab-studio/scripts/h3q.py verify shot01 --out results/
# 最終高清：Omni 單次直出 1344x768，10 秒
python skills/h3-colab-studio/scripts/h3q.py submit shot01 --prompt-file prompt.txt --mode omni --size native --seconds 10 --seed 7 --ref kai.png --ref vex.png
```

**3. 別讓它繼續扣點。** 一批做完就刪除 Colab 執行階段（它依執行時數計費，不是依工作數）。

**Agent 技能。** 把技能資料夾放到你的 agent 讀取技能的位置，例如 Claude Code：

```bash
cp -r skills/h3-colab-studio ~/.claude/skills/
```

搭配 [`h3-video-prompting`](https://github.com/ayase0307/h3-video-prompting)（寫什麼）與 [`h3-combat-impact`](https://github.com/ayase0307/h3-combat-impact)（打鬥、衝擊幀、鏡頭能量）效果最好。

## 儲存庫結構

```text
notebook/        MiniMax_H3_Studio.ipynb   Colab 筆記本（由 src/ 建置）
src/             h3_backend.py, ui.html    ComfyUI 圖形建構、佇列工作程式、繁中介面
tools/           build_notebook.py, make_gifs.py, make_banner.py, identity_probe.py
skills/          h3-colab-studio/          SKILL.md, scripts/h3q.py, references/
benchmarks/      prompts/, records/, collect.py, cu-log.jsonl, make_prompts.py
docs/            benchmarks.md, agent-protocol.md
tests/           run_all.py ＋ 5 個測試腳本（圖形接線、佇列工作程式、命令列）
assets/          橫幅、架構圖、GIF（24 fps）、截圖、720p MP4
```

改了 `src/` 之後重建筆記本：`python tools/build_notebook.py`。跑測試：`python tests/run_all.py`。

## 致謝與授權

- 程式與文件：MIT，見 [`LICENSE`](LICENSE)。
- 模型：[MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) 與 [FastH3 Omni](https://huggingface.co/FastVideo/FastH3-Omni-Comfy) 各依其授權；ComfyUI 釘在 `ce42de5f`（FastH3 Omni 的 PDD 支援需要它）。
- 30 秒戰鬥提示詞與量測工具來自 [h3-combat-impact](https://github.com/ayase0307/h3-combat-impact)；五小節提示詞格式來自 [h3-video-prompting](https://github.com/ayase0307/h3-video-prompting)。高動作提示詞參考的 Seedance 2.5 範例是公開的展示作品，這裡改寫成 H3 的格式。
