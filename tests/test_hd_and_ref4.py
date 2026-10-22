from pathlib import Path as _P
BACKEND = _P(__file__).resolve().parents[1] / "src" / "h3_backend.py"
import types, tempfile
from pathlib import Path
m = types.ModuleType("h3"); exec(compile(open(BACKEND, encoding="utf-8").read(), "b", "exec"), m.__dict__)
m.COMFY = Path(tempfile.mkdtemp()); (m.COMFY / "input").mkdir()
for n in ("h3ref_a.png", "h3ref_b.png"): (m.COMFY / "input" / n).write_bytes(b"x")
def wired(g):
    for k, nd in g.items():
        for v in nd["inputs"].values():
            if isinstance(v, list): assert v[0] in g, (k, v)
# omni_hd: default p480, graph shape
c = m.clean_config({"prompt": "<Picture 1> x", "mode": "omni_hd", "seconds": "15", "ref_1": "h3ref_a.png", "seed": 7})
assert (c["width"], c["height"], c["frames"], c["steps"], c["refine_steps"]) == (832, 480, 362, 8, 4), c
for prof in ("int8", "int8enc"):
    g = m.graph_for(c, prof, "h3_lab/x"); wired(g)
    assert g["48"]["inputs"]["step"] == 4 and g["48"]["inputs"]["sigmas"] == ["11", 0]
    assert g["50"]["inputs"]["sigmas"] == ["48", 1] and g["50"]["inputs"]["latent_image"] == ["44", 0]
    assert g["44"]["inputs"]["audio_latent"] == ["40", 1] and g["40"]["inputs"]["av_latent"] == ["12", 0]
    assert g["45"]["inputs"]["width"] == 1280 and g["45"]["inputs"]["height"] == 736 and g["45"]["inputs"]["ref_images.ref_image_0"] == ["30", 0]
    assert g["13"]["inputs"]["samples"] == ["50", 0] and g["14"]["inputs"]["samples"] == ["50", 0]
    assert g["51"]["inputs"] == {"image": ["13", 0], "width": 1280, "height": 720, "x": 0, "y": 8} and g["15"]["inputs"]["images"] == ["51", 0]
    assert g["49"]["inputs"]["noise_seed"] == 8 and g["12"]["inputs"]["noise"] == ["9", 0] and g["9"]["inputs"]["noise_seed"] == 7
    assert g["60"]["inputs"]["images"] == ["41", 0] and "audio" not in g["60"]["inputs"]
    assert g["46"]["inputs"]["model"] == ["16", 0] and g["7"]["inputs"]["width"] == 832 and g["7"]["inputs"]["height"] == 480
    assert not any("LoraLoader" in n["class_type"] for n in g.values())
# refine_steps 3 and portrait
c3 = m.clean_config({"prompt": "x", "mode": "omni_hd", "size": "p480v", "refine_steps": 3, "ref_1": "h3ref_a.png"})
g3 = m.graph_for(c3); assert g3["48"]["inputs"]["step"] == 5 and g3["45"]["inputs"]["width"] == 736 and g3["51"]["inputs"]["x"] == 8 and g3["51"]["inputs"]["width"] == 720 and g3["51"]["inputs"]["height"] == 1280
for bad in ({"size": "landscape"}, {"refine_steps": 1}, {"refine_steps": 7}, {}):
    try: m.clean_config({"prompt": "x", "mode": "omni_hd", "ref_1": "h3ref_a.png", **bad}); 
    except ValueError: continue
    if bad: raise SystemExit("accepted " + str(bad))
# ref4: LoRA once, 4 steps, refs, no sigma shift, ref2va model
r = m.clean_config({"prompt": "x", "mode": "ref4", "size": "p480", "seconds": "10", "ref_1": "h3ref_a.png"})
gr = m.graph_for(r); wired(gr)
assert r["steps"] == 4 and "ref2va_pruned_int8" in gr["1"]["inputs"]["unet_name"] and "ref2v_turbo_4step" in gr["2"]["inputs"]["lora_name"]
assert gr["8"]["inputs"]["model"] == ["2", 0] == gr["11"]["inputs"]["model"] and "16" not in gr and gr["7"]["class_type"] == "MiniMaxH3ReferenceToVideo" and gr["11"]["inputs"]["steps"] == 4
assert sum("LoraLoader" in n["class_type"] for n in gr.values()) == 1
# plain omni draft at p480 still the old shape
o = m.clean_config({"prompt": "x", "mode": "omni", "size": "p480", "seconds": "15", "ref_1": "h3ref_a.png"}); go = m.graph_for(o)
assert "40" not in go and go["13"]["inputs"]["samples"] == ["12", 0] and (o["width"], o["height"], o["frames"]) == (832, 480, 362)
# non-ref modes without refs still work, ref modes need refs
for mode in ("omni", "omni_hd", "ref4"):
    try: m.clean_config({"prompt": "x", "mode": mode}); raise SystemExit("no refs accepted " + mode)
    except ValueError: pass
m.graph_for(m.clean_config({"prompt": "x", "mode": "turbo"}))
print("hd OK")
