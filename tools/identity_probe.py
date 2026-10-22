"""Crude identity-presence probe for the Kai/Vex test pair: Vex wears pure red (crop top, shorts, sneakers); fire is orange.
Prints per-second red-pixel share of the draft vs the refined video and flags seconds where it collapses.

    python tools/identity_probe.py job.draft.mp4 job.mp4

A probe, not a face recognizer: it only catches the big failure (the second fighter turning into a copy of the first). Needs numpy + ffmpeg."""
import subprocess, sys
import numpy as np

def red_series(path, w=320, h=180):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 150) & (g < 70) & (b < 80) & (r - g > 100)
    return m.mean(axis=(1, 2))

draft, final = sys.argv[1], sys.argv[2]
d, f = red_series(draft), red_series(final)
n = min(len(d), len(f))
d, f = d[:n], f[:n]
# per-second means
print("sec  draft_red%  final_red%  flag")
bad = 0
for s in range(n // 24):
    dd, ff = d[s * 24:(s + 1) * 24].mean() * 100, f[s * 24:(s + 1) * 24].mean() * 100
    flag = "VEX LOST" if dd > 0.25 and ff < 0.4 * dd else ""
    bad += bool(flag)
    print(f"{s:>3}  {dd:>9.2f}  {ff:>9.2f}  {flag}")
print("seconds flagged:", bad, "of", n // 24)
