#!/usr/bin/env python3
"""Compose assets/banner.png from real render stills (no generated art, no text inside the stills).

    python tools/make_banner.py --out assets/banner.png still1.png still2.png still3.png [still4.png]

Needs Pillow. Fonts: Segoe UI Black / Bahnschrift on Windows, falls back to DejaVu Sans Bold.
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 640
ORANGE, BLUE, WHITE = (255, 138, 36), (74, 144, 255), (244, 247, 255)


def font(names, size):
    for n in names:
        for root in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", ""):
            try:
                return ImageFont.truetype(root + n, size)
            except OSError:
                continue
    return ImageFont.load_default()


def gradient():
    img = Image.new("RGB", (W, H), (10, 13, 26))
    px = img.load()
    for y in range(H):
        for x in range(0, W, 2):
            t = x / W
            r = int(12 + 26 * t + 10 * (y / H)); g = int(14 + 10 * t); b = int(30 + 40 * (1 - t) + 12 * (y / H))
            px[x, y] = (r, g, b)
            if x + 1 < W:
                px[x + 1, y] = (r, g, b)
    return img


def glow(size, center, radius, color, strength=0.55):
    layer = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=tuple(int(c * strength) for c in color))
    return layer.filter(ImageFilter.GaussianBlur(radius / 2))


def panel(still: Path, w: int, h: int, skew: int, edge):
    """A parallelogram crop with a coloured edge."""
    im = Image.open(still).convert("RGB")
    ratio = (w + skew) / h
    sw, sh = im.size
    if sw / sh > ratio:
        nw = int(sh * ratio); im = im.crop(((sw - nw) // 2, 0, (sw + nw) // 2, sh))
    else:
        nh = int(sw / ratio); im = im.crop((0, (sh - nh) // 3, sw, (sh - nh) // 3 + nh))
    im = im.resize((w + skew, h), Image.LANCZOS)
    full = Image.new("RGBA", (w + skew, h), (0, 0, 0, 0))
    mask = Image.new("L", (w + skew, h), 0)
    ImageDraw.Draw(mask).polygon([(skew, 0), (w + skew, 0), (w, h), (0, h)], fill=255)
    full.paste(im, (0, 0), mask)
    border = Image.new("RGBA", (w + skew, h), (0, 0, 0, 0))
    ImageDraw.Draw(border).polygon([(skew, 0), (w + skew, 0), (w, h), (0, h)], outline=edge + (255,), width=5)
    full.alpha_composite(border)
    return full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stills", nargs="+")
    ap.add_argument("--out", default="assets/banner.png")
    ap.add_argument("--title", default="H3 COLAB STUDIO")
    ap.add_argument("--tag", default="Draft at 480p. Re-roll by seed. Finish at 720p.")
    ap.add_argument("--chips", default="Colab A100|Drive job queue|No tunnel|Agent skill")
    a = ap.parse_args()

    img = gradient().convert("RGBA")
    img = ImageChops.add(img.convert("RGB"), glow((W, H), (1180, 300), 420, BLUE, 0.5)).convert("RGBA")
    img = ImageChops.add(img.convert("RGB"), glow((W, H), (760, 560), 300, ORANGE, 0.45)).convert("RGBA")

    # speed lines
    rnd = random.Random(7)
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for _ in range(70):
        x = rnd.randint(-200, W); y = rnd.randint(-50, H); length = rnd.randint(160, 520)
        ld.line([(x, y), (x + length, y - length * 0.36)], fill=(255, 255, 255, rnd.randint(10, 38)), width=rnd.randint(1, 3))
    img.alpha_composite(lines)

    # panels (right side, staggered)
    slots = [(820, 36, 470, 264, ORANGE), (1060, 188, 470, 264, BLUE), (860, 344, 470, 264, (255, 70, 90)), (1100, 400, 330, 186, ORANGE)]
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    placed = []
    for i, still in enumerate(a.stills[: len(slots)]):
        x, y, w, h, edge = slots[i]
        p = panel(Path(still), w, h, 80, edge)
        placed.append((p, x, y))
        sh = Image.new("RGBA", p.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), (0, 0), p.split()[3])
        shadow.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (x + 10, y + 14))
    img.alpha_composite(shadow)
    for p, x, y in sorted(placed, key=lambda t: t[2]):
        img.alpha_composite(p, (x, y))

    d = ImageDraw.Draw(img)
    size = 104
    big = font(["seguibl.ttf", "ariblk.ttf", "DejaVuSans-Bold.ttf"], size)
    while d.textlength(max(a.title.split(" ", 1), key=len), font=big) > 700 and size > 50:
        size -= 4
        big = font(["seguibl.ttf", "ariblk.ttf", "DejaVuSans-Bold.ttf"], size)
    mid = font(["bahnschrift.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 34)
    small = font(["segoeuib.ttf", "DejaVuSans-Bold.ttf"], 24)
    words = a.title.split(" ", 1)
    for i, line in enumerate((words[0], words[1] if len(words) > 1 else "")):
        y = 128 + i * int(size * 1.02)
        d.text((66, y + 6), line, font=big, fill=(0, 0, 0, 160))
        d.text((60, y), line, font=big, fill=ORANGE if i == 0 else WHITE)
    d.rectangle([60, 392, 330, 397], fill=ORANGE)
    tag_size = 34
    while d.textlength(a.tag, font=mid) > 700 and tag_size > 18:
        tag_size -= 2
        mid = font(["bahnschrift.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], tag_size)
    d.text((60, 414), a.tag, font=mid, fill=(200, 214, 240))
    x = 60
    for chip in a.chips.split("|"):
        tw = d.textlength(chip, font=small)
        d.rounded_rectangle([x, 520, x + tw + 32, 564], radius=22, fill=(26, 34, 62), outline=(70, 90, 150), width=2)
        d.text((x + 16, 527), chip, font=small, fill=WHITE)
        x += tw + 46
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=92, optimize=True)
    print("banner:", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
