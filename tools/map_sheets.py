"""Contact sheets of every map image, grouped by region and by whether the site shows the map.

    python3 tools/map_sheets.py        -> qa-evidence/map-rendering/contact-sheets/<region>-<shown|reference>-NN.png

Each cell is the committed PNG scaled down by a whole number where possible, with the map's name underneath. For looking, not for proof."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "qa-evidence/map-rendering/contact-sheets"
CELL, COLS, ROWS, PAD, CAP = 200, 8, 6, 6, 14


def main():
    a = json.loads((ROOT / "data/map-audit.json").read_text())["maps"]
    used = json.loads((ROOT / "data/map-usage.json").read_text())
    groups = {}
    for k, r in a.items():
        if r.get("img"):
            groups.setdefault((r["region"], "shown" if k in used else "reference"), []).append((r["type"], r["name"], k))
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    index = {}
    for (region, kind), items in sorted(groups.items()):
        items.sort()
        for n in range(0, len(items), COLS * ROWS):
            page = items[n:n + COLS * ROWS]
            rows = -(-len(page) // COLS)
            sheet = Image.new("RGB", (COLS * (CELL + PAD) + PAD, rows * (CELL + CAP + PAD) + PAD), (16, 20, 28))
            d = ImageDraw.Draw(sheet)
            for i, (_, name, k) in enumerate(page):
                im = Image.open(ROOT / "site/assets/game/maps" / f'{a[k]["slug"]}.png').convert("RGB")
                f = max(im.width, im.height) / CELL
                im = im.resize((max(1, round(im.width / f)), max(1, round(im.height / f))), Image.NEAREST if f <= 1 else Image.BOX)
                x, y = PAD + (i % COLS) * (CELL + PAD), PAD + (i // COLS) * (CELL + CAP + PAD)
                sheet.paste(im, (x + (CELL - im.width) // 2, y + (CELL - im.height) // 2))
                d.text((x, y + CELL + 1), name[:34], fill=(200, 205, 215))
            name = f"{region}-{kind}-{n // (COLS * ROWS) + 1:02d}.png"
            sheet.save(OUT / name, optimize=True)
            index[name] = [k for _, _, k in page]
    (OUT / "index.json").write_text(json.dumps(index, indent=0))
    print(len(index), "sheets,", sum(len(v) for v in index.values()), "maps")


if __name__ == "__main__":
    main()
