"""Post-pass graphs (SeedVR2 1080p, H3 FaceRefine): links resolve and inputs match the node definitions
read from ComfyUI ce42de5f (nodes_seedvr.py, nodes_post_processing.py), VHS 4d907bee and ComfyUI-H3-FaceRefine d8521d14."""
from pathlib import Path as _P
import types
BACKEND = _P(__file__).resolve().parents[1] / "src" / "h3_backend.py"
m = types.ModuleType("h3"); exec(compile(open(BACKEND, encoding="utf-8").read(), "b", "exec"), m.__dict__)

REQUIRED = {  # class -> required input names (copied from the pinned sources)
    "VHS_LoadVideoPath": {"video", "force_rate", "custom_width", "custom_height", "frame_load_cap", "skip_first_frames", "select_every_nth"},
    "ResizeImageMaskNode": {"input", "resize_type", "scale_method"},
    "SeedVR2Preprocess": {"resized_images"},
    "SeedVR2TemporalChunk": {"latent", "temporal_overlap", "chunking_mode"},
    "SeedVR2Conditioning": {"model", "vae_conditioning"},
    "SeedVR2TemporalMerge": {"latents", "temporal_overlap"},
    "SeedVR2PostProcessing": {"images", "original_resized_images", "color_correction_method"},
    "VAEEncodeTiled": {"pixels", "vae", "tile_size", "overlap", "temporal_size", "temporal_overlap"},
    "VAEDecodeTiled": {"samples", "vae", "tile_size", "overlap", "temporal_size", "temporal_overlap"},
    "KSampler": {"model", "positive", "negative", "latent_image", "seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"},
    "H3FaceTrackCrop": {"images", "detector", "confidence", "crop_factor", "canvas_width", "canvas_height", "canvas_mode", "smooth_window", "size_smooth_window", "smooth_method", "size_mode"},
    "H3InjectVideoLatent": {"av_latent", "images", "vae"},
    "H3PerFrameDenoise": {"model", "av_latent", "transform", "denoise_multiplier_small_face", "denoise_multiplier_large_face", "scale_mode", "face_px_small", "face_px_large", "gamma", "smooth_frames"},
    "H3FaceStitch": {"base_images", "refined_crops", "transform", "paste_region", "mask_dilation", "feather", "colour_match", "blend", "undetected_frames"},
}
OPTIONAL = {"H3FaceTrackCrop": {"identity_track", "select"}, "ResizeImageMaskNode": {"resize_type.shorter_size"}}
OUTPUTS = {"VHS_LoadVideoPath": 4, "H3FaceTrackCrop": 7, "SeedVR2TemporalChunk": 2, "SeedVR2Conditioning": 2, "H3PerFrameDenoise": 3, "MiniMaxH3ReferenceToVideo": 2}

def check(g):
    for k, n in g.items():
        ct, inp = n["class_type"], n["inputs"]
        if ct in REQUIRED:
            missing = REQUIRED[ct] - set(inp); extra = set(inp) - REQUIRED[ct] - OPTIONAL.get(ct, set())
            assert not missing and not extra, (k, ct, missing, extra)
        for v in inp.values():
            if isinstance(v, list):
                assert v[0] in g, (k, v)
                src = g[v[0]]["class_type"]
                if src in OUTPUTS: assert v[1] < OUTPUTS[src], (k, v)
    assert m.POST_OUT in g and g[m.POST_OUT]["class_type"] == "VHS_VideoCombine"

for model in ("3b_int8", "7b_fp16"):
    g = m.seedvr2_graph("/x/video.mp4", model)
    check(g)
    assert g["5"]["inputs"]["unet_name"] == m.SEEDVR2_MODELS[model].split("/")[1]
    assert g["2"]["inputs"]["resize_type"] == "scale shorter dimension" and g["2"]["inputs"]["resize_type.shorter_size"] == 1080
    assert g["12"]["inputs"]["color_correction_method"] in ("lab", "wavelet", "adain", "none")
for det in ("anime", "photo"):
    for prof in ("int8", "full"):
        g = m.facerefine_graph("/x/video.mp4", {"prompt": "p", "seed": 5}, prof, det, ["h3ref_a.png", "h3ref_b.png"])
        check(g)
        assert g["2"]["inputs"]["detector"].endswith(".pt") and g["2"]["inputs"]["canvas_mode"] in ("manual", "auto_no_downscale", "auto_capped_768")
        assert g["9"]["inputs"]["ref_images.ref_image_1"] == ["41", 0]
        assert g["2"]["inputs"]["identity_track"] == (det == "photo")
assert m.FACE_DETECTORS["anime"][3] != m.FACE_DETECTORS["photo"][3]
p = m.clean_post({}); assert p == {"post_face": False, "post_upscale": "off", "face_detector": "anime"}
c = m.clean_config({"prompt": "x", "post_face": True, "post_upscale": "7b_fp16", "face_detector": "photo"})
assert c["post_face"] and c["post_upscale"] == "7b_fp16" and c["face_detector"] == "photo"
for bad in ({"post_upscale": "4k"}, {"face_detector": "x"}):
    try: m.clean_post(bad); raise SystemExit("accepted " + str(bad))
    except ValueError: pass
try: m.postprocess("../../etc", {}); raise SystemExit("accepted bad id")
except ValueError: pass
print("post OK")
