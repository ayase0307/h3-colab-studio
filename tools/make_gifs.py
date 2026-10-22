#!/usr/bin/env python3
"""Make smooth README GIFs (24 fps, 4 cs delays) from MP4s. Picks the most active N-second window unless --start is given.

    python tools/make_gifs.py results/a.mp4 --out assets/gifs/a.gif --dur 5 --width 480
    python tools/make_gifs.py draft.mp4 final.mp4 --side-by-side --out assets/gifs/draft-vs-final.gif --start 2 --dur 4

Needs ffmpeg/ffprobe and Pillow (to verify frame delays). Prints size and effective fps.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def energy_series(mp4: str) -> list[float]:
    sig = run("ffmpeg", "-hide_banner", "-i", mp4, "-vf", "tblend=all_mode=difference,scale=320:-1,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-").stderr
    return [float(x) for x in re.findall(r"YAVG=([\d.]+)", sig)]


def best_window(mp4: str, dur: float, fps: int = 24, skip: float = 0.5) -> float:
    vals = energy_series(mp4)
    n = int(dur * fps)
    if len(vals) <= n + int(skip * fps):
        return 0.0
    best, start = -1.0, 0
    for i in range(int(skip * fps), len(vals) - n, fps // 4):
        m = sum(vals[i:i + n]) / n
        if m > best:
            best, start = m, i
    return round(start / fps, 2)


def make_gif(inputs, out: Path, start: float, dur: float, width: int, fps: int, colors: int, side: bool):
    pal = out.with_suffix(".palette.png")
    base = []
    for src in inputs:
        base += ["-ss", str(start), "-t", str(dur), "-i", src]
    if side and len(inputs) == 2:
        half = width // 2
        hh = round(half * 9 / 16 / 2) * 2  # draft is 832x480, final 1280x720: force one 16:9 size so hstack accepts both
        vf = f"[0:v]fps={fps},scale={half}:{hh}:flags=lanczos[a];[1:v]fps={fps},scale={half}:{hh}:flags=lanczos[b];[a][b]hstack"
    else:
        vf = f"[0:v]fps={fps},scale={width}:-1:flags=lanczos"
    r = run("ffmpeg", "-y", "-v", "error", *base, "-filter_complex", f"{vf}[v];[v]palettegen=max_colors={colors}:stats_mode=diff", str(pal))
    if r.returncode:
        raise SystemExit(r.stderr)
    r = run("ffmpeg", "-y", "-v", "error", *base, "-i", str(pal), "-filter_complex", f"{vf}[v];[v][{len(inputs)}:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle", "-loop", "0", str(out))
    pal.unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(r.stderr)


def report(out: Path):
    from collections import Counter
    from PIL import Image, ImageSequence
    im = Image.open(out)
    d = [f.info.get("duration", 0) for f in ImageSequence.Iterator(im)]
    print(f"{out}: {out.stat().st_size / 1e6:.1f} MB, {im.size[0]}x{im.size[1]}, {len(d)} frames, delays {dict(Counter(d))}, effective {1000 * len(d) / sum(d):.1f} fps")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur", type=float, default=5.0)
    ap.add_argument("--start", type=float)
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--colors", type=int, default=128)
    ap.add_argument("--side-by-side", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    start = a.start if a.start is not None else best_window(a.inputs[-1], a.dur, a.fps)
    make_gif(a.inputs, out, start, a.dur, a.width, a.fps, a.colors, a.side_by_side)
    print(f"window starts at {start}s")
    report(out)


if __name__ == "__main__":
    main()
