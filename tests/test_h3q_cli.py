import json, subprocess, sys, tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "skills" / "h3-colab-studio" / "scripts" / "h3q.py"
tmp = Path(tempfile.mkdtemp())
q = tmp / "q"
for d in ("inbox", "running", "done", "failed"):
    (q / d).mkdir(parents=True)
(tmp / "p.txt").write_text("integrated_multimodal_description: [Shot 1] test", encoding="utf-8")
(tmp / "a.png").write_bytes(b"png")
(tmp / "b.png").write_bytes(b"png")


def h3q(*args):
    return subprocess.run([sys.executable, str(CLI), "--queue", str(q), *args], capture_output=True, text=True, encoding="utf-8")


r = h3q("status"); assert "heartbeat: none" in r.stdout and r.returncode == 0
r = h3q("submit", "job1", "--prompt-file", str(tmp / "p.txt"), "--mode", "omni_hd", "--seconds", "10", "--seed", "7", "--ref", str(tmp / "a.png"), "--ref", str(tmp / "b.png"))
assert r.returncode == 0, r.stderr
cfg = json.loads((q / "inbox" / "job1.json").read_text(encoding="utf-8"))
assert cfg["images"] == ["ref_1", "ref_2"] and cfg["mode"] == "omni_hd" and cfg["seconds"] == "10" and cfg["seed"] == 7
assert (q / "inbox" / "job1.ref_1.png").exists() and (q / "inbox" / "job1.ref_2.png").exists() and not list((q / "inbox").glob("*.part"))
assert h3q("submit", "job1", "--prompt", "x").returncode != 0            # duplicate id
assert h3q("submit", "bad/name", "--prompt", "x").returncode != 0         # unsafe id
assert h3q("submit", "job2", "--prompt", "x", "--ref", str(tmp / "missing.png")).returncode != 0
assert h3q("submit", "job3", "--prompt", "  ").returncode != 0            # empty prompt
log = tmp / "cu.jsonl"
assert h3q("cu", "add", "--log", str(log), "--balance", "100", "--note", "a").returncode == 0
assert h3q("cu", "add", "--log", str(log), "--balance", "99", "--note", "b").returncode == 0
assert "total 1.00 CU" in h3q("cu", "report", "--log", str(log)).stdout
print("h3q OK")
