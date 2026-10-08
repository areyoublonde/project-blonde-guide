#!/usr/bin/env python3
"""Project Blonde guide - data extraction.

Reads the Project Blonde source tree (read-only) and writes structured JSON,
rendered maps and sprites into ../data and ../site/assets/game.

    python3 tools/extract.py [--game ../blonde]

Nothing in the game tree is modified. Every record keeps a `src` field
(file path, relative to the game root) so each fact can be traced back.
The site never prints `src`; it is provenance for editors only.

Scope: Johto / Kanto maps (the `_hns` source maps). Hoenn lives in the
Recharged-donor build layers and has its own extractor planned (DATA-SOURCES.md).
"""
import argparse, json, os, re, struct, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
ASSETS = ROOT / "site" / "assets" / "game"

# Maps rendered for the prototype (slug -> map dir). Add maps here as chapters are written.
RENDER_MAPS = {
    "ecruteak-city": "EcruteakCity_hns",
    "ecruteak-gym": "EcruteakCity_Gym_hns",
    "burned-tower-1f": "BurnedTower_1F_hns",
    "burned-tower-b1f": "BurnedTower_B1F_hns",
}
# Rendered only as region artwork (no chapter, no markers, no extra Pokemon pages).
ART_MAPS = {"vermilion-city": "VermilionCity_hns", "new-bark-town": "NewBarkTown_hns", "pallet-town": "PalletTown_hns", "olivine-city": "OlivineCity_hns"}
TRAINER_PICS = {"Leader Morty Hns": "leader_morty_hns", "Silver Hns": "silver_hns"}

NAME_FIX = {"MR_MIME": "Mr. Mime", "HO_OH": "Ho-Oh", "NIDORAN_F": "Nidoran♀", "NIDORAN_M": "Nidoran♂",
            "FARFETCHD": "Farfetch'd", "PORYGON_Z": "Porygon-Z", "MIME_JR": "Mime Jr.", "PORYGON2": "Porygon2"}


def title(const, prefix=""):
    s = const[len(prefix):] if const.startswith(prefix) else const
    return NAME_FIX.get(s) or " ".join(w.capitalize() for w in s.split("_"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def item_name(const):
    s = const.replace("ITEM_", "")
    m = re.match(r"(TM|HM)_(.+)", s)
    if m:
        return f"{m.group(1)} {title(m.group(2))}"
    return re.sub(r"\b(Hp|Pp|Tm|Hm)\b", lambda m: m.group(1).upper(), title(s))


# --------------------------------------------------------------------------- trainers
def parse_party(game, rel):
    text = (game / rel).read_text(encoding="utf-8")
    out = {}
    for block in re.split(r"\n(?==== )", text):
        m = re.match(r"=== (\w+) ===\n", block)
        if not m:
            continue
        tid = m.group(1)
        body = block[m.end():]
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        chunks = [c.strip() for c in re.split(r"\n\s*\n", body) if c.strip()]
        if not chunks:
            continue
        head = dict(l.split(":", 1) for l in chunks[0].splitlines() if ":" in l)
        head = {k.strip(): v.strip() for k, v in head.items()}
        mons = []
        for c in chunks[1:]:
            lines = c.splitlines()
            first = lines[0].strip()
            if ":" in first and not first.split(":")[0].strip().replace(" ", "").isalpha() is False and first.split(":")[0] in (
                    "Name", "Class", "Pic", "Gender", "Music", "Double Battle", "AI", "Items", "Mugshot"):
                continue
            sp, _, held = first.partition("@")
            sp = re.sub(r"\s*\((M|F)\)\s*", "", sp).strip()
            if "(" in sp:  # "Nickname (Species)"
                sp = sp[sp.index("(") + 1:sp.rindex(")")]
            mon = {"species": sp, "item": held.strip() or None, "moves": []}
            for l in lines[1:]:
                l = l.strip()
                if l.startswith("- "):
                    mon["moves"].append(l[2:].strip())
                elif l.startswith("Level:"):
                    mon["level"] = int(l.split(":")[1])
                elif l.startswith("Ability:"):
                    mon["ability"] = l.split(":")[1].strip()
                elif l.endswith("Nature"):
                    mon["nature"] = l.replace("Nature", "").strip()
            mons.append(mon)
        out[tid] = {
            "id": tid, "name": head.get("Name", ""), "class": re.sub(r"\s+Hns$", "", head.get("Class", "")),
            "pic": head.get("Pic", ""), "double": head.get("Double Battle", "No") == "Yes",
            "items": [i.strip() for i in head.get("Items", "").split("/") if i.strip()],
            "party": mons, "src": rel,
        }
    return out


# --------------------------------------------------------------------------- encounters
LAND = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]
WATER = [60, 30, 5, 4, 1]
RODS = {"old": ([0, 1], [70, 30]), "good": ([2, 3, 4], [60, 20, 20]), "super": ([5, 6, 7, 8, 9], [40, 40, 15, 4, 1])}


def merge(slots):
    agg = {}
    for sp, lo, hi, rate in slots:
        if sp == "SPECIES_NONE":
            continue
        a = agg.setdefault(sp, {"species": title(sp, "SPECIES_"), "id": sp, "min": lo, "max": hi, "rate": 0})
        a["min"], a["max"], a["rate"] = min(a["min"], lo), max(a["max"], hi), a["rate"] + rate
    return sorted(agg.values(), key=lambda a: -a["rate"])


def parse_encounters(game):
    rel = "src/data/wild_encounters.json"
    data = json.loads((game / rel).read_text())
    group = next(g for g in data["wild_encounter_groups"] if g["label"] == "gWildMonHeaders")
    out = {}
    for e in group["encounters"]:
        if not e["map"].endswith("_HNS"):
            continue
        label = e.get("base_label", "")
        tod = "night" if label.endswith("_Night") else "day"
        rec = out.setdefault(e["map"], {"map": e["map"], "src": rel, "tables": {}})
        for kind in ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons"):
            if kind not in e:
                continue
            mons = [(m["species"], m["min_level"], m["max_level"]) for m in e[kind]["mons"]]
            if kind == "land_mons":
                t = {"walk": merge([m + (LAND[i],) for i, m in enumerate(mons[:12])])}
            elif kind == "fishing_mons":
                t = {f"{rod}-rod": merge([mons[i] + (r,) for i, r in zip(idx, rates) if i < len(mons)])
                     for rod, (idx, rates) in RODS.items()}
            else:
                # Engine reads WATER_WILD_COUNT (5) slots; source rows list more. See DATA-SOURCES.md, V-03.
                key = "surf" if kind == "water_mons" else "rock-smash"
                t = {key: merge([m + (WATER[i],) for i, m in enumerate(mons[:5])])}
            for k, v in t.items():
                if v:
                    rec["tables"].setdefault(k, {})[tod] = v
    return out


# --------------------------------------------------------------------------- species
def parse_species(game):
    out = {}
    base = game / "src/data/pokemon/species_info"
    for f in sorted(base.glob("gen_*_families.h")):
        rel = str(f.relative_to(game))
        text = f.read_text(encoding="utf-8", errors="replace")
        parts = re.split(r"\n    \[(SPECIES_\w+)\] =\n", text)
        for i in range(1, len(parts), 2):
            sid, body = parts[i], parts[i + 1]
            g = lambda pat, d=None: (re.search(pat, body) or [None, d])[1]
            name = g(r'\.speciesName = _\("([^"]+)"\)')
            hp = g(r"\.baseHP\s*=\s*(\d+)")
            if not name or hp is None:
                continue
            types = re.search(r"\.types = MON_TYPES\(([^)]+)\)", body)
            abil = re.search(r"\.abilities = \{([^}]+)\}", body)
            evos = re.findall(r"\{(EVO_\w+),\s*([\w ]+?),\s*(SPECIES_\w+)", g(r"\.evolutions = EVOLUTION\((.*?)\),\n", "") or "")
            desc = re.search(r"\.description = COMPOUND_STRING\((.*?)\),\n", body, re.S)
            out[sid] = {
                "id": sid, "name": name, "slug": slug(name), "dir": sid.replace("SPECIES_", "").lower(),
                "types": [title(t.strip(), "TYPE_") for t in types.group(1).split(",")] if types else [],
                "stats": {k: int(g(rf"\.base{v}\s*=\s*(\d+)", 0)) for k, v in
                          [("hp", "HP"), ("atk", "Attack"), ("def", "Defense"), ("spa", "SpAttack"), ("spd", "SpDefense"), ("spe", "Speed")]},
                "abilities": [title(a.strip(), "ABILITY_") for a in abil.group(1).split(",") if a.strip() != "ABILITY_NONE"] if abil else [],
                "category": g(r'\.categoryName = _\("([^"]+)"\)'),
                "dex": " ".join(re.findall(r'"([^"]*)"', desc.group(1))).replace("\\n", " ").replace("  ", " ").strip() if desc else None,
                "evolves_to": [{"method": m, "param": p.strip(), "to": t} for m, p, t in evos],
                "src": rel,
            }
    for s in out.values():
        for e in s["evolves_to"]:
            if e["to"] in out:
                out[e["to"]].setdefault("evolves_from", {"from": s["id"], "method": e["method"], "param": e["param"]})
    return out


# --------------------------------------------------------------------------- maps
def read_pals(d, rng):
    pals = {}
    for i in rng:
        p = d / "palettes" / f"{i:02d}.pal"
        if p.exists():
            rows = p.read_text().split("\n")[3:19]
            pals[i] = [tuple(int(x) for x in r.split()) for r in rows if r.strip()]
    return pals


def tileset_dir(game, sym):
    header = (game / "src/data/tilesets/metatiles.h").read_text()
    m = re.search(rf"gMetatiles_{sym}\[\] = INCBIN_U16\(\"([^\"]+)/metatiles\.bin\"\)", header)
    return game / m.group(1)


def render_map(game, layout, out_png):
    """Compose a map exactly as the engine does: block -> metatile -> 8 tiles -> palette."""
    NP = 640  # NUM_TILES_IN_PRIMARY / NUM_METATILES_IN_PRIMARY for hns layouts (include/fieldmap.h)
    pri = tileset_dir(game, layout["primary_tileset"].replace("gTileset_", ""))
    sec = tileset_dir(game, layout["secondary_tileset"].replace("gTileset_", ""))
    pals = {**read_pals(pri, range(0, 7)), **read_pals(sec, range(7, 13))}
    tiles = []
    for d in (pri, sec):
        im = Image.open(d / "tiles.png")
        assert im.mode == "P", d
        tiles.append((im.size[0], im.size[1], im.tobytes()))
    metas = [struct.unpack(f"<{os.path.getsize(d / 'metatiles.bin') // 2}H", (d / "metatiles.bin").read_bytes()) for d in (pri, sec)]
    w, h = layout["width"], layout["height"]
    blocks = struct.unpack(f"<{w * h}H", (game / layout["blockdata_filepath"]).read_bytes())
    backdrop = pals[0][0]
    img = Image.new("RGB", (w * 16, h * 16), backdrop)
    px = img.load()
    for by in range(h):
        for bx in range(w):
            mid = blocks[by * w + bx] & 0x3FF
            mt = metas[0] if mid < NP else metas[1]
            base = (mid if mid < NP else mid - NP) * 8
            if base + 8 > len(mt):
                continue
            for k in range(8):
                e = mt[base + k]
                t, hf, vf, pal = e & 0x3FF, e & 0x400, e & 0x800, e >> 12
                tw, th, tb = tiles[0] if t < NP else tiles[1]
                ti = t if t < NP else t - NP
                tx, ty = (ti % (tw // 8)) * 8, (ti // (tw // 8)) * 8
                if ty + 8 > th or pal not in pals:
                    continue
                ox, oy = bx * 16 + (k % 2) * 8, by * 16 + ((k % 4) // 2) * 8
                colors = pals[pal]
                for y in range(8):
                    row = (ty + (7 - y if vf else y)) * tw + tx
                    for x in range(8):
                        c = tb[row + (7 - x if hf else x)] & 15
                        if c or k < 4:
                            px[ox + x, oy + y] = colors[c] if c else backdrop
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, optimize=True)
    return {"w": w, "h": h, "px": [w * 16, h * 16]}


def script_items(game, mapdir):
    """script label -> item constant, for finditem / giveitem one-liners in a map's scripts."""
    p = game / "data/maps" / mapdir / "scripts.inc"
    res = {}
    if p.exists():
        for m in re.finditer(r"^(\w+)::\s*\n\s*finditem (ITEM_\w+)", p.read_text(errors="replace"), re.M):
            res[m.group(1)] = m.group(2)
    return res


def parse_map(game, mapdir):
    rel = f"data/maps/{mapdir}/map.json"
    d = json.loads((game / rel).read_text())
    items = script_items(game, mapdir)
    ev = {"objects": [], "warps": [], "signs": [], "hidden": [], "triggers": [], "lights": []}
    for i, o in enumerate(d.get("object_events", [])):
        gfx = o["graphics_id"].replace("OBJ_EVENT_GFX_", "")
        rec = {"n": i + 1, "x": o["x"], "y": o["y"], "gfx": gfx, "script": o.get("script"), "flag": o.get("flag")}
        if gfx.startswith("SMALL_LIGHT"):
            ev["lights"].append([o["x"], o["y"]])
            continue
        if o.get("trainer_type", "TRAINER_TYPE_NONE") != "TRAINER_TYPE_NONE":
            rec["kind"] = "trainer"
        elif o.get("script") in items:
            rec["kind"], rec["item"] = "item", item_name(items[o["script"]])
        elif gfx.startswith("MON_BASE"):
            rec["kind"], rec["species"] = "pokemon", title(gfx.split("SPECIES_")[1])
        else:
            rec["kind"] = "npc"
        ev["objects"].append(rec)
    for i, wv in enumerate(d.get("warp_events", [])):
        ev["warps"].append({"n": i, "x": wv["x"], "y": wv["y"], "to": wv["dest_map"]})
    for b in d.get("bg_events", []):
        if b["type"] == "hidden_item":
            ev["hidden"].append({"x": b["x"], "y": b["y"], "item": item_name(b["item"])})
        else:
            ev["signs"].append({"x": b["x"], "y": b["y"], "script": b.get("script")})
    for c in d.get("coord_events", []):
        ev["triggers"].append({"x": c["x"], "y": c["y"], "script": c.get("script")})
    return {"id": d["id"], "dir": mapdir, "region": d.get("region", "").replace("REGION_", "").lower(),
            "mapsec": d.get("region_map_section"), "music": d.get("music"), "type": d.get("map_type"),
            "connections": [{"dir": c["direction"], "to": c["map"]} for c in (d.get("connections") or [])],
            "events": ev, "src": rel}


def sprite(src, dst, box=None):
    """Copy an indexed game sprite, making palette index 0 transparent."""
    if not src.exists():
        return False
    im = Image.open(src)
    if box:
        im = im.crop(box)
    if im.mode == "P":
        idx = im.tobytes()
        rgba = im.convert("RGBA")
        rgba.putdata([(r, g, b, 0 if i == idx[0] else 255) for (r, g, b, a), i in zip(rgba.getdata(), idx)])
        im = rgba
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, optimize=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game).resolve()
    if not (game / "data/maps").is_dir():
        sys.exit(f"Project Blonde source not found at {game}")
    OUT.mkdir(exist_ok=True)

    trainers = parse_party(game, "src/data/trainers_hns.party")
    enc = parse_encounters(game)
    species = parse_species(game)

    world = {}
    for d in sorted((game / "data/maps").iterdir()):
        if d.name.endswith("_hns") and (d / "map.json").exists():
            try:
                world[d.name] = parse_map(game, d.name)
            except Exception as ex:  # keep going; report at the end
                print("skip", d.name, ex)

    layouts = {l["id"]: l for l in json.loads((game / "data/layouts/layouts.json").read_text())["layouts"] if "id" in l}
    rendered = {}
    for s, mapdir in RENDER_MAPS.items():
        mj = json.loads((game / f"data/maps/{mapdir}/map.json").read_text())
        rendered[s] = {"map": mapdir, **render_map(game, layouts[mj["layout"]], ASSETS / "maps" / f"{s}.png")}

    for s, mapdir in ART_MAPS.items():
        mj = json.loads((game / f"data/maps/{mapdir}/map.json").read_text())
        rendered[s] = {"map": mapdir, "art": True, **render_map(game, layouts[mj["layout"]], ASSETS / "maps" / f"{s}.png")}

    # species -> where found (Johto / Kanto source maps only)
    where = {}
    id2dir = {m["id"]: k for k, m in world.items()}
    for mid, rec in enc.items():
        for method, tods in rec["tables"].items():
            for tod, rows in tods.items():
                for r in rows:
                    where.setdefault(r["id"], []).append({"map": id2dir.get(mid, mid), "method": method, "time": tod,
                                                          "min": r["min"], "max": r["max"], "rate": r["rate"]})

    # sprites actually referenced by the prototype pages
    need = set()
    for s in RENDER_MAPS.values():
        for r in enc.get(world[s]["id"], {"tables": {}})["tables"].values():
            for rows in r.values():
                need |= {x["id"] for x in rows}
    pic_ok = []
    pics = dict(TRAINER_PICS)
    pics.update({t["pic"]: t["pic"].lower().replace(" ", "_") for t in trainers.values() if t["pic"].startswith("Leader ")})
    for pic, fn in pics.items():
        if sprite(game / f"graphics/trainers/front_pics/{fn}.png", ASSETS / "trainers" / f"{fn}.png"):
            pic_ok.append(fn)
    for t in trainers.values():
        if t["pic"] in TRAINER_PICS:
            for m in t["party"]:
                sid = next((k for k, v in species.items() if v["name"].lower() == m["species"].lower()), None)
                if sid:
                    need.add(sid)
    for sid in list(need):  # include evolution relatives so family strips have art
        s = species.get(sid, {})
        need |= {e["to"] for e in s.get("evolves_to", [])}
        if s.get("evolves_from"):
            need.add(s["evolves_from"]["from"])
    got = []
    for sid in sorted(need):
        s = species.get(sid)
        if not s:
            continue
        d = game / "graphics/pokemon" / s["dir"]
        a = sprite(d / "anim_front.png", ASSETS / "pokemon" / f"{s['slug']}.png", (0, 0, 64, 64)) or \
            sprite(d / "front.png", ASSETS / "pokemon" / f"{s['slug']}.png", (0, 0, 64, 64))
        b = sprite(d / "icon.png", ASSETS / "icons" / f"{s['slug']}.png", (0, 0, 32, 32))
        if a:
            got.append(sid)
        s["art"], s["icon"] = bool(a), bool(b)
    for sid, s in species.items():  # small menu icons for every species (trainer rows can show any Pokemon)
        if "icon" not in s:
            s["icon"] = sprite(game / "graphics/pokemon" / s["dir"] / "icon.png", ASSETS / "icons" / f"{s['slug']}.png", (0, 0, 32, 32))

    # items: display name, in-game description, bag pocket
    items = {}
    itext = (game / "src/data/items.h").read_text(encoding="utf-8", errors="replace")
    iparts = re.split(r"\n    \[(ITEM_\w+)\] =\n", itext)
    for i in range(1, len(iparts), 2):
        body = iparts[i + 1]
        d = re.search(r"\.description = COMPOUND_STRING\((.*?)\),\n", body, re.S)
        pk = re.search(r"\.pocket = POCKET_(\w+)", body)
        items[item_name(iparts[i])] = {"id": iparts[i], "desc": " ".join(re.findall(r'"([^"]*)"', d.group(1))).replace("\\n", " ").strip() if d else None,
                                       "pocket": pk.group(1).replace("_", " ").title() if pk else None, "src": "src/data/items.h"}
    dump = lambda name, obj: (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    dump("items.json", items)
    dump("trainers.json", trainers)
    dump("encounters.json", enc)
    dump("species.json", species)
    dump("world.json", world)
    dump("where.json", where)
    dump("maps.json", rendered)
    dump("manifest.json", {"game": str(game), "trainers": len(trainers), "encounter_maps": len(enc), "species": len(species),
                           "maps": len(world), "rendered": list(rendered), "sprites": len(got), "trainer_pics": pic_ok})
    print(json.loads((OUT / "manifest.json").read_text()))


if __name__ == "__main__":
    main()
