"""Builds notebook/MiniMax_H3_Studio.ipynb from src/h3_backend.py, src/ui.html and docs/agent-protocol.md.

The notebook embeds the backend and the UI as strings so that it is a single file you can open in Colab.
Run:  python tools/build_notebook.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
backend = (ROOT / "src" / "h3_backend.py").read_text(encoding="utf-8")
ui = (ROOT / "src" / "ui.html").read_text(encoding="utf-8")
proto = (ROOT / "docs" / "agent-protocol.md").read_text(encoding="utf-8")

setup = f'''#@title ① 準備環境並開啟操作畫面（首次約數分鐘～20 分鐘）
model_precision = "INT8＋INT8 文字編碼器（建議）" #@param ["INT8＋INT8 文字編碼器（建議）", "INT8（NVFP4 文字編碼器，較省空間）", "未量化（A100 80GB）"]
download_omni = True #@param {{type:"boolean"}}
download_ref4 = True #@param {{type:"boolean"}}
download_seedvr2 = False #@param {{type:"boolean"}}
download_facerefine = False #@param {{type:"boolean"}}
#@markdown 勾選 download_seedvr2＝下載 SeedVR2 1080p 放大模型（3B INT8 3.2GiB＋7B FP16 15.4GiB＋VAE 0.5GiB，約 +19GiB）。勾選 download_facerefine＝安裝 ComfyUI-H3-FaceRefine 與臉部偵測模型（動畫臉、真人臉，約 75MB＋pip 套件）。兩者都在操作畫面「極致畫質後製」使用。
#@markdown 勾選 download_ref4＝另外下載 Ref2VA INT8 與 4 步 LoRA（約 +23GB），才能用 ref4 草稿模式與 ref2va／ref2va_hd／ayase（ayase 另含 HyperFlow LoRA、潛空間放大節點與模型，約 +2GB）。
#@markdown 勾選＝另外下載 FastH3 Omni（約 +22GB，INT8），才能用 Omni 參考圖模式。
import sys, types, hashlib
BACKEND_SOURCE = {backend!r}
_module_name = 'minimax_h3_colab_backend_v3'
_source_hash = hashlib.sha256(BACKEND_SOURCE.encode()).hexdigest()
h3 = sys.modules.get(_module_name)
if h3 is None or getattr(h3, '_source_hash', None) != _source_hash:
    if h3 is not None and getattr(h3, '_active', None):
        raise RuntimeError('請等目前的生成結束後，再重新執行這個 cell。')
    h3 = types.ModuleType(_module_name)
    exec(compile(BACKEND_SOURCE, 'h3_backend.py', 'exec'), h3.__dict__)
    h3._source_hash = _source_hash
    sys.modules[_module_name] = h3
UI_SOURCE = {ui!r}
from IPython.display import HTML, display
profile = 'full' if model_precision.startswith('未量化') else ('int8enc' if model_precision.startswith('INT8＋') else 'int8')
try:
    setup_report = h3.setup(profile, download_omni, download_ref4, download_seedvr2, download_facerefine)
    if setup_report:
        h3.install_callbacks()
        display(HTML(UI_SOURCE))
except Exception as error:
    import html
    display(HTML('<div style="padding:14px;color:#922c36">' + html.escape(str(error)) + '</div>'))
'''

agent = '''#@title ② 代理模式：接收 agent 從 Google Drive 送來的工作（執行期間會持續占用此 cell）
#@markdown 先跑過 ①。這個 cell 會一直執行並輪詢 Drive，期間 ① 的操作畫面按鈕會沒有反應（Colab 一次只跑一個 cell）。要停止：按 ■ 中斷（執行中的工作會退回 inbox，下次自動重跑），或在 h3-queue 資料夾建立名為 STOP 的檔案（每次啟動時會自動清掉舊的 STOP）。
queue_folder = "h3-queue" #@param {type:"string"}
poll_seconds = 30 #@param {type:"integer"}
import sys
h3 = sys.modules.get('minimax_h3_colab_backend_v3')
if h3 is None or not h3.BASE.joinpath('setup.json').exists():
    raise RuntimeError('請先執行 ① 完成環境準備。')
from google.colab import drive
drive.mount('/content/drive')
root = h3.queue_init('/content/drive/MyDrive/' + queue_folder)
print('佇列資料夾：', root)
print('代理協定說明在下方的說明儲存格。')
h3.agent_loop(root, poll=poll_seconds)
'''

nb = {"nbformat": 4, "nbformat_minor": 5,
 "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "A100"}, "kernelspec": {"name": "python3", "language": "python", "display_name": "Python 3"}, "language_info": {"name": "python"}},
 "cells": []}
def md(t): nb["cells"].append({"id": "c%d" % len(nb["cells"]), "cell_type": "markdown", "metadata": {}, "source": t.splitlines(True)})
def code(t): nb["cells"].append({"id": "c%d" % len(nb["cells"]), "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.splitlines(True)})
md("# MiniMax H3 影片工作站（手動操作 + agent 送件）\n\n右上角 ▼ →「變更執行階段類型」→ **A100** → 儲存 → 依序執行 **① 準備環境**；需要讓 agent 自動送件時，再執行 **② 代理模式**。\n\n> ⚠️ 這份筆記本**不開公網、不建隧道**（Colab 條款禁止遠端代理與對外服務）。agent 只透過你 Google Drive 裡的 `h3-queue` 資料夾送件、取件。\n")
code(setup)
code(agent)
md("## 說明\n\n- 手動模式用 ①；agent 模式用 ②，兩者同一時間只能跑一個（Colab 單 cell 限制）。\n- 模式：`omni_hd`（Omni 草稿 480p＋同一次工作內的二次取樣，輸出 1280×720；草稿尺寸用 `p480`／`p480v`，`refine_steps` 預設 4）、`ref4`（Ref2VA 4 步草稿，參考圖專用）、`turbo`（8 步）、`turbo4`（4 步，最快，768p 調校）、`omni`（FastH3 Omni，8 步，用 1～9 張參考圖，提示詞以 `<Picture 1>` 引用）、`quality`（20 步起）。同時只套用一個加速 LoRA，不疊加；Omni 本身已蒸餾，不再疊 LoRA。\n- Omni 目前只支援圖片參考，影片／音訊參考尚未接上；Omni 兩種 sampler（預設 `res_multistep+simple`、`euler+beta`）都實測過：角色特徵都保留、暖機後速度相同（5 秒影片約 55 秒），用預設即可；首次載入 Omni 模型會多出約 2 分鐘。\n- Colab 工作階段最長 12 小時（Pro+ 單位足夠時可到 24 小時），斷線後重跑 ① ② 即可；中斷時卡在 running 的工作會自動退回 inbox 重跑。\n- 結果也在 `/content/h3-lab/results`，刪除執行階段就會消失。\n- 模型授權：MiniMax H3 社群授權，使用前請自行確認你所在地區是否可使用。\n\n[模型](https://huggingface.co/MiniMaxAI/MiniMax-H3) · [ComfyUI 用模型](https://huggingface.co/Comfy-Org/MiniMax-H3) · [Colab FAQ](https://research.google.com/colaboratory/faq.html)\n")
md("## Agent 送件協定\n\n" + proto.split("\n", 2)[2])
OUT = ROOT / "notebook" / "MiniMax_H3_Studio.ipynb"
OUT.parent.mkdir(exist_ok=True)
json.dump(nb, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
try:  # validation is optional: pip install nbformat
    import nbformat
    nbformat.validate(nbformat.read(str(OUT), as_version=4))
except ImportError:
    pass
for c in nb["cells"]:
    if c["cell_type"] == "code":
        compile("".join(c["source"]).replace("#@", "#"), "cell", "exec")
print("notebook built:", OUT.relative_to(ROOT), "cells:", len(nb["cells"]))
