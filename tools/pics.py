#!/usr/bin/env python3
"""Trainer front pictures for every trainer class picture the ROM's trainer tables use (source art, read-only)."""
import json, sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
game = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "blonde"
out = ROOT / "site/assets/game/trainers"
out.mkdir(parents=True, exist_ok=True)
pics = {t["pic"] for t in json.loads((ROOT / "data/rom/trainers.json").read_text()).values() if t["pic"]}
n = 0
for p in sorted(pics):
    src = game / "graphics/trainers/front_pics" / f"{p}.png"
    if not src.exists():
        continue
    im = Image.open(src).crop((0, 0, 64, 64))
    if im.mode == "P":
        idx = im.tobytes(); rgba = im.convert("RGBA"); bg = idx[0]
        rgba.putdata([(r, g, b, 0 if i == bg else 255) for (r, g, b, a), i in zip(rgba.getdata(), idx)]); im = rgba
    im.save(out / f"{p}.png", optimize=True); n += 1
print(n, "of", len(pics), "trainer pictures")
