#!/usr/bin/env python3
"""Plates: deliberate, graded crops of the game world, used the way an editorial site uses photography.

    python3 tools/plates.py        (run after extract.py)

Each plate is cut from a map rendered by extract.py, enlarged 3x with hard pixels, then graded once:
darkened, washed violet-to-amber, lit at the map's real lantern tiles, lightly vignetted.
Nothing is drawn by hand; the only editorial input is the crop rectangle (in map tiles).
"""
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "site/assets/game/maps"
OUT = ROOT / "site/assets/game/plates"
world = json.loads((ROOT / "data/world.json").read_text())

# name: (map png, map dir, x0, y0, x1, y1 in tiles)
PLATES = {
    "ecruteak-towers": ("ecruteak-city", "EcruteakCity_hns", 13, 6, 47, 29),   # home: the two towers and the ponds
    "ecruteak-streets": ("ecruteak-city", "EcruteakCity_hns", 5, 24, 59, 46),  # chapter: lantern streets, theater, gates
    "new-bark-town": ("new-bark-town", "NewBarkTown_hns", 0, 1, 30, 21),         # home, before you have a position: where the road starts
    "olivine-harbour": ("olivine-city", "OlivineCity_hns", 0, 38, 60, 62),       # crossing: the pier the S.S. Aqua leaves from
    "pallet-town": ("pallet-town", "PalletTown_hns", 0, 0, 24, 20),              # crossing: where the road to Hoenn begins
}
S = 3


def gradient(size, top, bottom):
    w, h = size
    col = Image.new("RGB", (1, h))
    col.putdata([tuple(int(top[i] + (bottom[i] - top[i]) * y / (h - 1)) for i in range(3)) for y in range(h)])
    return col.resize((w, h))


def make(name, png, mapdir, x0, y0, x1, y1):
    src = Image.open(MAPS / f"{png}.png").convert("RGB").crop((x0 * 16, y0 * 16, x1 * 16, y1 * 16))
    im = src.resize((src.width * S, src.height * S), Image.NEAREST)
    w, h = im.size
    im = ImageEnhance.Color(im).enhance(0.92)
    im = ImageEnhance.Brightness(im).enhance(0.74)
    im = ImageChops.multiply(im, gradient((w, h), (150, 138, 196), (255, 196, 150)))   # dusk: violet sky light, amber ground light
    glow = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(glow)
    lights = [(x, y) for x, y in world[mapdir]["events"]["lights"] if x0 <= x < x1 and y0 <= y < y1]
    for x, y in lights:
        cx, cy = (x - x0 + .5) * 16 * S, (y - y0 + .35) * 16 * S
        d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=(120, 74, 30))
        d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(255, 196, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    im = ImageChops.screen(im, glow)
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse((-w * .15, -h * .25, w * 1.15, h * 1.25), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w // 8))
    im = Image.composite(im, ImageEnhance.Brightness(im).enhance(0.55), vig)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{name}.jpg", quality=86, optimize=True, progressive=True)
    return {"w": w, "h": h, "tiles": [x0, y0, x1, y1], "map": mapdir, "lights": len(lights)}


if __name__ == "__main__":
    meta = {n: make(n, *a) for n, a in PLATES.items()}
    (ROOT / "data/plates.json").write_text(json.dumps(meta, indent=1))
    print(meta)
