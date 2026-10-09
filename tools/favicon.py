#!/usr/bin/env python3
"""Site favicon: the owner's chosen 16x16 Ho-Oh pixel icon.

Source  : tools/favicon-source.png, the first frame of https://www.favicon.cc/?action=icon&file_id=930913
          (listed there as Creative Commons, no attribution). Chosen by the owner on 2026-10-09.
Method  : the 16x16 source is used as it is; every larger icon is an integer nearest-neighbour enlargement.
Outputs : site/assets/site-icon/{favicon.ico, favicon-16x16.png, favicon-32x32.png,
          apple-touch-icon.png, icon-192.png, icon-512.png, site.webmanifest}
Run     : python3 tools/favicon.py   (then tools/build.py copies site/assets into dist)

A changed icon should go in a renamed folder: browsers cache favicons hard, and qa_static.py
does not accept a query string on an asset URL.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "site-icon"
SOURCE = Path(__file__).resolve().parent / "favicon-source.png"
BG = (14, 13, 12, 255)  # the site's theme colour, behind the opaque Apple touch icon


def scaled(im, k, size=None, bg=(0, 0, 0, 0)):
    big = im.resize((im.width * k, im.height * k), Image.NEAREST)
    if not size or size == big.width:
        return big
    out = Image.new("RGBA", (size, size), bg)
    out.alpha_composite(big, ((size - big.width) // 2, (size - big.height) // 2))
    return out


def main():
    m16 = Image.open(SOURCE).convert("RGBA")
    assert m16.size == (16, 16), "source must be 16x16"
    OUT.mkdir(parents=True, exist_ok=True)
    m32 = scaled(m16, 2)
    m16.save(OUT / "favicon-16x16.png")
    m32.save(OUT / "favicon-32x32.png")
    scaled(m16, 3).save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)], append_images=[m16, m32])
    scaled(m16, 10, 180, BG).save(OUT / "apple-touch-icon.png")
    scaled(m16, 12).save(OUT / "icon-192.png")
    scaled(m16, 32).save(OUT / "icon-512.png")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": "Project Blonde Guide", "short_name": "Blonde Guide",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}],
        "theme_color": "#0e0d0c", "background_color": "#0e0d0c", "display": "browser"}, indent=1) + "\n", encoding="utf-8")
    print("favicon:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
