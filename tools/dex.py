#!/usr/bin/env python3
"""Project Blonde guide - Pokédex data.

    python3 tools/dex.py [--game ../blonde]      (after romx.py)

Numbers come from the shipped ROM (`gSpeciesInfo`: base stats, types, abilities, Pokédex number, evolution
methods with their conditions, level-up moves). Names, Pokédex text, form flags and sprite paths come from the
source tree, which is where the ROM's own strings and art were built from.

Output: data/dex.json, data/megas.json, site/assets/game/{pokemon,icons}/. Nothing in the game folder is written.
"""
import argparse, json, re, struct, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import romx
from romx import title, item_name, defines, B

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "site" / "assets" / "game"
SZ = 268          # sizeof(struct SpeciesInfo) in this build: distance between Bulbasaur's and Ivysaur's stat blocks
REGIONAL = {"isAlolanForm": "Alola", "isGalarianForm": "Galar", "isHisuianForm": "Hisui", "isPaldeanForm": "Paldea"}
TIME = {0: "in the morning", 1: "during the day", 2: "in the evening", 3: "at night"}
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().replace("♀", "-f").replace("♂", "-m").replace("é", "e")).strip("-")


def parse_source(game):
    out = {}
    for f in sorted((game / "src/data/pokemon/species_info").glob("gen_*_families.h")):
        text = f.read_text(encoding="utf-8", errors="replace")
        parts = re.split(r"\n    \[(SPECIES_\w+)\] =\n", text)
        for i in range(1, len(parts), 2):
            sid, body = parts[i], parts[i + 1]
            g = lambda pat: (re.search(pat, body) or [None, None])[1]
            name = g(r'\.speciesName = _\("([^"]+)"\)')
            if not name:
                continue
            desc = re.search(r"\.description = (?:COMPOUND_STRING\((.*?)\)|(\w+)),\n", body, re.S)
            out[sid] = {"name": name, "category": g(r'\.categoryName = _\("([^"]+)"\)'),
                        "text": " ".join(re.findall(r'"([^"]*)"', desc.group(1))).replace("\\n", " ").replace("  ", " ").strip() if desc and desc.group(1) else None,
                        "desc_ref": desc.group(2) if desc and desc.group(2) else None,
                        "front": g(r"\.frontPic = (\w+)"), "icon": g(r"\.iconSprite = (\w+)"),
                        "mega": bool(re.search(r"\.isMegaEvolution = TRUE", body)), "primal": bool(re.search(r"\.isPrimalReversion = TRUE", body)),
                        "regional": next((v for k, v in REGIONAL.items() if re.search(rf"\.{k} = TRUE", body)), None),
                        "src": str(f.relative_to(game))}
    return out


def pic_paths(game):
    """graphics symbol -> source image path"""
    out = {}
    for f in (game / "src/data/graphics").glob("pokemon*.h"):
        for m in re.finditer(r"(gMon(?:FrontPic|Icon)_\w+)\[\] = INCBIN_\w+\(\"([^\"]+?)\.(?:4bpp|8bpp)[^\"]*\"\)", f.read_text(errors="replace")):
            out.setdefault(m.group(1), m.group(2) + ".png")
    return out


def sprite(src, dst, box):
    if not src.exists():
        return False
    im = Image.open(src)
    im = im.crop(box)
    if im.mode == "P":
        idx = im.tobytes()
        rgba = im.convert("RGBA")
        bg = idx[0]
        rgba.putdata([(r, g, b, 0 if i == bg else 255) for (r, g, b, a), i in zip(rgba.getdata(), idx)])
        im = rgba
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, optimize=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    ap.add_argument("--no-sprites", action="store_true")
    args = ap.parse_args()
    game = Path(args.game).resolve()
    R = romx.Rom(game)
    S = R.S
    src = parse_source(game)
    pics = pic_paths(game)
    SP = defines(game / "include/constants/species.h", "SPECIES_")
    by_num = {}
    for k, v in SP.items():
        if k in src and (v not in by_num or len(k) < len(by_num[v])):
            by_num[v] = k
    ITEM, ABIL, TYPE = R.enum("ITEM_"), R.enum("ABILITY_"), R.enum("TYPE_")
    mv = (game / "include/constants/moves.h").read_text()
    MOVE = {S[n]: n for n in re.findall(r"^\s+(MOVE_\w+)(?:\s*=\s*\w+)?,", mv, re.M) if isinstance(S.get(n), int)}
    REGION = dict(enumerate(["", "Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola", "Galar", "Hisui", "Paldea"]))   # include/constants/regions.h
    secs = json.loads((ROOT / "data/rom/sections.json").read_text())["names"]
    base = S["gSpeciesInfo"]
    row = lambda n: base + SZ * n
    assert R.b[row(1) - B: row(1) - B + 6] == bytes([45, 49, 49, 45, 65, 65]), "gSpeciesInfo layout changed"

    def conds(p):
        out = []
        while p and R.ok(p) and R.u16(p) != 39 and len(out) < 6:       # CONDITIONS_END
            c, a1 = R.u16(p), R.u16(p + 2)
            if c == 1: out.append(TIME.get(a1, ""))
            elif c == 2: out.append("except " + TIME.get(a1, "").replace("in the ", "in the ").replace("at ", "at "))
            elif c == 3: out.append("with high friendship")
            elif c == 0: out.append("female only" if a1 == 254 else "male only")
            elif c == 7: out.append(f"holding {item_name(ITEM.get(a1, 'ITEM_?'))}")
            elif c == 4: out.append("Attack higher than Defense")
            elif c == 5: out.append("Attack equal to Defense")
            elif c == 6: out.append("Attack lower than Defense")
            elif c == 11: out.append("with high Beauty")
            elif c == 16: out.append(f"with {title(by_num.get(a1, 'SPECIES_?'), 'SPECIES_')} in the party")
            elif c in (17, 18): out.append(f"at {secs.get(str(a1), 'a special place').title()}" if c == 18 else "in a special location")
            elif c == 19: out.append(f"knowing {title(MOVE.get(a1, 'MOVE_?'), 'MOVE_')}")
            elif c == 20: out.append(f"traded for {title(by_num.get(a1, 'SPECIES_?'), 'SPECIES_')}")
            elif c == 21: out.append(f"with a {title(TYPE.get(a1, 'TYPE_?'), 'TYPE_')}-type in the party")
            elif c == 22: out.append("while it rains or is foggy")
            elif c == 23: out.append(f"knowing a {title(TYPE.get(a1, 'TYPE_?'), 'TYPE_')}-type move")
            elif c in (24, 25, 26): out.append("depending on its nature")
            elif c in (8, 9, 10, 32, 33, 34): out.append("depending on its personality value")
            elif c == 27: out.append(f"after taking {a1} recoil damage without fainting")
            elif c == 28: out.append(f"while missing at least {a1} HP")
            elif c == 29: out.append(f"after landing {a1} critical hits in one battle")
            elif c == 30: out.append(f"after using {title(MOVE.get(a1, 'MOVE_?'), 'MOVE_')} {R.u16(p + 4)} times")
            elif c == 31: out.append("after defeating specific wild Pokémon")
            elif c == 35: out.append(f"after {a1} steps walking with you")
            elif c == 36: out.append(f"with {R.u16(p + 4)} × {item_name(ITEM.get(a1, 'ITEM_?'))} in the Bag")
            elif c == 37: out.append(f"in {REGION.get(a1, 'a specific region')}")
            elif c == 38: out.append(f"outside {REGION.get(a1, 'a specific region')}")
            else: out.append("under a special condition")
            p += 8
        return [x for x in out if x]

    def evo_text(method, param, cs):
        if method == 1 or method == 6:
            t = f"Level {param}" if param else "Level up"
        elif method == 2:
            t = "Trade"
        elif method == 3:
            t = f"Use {item_name(ITEM.get(param, 'ITEM_?'))}"
        elif method == 5:
            t = "Special event"
        elif method == 7:
            t = "After a battle"
        elif method == 8:
            t = "Spin in the overworld"
        else:
            return None
        return t + (" " + ", ".join(cs) if cs else "")

    dex = {}
    for n in range(1, 1574):
        sid = by_num.get(n)
        if not sid:
            continue
        a = row(n)
        nat = R.u16(a + 60)
        s = src[sid]
        if not nat or not s["name"] or s["name"] in ("??????????",):
            continue
        evp = R.u32(a + 164)
        evos = []
        while R.ok(evp) and R.u16(evp) != 0xFFFF and len(evos) < 12:
            m, p, to = R.u16(evp), R.u16(evp + 2), R.u16(evp + 4)
            txt = evo_text(m, p, conds(R.u32(evp + 8)))
            if txt and to in by_num:
                evos.append({"to": by_num[to], "how": txt})
            evp += 12
        lp, moves = R.u32(a + 152), []
        while R.ok(lp) and R.u16(lp) != 0xFFFF and len(moves) < 120:
            moves.append([R.u16(lp + 2), title(MOVE.get(R.u16(lp), "MOVE_?"), "MOVE_")])
            lp += 4
        ab = [R.u16(a + 24 + 2 * i) for i in range(3)]
        types = [title(TYPE.get(R.u8(a + 6 + i), ""), "TYPE_") for i in range(2)]
        dex[sid] = {"id": sid, "num": n, "dex": nat, "name": re.sub(r"-[AGHP]$", "", s["name"]) if s["regional"] else s["name"], "category": s["category"], "text": s["text"],
                    "types": list(dict.fromkeys(types)), "stats": dict(zip(["hp", "atk", "def", "spe", "spa", "spd"], R.b[a - B: a - B + 6])),
                    "abilities": [title(ABIL.get(x, ""), "ABILITY_") for x in ab[:2] if x], "hidden_ability": title(ABIL.get(ab[2], ""), "ABILITY_") if ab[2] else None,
                    "catch_rate": R.u8(a + 8), "evolves_to": evos, "moves": moves, "mega": s["mega"], "primal": s["primal"], "regional": s["regional"],
                    "front": s["front"], "icon_sym": s["icon"], "src": f"gSpeciesInfo[{n}] @ {a:#x}; {s['src']}"}

    # group by Pokédex number: the plain species is the entry, everything else a form of it
    groups = {}
    for d in dex.values():
        groups.setdefault(d["dex"], []).append(d)
    for g in groups.values():
        g.sort(key=lambda d: d["num"])
        head = g[0]
        head["kind"] = "regional" if head["regional"] else "species"
        for f in g[1:]:
            f["kind"] = "mega" if (f["mega"] or f["primal"]) else "form"
            f["of"] = head["id"]
    name_first = {}
    for d in sorted(dex.values(), key=lambda d: d["num"]):
        if d["kind"] in ("species", "regional"):
            name_first.setdefault(d["name"].lower(), d["id"])
    for d in dex.values():
        if d["kind"] == "regional":
            d["base"] = name_first.get(d["name"].lower()) if name_first.get(d["name"].lower()) != d["id"] else None
            d["slug"] = slug(d["name"]) + "-" + d["regional"].lower()
            d["label"] = f'{d["regional"]}n form' if d["regional"] != "Paldea" else "Paldean form"
        elif d["kind"] == "species":
            d["slug"] = slug(d["name"])
        else:
            suffix = d["id"].replace(dex[d["of"]]["id"], "").strip("_").lower().replace("_", "-")
            d["slug"] = dex[d["of"]].get("slug", slug(d["name"])) + "-" + (suffix or "form")
            d["form_name"] = title(suffix.replace("-", "_").upper()) if suffix else "Form"
    seen = {}
    for d in sorted(dex.values(), key=lambda d: d["num"]):      # a few species share a display name with a form
        if d["slug"] in seen:
            d["slug"] += f'-{d["num"]}'
        seen[d["slug"]] = 1
    for d in dex.values():
        for e in d["evolves_to"]:
            if e["to"] in dex:
                dex[e["to"]].setdefault("evolves_from", {"from": d["id"], "how": e["how"]})

    # Mega Stones: form-change table (source) checked against the ROM's species rows
    megas = []
    fc = (game / "src/data/pokemon/form_change_tables.h").read_text()
    for m in re.finditer(r"\{FORM_CHANGE_BATTLE_MEGA_EVOLUTION_ITEM,\s*(SPECIES_\w+),\s*(ITEM_\w+)\}", fc):
        sp, item = m.group(1), m.group(2)
        if sp in dex and dex[sp].get("of"):
            megas.append({"stone": item_name(item), "item_id": item, "mega": sp, "species": dex[sp]["of"], "src": "src/data/pokemon/form_change_tables.h"})
    for m in re.finditer(r"\{FORM_CHANGE_BATTLE_MEGA_EVOLUTION_MOVE,\s*(SPECIES_\w+),\s*(MOVE_\w+)\}", fc):
        if m.group(1) in dex and dex[m.group(1)].get("of"):
            megas.append({"stone": None, "move": title(m.group(2), "MOVE_"), "mega": m.group(1), "species": dex[m.group(1)]["of"], "src": "src/data/pokemon/form_change_tables.h"})

    n_art = n_icon = 0
    for d in dex.values():
        fp, ip = pics.get(d["front"] or ""), pics.get(d["icon_sym"] or "")
        d["art"] = d["icon"] = False
        if not args.no_sprites:
            if fp:
                d["art"] = sprite(game / fp, ASSETS / "pokemon" / f"{d['slug']}.png", (0, 0, 64, 64))
            if ip:
                d["icon"] = sprite(game / ip, ASSETS / "icons" / f"{d['slug']}.png", (0, 0, 32, 32))
        else:
            d["art"], d["icon"] = (ASSETS / "pokemon" / f"{d['slug']}.png").exists(), (ASSETS / "icons" / f"{d['slug']}.png").exists()
        n_art += d["art"]; n_icon += d["icon"]
        d.pop("front"); d.pop("icon_sym")
    (ROOT / "data/dex.json").write_text(json.dumps(dex, indent=1, ensure_ascii=False))
    (ROOT / "data/megas.json").write_text(json.dumps(megas, indent=1, ensure_ascii=False))
    kinds = {}
    for d in dex.values():
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    print(json.dumps({"entries": len(dex), "kinds": kinds, "mega_links": len(megas), "art": n_art, "icons": n_icon}))


if __name__ == "__main__":
    main()
