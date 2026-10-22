from pathlib import Path as _P
BACKEND = _P(__file__).resolve().parents[1] / "src" / "h3_backend.py"
import json, os, shutil, tempfile, time, base64, types
from pathlib import Path
m = types.ModuleType("h3"); exec(compile(open(BACKEND, encoding="utf-8").read(),"b","exec"), m.__dict__)
def mk():
    root = Path(tempfile.mkdtemp())/"q"; m.queue_init(root); return root
tmp = Path(tempfile.mkdtemp()); (tmp/"v").write_bytes(b"12345"); (tmp/"s").write_text("{}")
ok = lambda c,i: (tmp/"v", tmp/"s")
val = lambda c: c
ls = lambda r,d: sorted(p.name for p in (r/d).iterdir())
put = lambda r,n,t: (r/"inbox"/n).write_text(t)
# 1 normal + marker has size, images via siblings
r = mk(); put(r,"a.json",json.dumps({"prompt":"x","images":["first_frame"]}))
seen=[]; m.agent_loop(r,poll=0,runner=lambda c,i:(seen.append((c,i)),(tmp/"v",tmp/"s"))[1],validate=val,max_loops=1)
assert not seen and ls(r,"running")==[] , "must wait for declared image"   # image missing, not claimed
(r/"inbox"/"a.first_frame.png").write_bytes(b"png")
m.agent_loop(r,poll=0,runner=lambda c,i:(seen.append((c,i)),(tmp/"v",tmp/"s"))[1],validate=val,max_loops=1)
assert seen and "first_frame" in seen[0][1] and "images" not in seen[0][0]
assert json.loads((r/"done"/"a.json").read_text())["video_bytes"]==5
# 2 missing image after timeout -> failed
r = mk(); put(r,"b.json",json.dumps({"prompt":"x","images":["last_frame"]}))
old=time.time()-m.IMAGE_WAIT_SECONDS-5; os.utime(r/"inbox"/"b.json",(old,old))
m.agent_loop(r,poll=0,runner=ok,validate=val,max_loops=1); assert "b.json" in ls(r,"failed")
# 3 KeyboardInterrupt -> job back in inbox with images kept
r = mk(); put(r,"c.json",json.dumps({"prompt":"x","images":["first_frame"]})); (r/"inbox"/"c.first_frame.png").write_bytes(b"png")
def boom(c,i): raise KeyboardInterrupt
try: m.agent_loop(r,poll=0,runner=boom,validate=val,max_loops=1); raise SystemExit("not raised")
except KeyboardInterrupt: pass
assert ls(r,"inbox")==["c.first_frame.png","c.json"] and ls(r,"running")==[] and ls(r,"failed")==[]
# 4 stale STOP cleared at start
r = mk(); (r/"STOP").write_text(""); put(r,"d.json",json.dumps({"prompt":"x"}))
m.agent_loop(r,poll=0,runner=ok,validate=val,max_loops=1); assert "d.json" in ls(r,"done") and not (r/"STOP").exists()
# 5 STOP created mid-run ends loop; bad json fails; dup skipped; crash recovered
r = mk(); put(r,"bad.json","{x"); (r/"running"/"crash.json").write_text(json.dumps({"prompt":"c"}))
(r/"running"/"dup.json").write_text("{}"); (r/"done"/"dup.json").write_text("{}")
def stopper(c,i): (r/"STOP").write_text(""); return tmp/"v", tmp/"s"
m.agent_loop(r,poll=0,runner=stopper,validate=val,max_loops=50)
assert "bad.json" in ls(r,"failed") and "crash.json" in ls(r,"done") and ls(r,"running")==[] and "dup.mp4" not in ls(r,"done")
print("queue2 OK")
