#!/usr/bin/env python3
"""h3q - drive the H3 Colab Studio job queue from any agent or shell.

The notebook polls a Google Drive folder (default name `h3-queue`) with the layout
    inbox/ running/ done/ failed/ heartbeat.json
and this CLI is the client side. Standard library only; `verify` and `gif` need ffmpeg/ffprobe on PATH.

    h3q.py status
    h3q.py submit  NAME --prompt-file p.txt --mode omni_hd --seconds 15 --seed 12 --ref kai.png --ref vex.png
    h3q.py wait    NAME [NAME ...] [--timeout 5400]
    h3q.py verify  NAME --out results/
    h3q.py cu      add --balance 376.67 --note "session start"   |   cu report
    h3q.py gif     in.mp4 out.gif --width 480 --fps 24 --start 0 --dur 5
Queue root: --queue PATH, or env H3Q_ROOT, or ~/Google Drive style default search (see `find_root`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DIRS = ("inbox", "running", "done", "failed")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MODES = ("turbo", "turbo4", "omni", "omni_hd", "ref4", "quality")
MAX_REFS = 9
LABELS = {"1": "load unet", "3": "load clip", "4": "load vae", "5": "load audio vae", "2": "lora", "16": "shift", "7": "conditioning",
          "12": "draft sampling", "40": "split av", "41": "draft decode", "42": "resize", "43": "hd encode", "44": "concat av",
          "45": "hd conditioning", "50": "refine sampling", "13": "final decode", "14": "audio decode", "51": "crop", "15": "mux+save", "60": "draft save"}


def find_root(arg: str | None) -> Path:
    candidates = [arg, os.environ.get("H3Q_ROOT")]
    for drive in ("G:/我的雲端硬碟", "G:/My Drive", str(Path.home() / "Google Drive" / "My Drive"), str(Path.home() / "My Drive")):
        candidates.append(str(Path(drive) / "h3-queue"))
    for c in candidates:
        if c and (Path(c) / "inbox").is_dir():
            return Path(c)
    sys.exit("queue folder not found: pass --queue or set H3Q_ROOT (the folder that contains inbox/ done/ failed/)")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------ status
def cmd_status(a):
    q = find_root(a.queue)
    counts = {d: len([p for p in (q / d).glob("*.json")]) for d in DIRS}
    beat = q / "heartbeat.json"
    if beat.exists():
        info = read_json(beat)
        age = (time.time() - beat.stat().st_mtime) / 60
        busy = counts["running"] > 0  # the heartbeat is only written between jobs; a long render keeps it old
        alive = "ALIVE" if age < 10 else ("BUSY (a job is in running/; heartbeat updates when it ends)" if busy else "STALE (notebook cell 2 is probably not running)")
        print(f"heartbeat: {info.get('alive_at')}  last_job={info.get('last_job')}  file age {age:.1f} min -> {alive}")
    else:
        print("heartbeat: none (notebook cell 2 never ran against this folder)")
    print("queue:", counts)


# ------------------------------------------------------------------ submit
def cmd_submit(a):
    q = find_root(a.queue)
    if not ID_RE.match(a.name):
        sys.exit("name must be 1-64 chars of A-Z a-z 0-9 _ -")
    if (q / "done" / f"{a.name}.json").exists() or (q / "inbox" / f"{a.name}.json").exists():
        sys.exit(f"{a.name} already exists in the queue; pick a new name")
    prompt = Path(a.prompt_file).read_text(encoding="utf-8") if a.prompt_file else a.prompt
    if not prompt or not prompt.strip():
        sys.exit("empty prompt")
    if len(a.ref) > MAX_REFS:
        sys.exit(f"at most {MAX_REFS} reference images")
    cfg = {"prompt": prompt, "mode": a.mode, "seconds": str(a.seconds), "seed": a.seed}
    if a.size:
        cfg["size"] = a.size
    if a.sampler:
        cfg["sampler"] = a.sampler
    if a.mode in ("omni_hd",) and a.refine_steps:
        cfg["refine_steps"] = a.refine_steps
    declared = []
    for i, ref in enumerate(a.ref, 1):  # images first, JSON last: the notebook only scans *.json
        if not Path(ref).is_file():
            sys.exit(f"reference not found: {ref}")
        shutil.copyfile(ref, q / "inbox" / f"{a.name}.ref_{i}.png") if Path(ref).suffix.lower() == ".png" else _to_png(ref, q / "inbox" / f"{a.name}.ref_{i}.png")
        declared.append(f"ref_{i}")
    if declared:
        cfg["images"] = declared
    tmp = q / "inbox" / f"{a.name}.json.part"
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, q / "inbox" / f"{a.name}.json")
    print(f"submitted {a.name}: mode={a.mode} seconds={a.seconds} refs={len(declared)} chars={len(prompt)} words={len(prompt.split())}")


def _to_png(src, dst):
    from PIL import Image  # optional dependency, only for non-PNG references
    Image.open(src).convert("RGB").save(dst)


# ------------------------------------------------------------------ wait / summary
def stage_rows(timeline, total):
    ordered = list(timeline) + [["END", total]]
    return [(LABELS.get(n, n), round(nxt - t, 1)) for (n, t), (_, nxt) in zip(ordered, ordered[1:]) if nxt - t >= 2]


def wait_one(q: Path, name: str, timeout: float) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if (q / "failed" / f"{name}.json").exists():
            return {"name": name, "state": "failed", **read_json(q / "failed" / f"{name}.json")}
        if (q / "done" / f"{name}.json").exists():
            marker = read_json(q / "done" / f"{name}.json")
            mp4 = q / "done" / marker["video"]
            for _ in range(120):  # Drive may sync the marker before the video; marker carries the expected size
                if mp4.exists() and mp4.stat().st_size == marker["video_bytes"]:
                    break
                time.sleep(3)
            settings = read_json(q / "done" / marker["settings"])
            return {"name": name, "state": "done", "marker": marker, "settings": settings}
        time.sleep(4)
    return {"name": name, "state": "timeout"}


def describe(r: dict) -> str:
    if r["state"] != "done":
        return f"{r['name']}: {r['state'].upper()} {str(r.get('error', ''))[:500]}"
    s = r["settings"]
    c = s["config"]
    rows = ", ".join(f"{k} {v}s" for k, v in stage_rows(s.get("timeline", []), s["generation_seconds"]))
    return (f"{r['name']}: {c['mode']} {c['width']}x{c['height']} {c['actual_seconds']:.1f}s total={s['generation_seconds']}s "
            f"mb={r['marker']['video_bytes'] / 1e6:.1f} :: {rows}")


def cmd_wait(a):
    q = find_root(a.queue)
    rc = 0
    for name in a.names:
        r = wait_one(q, name, a.timeout)
        print(describe(r), flush=True)
        rc |= r["state"] != "done"
    sys.exit(rc)


# ------------------------------------------------------------------ verify
def run(*args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def cmd_verify(a):
    q = find_root(a.queue)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    marker = read_json(q / "done" / f"{a.name}.json")
    src = q / "done" / marker["video"]
    local = out / f"{a.name}.mp4"
    shutil.copyfile(src, local)
    draft = q / "done" / f"{a.name}.draft.mp4"
    if draft.exists():
        shutil.copyfile(draft, out / f"{a.name}.draft.mp4")
    probe = json.loads(run("ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(local)).stdout)
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
    vol = run("ffmpeg", "-hide_banner", "-i", str(local), "-af", "volumedetect", "-vn", "-f", "null", "-").stderr
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    sig = run("ffmpeg", "-hide_banner", "-i", str(local), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YDIF", "-an", "-f", "null", "-").stderr
    ydif = [float(x) for x in re.findall(r"YDIF=([\d.]+)", sig)]
    rep = {"name": a.name, "bytes_match": src.stat().st_size == marker["video_bytes"], "width": v["width"], "height": v["height"], "fps": v["r_frame_rate"],
           "duration": round(float(probe["format"]["duration"]), 2), "has_audio": has_audio, "audio_mean_db": float(mean.group(1)) if mean else None,
           "motion_mean_ydif": round(sum(ydif) / len(ydif), 3) if ydif else None}
    rep["ok"] = bool(rep["bytes_match"] and has_audio and (rep["motion_mean_ydif"] or 0) > 0.3)
    dur = rep["duration"]
    for i, t in enumerate((0.3, dur / 2, dur - 0.3)):
        run("ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(local), "-frames:v", "1", str(out / f"{a.name}_f{i}.png"))
    (out / f"{a.name}.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep))
    sys.exit(0 if rep["ok"] else 1)


# ------------------------------------------------------------------ compute-unit log
def cu_path(a) -> Path:
    return Path(a.log)


def cmd_cu(a):
    p = cu_path(a)
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()] if p.exists() else []
    if a.action == "add":
        rows.append({"t": now_iso(), "epoch": time.time(), "balance": a.balance, "note": a.note or ""})
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        print(f"logged {a.balance} CU ({a.note or ''})")
        return
    if len(rows) < 2:
        sys.exit("need at least two readings")
    print(f"{'from':<28}{'to':<28}{'min':>7}{'CU':>8}{'CU/h':>7}")
    for x, y in zip(rows, rows[1:]):
        minutes = (y["epoch"] - x["epoch"]) / 60
        used = x["balance"] - y["balance"]
        print(f"{x['note'][:26]:<28}{y['note'][:26]:<28}{minutes:>7.1f}{used:>8.2f}{(used / minutes * 60 if minutes else 0):>7.2f}")
    total = rows[0]["balance"] - rows[-1]["balance"]
    hours = (rows[-1]["epoch"] - rows[0]["epoch"]) / 3600
    print(f"total {total:.2f} CU over {hours * 60:.0f} min = {total / hours:.2f} CU/h" if hours else "")


# ------------------------------------------------------------------ gif
def cmd_gif(a):
    palette = Path(a.out).with_suffix(".palette.png")
    base = ["-ss", str(a.start)] + (["-t", str(a.dur)] if a.dur else []) + ["-i", a.input]
    vf = f"fps={a.fps},scale={a.width}:-1:flags=lanczos"
    r = run("ffmpeg", "-y", "-v", "error", *base, "-vf", f"{vf},palettegen=max_colors=192:stats_mode=diff", str(palette))
    if r.returncode:
        sys.exit(r.stderr)
    r = run("ffmpeg", "-y", "-v", "error", *base, "-i", str(palette), "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", "-loop", "0", a.out)
    palette.unlink(missing_ok=True)
    if r.returncode:
        sys.exit(r.stderr)
    size = Path(a.out).stat().st_size / 1e6
    delays = run("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,nb_frames", "-of", "csv=p=0", a.out).stdout.strip()
    print(f"{a.out}: {size:.1f} MB, {delays}")


def main():
    ap = argparse.ArgumentParser(description="H3 Colab Studio queue client")
    ap.add_argument("--queue", help="queue folder (contains inbox/ done/ failed/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("submit"); s.set_defaults(fn=cmd_submit)
    s.add_argument("name"); s.add_argument("--prompt-file"); s.add_argument("--prompt")
    s.add_argument("--mode", default="omni_hd", choices=MODES); s.add_argument("--seconds", default="5", choices=("5", "8", "10", "15"))
    s.add_argument("--seed", type=int, default=-1); s.add_argument("--size"); s.add_argument("--sampler"); s.add_argument("--refine-steps", type=int)
    s.add_argument("--ref", action="append", default=[], help="reference image, repeat for ref_1..ref_9 (order = <Picture N>)")
    w = sub.add_parser("wait"); w.set_defaults(fn=cmd_wait); w.add_argument("names", nargs="+"); w.add_argument("--timeout", type=float, default=5400)
    v = sub.add_parser("verify"); v.set_defaults(fn=cmd_verify); v.add_argument("name"); v.add_argument("--out", default="results")
    c = sub.add_parser("cu"); c.set_defaults(fn=cmd_cu); c.add_argument("action", choices=("add", "report"))
    c.add_argument("--balance", type=float); c.add_argument("--note"); c.add_argument("--log", default="cu-log.jsonl")
    g = sub.add_parser("gif"); g.set_defaults(fn=cmd_gif); g.add_argument("input"); g.add_argument("out")
    g.add_argument("--width", type=int, default=480); g.add_argument("--fps", type=int, default=24); g.add_argument("--start", type=float, default=0); g.add_argument("--dur", type=float)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
