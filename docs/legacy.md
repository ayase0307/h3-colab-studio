# Legacy flows (not recommended)

The `omni_hd` draft + 720p second sampling caused blur and ghosting on A100 and was replaced by HQ Omni single pass at 1344×768 (see README). Kept for reference.

## Draft first, then a second sampling at 720p

> **Legacy:** the draft + 720p second-sampling flow (`omni_hd`) below is no longer recommended; it caused blur and ghosting. Use HQ Omni single pass at 1344×768 (next section).

<p align="center">
  <img src="../assets/diagram-two-pass.svg" alt="omni_hd: Omni 8-step draft at 832x480, decode, resize to 1280x736, re-encode, resample the last 4 of 8 steps, crop to 1280x720" width="100%">
</p>

The second pass is the same distilled model run on only the tail of its own 8-step schedule, over the up-scaled draft, with the references injected again. A tail split matches how the distilled model was trained better than a partial-denoise schedule would.

<p align="center">
  <img src="../assets/stills/draft-vs-final-detail.jpg" alt="Left: the draft stretched to 720p, soft lines and noise on the hand. Right: after the second sampling, clean hair strands, goggle reflections and fingers" width="92%"><br>
  <sub>Left: the 480p draft stretched to 720p. Right: after the second sampling. Same frame.</sub>
</p>


## Measured on a Colab A100 (40 GB)

Session 1: 7 renders, **7.03 compute units** from a fresh VM (376.67 to 369.64), about 4.8 CU/hour averaged. Session 2 (the re-run with the original references): 2 renders, 2.21 CU. Full tables, methods and caveats: [`docs/benchmarks.md`](benchmarks.md). Sessions 3-4 (non-distilled controls): see [benchmarks](benchmarks.md#control-runs-non-distilled-ref2va-r1-single-pass-r2-draft--second-sampling).

| Clip | Draft only (`omni`) | `omni_hd` (draft + 720p) | Compute units (`omni_hd`) |
|---|---:|---:|---:|
| 5 s | 41 s ¹ | 133 s ¹ (355 s cold ²) | 0.18 ³ |
| 10 s | about 115 s ⁴ | 378 s | 0.5 ³ |
| 15 s | 171 s ¹ | 656-681 s | 0.88 ⁵ |

<sub>¹ measured in an earlier single-reference session (one reference image, different prompts), not in the two-reference run below. ² the first job of the two-reference session, including model loading. ³ computed: 4.8 CU/h x seconds. ⁴ derived from the stage times of `omni_hd` jobs. ⁵ measured balance deltas (0.87-0.89 per job).</sub>

The second sampling is 54% of a 15 s job. `--refine-steps 3` cuts a 15 s job from 665 s to 582 s.

**30 s combat test** (two 15 s Ref2VA segments from h3-combat-impact; prompts byte-identical, original reference images):

| | This repo | Original showcase (local 8 GB GPU, 16-step `high`) |
|---|---:|---:|
| Part 1 motion energy / end-over-mid | 24.7 / 93% | 28.2 / 96% |
| Part 2 motion energy / end-over-mid | 28.3 / 81% | 28.1 / 93% |
| Quiet talking portraits, for scale | 1.4-2.1 | - |

**Reference images decide a lot.** My first run used two images I generated from the character text; the draft drew both fighters as Kai in one shot and the whole result looked weaker. Re-running the same prompts and seed with the original two images fixed that. The original pipeline is also a different recipe (FreeVideo on VDN-H3, 16-step `high`, one pass), so expect a similar look, not the same shots. A non-distilled Ref2VA control gave cleaner frames but less motion (18.6 single pass, 16.4 with second sampling), so Omni's speed-up alone does not explain the gap. Side-by-side frames and details: [`docs/benchmarks.md`](benchmarks.md#3-the-30-second-combat-test-two-15-s-segments).

<p align="center">
  <img src="../assets/stills/combat-part1-vs-showcase.jpg" alt="Part 1 frames: the h3-combat-impact showcase on rows 1 and 3, this repo on rows 2 and 4" width="92%"><br>
  <sub>Same prompt. Rows 1 and 3: the original showcase. Rows 2 and 4: this repo, original reference images, 720p.</sub>
</p>


