from pathlib import Path as _P
BACKEND = _P(__file__).resolve().parents[1] / "src" / "h3_backend.py"
import types
m = types.ModuleType("h3"); exec(compile(open(BACKEND, encoding="utf-8").read(),"b","exec"), m.__dict__)
import tempfile; from pathlib import Path
for mode, steps, lora in (("turbo",8,"turbo_8step"),("turbo4",4,"turbo_4step"),("quality",20,None)):
    for prof in ("int8","full"):
        c = m.clean_config({"prompt":"x","mode":mode})
        g = m.graph_for(c, prof)
        assert c["steps"]==steps and g["11"]["inputs"]["steps"]==steps
        if lora:
            assert lora in g["2"]["inputs"]["lora_name"]
            assert g["8"]["inputs"]["model"]==["2",0]==g["11"]["inputs"]["model"]
        else:
            assert "2" not in g and g["8"]["inputs"]["model"]==["1",0]
        assert sum(1 for n in g.values() if n["class_type"].startswith("LoraLoader"))==(1 if lora else 0)
        for k,n in g.items():
            for v in n["inputs"].values():
                if isinstance(v,list): assert v[0] in g, (k,v)
for bad in ({"prompt":"x","mode":"nope"},{"prompt":""},{"prompt":"x","seed":-5},{"prompt":"x","first_frame":"../etc"}):
    try: m.clean_config(bad); raise SystemExit("accepted "+str(bad))
    except ValueError: pass
print("graph OK")
