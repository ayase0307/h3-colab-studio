#!/usr/bin/env python3
"""Turn finished queue jobs into benchmark records.

    python benchmarks/collect.py --queue G:/.../h3-queue --jobs s5-b5-smoke s6-a1-combat-part1 ... --prompts benchmarks/prompts --out benchmarks/records

For every job it reads done/<id>.settings.json (stage timeline, seconds), measures motion energy from the MP4 with the same
frame-difference method as h3-combat-impact's measure_motion.py, counts prompt characters/words, and writes
records/<id>.json plus one RESULTS.md table. Needs ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

STAGES = {
    "load+draft": {"1", "3", "4", "5", "16", "7", "8", "9", "10", "11", "12"},
    "decode draft": {"40", "41", "60"},
    "up-res": {"42", "43", "44", "45", "46", "48", "49"},
    "refine": {"50"},
    "final decode+mux": {"13", "14", "51", "15"},
}


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def motion(mp4: Path) -> dict:
    sig = run("ffmpeg", "-hide_banner", "-i", str(mp4), "-vf", "tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-").stderr
    vals = [float(x) for x in re.findall(r"YAVG=([\d.]+)", sig)]
    if not vals:
        return {}
    # energy matches measure_motion.py; for the end/mid ratio run that tool (its windowing differs slightly)
    return {"energy": round(sum(vals) / len(vals), 2)}


def stage_seconds(timeline, total):
    ordered = list(timeline) + [["END", total]]
    out = {k: 0.0 for k in STAGES}
    for (node, t), (_, nxt) in zip(ordered, ordered[1:]):
        for name, nodes in STAGES.items():
            if node in nodes:
                out[name] += nxt - t
    return {k: round(v, 1) for k, v in out.items()}


def words(text):
    return len(text.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--jobs", nargs="+", required=True)
    ap.add_argument("--prompts", default=None, help="folder of prompt .txt files; matched by the job's prompt text")
    ap.add_argument("--out", default="benchmarks/records")
    a = ap.parse_args()
    q = Path(a.queue) / "done"
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in a.jobs:
        marker = json.loads((q / f"{name}.json").read_text(encoding="utf-8"))
        st = json.loads((q / marker["settings"]).read_text(encoding="utf-8"))
        c = st["config"]
        rec = {"id": name, "mode": c["mode"], "draft_size": f"{c['width']}x{c['height']}", "seconds": round(c["actual_seconds"], 1), "seed": c["seed"],
               "total_s": st["generation_seconds"], "stages_s": stage_seconds(st.get("timeline", []), st["generation_seconds"]),
               "prompt_chars": len(c["prompt"]), "prompt_words": words(c["prompt"]), "refs": len(c.get("refs", [])),
               "mp4_mb": round(marker["video_bytes"] / 1e6, 1), "environment": st.get("environment", {}).get("profile")}
        mp4 = q / marker["video"]
        if mp4.exists():
            rec["motion"] = motion(mp4)
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        rows.append(rec)
    lines = ["| job | mode | clip | prompt (chars / words) | total | load+draft | decode | up-res | refine | final | motion energy |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        s = r["stages_s"]
        m = r.get("motion", {})
        lines.append(f"| {r['id']} | {r['mode']} | {r['seconds']} s | {r['prompt_chars']} / {r['prompt_words']} | {r['total_s']:.0f} s | {s['load+draft']:.0f} | {s['decode draft']:.0f} | {s['up-res']:.0f} | {s['refine']:.0f} | {s['final decode+mux']:.0f} | "
                     f"{m.get('energy', '-')} |")
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
