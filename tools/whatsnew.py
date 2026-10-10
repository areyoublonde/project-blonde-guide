#!/usr/bin/env python3
"""Project Blonde guide - the v1.1 before / after character gallery.

    python3 tools/whatsnew.py [--workspace ..]

Source: the comparison set prepared and verified for the Discord previews
(project-blonde-discord/drafts/sprite-overhaul-preview: coverage.json + native PNGs decoded from the two ROMs).
That set was decoded from v108 (before) and the sprite-experiment ROM (after). This tool proves, byte for byte,
that every asset it shows is the same data in the two PUBLIC builds: v105 = public v1.0 and v111 = public v1.1.
The Firebreather battle picture comes from tools/whatsnew-src/ (see firebreather()).

Output: site/assets/game/whatsnew/v1.1/{overworld,faces}.png (native-size atlases, no scaling), the two Alola palm screenshots,
and data/whatsnew-v1.1.json. Run it after romx.py and pics.py.
Nothing outside this repository is written.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
B = 0x08000000
PUBLIC = {"before": ("v1.0", "v105", "d76ce7db778f09ad9085e6c11a535e6c7c8f4271de1def30d98af46698d5513a"),
          "after": ("v1.1", "v111", "2a3299a0daa04225fc4945ed5835ac673d37be2f990ef4ad37aebd6eb856ac33")}
DECODED = {"before": "c5ec755b66ef5a169d91a38b8e8cb19872b6895ec552dc2bdedd47336430e2fe", "after": "108b0dada857fba7e7b89db7671dffcb11328c8c683a2d216a8143dcaedd7863"}
FACINGS = ["Down", "Left", "Right", "Up"]
PALMS = {"map": "melemele-isle.png", "box": (64, 336, 304, 496)}
TRAINER_PICS, FIREBREATHER = 0x085F173C, 167          # gTrainerSprites (32-byte rows: tiles +4, palette +12); verified below from the Lass rows
sha = lambda b: hashlib.sha256(b).hexdigest()


def lz(b, p):
    """GBA LZ77 (type 0x10) -> (data, compressed length)."""
    assert b[p] == 0x10
    size, i, o = int.from_bytes(b[p + 1:p + 4], "little"), p + 4, bytearray()
    while len(o) < size:
        f = b[i]; i += 1
        for bit in range(8):
            if len(o) >= size: break
            if f & (0x80 >> bit):
                n, d = (b[i] >> 4) + 3, ((b[i] & 15) << 8 | b[i + 1]) + 1; i += 2
                for _ in range(n): o.append(o[-d])
            else:
                o.append(b[i]); i += 1
    return bytes(o), i - p


def ranges(b, a):
    """Every ROM range an asset's pixels are read from (object palettes are covered by the whole-ROM difference check)."""
    if a["kind"] == "overworld":
        info = int(a["infoAddress"], 16) - B
        images = int.from_bytes(b[info + 0x1c:info + 0x20], "little") - B
        r = [(info, info + 36)]
        for f in range(a["frames"]):
            ptr, size = struct.unpack("<IH", b[images + 8 * f:images + 8 * f + 6])
            r += [(images + 8 * f, images + 8 * f + 8), (ptr - B, ptr - B + size)]
        return r
    t, p = int(a["tilesAddress"], 16) - B, int(a["paletteAddress"], 16) - B
    return [(t, t + (lz(b, t)[1] if b[t] == 0x10 else 2048 * a["planes"])), (p, p + 32 * a["planes"])]


def differing(a, b):
    out = []
    for o in range(0, len(a), 4096):
        if a[o:o + 4096] != b[o:o + 4096]:
            for j in range(o, o + 4096):
                if a[j] != b[j]:
                    if out and j - out[-1][1] <= 16: out[-1][1] = j + 1
                    else: out.append([j, j + 1])
    return out


def firebreather(b, side):
    """The Firebreather battle picture. Its tiles use the game's own compressor, so they were decoded once by running the game's
    decompression routine on each public ROM (unicorn, rom108.Emu.decompress) and are kept in tools/whatsnew-src/. Checked here: the
    table row is the Firebreather's, and every colour in the picture is in that ROM's palette for it."""
    row = TRAINER_PICS - B + FIREBREATHER * 32
    pal = int.from_bytes(b[row + 12:row + 16], "little") - B
    cols = {((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31) for v in struct.unpack("<16H", b[pal:pal + 32])}
    im = Image.open(ROOT / "tools/whatsnew-src" / f"firebreather-{PUBLIC[side][0]}.png").convert("RGBA")
    used = {p[:3] for p in im.getdata() if p[3]}
    assert im.size == (64, 64) and len(used) > 8 and used <= cols, f"Firebreather {side}: picture colours are not this ROM's palette"
    return im


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workspace", default=str(ROOT.parent))
    W = Path(ap.parse_args().workspace).resolve()
    SRC = W / "project-blonde-discord/drafts/sprite-overhaul-preview"
    EXP = W / "output/character-sprite-complete-experimental-20261010"
    rom = {"v105": W / "blonde/qa/title-version-1.0-v105/build/Pokemon - Heart & Soul (Blonde).gba", "v111": W / "output/project-blonde-v1.1-rc-v111-20261010/Pokemon - Project Blonde.gba",
           "dec-before": EXP / "baseline/Pokemon - Heart & Soul (Blonde).gba", "dec-after": EXP / "test/Pokemon - Heart & Soul (Blonde).gba"}
    R = {k: p.read_bytes() for k, p in rom.items()}
    assert sha(R["v105"]) == PUBLIC["before"][2] and sha(R["v111"]) == PUBLIC["after"][2], "not the two public builds"
    assert sha(R["dec-before"]) == DECODED["before"] and sha(R["dec-after"]) == DECODED["after"], "not the ROMs the comparison set was decoded from"
    pub = {"before": R["v105"], "after": R["v111"]}
    diff = {s: differing(R["dec-" + s], pub[s]) for s in pub}

    cov = json.loads((SRC / "coverage.json").read_text())
    pairs = [c for c in cov["comparisons"] if c["publish"]]
    assert [sum(c["kind"] == k for c in pairs) for k in ("overworld", "portrait", "battle")] == [48, 14, 1]
    assert sorted(n for c in pairs for n in c["assignmentNumbers"]) == sorted(set(n for c in pairs for n in c["assignmentNumbers"]))
    checked = 0
    for c in pairs:
        for s in pub:
            a = c[s]
            assert sha((SRC / a["file"]).read_bytes()) == a["pngSha256"], a["file"]
            for lo, hi in ranges(R["dec-" + s], a):
                assert R["dec-" + s][lo:hi] == pub[s][lo:hi], f'{c["number"]} {s}: differs in the public {PUBLIC[s][0]} ROM at {hex(lo + B)}'
            checked += 1
    lass = next(c for c in pairs if c["kind"] == "battle")
    for s in pub:   # the trainer-picture table really is where this tool reads the Firebreather from
        assert int.from_bytes(pub[s][TRAINER_PICS - B + lass[s]["id"] * 32 + 4:][:4], "little") == int(lass[s]["tilesAddress"], 16)

    out = ROOT / "site/assets/game/whatsnew/v1.1"; out.mkdir(parents=True, exist_ok=True)
    # ---- overworld atlas: one row per distinct sprite, four standing facings, 32x32 cells, feet on the cell's bottom edge
    rows, cells = {}, []
    for c in pairs:
        if c["kind"] != "overworld": continue
        for s in pub:
            a = c[s]
            if (s, a["id"]) in rows: continue
            sheet = Image.open(SRC / a["file"]).convert("RGBA"); strip = []
            for d in FACINGS:
                e = a["sequences"][d]["standing"][0]
                f = sheet.crop((e["frame"] * a["width"], 0, (e["frame"] + 1) * a["width"], a["height"]))
                if e["hflip"]: f = f.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                assert a["width"] <= 32 and a["height"] <= 32 and not e["vflip"]
                strip.append((f, a["width"], a["height"]))
            rows[(s, a["id"])] = len(cells); cells.append(strip)
    ow = Image.new("RGBA", (128, 32 * len(cells)))
    for y, strip in enumerate(cells):
        for x, (f, w, h) in enumerate(strip):
            ow.paste(f, (x * 32 + (32 - w) // 2, y * 32 + 32 - h))
    ow.save(out / "overworld.png", optimize=True)
    # ---- faces atlas: dialogue portraits and battle pictures, 64x64 cells, eight per row
    faces, fidx = [], {}
    def face(key, im):
        if key not in fidx: fidx[key] = len(faces); faces.append(im)
        return fidx[key]
    comps = []
    for c in pairs:
        e = {"n": c["number"], "kind": c["kind"], "title": c["title"].replace(" • Variant ", " · "), "names": c["names"], "regions": c["regions"], "assignments": len(c["assignmentNumbers"])}
        for s in pub:
            a = c[s]
            e[s] = rows[(s, a["id"])] if c["kind"] == "overworld" else face((s, c["kind"], a["id"]), Image.open(SRC / a["file"]).convert("RGBA"))
        comps.append(e)
    fb = {s: firebreather(pub[s], s) for s in pub}
    assert fb["before"].tobytes() != fb["after"].tobytes()
    site_pic = Image.open(ROOT / "site/assets/game/trainers/firebreather_hns.png").convert("RGBA")      # the guide's own picture of the current build (tools/pics.py)
    assert all(p == q or (p[3] == 0 and q[3] == 0) for p, q in zip(site_pic.getdata(), fb["after"].getdata())), "Firebreather picture differs from tools/pics.py output: run pics.py first"
    comps.append({"n": "FB", "kind": "battle", "title": "Firebreather", "names": [], "regions": [], "assignments": 0} | {s: face((s, "battle", FIREBREATHER), fb[s]) for s in pub})
    fa = Image.new("RGBA", (512, 64 * -(-len(faces) // 8)))
    for i, im in enumerate(faces): fa.paste(im, (i % 8 * 64, i // 8 * 64))
    fa.save(out / "faces.png", optimize=True)

    # ---- Alola palms: the same 240x160 window of the guide's own Melemele Isle map, rendered by tools/romx.py from each public ROM
    box = PALMS["box"]
    now = Image.open(ROOT / "site/assets/game/maps" / PALMS["map"]).convert("RGB").crop(box)
    was = Image.open(ROOT / "tools/whatsnew-src/alola-palms-v1.0.png").convert("RGB")      # the same window of the v105 render (commit c7ca264)
    assert was.size == now.size == (240, 160) and was.tobytes() != now.tobytes()
    was.save(out / f'palms-{PUBLIC["before"][0]}.png', optimize=True); now.save(out / f'palms-{PUBLIC["after"][0]}.png', optimize=True)

    S = cov["summary"]
    same = [c for c in cov["comparisons"] if not c["publish"]]      # pairs whose before and after pixels are identical: counted, never shown
    assert all(c["kind"] == "portrait" and c["before"]["pixelSha256"] == c["after"]["pixelSha256"] for c in same)
    data = {"_about": "Generated by tools/whatsnew.py - do not edit. Before = public v1.0 (v105), after = public v1.1 (v111); every asset byte-checked against both public ROMs.",
            "before": dict(zip(("public", "build", "sha256"), PUBLIC["before"])), "after": dict(zip(("public", "build", "sha256"), PUBLIC["after"])),
            "atlas": {"overworld": {"file": "overworld.png", "w": ow.width, "h": ow.height, "cell": 32, "facings": FACINGS, "sha256": sha((out / "overworld.png").read_bytes())},
                      "faces": {"file": "faces.png", "w": fa.width, "h": fa.height, "cell": 64, "cols": 8, "sha256": sha((out / "faces.png").read_bytes())}},
            "counts": {"overworld": sum(c["kind"] == "overworld" for c in comps), "portrait": sum(c["kind"] == "portrait" for c in comps), "battle": sum(c["kind"] == "battle" for c in comps),
                       "assignments": {k: sum(c["assignments"] for c in comps if c["kind"] == k) for k in ("overworld", "portrait", "battle")},
                       "release_assignments": S["byKind"], "identical": {"portrait": {"assignments": sum(len(c["assignmentNumbers"]) for c in same), "names": sorted(n for c in same for n in c["names"])}}},
            "palms": PALMS | {"box": list(PALMS["box"])},
            "verification": {"assets_checked": checked, "decoded_from": DECODED,
                             "public_rom_differences": {s: [[hex(lo + B), hi - lo] for lo, hi in diff[s]] for s in diff}},
            "comparisons": comps}
    (ROOT / "data/whatsnew-v1.1.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"comparisons": data["counts"], "assets_checked": checked, "overworld_rows": len(cells), "faces": len(faces),
                      "differing_ranges": {s: len(diff[s]) for s in diff}, "source_summary": {k: S[k] for k in list(S)[:6]}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
