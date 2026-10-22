---
name: h3-colab-studio
description: Use when you need to generate MiniMax H3 / FastH3 Omni videos on the user's Google Colab Pro GPU (A100) through the Drive job queue instead of a local GPU - submit prompt + reference images, wait for the render, verify the MP4, track Colab compute units, and run the draft-then-720p two-pass flow (omni draft at 480p, then omni_hd second sampling to 1280x720). Triggers - "Colab", "A100", "運算單元 / compute units", "抽卡 / draft then refine", "omni_hd", "h3q", "送件 / 取件", "h3-queue", "用 Colab 跑 H3", reference-image video (Ref2VA) at 5/10/15 s, "ref2va_hd".
---

# H3 Colab Studio

Operate the user's Colab notebook (`notebook/MiniMax_H3_Studio.ipynb`) as a **video render service**. No public tunnel exists: you talk to it only through a Google Drive folder, `h3-queue/{inbox,running,done,failed}`, with the CLI `scripts/h3q.py`.

Prompt *content* comes from other skills. Write it first, then submit:
- `h3-video-prompting` (what to write, Ref2VA six-part format, five-part shots, length rules)
- `h3-combat-impact` (fights, impact frames, camera energy)

## 0. Preconditions (check before anything else)

```bash
python scripts/h3q.py status      # ALIVE = notebook cell 2 is running; STALE = it is not
```

If STALE, the **user** must start the notebook: open it in Colab, runtime A100, run cell 1 (about 6 min on a fresh VM), run cell 2, click the Drive authorization dialog (a Google OAuth popup that only the user can click). You cannot start it for them. Say so plainly, then wait.

Queue root is found automatically (`G:/我的雲端硬碟/h3-queue`, `~/Google Drive/My Drive/h3-queue`, or env `H3Q_ROOT`, or `--queue PATH`).

## 1. Choose a mode

| Goal | `--mode` | Refs | Time (A100 40 GB, warm) |
|---|---|---|---|
| Fast draft you can re-roll by seed | `omni` + `--size p480` | 1-9 images | 5 s: 41 s, 15 s: 171 s (earlier 1-reference session) |
| Final 720p, same seed as the chosen draft | `omni_hd` (size defaults to `p480`) | 1-9 images | 5 s: 133 s warm (355 s cold), 10 s: 378 s, 15 s: 656-681 s |
| Faster draft, **cannot** be refined | `ref4` | 1-9 images | 5 s: 27 s, 10 s: 57 s (earlier 1-reference session) |
| Cleaner frames, non-distilled, one pass (slow) | `ref2va` (--steps, default 20) | 1-9 images | 15 s: 1,817 s cold, 1280x704 |
| Non-distilled draft + 720p second sampling (slow) | `ref2va_hd` (--refine-steps default 8) | 1-9 images | 15 s: 1,412 s cold |
| No reference images | `turbo`, `turbo4`, `quality` | optional first/last frame | 5 s: 130 s |

Rules that matter:
1. A draft can only be refined if it came from `omni`. The `omni` draft and the draft inside `omni_hd` are frame-identical for the same seed, prompt and refs. `ref4` drafts are a different model and cannot be refined. Frame-identity of a standalone `ref2va --size p480` draft with the draft inside `ref2va_hd` has not been tested. Plain `ref2va` defaults to 1280x704, so it is not a draft.
2. `ref_N` maps to `<Picture N>` in the prompt. Numbers must start at 1 and be contiguous.
3. `omni_hd` renders 1280x736 and crops to 1280x720 (720 is not on H3's 32-pixel grid).
4. Never stack LoRAs. Omni is already 8-step distilled.
5. **Reference images matter more than most settings.** Use images with clearly different silhouettes and colours (in our test, a blond braid + orange visor against white spiky hair + horns). With look-alike or weak references the draft itself can draw two fighters as the same person; the second sampling cannot fix that. Check the draft stills (`omni_hd` keeps `<id>.draft.mp4`).
6. For `omni_hd`: `--refine-steps` defaults to 4. For two-character fights prefer **3**: it is 90 s faster at 15 s and avoided an identity slip (the second fighter turning into a copy of the first) seen once at 4. One sample, so verify with the stills.
7. `ref2va` / `ref2va_hd` use the Ref2VA weights from the download_ref4 box in cell ①. In the one combat test they gave cleaner frames but lower motion energy than Omni (18.6 / 16.4 vs 24.7). Use when clean identity matters more than impact (one sample each). About 2-3x the time.

## 2. Submit, wait, verify

```bash
python scripts/h3q.py submit shot01 --prompt-file prompt.txt --mode omni --size p480 --seconds 15 --seed 7 --ref kai.png --ref vex.png
python scripts/h3q.py wait shot01                      # prints per-stage seconds; exit code 1 on failure
python scripts/h3q.py verify shot01 --out results/     # size match, streams, audio level, motion, 3 stills
# happy with seed 7?  re-run it at 720p with the identical prompt and refs:
python scripts/h3q.py submit shot01-hd --prompt-file prompt.txt --mode omni_hd --seconds 15 --seed 7 --ref kai.png --ref vex.png
```

Submit order is handled by the CLI (images first, JSON last, atomic rename). Job ids: `A-Za-z0-9_-`, max 64. Jobs run one at a time in mtime order; queue several at once so the GPU never idles.

Read `references/modes-and-timings.md` for stage timings, and `references/protocol.md` for the file protocol (use it if you cannot run the CLI).

## 3. Verify like you mean it

`verify` fails (exit 1) if the MP4 size differs from the marker, there is no audio track, or motion is near zero. Then **look at the stills** (`<name>_f0..f2.png`) - the checks cannot tell you the face is right. For fights also run the combat skill's `scripts/measure_motion.py` (end-over-mid >= 60%).

For multi-character `omni_hd` clips also run `tools/identity_probe.py draft.mp4 final.mp4` if the repo is available (it compares a character's colour presence in the draft and the refined clip).

Typical failure messages (they name the ComfyUI node):
- `Omni 模式至少需要一張參考圖片` / `參考圖模式...至少需要` - a reference mode got no `--ref`.
- `參考圖片沒有送達` - a declared image did not sync from Drive within 10 minutes; resubmit.
- `The size of tensor a ... must match` - the ComfyUI pin is older than `ce42de5f` (Omni needs PDD support). Rebuild the notebook.
- CUDA out of memory - lower `--seconds`, or ask the user whether to switch the runtime to G4 (96 GB, higher CU rate).

## 4. Track compute units

Colab bills runtime hours, not jobs. A100 runs about **5.3 CU/hour** idle or busy. The balance is only visible in the Colab "Resources" panel (it is not exposed as text), so ask the user to read it, or read it from a screenshot if you drive the browser:

```bash
python scripts/h3q.py cu add --balance 376.67 --note "session start"
python scripts/h3q.py cu add --balance 371.40 --note "after 15 s HD"
python scripts/h3q.py cu report          # minutes, CU used, CU/h per interval
```

Take a reading at the start, after each long job, and at the end. Report wall-clock share including install (about 6 minutes) and idle time, not only render seconds.

## 5. Finish the session

When the batch is done, **tell the user and ask before deleting the runtime** unless they already said to ("跑完就幫我結束"). Deleting it stops billing; the next session needs about 6 minutes of setup plus one more Drive authorization click. Videos are safe in `done/`.

## 6. GIF previews for READMEs

```bash
python scripts/h3q.py gif results/shot01-hd.mp4 preview.gif --width 400 --fps 24 --start 2 --dur 5
```

24 fps (4 cs delay) plays smoothly; keep each GIF under about 10 MB (GitHub proxies larger ones poorly) by cutting 4-6 s excerpts and using 400-480 px width. Link the full MP4 next to it.

## Boundaries

- No public URLs, no tunnels, no ngrok: Colab's terms forbid serving from a runtime.
- MiniMax H3 weights are under the MiniMax community license; outputs are the user's to check against it (region limits apply).
- You cannot click Google OAuth popups; do not try to work around that.
