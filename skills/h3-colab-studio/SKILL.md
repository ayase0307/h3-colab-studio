---
name: h3-colab-studio
description: Use when generating MiniMax H3 / FastH3 Omni videos on the user's Google Colab A100 via ayase0307/h3-colab-studio - choosing quality mode, duration, post-processing (face refine, SeedVR2 1080p), multi-reference images, estimating render time and Colab compute units (CU), and driving the notebook either through the web UI or the Drive job queue (agent mode). Triggers: Colab, A100, H3, Omni, 運算單元, 出片, 1080p, 臉部修復, 多參考圖, h3-queue, h3q.
---

# H3 Colab Studio

## Notebooks
- main (stable fast/HQ): https://colab.research.google.com/github/ayase0307/h3-colab-studio/blob/main/notebook/MiniMax_H3_Studio.ipynb
- feat/ultra-quality (adds face refine, SeedVR2 1080p, up to 9 refs in UI): https://colab.research.google.com/github/ayase0307/h3-colab-studio/blob/feat/ultra-quality/notebook/MiniMax_H3_Studio.ipynb

Runtime: A100 (A100-SXM4-40GB; H100 usually unavailable), High-RAM on. Cost ~5.3 CU/hour (Google AI Pro balance). Cell ① setup ~4.5-5.3 min on a fresh VM.

## Cell ① options
- Model profile INT8 + INT8 text encoder. Never NVFP4 on A100 (no FP4 support).
- `download_omni` - required for HQ / multi-reference.
- `download_facerefine` - face refine pass (anime detector).
- `download_seedvr2` - SeedVR2 1080p upscaler (3B INT8 recommended, 7B FP16 optional).
Pipeline defaults: fp16 video VAE, euler/simple, native single pass (do not use omni_hd draft+refine for finals: it caused blur/ghosting).

## Quality modes
| Mode | Setting | Resolution | Needs |
|---|---|---|---|
| Fast | 極速 Turbo 4-step, landscape | 960x544 | text only |
| HQ | Omni 8-step, 橫向・高解析度, single pass | 1344x768 (H3 native max) | >=1 reference image |

## Measured times (A100 40 GB)
| Path | 5 s cold | 5 s warm | 10 s | 15 s |
|---|---:|---:|---:|---:|
| Fast | 1m38s | 31s | 1m20s | 2m25s |
| HQ | 4m56s | 3m28s | 7m11s | FAILS (OOM, runtime dies) |

Multi-reference HQ (3 refs, 10 s, 1344x768): 9m53s cold, 8m10s next.

Post-process on a 5 s HQ clip (feat/ultra-quality, 「極致畫質後製」 or history 「後製」):
- Face refine: ~3.7 min (219-228 s) -> video_face.mp4, 1344x768
- SeedVR2 3B 1080p after face: +462 s (total ~11.6 min) -> video_face_1080p.mp4, 1890x1080
- 10 s clip + 1080p pass: runtime died. Keep 1080p to <=5 s clips or use an 80 GB GPU.

## Multi-reference
Click 「+ 新增參考圖」 (up to 9). Image N = `<Picture N>` in the prompt; numbering from 1, contiguous. Use visually distinct references.

## Planning rules
- Max per clip on 40 GB: Fast 15 s, HQ 10 s, HQ+1080p 5 s. Longer scenes: split into segments.
- Budget: CU ≈ wall-clock hours x 5.3 (including ~5 min setup).
- Batch jobs in one session to reuse the warm model.
- ALWAYS finish with Runtime > Disconnect and delete runtime, or CUs keep draining.

## Two ways to drive it
1. UI mode: open notebook, run cells, use the in-notebook panel, download with 「儲存 MP4」. Needs the user's Google account signed in to the browser.
2. Agent (queue) mode: no public tunnel. Run the notebook's agent-mode cell; it polls Google Drive `My Drive/h3-queue/{inbox,running,done,failed}` + heartbeat.json. Submit with `skills/h3-colab-studio/scripts/h3q.py` (or write `<id>.json` + `<id>.ref_N.png` into inbox, images first, JSON last). Spec: docs/agent-protocol.md.
   Manual authorization: the user must start the notebook on an A100 and click the Google Drive mount OAuth popup (google.colab drive.mount) - an agent cannot click it. Agent side needs access to the same Drive (Drive desktop sync folder or Drive connector). `h3q.py status` STALE = notebook not running. Create `h3-queue/STOP` to end the loop. Then still disconnect & delete the runtime.

## Queue CLI (run from skills/h3-colab-studio/)
```bash
python scripts/h3q.py status                      # ALIVE / STALE
# HQ: Omni 8-step single pass 1344x768 (native), refs map to <Picture N>
python scripts/h3q.py submit shot01 --prompt-file prompt.txt --mode omni --size native --seconds 10 --seed 7 --ref a.png --ref b.png --ref bg.png
# Fast: Turbo 4-step 960x544
python scripts/h3q.py submit draft01 --prompt-file prompt.txt --mode turbo4 --size landscape --seconds 5
python scripts/h3q.py wait shot01
python scripts/h3q.py verify shot01 --out results/
python scripts/h3q.py cu add --balance 324.55 --note "session start"; python scripts/h3q.py cu report
python scripts/h3q.py gif results/shot01.mp4 preview.gif --width 480 --fps 10
```
Field reference: `references/protocol.md` / `docs/agent-protocol.md`. Face refine and SeedVR2 1080p are UI-only (「後製」) on this branch.
Legacy modes (`omni_hd` draft+refine, `ref2va_hd`, `ayase`) still exist but are not recommended: `omni_hd` caused the blur/ghosting fixed here.
