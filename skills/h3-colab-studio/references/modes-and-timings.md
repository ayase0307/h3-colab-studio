# Modes and timings (A100 40 GB, Colab Pro, measured 2026-10-22)

Warm = model already loaded. The first job after a model change adds 1-3 minutes. Source: `docs/benchmarks.md` and `benchmarks/records/`.

| Mode | Model | Steps | Size it renders | Needs refs | 5 s | 10 s | 15 s |
|---|---|---:|---|---|---:|---:|---:|
| `omni` | FastH3 Omni INT8 | 8 | `--size p480` = 832x480 (also landscape, portrait, square, native) | 1-9 | 41 s ¹ | about 115 s ³ | 171 s ¹ |
| `omni_hd` | FastH3 Omni INT8 | 8 draft + last 4 (default) | draft p480, output 1280x720 | 1-9 | 133 s ¹ (355 s cold ²) | 378 s | 656-681 s |
| `ref4` | Ref2VA INT8 + 4-step LoRA | 4 | same sizes as omni | 1-9 | 27 s ¹ | 57 s ¹ | not run |
| `ref2va` | Ref2VA INT8, non-distilled, no LoRA, no shift (official r2v template) | 20 (--steps 12-30) | default 1280x704 (p720) | 1-9 | not run | not run | 1,817 s cold ⁴ |
| `ref2va_hd` | same as ref2va | 20 draft + last 8 (default, my choice, range 2-12) | draft p480, output 1280x720 | 1-9 | not run | not run | 1,412 s cold ⁴ |
| `turbo` / `turbo4` | FL2VA INT8 + 8/4-step LoRA | 8 / 4 | landscape 960x544 etc. | no | 130 s | - | - |
| `quality` | FL2VA INT8 | 20-30 | landscape 960x544 etc. | no | slow | - | - |

¹ from an earlier single-reference session (one reference image, different prompts); ² first job of the two-reference session, includes model loading; ³ derived from `omni_hd` stage times. `turbo` rows are from that earlier session too.

⁴ one job on a fresh VM (cold), part 1 of the combat test, seed 20261019; both modes need the download_ref4 box ticked in cell ①.

Stage split of a 15 s `omni_hd` job (665 s): draft 26%, decode 3%, up-res 11%, second sampling 54%, final decode and mux 7%.

Stage split of a 15 s `ref2va_hd` job (1,412 s): conditioning + draft 38%, draft decode 2%, up-res 5%, second sampling 52%, decode and mux 3%.

Choosing `--refine-steps` (omni_hd):
- 4 (default): crisper detail, 358 s second sampling at 15 s.
- 3: 269 s at 15 s, same motion energy, and avoided a Vex-to-Kai identity slip seen once at 4. Prefer 3 for two-character fights.
- Valid range 2-6. 5-6 were not tested.

For `ref2va_hd` the default is 8 of 20; only 8 has been run. The omni_hd advice (prefer 3) does not carry over.

Compute units: about 4.8 CU/hour averaged over a whole session on A100 (the Colab panel states 5.3). One 15 s `omni_hd` job cost 0.87-0.89 CU (measured balance deltas); 10 s about 0.5 and 5 s about 0.18 are computed from rate x seconds. One session with a single 15 s `ref2va_hd` job: 2.65 CU over about 27 min after install (render 23.5 min).

Prompt length: ComfyUI's tokenizer does not truncate (max_length 99,999,999). Prompts up to 8,986 characters / 1,525 words rendered in full. The hosted MiniMax API caps at 7,000 characters, so long prompts are local-only.
