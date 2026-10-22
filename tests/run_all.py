"""Run every test script in this folder (no pytest needed): python tests/run_all.py"""
import subprocess, sys
from pathlib import Path

failed = []
for t in sorted(Path(__file__).parent.glob("test_*.py")):
    r = subprocess.run([sys.executable, str(t)], capture_output=True, text=True, encoding="utf-8")
    print(("PASS " if r.returncode == 0 else "FAIL ") + t.name, (r.stdout.strip().splitlines() or [""])[-1])
    if r.returncode:
        failed.append(t.name); print(r.stderr[-800:])
sys.exit(1 if failed else 0)
