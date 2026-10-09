"""Map image checks.

  python3 tools/qa_maps.py --audit [--game ../blonde]   re-derive every map from the ROM and write data/map-audit.json
  python3 tools/qa_maps.py [--dist dist]                check the committed images against that record (no game folder needed; runs in CI)

--audit decodes each layout again, independently of the PNG on disk, and records for every map: tilesets, where the tile art
came from, references that do not resolve (metatile id, tile index, palette), and the image's size, hash and flat-colour share.
The plain run proves the shipped PNG files are still the audited ones and that the site refers only to maps that exist.
A structural pass is not a statement that a map looks right: `visual` in the record says how far each one was looked at."""
import argparse, hashlib, json, re, struct, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "site/assets/game/maps"
AUDIT = ROOT / "data/map-audit.json"
REVIEW = ROOT / "content/map-review.json"      # hand-kept: what was looked at, and known limits of a static picture
FLAT_MAX = 0.97                                # a map that is almost one flat colour has lost its tiles (dark caves sit near 0.6)


def image_stats(p):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    px = im.load()
    flat, top = 0, {}
    for by in range(0, h, 16):
        for bx in range(0, w, 16):
            c = px[bx, by]
            if all(px[bx + x, by + y] == c for y in range(0, 16, 3) for x in range(0, 16, 3)) and im.crop((bx, by, bx + 16, by + 16)).getcolors(1):
                flat += 1
                top[c] = top.get(c, 0) + 1
    n = (w // 16) * (h // 16) or 1
    return {"px": [w, h], "flat": round(flat / n, 4), "flat_top": round(max(top.values(), default=0) / n, 4),
            "sha": hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]}


def audit(game):
    sys.path.insert(0, str(ROOT / "tools"))
    import romx, romrender
    R = romx.Rom(game)
    rr = romrender.Renderer(R, game)
    B = romx.B
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    tsinfo = {}

    def ts(a):
        if a not in tsinfo:
            raw, _, meta = rr.tileset(a)
            tiles = R.u32(a + 4)
            sym = R.rev.get(tiles, hex(tiles))
            src = rr.dirs.get(sym)
            if not raw:
                how = "missing"
            elif not R.u8(a) & 1:
                how = "rom-raw"
            elif src is None:
                how = "rom-lz77"
            else:                                  # art read from the source folder: prove the ROM holds that same file
                how = "source"
                for f in sorted(src.glob("tiles.4bpp.*")):
                    blob = f.read_bytes()
                    if R.b[tiles - B: tiles - B + len(blob)] == blob:
                        how = "source=rom"
                        break
            tsinfo[a] = {"sym": R.rev.get(a, hex(a)), "tiles": len(raw) // 64, "art": how}
        return tsinfo[a]

    out = {}
    for k, m in world.items():
        lay = m["layout"]
        rec = {"id": f'{m["group"]}.{m["num"]}', "name": m["name"], "region": m["region"], "type": m["type"], "w": m["w"], "h": m["h"], "slug": m.get("slug"), "img": bool(m.get("img"))}
        out[k] = rec
        if not R.ok(lay):
            rec["problems"] = ["no layout"]
            continue
        w, h, blocks, pri, sec, ver = R.s32(lay), R.s32(lay + 4), R.u32(lay + 12), R.u32(lay + 16), R.u32(lay + 20), R.u8(lay + 24)
        prob = []
        if (w, h) != (m["w"], m["h"]):
            prob.append(f"layout {w}x{h} differs from world.json")
        if not (R.ok(blocks & ~1) and R.ok(pri) and R.ok(sec)) or w <= 0 or h <= 0:
            rec["problems"] = prob + ["layout pointers invalid"]
            continue
        P, S = ts(pri), ts(sec)
        rec.update(primary=P["sym"], secondary=S["sym"], version=ver, art=[P["art"], S["art"]])
        npri, npal = rr.split(ver)
        Pt, St = rr.tileset(pri), rr.tileset(sec)
        data = struct.unpack_from(f"<{w * h}H", romrender.packed(R, blocks, w * h * 2))
        used = {}
        for v in data:
            used[v & 0x3FF] = used.get(v & 0x3FF, 0) + 1
        bad_mt = bad_tile = bad_pal = 0
        for mid, n in used.items():
            meta, base = (Pt[2], mid * 16) if mid < npri else (St[2], (mid - npri) * 16)
            if base + 16 > len(meta):
                bad_mt += n
                continue
            hit_t = hit_p = False
            for e in struct.unpack_from("<8H", meta, base):
                t, pal = e & 0x3FF, e >> 12
                raw = Pt[0] if t < npri else St[0]
                if ((t if t < npri else t - npri) + 1) * 64 > len(raw):
                    hit_t = True
                if pal >= 13:
                    hit_p = True
            bad_tile += n * hit_t
            bad_pal += n * hit_p
        n = w * h
        rec["unresolved"] = {"metatile": bad_mt, "tile": bad_tile, "palette": bad_pal, "blocks": n}
        for label, a in (("primary", P), ("secondary", S)):
            if a["art"] == "missing":
                prob.append(f"{label} tile art not found ({a['sym']})")
            elif a["art"] == "source":
                prob.append(f"{label} art from source could not be matched to the ROM ({a['sym']})")
        if bad_mt:
            prob.append(f"{bad_mt} blocks use a metatile outside the tileset")
        if bad_tile / n > 0.02:
            prob.append(f"{bad_tile} blocks reference tiles outside the art")
        p = MAPS / f'{m.get("slug")}.png'
        if m.get("img"):
            if not p.exists():
                prob.append("PNG missing")
            else:
                st = image_stats(p)
                rec["image"] = st
                if st["px"] != [w * 16, h * 16]:
                    prob.append(f"PNG is {st['px']}, layout needs {[w * 16, h * 16]}")
                if st["flat_top"] > FLAT_MAX and n > 4:
                    prob.append(f"{st['flat_top']:.0%} of the map is one flat colour")
        else:
            prob.append("not rendered")
        if prob:
            rec["problems"] = prob
    AUDIT.write_text(json.dumps({"build": romx.BUILD["version"], "sha256": romx.BUILD["sha256"], "tilesets": sorted(tsinfo.values(), key=lambda t: t["sym"]), "maps": out}, indent=1))
    bad = {k: r["problems"] for k, r in out.items() if r.get("problems")}
    print(f"audited {len(out)} maps from the ROM; {len(bad)} with problems")
    for k, v in bad.items():
        print("  ", k, "|", "; ".join(v))
    return 1 if bad else 0


def check(dist):
    a = json.loads(AUDIT.read_text())
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    review = json.loads(REVIEW.read_text()) if REVIEW.exists() else {}
    err = []
    slugs = {}
    for k, m in world.items():
        r = a["maps"].get(k)
        if r is None:
            err.append(f"{k}: not in the audit record")
            continue
        if r.get("problems") and k not in review.get("accepted", {}):
            err.append(f"{k}: {'; '.join(r['problems'])}")
        if not m.get("img"):
            continue
        if m["slug"] in slugs:
            err.append(f"{k}: image name {m['slug']} is shared with {slugs[m['slug']]}")
        slugs[m["slug"]] = k
        p = MAPS / f'{m["slug"]}.png'
        if not p.exists():
            err.append(f"{k}: {p.name} missing")
            continue
        with Image.open(p) as im:
            if im.size != (m["w"] * 16, m["h"] * 16):
                err.append(f"{k}: {p.name} is {im.size}, metadata says {m['w']}x{m['h']} tiles")
        if hashlib.sha256(p.read_bytes()).hexdigest()[:16] != r.get("image", {}).get("sha"):
            err.append(f"{k}: {p.name} is not the audited image (re-run --audit after re-rendering)")
    for k in review.get("fixed", {}):                       # maps that were once broken must stay drawn
        r = a["maps"].get(k, {})
        if r.get("image", {}).get("flat_top", 1) > 0.6 or "missing" in r.get("art", ["missing"]):
            err.append(f"{k}: previously defective map has regressed")
    extra = sorted(p.name for p in MAPS.glob("*.png") if p.stem not in slugs)
    if extra:
        err.append(f"images no map uses: {', '.join(extra[:8])}")
    used = {}
    if dist and Path(dist).exists():
        for f in Path(dist).rglob("*.html"):
            for s in set(re.findall(r'assets/game/maps/([a-z0-9-]+)\.png', f.read_text(encoding="utf-8"))):
                used.setdefault(s, []).append(str(f.relative_to(dist).parent))
                if s not in slugs:
                    err.append(f"{f.relative_to(dist)}: refers to map image {s}.png, which does not exist")
            for s in set(re.findall(r'id="m-([a-z0-9-]+)"', f.read_text(encoding="utf-8"))):
                if s not in {m["slug"] for m in world.values()}:
                    err.append(f"{f.relative_to(dist)}: anchor m-{s} matches no map")
        (ROOT / "data/map-usage.json").write_text(json.dumps({slugs[s]: sorted(v) for s, v in sorted(used.items())}, indent=0))
    print(f"maps: {len(slugs)} images checked against the audit of {a['build']}" + (f"; {len(used)} shown on the site" if used else "") + f"; {len(err)} problems")
    for e in err:
        print("  ", e)
    return 1 if err else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    ap.add_argument("--dist", default=str(ROOT / "dist"))
    args = ap.parse_args()
    sys.exit(audit(Path(args.game).resolve()) if args.audit else check(args.dist))
