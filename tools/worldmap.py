#!/usr/bin/env python3
"""World maps: compose the game's own Town Maps and read where every place sits on them.

    python3 tools/worldmap.py [--game ../blonde]

Sources (read-only):
  graphics/pokenav/region_map/map_jk.{png,bin}   combined Johto + Kanto Town Map (the one the game shows once Kanto is reached)
  graphics/pokenav/region_map/map.{png,bin}      Hoenn Town Map
  src/data/region_map/region_map_layout_jk.h, region_map_layout.h   grid of map sections (28 x 15 cells of 8 px, origin at cell 1,2)
"""
import argparse, json, re, warnings
from pathlib import Path
from PIL import Image

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent.parent
SCALE = 4
MAPS = {"jk": ("map_jk", "region_map_layout_jk.h"), "hoenn": ("map", "region_map_layout.h")}


def compose(d, name):
    sheet = Image.open(d / f"{name}.png").convert("RGB")
    tm = (d / f"{name}.bin").read_bytes()          # 64 x 64 affine tilemap, one byte per tile
    tw = sheet.width // 8
    out = Image.new("RGB", (512, 512))
    for i, t in enumerate(tm):
        out.paste(sheet.crop(((t % tw) * 8, (t // tw) * 8, (t % tw) * 8 + 8, (t // tw) * 8 + 8)), ((i % 64) * 8, (i // 64) * 8))
    return out.crop((0, 0, 240, 160))              # the visible GBA screen


def sections(path):
    text = path.read_text()
    body = text[text.index("{", text.index("=")):]
    rows = re.findall(r"\{([^{}]+)\}", body)
    cells = {}
    for r, row in enumerate(rows):
        for c, sec in enumerate(x.strip() for x in row.split(",") if x.strip()):
            if sec != "MAPSEC_NONE":
                cells.setdefault(sec, []).append((c, r))
    # centre of each section's cells, in map pixels (cursor origin is cell 1,2)
    return {k: [round((sum(c for c, _ in v) / len(v) + 1.5) * 8, 1), round((sum(r for _, r in v) / len(v) + 2.5) * 8, 1)] for k, v in cells.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game)
    out = {}
    names = {m["id"]: m.get("name", "") for grp in json.loads((game / "src/data/region_map/region_map_sections.json").read_text()).values() for m in grp if "id" in m}
    for key, (img, layout) in MAPS.items():
        im = compose(game / "graphics/pokenav/region_map", img)
        dst = ROOT / "site/assets/game/world"
        dst.mkdir(parents=True, exist_ok=True)
        im.resize((240 * SCALE, 160 * SCALE), Image.NEAREST).save(dst / f"{key}.png", optimize=True)
        out[key] = {"w": 240, "h": 160, "src": f"graphics/pokenav/region_map/{img}.png + src/data/region_map/{layout}",
                    "sections": sections(game / "src/data/region_map" / layout)}
        out[key]["names"] = {k: names.get(k, k) for k in out[key]["sections"]}
        print(key, len(out[key]["sections"]), "sections")
    (ROOT / "data/worldmap.json").write_text(json.dumps(out, indent=1))
