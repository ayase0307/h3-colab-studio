"""Self-contained MiniMax H3 backend for a Colab notebook. No public server."""
from __future__ import annotations

import base64
import html
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from pathlib import Path

BASE = Path(os.environ.get("H3_LAB_DIR", "/content/h3-lab"))
COMFY = BASE / "ComfyUI"
OUTPUT = BASE / "results"
PORT = 8193
URL = f"http://127.0.0.1:{PORT}"
# ce42de5f (2026-10-18) adds "models with PDD baked in", which FastH3 Omni needs; the older pin fails in sampling.
COMFY_COMMIT = "ce42de5f64ac1d421e304ab7b6c0b3d2f0dde1f6"
VHS_COMMIT = "4d907bee61e92c2e65af3bd6383a4e4d356126d1"
MODEL_REVISION = "e5eb578a89295337b8ff433a035929ce0279e0b6"
COMMON = {"audio": "vae/minimax_h3_audio_vae_fp32.safetensors", "lora": "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "lora4": "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"}
PROFILES = {
    "int8": {"label": "INT8（量化）", "min_vram": 38, "min_ram": 60, "free_disk": 58,
             "files": {**COMMON, "model": "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "text": "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "video": "vae/minimax_h3_video_vae_fp16.safetensors"}},  # fp16 VAE: int8 VAE adds blocky/flicker artifacts, saves <1 GB
    "full": {"label": "BF16 / FP16（非量化）", "min_vram": 75, "min_ram": 120, "free_disk": 120,
             "files": {**COMMON, "model": "diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors", "text": "text_encoders/qwen3vl_32b_minimax_h3_bf16.safetensors", "video": "vae/minimax_h3_video_vae_fp16.safetensors"}},
}
OMNI_REPO = "FastVideo/FastH3-Omni-Comfy"
OMNI_REVISION = "82eff2a6eee6c962846879f4bab52610a4df24d3"
OMNI_FILES = {"int8": "diffusion_models/fasth3_omniref_8step_pruned_int8_convrot.safetensors", "full": "diffusion_models/fasth3_omniref_8step_pruned_bf16.safetensors"}
OMNI_FILES["int8enc"] = OMNI_FILES["int8"]
OMNI_DISK_GIB = {"int8": 22, "int8enc": 22, "full": 42}
MAX_REFS = 9
IMAGE_NAMES = ("first_frame", "last_frame") + tuple(f"ref_{i}" for i in range(1, MAX_REFS + 1))
SAMPLERS = {"res_multistep+simple": ("res_multistep", "simple"), "euler+beta": ("euler", "beta"), "euler+simple": ("euler", "simple")}
PROFILES["int8enc"] = {**PROFILES["int8"], "label": "INT8（INT8 文字編碼器）", "free_disk": 70,
                       "files": {**PROFILES["int8"]["files"], "text": "text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors"}}
# Ref2VA INT8 + ref2v turbo 4-step LoRA: the alternative draft engine to compare against Omni.
REF4_FILES = {"model": "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors", "lora": "loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"}
REF4_DISK_GIB = 23
# Ayase Studio recipe: HyperFlow 8-step LoRA, 8-step draft at ~0.5 MP, neural latent upscale, low-denoise second pass.
AYASE_LORA = ("drbaph/MiniMax-H3-Turbo-Lora-ComfyUI", "bb2bc497cbaca89dadd0bcf1856eed4f8275be20", "minimax_h3_hyperflow_8step_v1.0_comfyui_pruned_bf16_resized_avg_rank_20_bf16.safetensors")
AYASE_UPSCALER = ("LBH-123-AI/Minimax_h3_latent_Upscaler", "3f941d5d182014dd5c0a5e16330420ee2d4aa0c6", "minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors")
AYASE_UPSCALER_NAME = "minimax_h3_latent_upscaler_3d_fp16.safetensors"  # the node only lists files whose name has "3d" and "fp16"
AYASE_NODES = ("https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler.git", "40316cf008b2fd8663263270669eb4da23f89d2c")  # MIT, user-approved, pinned
AYASE_DISK_GIB = 2
AYASE_REPAIR = "修復一採中的結構畸形、重影、重複或缺失部件、破損邊緣、紋理斷裂和閃爍；嚴格保持原劇情時序、運鏡、構圖、主體身份、服裝、動作、場景、畫面風格和正常區域不變。"
REF_MODES = ("omni", "omni_hd", "ref4", "ref2va", "ref2va_hd", "ayase")
HD_MODES = ("omni_hd", "ref2va_hd")
# draft size -> (render w, render h, crop w, crop h, crop x, crop y). 720 is not on H3's 32-px grid, so render 736 and crop in-graph.
HD_TARGETS = {"p480": (1280, 736, 1280, 720, 0, 8), "p480v": (736, 1280, 720, 1280, 8, 0)}
SIZES = {"p480": (832, 480), "p480v": (480, 832), "landscape": (960, 544), "portrait": (544, 960), "square": (768, 768), "native": (1344, 768), "p720": (1280, 704), "hd": (1280, 736), "hdv": (736, 1280)}  # hd = native 736p single pass, as the RTX 5090 reference clip
FRAMES = {"5": 124, "8": 192, "10": 243, "15": 362}
_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_active: str | None = None
_process = None


def _request(method, route, **kwargs):
    import requests
    response = requests.request(method, URL + route, timeout=kwargs.pop("timeout", 30), **kwargs)
    if not response.ok:
        raise RuntimeError(f"ComfyUI {response.status_code}: {response.text[:2500]}")
    return response.json()


def _run(args, **kwargs):
    if "stdout" in kwargs:
        subprocess.run(args, check=True, **kwargs)
    else:
        with (BASE / "setup.log").open("a") as log:
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT, **kwargs)


def _checkout(url, destination, commit):
    if not (destination / ".git").exists():
        destination.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", str(destination)])
        _run(["git", "-C", str(destination), "remote", "add", "origin", url])
    current = subprocess.run(["git", "-C", str(destination), "rev-parse", "HEAD"], capture_output=True, text=True)
    if current.returncode or current.stdout.strip() != commit:
        _run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", commit])
        _run(["git", "-C", str(destination), "checkout", "--detach", commit])


def hardware():
    """Works before pip/torch setup, including CPU-only runtimes."""
    info = dict(gpu=None, vram_gib=0, ram_gib=0, free_disk_gib=0)
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            name, memory = result.stdout.strip().splitlines()[0].rsplit(",", 1)
            info.update(gpu=name.strip(), vram_gib=float(memory.strip()) / 1024)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    try:
        info["ram_gib"] = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2**30
    except (ValueError, OSError):
        import psutil
        info["ram_gib"] = psutil.virtual_memory().total / 2**30
    info["free_disk_gib"] = shutil.disk_usage(BASE if BASE.exists() else Path.cwd()).free / 2**30
    return info


def gpu_issues(info, profile="int8"):
    selected = PROFILES[profile]
    if not info["gpu"]:
        return ["未偵測到 GPU"]
    issues = []
    if info["vram_gib"] < selected["min_vram"]:
        issues.append("GPU 記憶體不足")
    if info["ram_gib"] < selected["min_ram"]:
        issues.append("主記憶體不足")
    return issues


def gpu_card(info, profile="int8"):
    issues = gpu_issues(info, profile)
    label = " / ".join(issues) if issues else "GPU OK"
    color = "#9b620a" if issues else "#14765e"
    device = html.escape(info["gpu"] or "無 GPU")
    instructions = []
    if not info["gpu"] or info["vram_gib"] < PROFILES[profile]["min_vram"]:
        instructions.append("選擇「A100 GPU」")
    if info["gpu"] and info["ram_gib"] < PROFILES[profile]["min_ram"]:
        instructions.append("開啟「高 RAM」")
    guide = ('<ol style="padding-left:22px;margin:10px 0 0">'
             '<li>右上角「連線」旁的 ▼ →「變更執行階段類型」</li>'
             + ''.join('<li>' + step + '</li>' for step in instructions)
             + '<li>「儲存」並重新連線後，再按一次 ▶</li></ol>') if issues else ""
    if not info["gpu"] or info["vram_gib"] < PROFILES[profile]["min_vram"]:
        guide += '<p style="margin:8px 0 0;font-size:12px">若無法選擇 A100，請確認 Colab 的方案與剩餘用量。不支援免費的 T4。</p>'
    if issues and profile == "full":
        guide += '<p>非量化版需要 A100 80GB。也可以在模型設定中選擇「INT8」。</p>'
    return f"""<div style="font:14px/1.65 system-ui;padding:16px;border:1px solid #dce3ef;border-radius:12px;max-width:700px">
    <b style="color:{color}">{html.escape(label)}</b><div>{device} · GPU {info['vram_gib']:.0f} GB · RAM {info['ram_gib']:.0f} GB</div>{guide}
    <details style="margin-top:10px;font-size:12px"><summary>檢查指令</summary><code>!nvidia-smi</code></details></div>"""


class SetupProgress:
    """One output card, updated even while a download or pip command runs."""
    def __init__(self):
        self.started = time.monotonic()
        self.message = "檢查 GPU 中"
        self.step = 0
        self.error = False
        self.stopped = threading.Event()
        from IPython.display import HTML, display
        self.handle = display(HTML(self.render()), display_id=True)
        self.thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.thread.start()

    def render(self):
        elapsed = int(time.monotonic() - self.started)
        color = "#922c36" if self.error else "#4c48d9"
        return f'<div style="font:14px/1.6 system-ui;max-width:700px;padding:16px;border:1px solid #dce3ef;border-radius:12px"><b style="color:{color}">{html.escape(self.message)}</b><div style="color:#68758d;font-size:12px">已耗時 {elapsed//60} 分 {elapsed%60:02d} 秒 · 首次預估 數分鐘至 20 分鐘（依網路而異）</div><progress aria-label="準備流程" max="3" value="{self.step}" style="width:100%;accent-color:{color}"></progress></div>'

    def update(self, message, step):
        from IPython.display import HTML
        self.message, self.step = message, step
        self.handle.update(HTML(self.render()))

    def heartbeat(self):
        from IPython.display import HTML
        while not self.stopped.wait(1):
            self.handle.update(HTML(self.render()))

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=2)


def setup(profile="int8", omni=True, ref4=False):
    if _active:
        record = json.loads((BASE / "setup.json").read_text())
        if record.get("profile") == profile:
            return record  # Reopen the UI and reconnect to the running job.
        raise RuntimeError("影片生成中無法變更設定。請等待完成或中止後再執行。")
    if profile not in PROFILES:
        raise ValueError("模型設定不正確。")
    BASE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    selected = PROFILES[profile]
    info = hardware()
    if gpu_issues(info, profile):
        from IPython.display import HTML, display
        display(HTML(gpu_card(info, profile)))
        return None
    if ref4 and profile == "full":
        raise RuntimeError("Ref2VA 4 步草稿目前只支援 INT8 設定。")
    wanted = list(selected["files"].values()) + ([OMNI_FILES[profile]] if omni else []) + (list(REF4_FILES.values()) if ref4 else []) + (["loras/" + AYASE_LORA[2], "latent_upscale_models/" + AYASE_UPSCALER_NAME] if ref4 else [])
    need_disk = selected["free_disk"] + (OMNI_DISK_GIB[profile] if omni else 0) + (REF4_DISK_GIB + AYASE_DISK_GIB if ref4 else 0)
    if info["free_disk_gib"] < need_disk and not all((COMFY / "models" / f).exists() for f in wanted):
        raise RuntimeError(f"首次執行需要至少 {need_disk} GiB 的可用空間。")
    progress = SetupProgress()
    try:
        if (BASE / "setup.json").exists():
            cached = json.loads((BASE / "setup.json").read_text())
            if (cached.get("profile"), cached.get("comfy_commit"), cached.get("vhs_commit"), cached.get("model_revision")) == (profile, COMFY_COMMIT, VHS_COMMIT, MODEL_REVISION) and bool(cached.get("omni")) == omni and bool(cached.get("ref4")) == ref4 and all((COMFY / "models" / f).exists() for f in wanted):
                progress.update("連線到生成畫面中", 2)
                start_server(omni)
                progress.update("準備完成 ↓ 請在下方畫面製作影片", 3)
                return cached
        progress.update("1/3 準備環境中", 0)
        torch_probe = subprocess.run([sys.executable, "-c", "import torch; print(torch.version.cuda or '0')"], capture_output=True, text=True, timeout=60)
        cuda = torch_probe.stdout.strip().split(".")[0] if torch_probe.returncode == 0 else "0"
        if profile != "full" and int(cuda or "0") < 13:
            _run([sys.executable, "-m", "pip", "install", "-q", "torch==2.11.0", "torchvision==0.26.0", "torchaudio==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu130"])
        if (COMFY / ".git").exists():
            head = subprocess.run(["git", "-C", str(COMFY), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            if head != COMFY_COMMIT:  # a server started from the old checkout would keep running old code
                subprocess.run(["pkill", "-f", str(COMFY / "main.py")])
                time.sleep(3)
        _checkout("https://github.com/Comfy-Org/ComfyUI.git", COMFY, COMFY_COMMIT)
        vhs = COMFY / "custom_nodes" / "ComfyUI-VideoHelperSuite"
        _checkout("https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git", vhs, VHS_COMMIT)
        _run([sys.executable, "-m", "pip", "install", "-q", "-r", str(COMFY / "requirements.txt"), "-r", str(vhs / "requirements.txt"), "huggingface_hub", "hf_xet", "psutil", "requests", "Pillow", "imageio-ffmpeg", "websocket-client"])
        downloads = [("Comfy-Org/MiniMax-H3", name, MODEL_REVISION) for name in selected["files"].values()]
        if omni:
            downloads.append((OMNI_REPO, OMNI_FILES[profile], OMNI_REVISION))
        if ref4:
            downloads += [("Comfy-Org/MiniMax-H3", name, MODEL_REVISION) for name in REF4_FILES.values()]
        for index, (repo, name, revision) in enumerate(downloads):
            progress.update(f"2/3 下載模型中 · {index + 1}/{len(downloads)}", 1 + index / len(downloads))
            script = "from huggingface_hub import hf_hub_download; import sys; hf_hub_download(sys.argv[1],sys.argv[2],revision=sys.argv[3],local_dir=sys.argv[4])"
            _run([sys.executable, "-c", script, repo, name, revision, str(COMFY / "models")], env={**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1", "HF_XET_HIGH_PERFORMANCE": "1"})
        if ref4:  # Ayase Studio assets ride on the download_ref4 box: HyperFlow LoRA, neural latent upscaler weights and node pack
            _checkout(AYASE_NODES[0], COMFY / "custom_nodes" / "Comfyui_Minimax_h3_latent_Upscaler", AYASE_NODES[1])
            script = "from huggingface_hub import hf_hub_download; import sys; hf_hub_download(sys.argv[1],sys.argv[2],revision=sys.argv[3],local_dir=sys.argv[4])"
            quiet = {**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1", "HF_XET_HIGH_PERFORMANCE": "1"}
            _run([sys.executable, "-c", script, AYASE_LORA[0], AYASE_LORA[2], AYASE_LORA[1], str(COMFY / "models" / "loras")], env=quiet)
            target = COMFY / "models" / "latent_upscale_models"
            _run([sys.executable, "-c", script, AYASE_UPSCALER[0], AYASE_UPSCALER[2], AYASE_UPSCALER[1], str(target)], env=quiet)
            if not (target / AYASE_UPSCALER_NAME).exists():
                shutil.copy2(target / AYASE_UPSCALER[2], target / AYASE_UPSCALER_NAME)
        progress.update("3/3 啟動生成引擎中", 2)
        start_server(omni)
        record = {"profile": profile, "profile_label": selected["label"], "comfy_commit": COMFY_COMMIT, "vhs_commit": VHS_COMMIT, "model_revision": MODEL_REVISION, "omni": omni, "ref4": ref4, "hardware": hardware(), "setup_seconds": round(time.monotonic() - progress.started, 2)}
        (BASE / "setup.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
        progress.update("準備完成 ↓ 請在下方畫面製作影片", 3)
        return record
    except Exception as exc:
        progress.error = True
        progress.update("準備已中止，請重新執行準備儲存格", progress.step)
        from IPython.display import HTML, display
        log = (BASE / "setup.log").read_text(errors="replace")[-5000:] if (BASE / "setup.log").exists() else ""
        display(HTML('<details><summary>錯誤詳情</summary><pre style="white-space:pre-wrap">' + html.escape(str(exc) + "\n" + log) + '</pre></details>'))
        return None
    finally:
        progress.close()


def start_server(omni=False):
    global _process
    try:
        _request("GET", "/system_stats", timeout=2)
        return
    except Exception:
        pass
    log = (BASE / "comfy.log").open("a")
    # Loopback only: neither a public tunnel nor a public Gradio link is created.
    _process = subprocess.Popen([sys.executable, str(COMFY / "main.py"), "--listen", "127.0.0.1", "--port", str(PORT), "--disable-auto-launch"], cwd=COMFY, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(150):
        if _process.poll() is not None:
            raise RuntimeError("生成引擎啟動失敗。\n" + (BASE / "comfy.log").read_text(errors="replace")[-4000:])
        try:
            _request("GET", "/system_stats", timeout=2)
            nodes = _request("GET", "/object_info")
            for required in ("MiniMaxH3ImageToVideo", "VHS_VideoCombine", "VAEDecodeAudio") + (("MiniMaxH3ReferenceToVideo", "MiniMaxH3SigmaShift") if omni else ()):
                if required not in nodes:
                    raise RuntimeError(f"必要節點 {required} 無法載入。請檢查準備紀錄。")
            return
        except Exception:
            time.sleep(2)
    raise TimeoutError("啟動未能在 5 分鐘內完成。請檢查準備紀錄。")


def clean_config(value, need_refs=True):
    if not isinstance(value, dict):
        raise ValueError("設定請以 JSON 物件傳入。")
    prompt = str(value.get("prompt", "")).strip()
    if not prompt or len(prompt) > 16000:
        raise ValueError("請輸入提示詞（16,000 字以內）。")
    seconds = str(value.get("seconds", "5"))
    mode = value.get("mode", "turbo")
    size = value.get("size", "p480" if mode in HD_MODES else ("hd" if mode == "omni" else "landscape"))
    if size not in SIZES or seconds not in FRAMES or mode not in ("turbo", "turbo4", "omni", "omni_hd", "ref4", "ref2va", "ref2va_hd", "ayase", "quality"):
        raise ValueError("請確認畫面比例、長度與品質設定。")
    if mode == "ref2va" and "size" not in value:
        size = "p720"
    if mode in HD_MODES and size not in HD_TARGETS:
        raise ValueError("omni_hd／ref2va_hd 的草稿尺寸只能是 " + " 或 ".join(HD_TARGETS) + "。")
    refine_steps = int(value.get("refine_steps", 4))
    if mode == "ref2va_hd" and "refine_steps" not in value:
        refine_steps = 8  # last 8 of the 20-step schedule
    if not 2 <= refine_steps <= (12 if mode == "ref2va_hd" else 6):
        raise ValueError("refine_steps 請設為 2 至 6（ref2va_hd 可到 12）。")
    steps = {"turbo": 8, "turbo4": 4, "omni": 8, "omni_hd": 8, "ref4": 4, "ayase": 8}.get(mode) or int(value.get("steps", 20))
    if mode in ("ref2va", "ref2va_hd") and not 12 <= steps <= 30:  # official template default 20; audio needs 12+
        raise ValueError("ref2va 的步數請設為 12 至 30。")
    if mode == "ref2va_hd" and refine_steps >= steps:
        raise ValueError("ref2va_hd 的 refine_steps 必須小於 steps，否則二次取樣會完全重畫、忽略草稿。")
    if mode == "quality" and steps not in (16, 20, 25, 30):
        raise ValueError("標準模式的步數請從 16、20、25、30 中選擇。")
    raw_seed = value.get("seed", -1)
    seed = int(raw_seed)
    if isinstance(raw_seed, float) and not raw_seed.is_integer():
        raise ValueError("Seed 請設為整數。")
    if seed != -1 and not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed 請設為 -1（隨機）或 0 至 4294967295。")
    if seed == -1:
        seed = secrets.randbelow(2**32)
    width, height = SIZES[size]
    sampler = value.get("sampler", "euler+simple" if mode in ("ayase", "omni", "omni_hd", "ref4") else "res_multistep+simple")  # distilled few-step models: first-order euler; multistep history smears motion
    if sampler not in SAMPLERS:
        raise ValueError("sampler 只能是 " + " 或 ".join(SAMPLERS) + "。")
    images = {}
    for key in IMAGE_NAMES:
        name = str(value.get(key, ""))
        if name:
            if Path(name).name != name or not name.startswith("h3ref_") or not (COMFY / "input" / name).is_file():
                raise ValueError("請重新上傳參考圖片。")
            images[key] = name
    if mode in REF_MODES:
        # Omni takes ordered references (<Picture 1>, <Picture 2>...); the UI first/last slots count as the first two.
        numbered = [i for i in range(1, MAX_REFS + 1) if f"ref_{i}" in images]
        if numbered != list(range(1, len(numbered) + 1)):
            raise ValueError("參考圖片編號必須從 ref_1 開始連續（ref_N 對應提示詞裡的 <Picture N>）。")
        refs = [images[k] for k in IMAGE_NAMES[2:] if k in images] or [images[k] for k in IMAGE_NAMES[:2] if k in images]
        if not refs and need_refs:
            raise ValueError("參考圖模式（omni、omni_hd、ref4、ref2va、ref2va_hd、ayase）至少需要一張參考圖片。")
        images = {"refs": refs}
    else:
        images = {k: v for k, v in images.items() if k in IMAGE_NAMES[:2]}
    shift = bool(value.get("shift", False))
    if shift and mode not in ("ref4", "ref2va", "ref2va_hd"):
        raise ValueError("shift 只能用在 ref4、ref2va、ref2va_hd（Omni 本來就有 shift）。")
    extra = {}
    if mode == "ayase":
        upscale, second_steps, second_denoise = float(value.get("upscale", 2.0)), int(value.get("second_steps", 7)), float(value.get("second_denoise", 0.22))
        if not 1.25 <= upscale <= 2.5 or not 3 <= second_steps <= 12 or not 0.05 <= second_denoise <= 0.6:
            raise ValueError("ayase 的 upscale 請設為 1.25 至 2.5、second_steps 3 至 12、second_denoise 0.05 至 0.6。")
        extra = dict(tiled=bool(value.get("tiled", False)), upscale=upscale, second_steps=second_steps, second_denoise=second_denoise,
                     target_width=round(width * upscale / 32) * 32, target_height=round(height * upscale / 32) * 32)
    return dict(**extra, shift=shift, sampler=sampler, refine_steps=refine_steps, prompt=prompt, size=size, seconds=seconds, frames=FRAMES[seconds], actual_seconds=FRAMES[seconds] / 24, mode=mode, steps=steps, seed=seed, width=width, height=height, **images)


def upload_image(data_url, _filename="image"):
    from PIL import Image, ImageOps
    if not isinstance(data_url, str) or not data_url.startswith("data:image/") or len(data_url) > 15_000_000:
        raise ValueError("請選擇 10MB 以內的 PNG、JPEG 或 WebP 圖片。")
    raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    if len(raw) > 10 * 1024**2:
        raise ValueError("圖片請限制在 10MB 以內。")
    with Image.open(io.BytesIO(raw)) as source:
        if source.width * source.height > 30_000_000:
            raise ValueError("圖片請限制在 3,000 萬像素以內。")
        picture = ImageOps.exif_transpose(source).convert("RGB")
        picture.thumbnail((2048, 2048))
        name = "h3ref_" + uuid.uuid4().hex + ".png"
        target = COMFY / "input" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        picture.save(target)
    return {"filename": name, "width": picture.width, "height": picture.height}


def _add_refine_pass(graph, config, sampler_name, prefix):
    """Second sampling at 720p: decode draft, resize, re-encode, then run only the tail of the same schedule (8 steps for omni_hd, `refine_steps` of `steps` for ref2va_hd).
    The distilled model was trained on those exact timesteps, so a tail split beats a partial-denoise schedule."""
    rw, rh, cw, ch, cx, cy = HD_TARGETS[config["size"]]
    graph["40"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["12", 0]}}
    graph["41"] = {"class_type": "VAEDecode", "inputs": {"samples": ["40", 0], "vae": ["4", 0]}}
    graph["42"] = {"class_type": "ImageScale", "inputs": {"image": ["41", 0], "upscale_method": "lanczos", "width": rw, "height": rh, "crop": "disabled"}}
    graph["43"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["42", 0], "vae": ["4", 0]}}
    graph["44"] = {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["43", 0], "audio_latent": ["40", 1]}}
    refs = {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["5", 0], "prompt": config["prompt"], "width": rw, "height": rh, "length": config["frames"], "ref_image_size": "match"}
    for index in range(len(config["refs"])):
        refs[f"ref_images.ref_image_{index}"] = [str(30 + index), 0]
    graph["45"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": refs}
    graph["46"] = {"class_type": "BasicGuider", "inputs": {"model": ["16", 0] if "16" in graph else ["1", 0], "conditioning": ["45", 0]}}
    graph["48"] = {"class_type": "SplitSigmas", "inputs": {"sigmas": ["11", 0], "step": config["steps"] - config["refine_steps"]}}
    graph["49"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": (config["seed"] + 1) % 2**32}}
    graph["50"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["49", 0], "guider": ["46", 0], "sampler": ["10", 0], "sigmas": ["48", 1], "latent_image": ["44", 0]}}
    graph["13"]["inputs"]["samples"] = ["50", 0]
    graph["14"]["inputs"]["samples"] = ["50", 0]
    graph["51"] = {"class_type": "ImageCrop", "inputs": {"image": ["13", 0], "width": cw, "height": ch, "x": cx, "y": cy}}
    graph["15"]["inputs"]["images"] = ["51", 0]
    # silent draft preview, to judge draft vs final and to confirm a seed reproduces the draft you picked
    graph["60"] = {"class_type": "VHS_VideoCombine", "inputs": {"images": ["41", 0], "frame_rate": 24, "loop_count": 0, "filename_prefix": prefix + "_draft", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 18, "save_metadata": False, "trim_to_audio": False, "pingpong": False, "save_output": True}}


def _add_ayase_pass(graph, config, prefix):
    """Ayase Studio second sampling: split the AV latent, neural-upscale the video half, re-noise with a new seed and run a
    partial-denoise pass at the target size (BasicScheduler denoise = the studio's sigma tail), then put the first-pass audio back."""
    w2, h2 = config["target_width"], config["target_height"]
    graph["40"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["12", 0]}}
    graph["41"] = {"class_type": "MinimaxH3LatentUpscaler3D", "inputs": {"latent": ["40", 0], "model_name": AYASE_UPSCALER_NAME, "mode": "target dimensions", "mode.width": w2, "mode.height": h2,
                   "align": 32, "enable_temporal_chunking": True, "force_unload": True, "device": "cuda", "precision": "fp16"}}
    graph["42"] = {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["41", 0], "audio_latent": ["40", 1]}}
    refs = {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["5", 0], "prompt": config["prompt"] + "\n\nrepair_instruction:\n" + AYASE_REPAIR, "width": w2, "height": h2, "length": config["frames"], "ref_image_size": "match"}
    for index in range(len(config["refs"])):
        refs[f"ref_images.ref_image_{index}"] = [str(30 + index), 0]
    graph["45"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": refs}
    graph["46"] = {"class_type": "BasicGuider", "inputs": {"model": ["16", 0], "conditioning": ["45", 0]}}
    graph["47"] = {"class_type": "BasicScheduler", "inputs": {"model": ["16", 0], "scheduler": "simple", "steps": config["second_steps"], "denoise": config["second_denoise"]}}
    graph["49"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": (config["seed"] + 1) % 2**32}}
    if config.get("tiled"):
        # Same pack as the upscaler: spatial tiles (the first-pass size) and 243-frame temporal chunks with overlap, as in the user's local single-segment workflow.
        graph["55"] = {"class_type": "MMH3TemporalSplitParamsV10", "inputs": {"chunk_frames": 243, "temporal_overlap_frames": 22, "anchor_strength": 0.999, "motion_anchor_frames": "22", "identity_anchor_frames": 24}}
        graph["56"] = {"class_type": "MMH3SpatialSplitParamsV10", "inputs": {"tile_width": config["width"], "tile_height": config["height"], "overlap_ratio": 0.25, "fade_ratio": 0.5, "min_tile_size": 256, "seam_denoise": 0.7}}
        graph["50"] = {"class_type": "MMH3SplitUpscale", "inputs": {"model": ["16", 0], "conditioning": ["45", 0], "latent": ["42", 0], "noise": ["49", 0], "sampler": ["10", 0], "sigmas": ["47", 0], "cfg": 1.0,
                       "temporal_split_param": ["55", 0], "spatial_split_param": ["56", 0], "seam_polish": "auto", "color_match": True}}
    else:
        graph["50"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["49", 0], "guider": ["46", 0], "sampler": ["10", 0], "sigmas": ["47", 0], "latent_image": ["42", 0]}}
    graph["52"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["50", 0]}}
    graph["53"] = {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["52", 0], "audio_latent": ["40", 1]}}
    graph["13"]["inputs"]["samples"] = ["53", 0]
    graph["14"]["inputs"]["samples"] = ["53", 0]
    graph["54"] = {"class_type": "VAEDecode", "inputs": {"samples": ["40", 0], "vae": ["4", 0]}}
    graph["60"] = {"class_type": "VHS_VideoCombine", "inputs": {"images": ["54", 0], "frame_rate": 24, "loop_count": 0, "filename_prefix": prefix + "_draft", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 18, "save_metadata": False, "trim_to_audio": False, "pingpong": False, "save_output": True}}


def graph_for(config, profile="int8", prefix="h3"):
    files = {k: Path(v).name for k, v in PROFILES[profile]["files"].items()}
    if config["mode"] in ("omni", "omni_hd"):
        files["model"] = Path(OMNI_FILES[profile]).name
    if config["mode"] in ("ref4", "ref2va", "ref2va_hd", "ayase"):
        files["model"], files["lora"] = (Path(v).name for v in REF4_FILES.values())
    if config["mode"] == "ayase":
        files["lora"] = AYASE_LORA[2]
    sampler_name, scheduler = SAMPLERS[config.get("sampler", "res_multistep+simple")]
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": files["model"], "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": files["text"], "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": files["video"]}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": files["audio"]}},
        "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": config["prompt"], "width": config["width"], "height": config["height"], "length": config["frames"]}},
        "8": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["7", 0]}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": config["seed"]}},
        "10": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler_name}},
        "11": {"class_type": "BasicScheduler", "inputs": {"model": ["1", 0], "scheduler": scheduler, "steps": config["steps"], "denoise": 1.0}},
        "12": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["8", 0], "sampler": ["10", 0], "sigmas": ["11", 0], "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["4", 0]}},
        "14": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}},
        "15": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["13", 0], "audio": ["14", 0], "frame_rate": 24, "loop_count": 0, "filename_prefix": prefix, "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 18, "save_metadata": True, "trim_to_audio": False, "pingpong": False, "save_output": True}},
    }
    if config["mode"] in ("turbo", "turbo4"):  # exactly one turbo LoRA; never stack two
        graph["2"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": files["lora" if config["mode"] == "turbo" else "lora4"], "strength_model": 1.0}}
        graph["8"]["inputs"]["model"] = ["2", 0]
        graph["11"]["inputs"]["model"] = ["2", 0]
    if config["mode"] == "ref4":  # official ref2v template path: the 4-step turbo LoRA only, no extra shift node
        graph["2"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": files["lora"], "strength_model": 1.0}}
        graph["8"]["inputs"]["model"] = ["2", 0]
        graph["11"]["inputs"]["model"] = ["2", 0]
    if config["mode"] == "ayase":  # HyperFlow LoRA, then video/audio shift 12/3 (the sigma grid HyperFlow was trained on)
        graph["2"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": files["lora"], "strength_model": 1.0}}
        graph["16"] = {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["2", 0], "shift_video": 12.0, "shift_audio": 3.0}}
        graph["8"]["inputs"]["model"] = ["16", 0]
        graph["11"]["inputs"]["model"] = ["16", 0]
    if config["mode"] in ("omni", "omni_hd"):
        # FastH3 Omni is already 8-step distilled: no turbo LoRA, video/audio shift 12/3 as its README says.
        graph["16"] = {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1", 0], "shift_video": 12.0, "shift_audio": 3.0}}
        graph["8"]["inputs"]["model"] = ["16", 0]
        graph["11"]["inputs"]["model"] = ["16", 0]
    if config.get("shift"):  # opt-in video/audio shift 12/3: community Ref2VA workflows and Ayase Studio use it, the official r2v template does not
        graph["16"] = {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": graph["8"]["inputs"]["model"], "shift_video": 12.0, "shift_audio": 3.0}}
        graph["8"]["inputs"]["model"] = ["16", 0]
        graph["11"]["inputs"]["model"] = ["16", 0]
    # ref2va = official Comfy-Org r2v template: non-distilled Ref2VA, no LoRA, no shift node (unless shift=true), BasicGuider, res_multistep + simple
    if config["mode"] in REF_MODES:
        graph["7"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["5", 0], "prompt": config["prompt"], "width": config["width"], "height": config["height"], "length": config["frames"], "ref_image_size": "match"}}
        for index, name in enumerate(config["refs"]):
            graph[str(30 + index)] = {"class_type": "LoadImage", "inputs": {"image": name}}
            graph["7"]["inputs"][f"ref_images.ref_image_{index}"] = [str(30 + index), 0]
    if config["mode"] in HD_MODES:
        _add_refine_pass(graph, config, sampler_name, prefix)
    if config["mode"] == "ayase":
        _add_ayase_pass(graph, config, prefix)
    for number, key in (("20", "first_frame"), ("21", "last_frame")):
        if config.get(key):
            graph[number] = {"class_type": "LoadImage", "inputs": {"image": config[key]}}
            graph["7"]["inputs"][key] = [number, 0]
    return graph


def _update(job_id, **values):
    with _lock:
        _jobs[job_id].update(values)


def _progress_event(job_id, prompt_id, event):
    data = event.get("data", {})
    if data.get("prompt_id") != prompt_id:
        return
    if event.get("type") == "executing":
        node = str(data.get("node"))
        if node != "None":
            with _lock:  # per-node start times, so draft / refine / decode can be timed separately
                _jobs[job_id].setdefault("timeline", []).append([node, round(time.time() - _jobs[job_id]["started"], 1)])
        stage, message = {
            "1": ("loading", "載入模型中"), "3": ("loading", "載入模型中"),
            "7": ("loading", "載入提示詞中"), "12": ("sampling", "生成影片與音訊中"),
            "40": ("sampling", "放大草稿並準備精修中"), "45": ("sampling", "放大草稿並準備精修中"), "50": ("sampling", "二次取樣精修中"),
            "13": ("saving", "輸出影片中"), "14": ("saving", "輸出音訊中"),
            "15": ("saving", "儲存為 MP4 中"),
        }.get(node, (None, None))
        if stage:
            _update(job_id, stage=stage, message=message, step=None, total_steps=None)
    elif event.get("type") == "progress" and str(data.get("node")) in ("12", "50"):
        value, total = data.get("value"), data.get("max")
        if isinstance(value, (int, float)) and isinstance(total, (int, float)) and total > 0:
            _update(job_id, stage="sampling", message="生成影片與音訊中", step=min(value, total), total_steps=total)


def _listen_progress(socket, stopped, job_id, prompt_id):
    import websocket
    while not stopped.is_set():
        try:
            message = socket.recv()
            if isinstance(message, str) and message:
                _progress_event(job_id, prompt_id, json.loads(message))
        except websocket.WebSocketTimeoutException:
            continue
        except Exception:
            return  # History polling still completes the job if the socket closes.


def submit(config):
    global _active
    config = clean_config(config)
    if not (BASE / "setup.json").exists():
        raise RuntimeError("請先執行「準備環境」儲存格。")
    if config["mode"] in ("omni", "omni_hd") and not json.loads((BASE / "setup.json").read_text()).get("omni"):
        raise RuntimeError("尚未下載 FastH3 Omni 模型。請在 ① 勾選「下載 FastH3 Omni」後重新執行。")
    record = json.loads((BASE / "setup.json").read_text())
    if config["mode"] in ("ref4", "ref2va", "ref2va_hd", "ayase") and not record.get("ref4"):
        raise RuntimeError("尚未下載 Ref2VA 模型（ref4／ref2va 共用）。請在 ① 勾選「download_ref4」後重新執行。")
    with _lock:
        if _active:
            raise RuntimeError("目前正在生成。請等待完成或中止後再執行。")
        job_id = uuid.uuid4().hex[:12]
        _active = job_id
        _jobs[job_id] = {"id": job_id, "state": "running", "stage": "loading", "message": "連線到生成引擎中", "started": time.time(), "config": config, "cancel": False}
    threading.Thread(target=_worker, args=(job_id, config), daemon=True).start()
    return {"id": job_id}


def _comfy_error(messages):
    """Readable ComfyUI failure: node, exception type/message and traceback tail. The raw dump holds huge tensor prints."""
    for kind, info in messages:
        if kind == "execution_error" and isinstance(info, dict):
            trace = [str(line).strip()[:300] for line in info.get("traceback", [])][-6:]
            head = f"節點 {info.get('node_id')} ({info.get('node_type')}) 失敗：{info.get('exception_type')}: {str(info.get('exception_message'))[:800]}"
            return head + chr(10) + chr(10).join(trace)
    return json.dumps(messages, ensure_ascii=False)[:1500]


def _worker(job_id, config):
    global _active
    started = time.monotonic()
    folder = OUTPUT / job_id
    folder.mkdir(parents=True, exist_ok=True)
    socket = None
    listener = None
    stopped = threading.Event()
    try:
        record = json.loads((BASE / "setup.json").read_text())
        start_server(record.get("omni"))
        graph = graph_for(config, record["profile"], f"h3_lab/{job_id}")
        client_id = "h3-lab-" + job_id
        try:
            import websocket
            socket = websocket.create_connection(f"ws://127.0.0.1:{PORT}/ws?clientId={client_id}", timeout=1)
        except Exception:
            socket = None
        response = _request("POST", "/prompt", json={"prompt": graph, "client_id": client_id})
        if response.get("node_errors") or "prompt_id" not in response:
            raise RuntimeError(json.dumps(response, ensure_ascii=False))
        prompt_id = response["prompt_id"]
        _update(job_id, message="載入並生成模型中（首次較久）", prompt_id=prompt_id)
        if socket:
            listener = threading.Thread(target=_listen_progress, args=(socket, stopped, job_id, prompt_id), daemon=True)
            listener.start()
        min_free = None
        busy_since = None
        while time.monotonic() - started < 5400:
            try:  # lowest free VRAM seen during the job shows directly whether a long/HD clip fits this GPU
                device = _request("GET", "/system_stats", timeout=5)["devices"][0]
                free = device["torch_vram_free"] if "torch_vram_free" in device else device["vram_free"]
                min_free = free if min_free is None else min(min_free, free)
                vram_total = device["vram_total"]
                _update(job_id, min_vram_free_gib=round(min_free / 2**30, 1), vram_total_gib=round(vram_total / 2**30, 1))
            except Exception:
                pass
            if _jobs[job_id]["cancel"]:
                _request("POST", "/interrupt")
                raise InterruptedError("已中止生成。")
            try:  # a long decode/upscale can keep the server from answering for a while; that is not a failure unless it exits
                history = _request("GET", "/history/" + prompt_id, timeout=90)
                busy_since = None
            except Exception as exc:
                import requests
                if not isinstance(exc, requests.exceptions.RequestException):
                    raise
                if _process is not None and _process.poll() is not None:
                    raise RuntimeError("生成引擎已結束（可能是記憶體不足）。" + (BASE / "comfy.log").read_text(errors="replace")[-1500:])
                busy_since = busy_since or time.monotonic()
                if time.monotonic() - busy_since > 900:
                    raise RuntimeError("生成引擎超過 15 分鐘沒有回應：" + str(exc))
                _update(job_id, message="生成引擎忙碌中，等待回應")
                time.sleep(5)
                continue
            result = history.get(prompt_id)
            if result:
                if result.get("status", {}).get("status_str") == "error":
                    raise RuntimeError(_comfy_error(result.get("status", {}).get("messages", [])))
                outputs = result.get("outputs", {}).get("15", {}).get("gifs", [])
                video = next((x for x in outputs if x.get("filename", "").endswith(".mp4")), None)
                if video:
                    break
                if result.get("status", {}).get("completed"):
                    raise RuntimeError("處理已結束，但未回傳影片檔。")
            time.sleep(2)
        else:
            _request("POST", "/interrupt")
            raise TimeoutError("已達 90 分上限，因此中止此次生成。")
        stopped.set()
        if listener:
            listener.join(timeout=2)
        _update(job_id, stage="saving", message="確認並儲存影片中", step=None, total_steps=None)
        source = (COMFY / "output" / video.get("subfolder", "") / video["filename"]).resolve()
        if not source.is_relative_to((COMFY / "output").resolve()):
            raise RuntimeError("輸出路徑不正確。")
        shutil.copy2(source, folder / "video.mp4")
        draft = next((x for x in result.get("outputs", {}).get("60", {}).get("gifs", []) if x.get("filename", "").endswith(".mp4")), None)
        if draft:
            shutil.copy2(COMFY / "output" / draft.get("subfolder", "") / draft["filename"], folder / "draft.mp4")
        import imageio_ffmpeg
        ffmpeg = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
        # Decode one frame of each stream so an empty/broken result is not reported as success.
        for stream in ("v", "a"):
            check = subprocess.run([ffmpeg, "-v", "error", "-i", str(folder / "video.mp4"), "-map", f"0:{stream}:0", f"-frames:{stream}", "1", "-f", "null", "-"], capture_output=True, text=True, timeout=90)
            if check.returncode:
                raise RuntimeError("無法確認生成檔案的影片或音訊。" + check.stderr[-1200:])
        (folder / "prompt.txt").write_text(config["prompt"], encoding="utf-8")
        (folder / "workflow-api.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2))
        report = {"id": job_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "generation_seconds": round(time.monotonic() - started, 2), "config": config, "environment": record, "video_bytes": (folder / "video.mp4").stat().st_size, "video_audio_decode_check": True,
                  "timeline": _jobs[job_id].get("timeline", []), "min_vram_free_gib": round(min_free / 2**30, 1) if min_free is not None else None, "vram_total_gib": round(vram_total / 2**30, 1) if min_free is not None else None}
        (folder / "settings.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        copies = {k: config[k] for k in ("first_frame", "last_frame") if config.get(k)}
        copies.update({f"ref_{i + 1}": name for i, name in enumerate(config.get("refs", []))})
        for key, name in copies.items():
            shutil.copy2(COMFY / "input" / name, folder / (key + ".png"))
        with zipfile.ZipFile(folder / "result.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for item in folder.iterdir():
                if item.name != "result.zip":
                    bundle.write(item, item.name)
        _update(job_id, state="done", stage="done", message="已完成", report=report)
    except InterruptedError as exc:
        _update(job_id, state="cancelled", message=str(exc))
    except Exception as exc:
        hint = " 若記憶體不足，請以 5 秒・橫式・Turbo 重試。" if "memory" in str(exc).lower() else ""
        seen = _jobs[job_id]
        vram = f" [VRAM 最低剩餘 {seen['min_vram_free_gib']} / {seen['vram_total_gib']} GiB]" if seen.get("min_vram_free_gib") is not None else ""
        _update(job_id, state="error", message=str(exc) + hint + vram)
    finally:
        stopped.set()
        if socket:
            socket.close()
        if listener:
            listener.join(timeout=2)
        with _lock:
            _jobs[job_id]["ended"] = time.time()
            _active = None


def status(job_id):
    with _lock:
        if job_id not in _jobs:
            raise ValueError("找不到此生成。請從歷史紀錄確認結果。")
        state = dict(_jobs[job_id])
    state.pop("cancel", None)
    state["elapsed"] = round(state.get("ended", time.time()) - state["started"])
    return state


def cancel(job_id):
    with _lock:
        if job_id != _active:
            return {"message": "目前沒有執行中的生成。"}
        _jobs[job_id]["cancel"] = True
    return {"message": "已要求中止，請稍候至處理結束。"}


def download(job_id, kind="video"):
    if not job_id.isalnum() or len(job_id) != 12:
        raise ValueError("生成 ID 不正確。")
    names = {"video": ("video.mp4", "video/mp4"), "zip": ("result.zip", "application/zip"), "settings": ("settings.json", "application/json")}
    if kind not in names:
        raise ValueError("儲存格式不正確。")
    name, mime = names[kind]
    path = OUTPUT / job_id / name
    if not path.is_file():
        raise ValueError("找不到結果。刪除執行階段後結果也會一併消失。")
    if path.stat().st_size > 60 * 1024**2:
        raise ValueError("檔案超過 60MB，請從 Colab 左側檔案清單開啟 /content/h3-lab/results 後再儲存。")
    return {"filename": f"minimax_h3_{job_id}.{name.split('.')[-1]}", "mime": mime, "base64": base64.b64encode(path.read_bytes()).decode()}


def about():
    record = json.loads((BASE / "setup.json").read_text()) if (BASE / "setup.json").exists() else {}
    results = []
    if OUTPUT.exists():
        for file in sorted(OUTPUT.glob("*/settings.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try:
                results.append(json.loads(file.read_text()))
            except (ValueError, OSError):
                pass
    return {"ready": bool(record), "environment": record, "results": results, "active": _active}


def install_callbacks():
    from google.colab import output
    from IPython.display import JSON
    def safe(function):
        def call(*args):
            try:
                result = {"ok": True, "value": function(*args)}
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            # invokeFunction returns an IPython MIME bundle, not the raw dict.
            return JSON(result)
        return call
    for name, fn in {"about": about, "upload": upload_image, "run": submit, "status": status, "cancel": cancel, "download": download}.items():
        output.register_callback("h3lab." + name, safe(fn))


# ---- Agent mode: Google Drive folder queue (no tunnel, no public port) ----
import re as _re

QUEUE_DIRS = ("inbox", "running", "done", "failed")
_ID = _re.compile(r"^[A-Za-z0-9_-]{1,64}$")
IMAGE_KEYS = {key: f".{key}.png" for key in IMAGE_NAMES}
IMAGE_WAIT_SECONDS = 600  # Drive uploads are async: wait this long for declared images, then fail
HEARTBEAT_SECONDS = 300


def queue_init(root):
    root = Path(root)
    for name in QUEUE_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def _write_json(path, value):
    # Write to a temp name then rename, so an agent never reads a half-written file.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def queue_recover(root):
    """Sessions die at 12/24h: put jobs left in running/ back, unless already finished."""
    root = Path(root)
    for file in (root / "running").glob("*.json"):
        if (root / "done" / file.name).exists() or (root / "failed" / file.name).exists():
            file.unlink()
        else:
            os.replace(file, root / "inbox" / file.name)


def _fail(root, job_id, message):
    _write_json(Path(root) / "failed" / f"{job_id}.json", {"id": job_id, "state": "failed", "error": message})


def _declared_images(config):
    declared = config.get("images", []) if isinstance(config, dict) else []
    return [k for k in declared if k in IMAGE_KEYS] if isinstance(declared, list) else []


def process_one(root, runner, validate):
    """Claim and run one inbox job. Returns the id handled, or None when nothing is ready."""
    root = Path(root)
    for file in sorted((root / "inbox").glob("*.json"), key=lambda p: p.stat().st_mtime):
        job_id = file.stem
        if not _ID.match(job_id):
            file.unlink()
            continue
        if (root / "done" / file.name).exists():
            file.unlink()  # duplicate submission: result already exists
            continue
        try:
            peek = json.loads(file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            peek = None  # malformed: claim it below so it lands in failed/
        missing = [k for k in _declared_images(peek) if not (root / "inbox" / (job_id + IMAGE_KEYS[k])).is_file()]
        if missing and time.time() - file.stat().st_mtime < IMAGE_WAIT_SECONDS:
            continue  # reference image still syncing from Drive
        claimed = root / "running" / file.name
        try:
            os.replace(file, claimed)
        except OSError:
            continue
        requeue = False
        try:
            if missing:
                raise ValueError("參考圖片沒有送達：" + ", ".join(missing))
            config = json.loads(claimed.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError("工作單必須是 JSON 物件。")
            for key in (*IMAGE_KEYS, "images"):
                config.pop(key, None)  # images come only from sibling files, never from raw paths in the JSON
            config = validate(config)
            images = {key: root / "inbox" / (job_id + suffix) for key, suffix in IMAGE_KEYS.items() if (root / "inbox" / (job_id + suffix)).is_file()}
            video, settings = runner(config, images)
            shutil.copy2(video, root / "done" / f"{job_id}.mp4")
            shutil.copy2(settings, root / "done" / f"{job_id}.settings.json")
            draft = Path(video).with_name("draft.mp4")  # omni_hd keeps its silent draft so draft vs final can be compared
            if draft.is_file():
                shutil.copy2(draft, root / "done" / f"{job_id}.draft.mp4")
            # Marker goes last and carries the mp4 size: Drive may sync the marker before the video.
            _write_json(root / "done" / f"{job_id}.json", {"id": job_id, "state": "done", "video": f"{job_id}.mp4", "video_bytes": (root / "done" / f"{job_id}.mp4").stat().st_size, "settings": f"{job_id}.settings.json", "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        except Exception as exc:
            _fail(root, job_id, str(exc)[-3000:])
        except BaseException:
            requeue = True  # Ctrl-C / runtime kill: keep the job
            raise
        finally:
            if requeue:
                os.replace(claimed, root / "inbox" / file.name)
            else:
                claimed.unlink(missing_ok=True)
                for suffix in IMAGE_KEYS.values():
                    (root / "inbox" / (job_id + suffix)).unlink(missing_ok=True)
        return job_id
    return None


def comfy_runner(config, images):
    """Real runner: upload reference images (PIL-validated), submit, block until the job ends."""
    for key, path in images.items():
        data = base64.b64encode(path.read_bytes()).decode()
        config[key] = upload_image("data:image/png;base64," + data)["filename"]
    job_id = submit(config)["id"]
    try:
        while True:
            state = status(job_id)
            if state["state"] != "running":
                break
            time.sleep(3)
    except BaseException:
        cancel(job_id)  # stop ComfyUI so the next run is not blocked by a ghost job
        raise
    if state["state"] != "done":
        raise RuntimeError(state.get("message", "生成失敗。"))
    folder = OUTPUT / job_id
    return folder / "video.mp4", folder / "settings.json"


def agent_loop(root, poll=20, runner=None, validate=None, max_loops=None):
    """Blocking queue worker. Keep this cell running; create <root>/STOP to end it."""
    root = queue_init(root)
    runner = runner or comfy_runner
    validate = validate or (lambda c: clean_config(c, need_refs=False))  # images are attached after validation
    (root / "STOP").unlink(missing_ok=True)  # a leftover STOP from the last run must not end this one
    while _active:  # a cancelled job may still be winding down
        time.sleep(2)
    queue_recover(root)
    loops, beat = 0, 0.0
    while not (root / "STOP").exists() and (max_loops is None or loops < max_loops):
        loops += 1
        handled = process_one(root, runner, validate)
        if handled or time.time() - beat >= HEARTBEAT_SECONDS:
            _write_json(root / "heartbeat.json", {"alive_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "last_job": handled})
            beat = time.time()
        if handled:
            print(time.strftime("%H:%M:%S"), "完成處理工作", handled)
        else:
            time.sleep(poll)
