# Benchmarks and test record

Everything below was measured on 2026-10-22 on one Colab Pro A100 40 GB VM, ComfyUI `ce42de5f`, INT8 FastH3 Omni + INT8 text encoder, 24 fps, reference images only (two characters). Raw per-job JSON is in [`benchmarks/records/`](../benchmarks/records), prompts in [`benchmarks/prompts/`](../benchmarks/prompts), the compute-unit log in [`benchmarks/cu-log.jsonl`](../benchmarks/cu-log.jsonl).

Read the numbers with these caveats: one seed per cell, one pair of characters, motion and identity scored by simple scripts plus my own eyes. The first job after any model change includes 1-3 minutes of model loading; that is labelled "cold" where it applies.

## 1. Setup and the session in numbers

| Item | Value |
|---|---|
| GPU | Colab A100 40 GB (about 39.5 GiB visible), 83.5 GB system RAM |
| Fresh-VM install (cell 1, 62 GB of weights) | about 6-7 minutes |
| Colab compute units, whole session | 376.67 -> 369.64 = **7.03 CU** in about 88 minutes (includes install, waiting, 8 renders) |
| Average burn | 4.8 CU/h measured, the Colab panel states 5.3 CU/h |
| Per-job CU | 5 s about 0.18, 10 s about 0.5, 15 s about 0.88 (measured 0.87-0.89 for each 15 s job) |

The compute-unit balance is only shown in Colab's Resources panel and updates in coarse steps, so single-job deltas jump around (0.44 to 1.33 for similar jobs). Use the long-run slope, not one reading. Colab bills runtime hours, not jobs: batching is what saves units.

## 2. Draft and second-sampling timings (A100 40 GB, warm unless noted)

Draft = Omni 8 steps at 832x480. `omni_hd` = draft + second sampling (last 4 of 8 steps) at 1280x736, cropped to 1280x720.

| Clip | Draft only (`omni`) | Draft only (`ref4`) | `omni_hd` total | of which second sampling |
|---|---:|---:|---:|---:|
| 5 s | 41 s | 27 s | 133 s (warm), 355 s (cold, first job) | 54 s |
| 10 s | about 115 s (derived) | 57 s | 378 s | 180 s |
| 15 s | 171 s | not run | 656-681 s | 354-361 s |

Where the time goes in a 15 s `omni_hd` job (job `s6`, 665 s):

| Stage | Seconds | Share |
|---|---:|---:|
| Conditioning + draft sampling | 171 | 26% |
| Draft decode + save | 17 | 3% |
| Up-res (resize, VAE encode, second conditioning) | 75 | 11% |
| **Second sampling** | **358** | **54%** |
| Final decode + audio + mux | 44 | 7% |

`--refine-steps 3` instead of 4 cut the second sampling from 358 s to 269 s (job `s11`, total 582 s).

## 3. The 30-second combat test (two 15 s segments)

Prompts: [`anime-ref2va-part1/part2`](../benchmarks/prompts) from [h3-combat-impact](https://github.com/ayase0307/h3-combat-impact), unchanged. References: two generated adult characters (Kai, Vex) matching that repo's `subject_definitions`. Seed 21. Motion metric is the combat skill's `measure_motion.py` (mean frame-difference energy; "end / mid" = last 2 s over the middle, pass at 60% or more).

| Clip | Pipeline | Energy | End / mid | Notes |
|---|---|---:|---:|---|
| Part 1 | this repo, `omni_hd` | 25.6 | 85% | 665 s |
| Part 1 | h3-combat-impact showcase (local 8 GB GPU, 1280x704) | 28.2 | 96% | same prompt |
| Part 2 | this repo, `omni_hd` | 26.0 | 75% | 669 s |
| Part 2 | h3-combat-impact showcase | 28.1 | 93% | same prompt |
| Joined 30 s | `ffmpeg -c copy` | 25.9 | 77% | 104 peaks |
| Earlier Tomie talking portraits (5-15 s) | `omni_hd` | 1.4-2.1 | 64-106% | flagged "too quiet", this is the static baseline |

The two pipelines land within about 10% of each other on energy; ours is a little lower, with a weaker ending on part 2 (75% vs 93%, still above the 60% bar).

Refine 3 (`s11`): 25.1 energy, 85% end / mid, same as refine 4 on both numbers.

Seam check (`seam_check.py`) on the A1 -> A2 join: **FAIL**. The seam frame differs by 3.4 against a neighbourhood median of 14.4 (24%), i.e. the join reads as a near-still frame. The two segments are independent generations with no hand-off frame, so a cut is expected; hide it with a cutaway or chain with the last frame as the next first frame.

Prompt linter (`validate_prompt.py`) on the shipped examples: 0 FAIL, but both exceed its 820-word budget (1,207 and 1,135 words), as do all of our long prompts.

### Identity loss at the end of part 1, and the fix

Job `s6` (refine 4): in the last second Vex turns into a second Kai after the second sampling, although the draft was correct. A red-pixel probe (`tools/identity_probe.py`) flags exactly that second (red share 1.20% in the draft, 0.43% after). With `--refine-steps 3` (job `s11`) the probe flags nothing and the frame keeps Vex. One sample, so treat 3 as the safer default for two-character fights, not as proof.

![draft, refine 4, refine 3 at 14.78 s](../assets/stills/identity-tail-fix.jpg)

## 4. High-motion prompts at 5, 10 and 15 s (technique from the Seedance 2.5 example, written for H3)

Written with `h3-video-prompting` (origin/main) five-part shots: every `[Shot N]` has Camera / Motion / Performance / Light / Sound, one camera move per shot, no appearance restatement. Scene: a rain-lashed scrapyard under a gantry crane. Seed 12 (B15 pair), all `omni_hd`.

| Job | Clip | Shots | Prompt chars / words (detailed_description words) | Total | Energy | End / mid | Identity probe |
|---|---|---:|---|---:|---:|---:|---|
| B5 | 5.2 s | 3 | 5,630 / 940 (620) | 355 s cold | 20.0 | 100% | ok |
| B10 | 10.1 s | 5 | 7,145 / 1,200 (870) | 378 s | 20.5 | 131% | ok |
| B15 five-part | 15.1 s | 6 | 8,986 / 1,525 (1,192) | 681 s | 22.2 | 118% | ok |
| B15 one-line | 15.1 s | 6 | 4,608 / 762 (428) | 656 s | 22.4 | 90% | ok |

Shot-length note: B5's three shots (1.7-1.9 s) and B10's first and last (1.7-1.8 s) are below the skill's 2 s guideline on purpose, to keep the energy high; the linter accepts them once the last shot is under 30% of the clip.

## 5. Prompt-length unlock: what happened

The newest `h3-video-prompting` makes five-part shots a normal choice and lets the user release prompts above 700 words. I released all of them and checked what changes:

- **No truncation.** ComfyUI's MiniMax tokenizer is built on a Qwen3-VL tokenizer with `max_length=99999999`; it raises an error rather than silently cutting. All four long prompts (up to 8,986 characters, 1,525 words) rendered in full; later shots (the fist at the lens in Shot 6) appear.
- **The hard cap is the hosted API:** 7,000 characters. B10 (7,145), B15 (8,986) and combat part 1 (7,022) exceed it, so they are local-only.
- **Render time did not change** (second sampling dominates; prompt length barely touches it).
- **Quality: no measurable gain or loss.** Five-part B15 and the one-line B15 have the same energy (22.2 vs 22.4). The five-part opening is quieter (first 0.8 s energy 9.2 vs 22.8) but its ending is stronger (118% vs 90%). With one seed per cell this is inconclusive, not a verdict.

## 6. How the numbers were produced

```bash
python skills/h3-colab-studio/scripts/h3q.py submit s9-b15-fivepart --prompt-file benchmarks/prompts/b15-scrapyard-15s.txt --mode omni_hd --seconds 15 --seed 12 --ref kai.png --ref vex.png
python skills/h3-colab-studio/scripts/h3q.py wait s9-b15-fivepart
python skills/h3-colab-studio/scripts/h3q.py verify s9-b15-fivepart --out results/
python benchmarks/collect.py --queue <queue> --jobs s5-b5-smoke ... --out benchmarks/records
python tools/identity_probe.py results/job.draft.mp4 results/job.mp4
```

The reference images of Kai and Vex are not in the repo (they follow a public Seedance showcase, as in h3-combat-impact); generate your own from the `subject_definitions` text.

## 7. Not measured

- A second seed for any cell; other character pairs; real-world (non-anime) subjects.
- G4 (96 GB) or H100; resolutions above 1280x736.
- Lip-sync and dialogue; only audio presence and level were checked.
- A human blind comparison of draft vs refined; the detail comparison is by eye.
