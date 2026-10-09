#!/usr/bin/env python3
"""Site favicon: a Wigglytuff head, simplified by hand from the game's own battle sprite.

Source  : site/assets/game/pokemon/wigglytuff.png (64x64 front sprite, extracted from the ROM by pics.py)
Method  : the two pixel maps below are the source of truth. They are drawn at their target
          resolution with the battle sprite's palette; nothing is resampled from a larger picture.
          Larger icons are integer nearest-neighbour enlargements of the 32x32 map.
Outputs : site/assets/favicon/{favicon.ico, favicon-16x16.png, favicon-32x32.png,
          apple-touch-icon.png, icon-192.png, icon-512.png, site.webmanifest}
Run     : python3 tools/favicon.py   (then tools/build.py copies site/assets into dist)
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "favicon"
SPRITE = ROOT / "site" / "assets" / "game" / "pokemon" / "wigglytuff.png"
BG = (14, 13, 12, 255)  # the site's theme colour, behind the opaque Apple touch icon

# Colours of the battle sprite, keyed as in the maps.
PAL = {
    ".": (0, 0, 0, 0),
    "a": (255, 172, 189, 255),  # body pink
    "d": (246, 123, 148, 255),  # shaded pink
    "f": (139, 65, 65, 255),    # outline
    "e": (16, 16, 16, 255),     # inner ear
    "b": (255, 255, 255, 255),  # fur / eye white
    "c": (230, 222, 230, 255),  # fur shade
    "k": (255, 222, 205, 255),  # fur edge
    "h": (32, 90, 98, 255),     # eye
    "j": (82, 164, 139, 255),   # eye rim
    "n": (148, 222, 205, 255),  # eye highlight
    "l": (115, 65, 24, 255),    # mouth line
    "m": (230, 49, 49, 255),    # mouth
}

# 32x32: left half, mirrored; PATCH32 then draws the forehead curl and the right eye highlights.
HALF32 = """
................
..ff............
.fbbf...........
.fbebf..........
.fbeebf.........
.fbeeeaf........
..feeeaaf.......
..fdeeeaf....fff
...fdeeaaf.ffaaa
...fddeeafaaaaaa
....fddeaaaaaaaa
....fadaaaaaaaaa
...faaaaaaaaaaaa
..faaaaaaaaaaaaa
..fadbbbbbdaaaaa
.faabjhhhjbaaaaa
.faabhbnhhbaaaaa
.faabhnhhhbaaaaa
.faabhhhhhbaaaaa
.faabjhhhjbaaaaa
.faadbbbbbdaakkk
.faaaaaaaaakbbbb
.faaaaaaaakbllll
.fdaaaaaakbbblmm
..fdaaaakbbbbbmm
..fddaakbbbbbbbb
...fddbbbbbbbbbb
....ffcbbbbbbbbb
......ffccbbbbbb
........ffffcccc
............ffff
................
""".split()
PATCH32 = [(8, 13, "adddaa"), (9, 13, "daaada"), (10, 13, "daddda"), (11, 13, "daaaaa"), (12, 13, "adddda"),
           (16, 21, "bhbnhhb"), (17, 21, "bhnhhhb")]

MAP16 = """
.f............f.
fbf..........fbf
febf........fbef
feef..ffff..feef
.feafaaaaaafaef.
.fdaaaaddaaaadf.
.faaaaadaaaaaaf.
faabbaaaaaabbaaf
fabhhbaaaabhhbaf
fabnhbaaaabnhbaf
faabbakkkkabbaaf
faaaakbmmbkaaaaf
.faakbbbbbbkaaf.
.fdbbbbbbbbbbdf.
..ffcbbbbbbcff..
....ffffffff....
""".split()


def map32():
    rows = [list(r + r[::-1]) for r in HALF32]
    for y, x, s in PATCH32:
        rows[y][x:x + len(s)] = s
    return ["".join(r) for r in rows]


def draw(rows):
    n = len(rows)
    assert all(len(r) == n for r in rows), "map is not square"
    im = Image.new("RGBA", (n, n))
    im.putdata([PAL[c] for r in rows for c in r])
    return im


def scaled(im, k, size=None, bg=(0, 0, 0, 0)):
    big = im.resize((im.width * k, im.height * k), Image.NEAREST)
    if not size or size == big.width:
        return big
    out = Image.new("RGBA", (size, size), bg)
    out.alpha_composite(big, ((size - big.width) // 2, (size - big.height) // 2))
    return out


def main():
    used = {c for c in PAL.values() if c[3]}
    assert used <= set(Image.open(SPRITE).convert("RGBA").getdata()), "palette is not the battle sprite's"
    OUT.mkdir(parents=True, exist_ok=True)
    m16, m32 = draw(MAP16), draw(map32())
    m16.save(OUT / "favicon-16x16.png")
    m32.save(OUT / "favicon-32x32.png")
    m48 = scaled(m16, 3)
    m48.save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)], append_images=[m16, m32])
    scaled(m32, 5, 180, BG).save(OUT / "apple-touch-icon.png")
    scaled(m32, 6).save(OUT / "icon-192.png")
    scaled(m32, 16).save(OUT / "icon-512.png")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": "Project Blonde Guide", "short_name": "Blonde Guide",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}],
        "theme_color": "#0e0d0c", "background_color": "#0e0d0c", "display": "browser"}, indent=1) + "\n", encoding="utf-8")
    print("favicon:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
