from pathlib import Path as _P
BACKEND = _P(__file__).resolve().parents[1] / "src" / "h3_backend.py"
import types, tempfile, json
from pathlib import Path
m = types.ModuleType("h3"); exec(compile(open(BACKEND, encoding="utf-8").read(), "b", "exec"), m.__dict__)
m.COMFY = Path(tempfile.mkdtemp()); (m.COMFY / "input").mkdir()
for n in ("h3ref_a.png", "h3ref_b.png", "h3ref_c.png"): (m.COMFY / "input" / n).write_bytes(b"x")
# omni: refs from ref_N, ordered; UI first/last fallback
c = m.clean_config({"prompt": "<Picture 1> walks", "mode": "omni", "ref_2": "h3ref_b.png", "ref_1": "h3ref_a.png"})
assert c["refs"] == ["h3ref_a.png", "h3ref_b.png"] and c["steps"] == 8 and "first_frame" not in c
c2 = m.clean_config({"prompt": "x", "mode": "omni", "first_frame": "h3ref_c.png"}); assert c2["refs"] == ["h3ref_c.png"]
for prof in ("int8", "full"):
    g = m.graph_for(c, prof)
    n7 = g["7"]; assert n7["class_type"] == "MiniMaxH3ReferenceToVideo"
    assert n7["inputs"]["ref_images.ref_image_0"] == ["30", 0] and n7["inputs"]["ref_images.ref_image_1"] == ["31", 0]
    assert g["30"]["inputs"]["image"] == "h3ref_a.png"
    assert g["16"]["class_type"] == "MiniMaxH3SigmaShift" and g["16"]["inputs"]["shift_video"] == 12.0
    assert g["8"]["inputs"]["model"] == ["16", 0] == g["11"]["inputs"]["model"]
    assert "2" not in g and "fasth3_omniref_8step" in g["1"]["inputs"]["unet_name"]
    assert "first_frame" not in n7["inputs"] and "last_frame" not in n7["inputs"]
    assert g["13"]["inputs"]["vae"] == ["4", 0] and g["14"]["inputs"]["vae"] == ["5", 0]
    for k, nd in g.items():
        for v in nd["inputs"].values():
            if isinstance(v, list): assert v[0] in g, (k, v)
assert not any("LoraLoader" in nd["class_type"] for nd in g.values())
# omni without refs rejected at submit-time validation, allowed in queue pre-validation
try: m.clean_config({"prompt": "x", "mode": "omni"}); raise SystemExit("accepted")
except ValueError: pass
assert m.clean_config({"prompt": "x", "mode": "omni"}, need_refs=False)["refs"] == []
# non-omni drops ref_N; sampler option
c3 = m.clean_config({"prompt": "x", "mode": "turbo", "ref_1": "h3ref_a.png", "sampler": "euler+beta"})
assert "refs" not in c3 and "ref_1" not in c3
g3 = m.graph_for(c3); assert g3["10"]["inputs"]["sampler_name"] == "euler" and g3["11"]["inputs"]["scheduler"] == "beta"
try: m.clean_config({"prompt": "x", "sampler": "ddim"}); raise SystemExit("accepted")
except ValueError: pass
try: m.clean_config({"prompt": "x", "mode": "omni", "ref_1": "../etc/passwd"}); raise SystemExit("accepted")
except ValueError: pass
print("omni OK")

# --- patch3 checks ---
for bad in ({"ref_1": "h3ref_a.png", "ref_3": "h3ref_c.png"}, {"ref_2": "h3ref_b.png"}):
    try: m.clean_config({"prompt": "x", "mode": "omni", **bad}); raise SystemExit("accepted gap")
    except ValueError: pass
pe = m.PROFILES["int8enc"]; assert "int8_convrot" in pe["files"]["text"] and m.OMNI_FILES["int8enc"] and m.graph_for(c, "int8enc")["3"]["inputs"]["clip_name"].endswith("int8_convrot.safetensors")
# two-pass validation through the real comfy_runner with fake ComfyUI calls
seen = {}
m.upload_image = lambda data, name="image": {"filename": "h3ref_up%d.png" % len(seen)} if seen.setdefault(len(seen), 1) else None
for i in range(0, 3): (m.COMFY / "input" / ("h3ref_up%d.png" % i)).write_bytes(b"x")
rec = {}
def fake_submit(cfg): rec["cfg"] = m.clean_config(cfg); return {"id": "job1"}
m.submit = fake_submit; m.status = lambda j: {"state": "done"}
m.OUTPUT = Path(tempfile.mkdtemp())
imgs = {k: Path(tempfile.mktemp()) for k in ("ref_1", "ref_2")}
for p in imgs.values(): p.write_bytes(b"png")
pre = m.clean_config({"prompt": "<Picture 1> x", "mode": "omni"}, need_refs=False)
m.comfy_runner(dict(pre), imgs)
assert rec["cfg"]["mode"] == "omni" and rec["cfg"]["refs"] == ["h3ref_up1.png", "h3ref_up2.png"], rec
print("omni2 OK")

# --- UI multi-ref: 9 slots accepted, gaps rejected, refs win over first/last ---
for i in range(1, 10): (m.COMFY / "input" / f"h3ref_{i}.png").write_bytes(b"x")
c9 = m.clean_config({"prompt": "x", "mode": "omni", **{f"ref_{i}": f"h3ref_{i}.png" for i in range(1, 10)}})
assert c9["refs"] == [f"h3ref_{i}.png" for i in range(1, 10)]
assert m.clean_config({"prompt": "x", "mode": "omni", "first_frame": "h3ref_c.png", "ref_1": "h3ref_a.png"})["refs"] == ["h3ref_a.png"]
try: m.clean_config({"prompt": "x", "mode": "omni", "ref_1": "h3ref_a.png", "ref_3": "h3ref_c.png"}); raise SystemExit("gap accepted")
except ValueError: pass
print("omni multiref OK")
