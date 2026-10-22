# Troubleshooting (every item below happened during real runs)

## The notebook side

| Symptom | Cause | Fix |
|---|---|---|
| Cell 2 ends with `ValueError: mount failed` | The Drive authorization finished after Colab's mount timeout, or the Drive has a huge flat folder | Run cell 2 again. The authorization is now cached for this VM and the second mount succeeds |
| Cell 2 shows the Drive consent dialog and nothing happens | Google's OAuth opens a popup. Embedded browser panes and agents cannot open it; only a real user click can | Ask the user to click "Connect to Google Drive" and finish the popup themselves. Every new VM needs this once |
| `Omni 模式至少需要一張參考圖片` / reference modes fail instantly | `omni`, `omni_hd` and `ref4` need at least one image | Pass `--ref image.png` |
| `The size of tensor a (24) must match the size of tensor b (768)` while sampling | ComfyUI is older than commit `ce42de5f` (2026-10-18). FastH3 Omni is a PDD model and needs that support | Use this repo's notebook (it pins `ce42de5f`). Cell 1 restarts ComfyUI automatically when the pin changes |
| Cell 1 re-downloads 40-60 GB | New VM: `/content` is wiped with the runtime | Expected: about 6-7 minutes on A100 |
| `CUDA out of memory` at 15 s | 15 s at 1280x736 fits an A100 40 GB with `omni_hd`. Higher resolutions or other models may not | Lower `--seconds`, or switch the runtime to G4 (96 GB) |

## The queue side

| Symptom | Cause | Fix |
|---|---|---|
| `h3q status` says STALE | Notebook cell 2 is not running, or the runtime was deleted | Ask the user to start cell 2 (see above) |
| Heartbeat is old but `running/` holds a file | The heartbeat is written only between jobs; a 15 s HD render takes about 11 minutes | Not a fault. `h3q status` reports BUSY when `running/` is non-empty |
| A file stays in `running/` for minutes after the job finished | Drive propagates deletions slowly | Ignore it; trust `done/<id>.json` |
| `done/<id>.json` exists but the MP4 is smaller than expected | Drive synced the marker before the video | `h3q wait` compares the size recorded in the marker and keeps waiting until they match |
| A declared reference never arrives | Image upload lagged more than 10 minutes | The job fails with `參考圖片沒有送達`; resubmit under a new id |
| Job id rejected | ids are `A-Za-z0-9_-`, max 64 | Rename |

## Output quality

| Symptom | Cause | Fix |
|---|---|---|
| A character turns into a copy of the other one in a short stretch after the second sampling | Two references, similar poses, partially re-noised latent | Re-run with `--refine-steps 3`; check with an identity probe (see `docs/benchmarks.md`); pick another seed |
| Static opening (first 0.8 s) | The prompt's first shot is a set-up, not contact | Start Shot 1 with the first contact inside 0.5 s |
| Image hair/clothes drift from the reference | Long appearance text fights the reference image | Do not restate appearance in shots; keep it only in `subject_definitions` |
