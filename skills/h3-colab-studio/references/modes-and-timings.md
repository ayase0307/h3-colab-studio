# Modes and timings (A100 40 GB, Colab Pro, measured 2026-10-22)

Warm = model already loaded. The first job after a model change adds 1-3 minutes. Source: `docs/benchmarks.md` and `benchmarks/records/`.

| Mode | Model | Steps | Size it renders | Needs refs | 5 s | 10 s | 15 s |
|---|---|---:|---|---|---:|---:|---:|
| `omni` | FastH3 Omni INT8 | 8 | `--size p480` = 832x480 (also landscape, portrait, square, native) | 1-9 | 41 s ¹ | about 115 s ³ | 171 s ¹ |
| `omni_hd` | FastH3 Omni INT8 | 8 draft + last 4 (default) | draft p480, output 1280x720 | 1-9 | 133 s ¹ (355 s cold ²) | 378 s | 656-681 s |
| `ref4` | Ref2VA INT8 + 4-step LoRA | 4 | same sizes as omni | 1-9 | 27 s ¹ | 57 s ¹ | not run |
| `turbo` / `turbo4` | FL2VA INT8 + 8/4-step LoRA | 8 / 4 | landscape 960x544 etc. | no | 130 s | - | - |
| `quality` | FL2VA INT8 | 20-30 | landscape 960x544 etc. | no | slow | - | - |

¹ from an earlier single-reference session (one reference image, different prompts); ² first job of the two-reference session, includes model loading; ³ derived from `omni_hd` stage times. `turbo` rows are from that earlier session too.

Stage split of a 15 s `omni_hd` job (665 s): draft 26%, decode 3%, up-res 11%, second sampling 54%, final decode and mux 7%.

Choosing `--refine-steps`:
- 4 (default): crisper detail, 358 s second sampling at 15 s.
- 3: 269 s at 15 s, same motion energy, and avoided a Vex-to-Kai identity slip seen once at 4. Prefer 3 for two-character fights.
- Valid range 2-6. 5-6 were not tested.

Compute units: about 4.8 CU/hour averaged over a whole session on A100 (the Colab panel states 5.3). One 15 s `omni_hd` job cost 0.87-0.89 CU (measured balance deltas); 10 s about 0.5 and 5 s about 0.18 are computed from rate x seconds.

Prompt length: ComfyUI's tokenizer does not truncate (max_length 99,999,999). Prompts up to 8,986 characters / 1,525 words rendered in full. The hosted MiniMax API caps at 7,000 characters, so long prompts are local-only.
