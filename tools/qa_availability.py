#!/usr/bin/env python3
"""Regression tests for the availability audit: item aliases, NPC gifts and shops a clerk opens through a script branch.

    python3 tools/qa_availability.py [--game ../blonde]      -> exit 1 on any failure

Background (2026-10-09): Porygon2 and Porygon-Z were left out of the public Pokédex because the audit compared item
constants by name. The scripts say ITEM_UP_GRADE, the evolution table resolves to ITEM_UPGRADE; both are item 228.
The Up-Grade is a gift in Silph Co and is sold in Mahogany Town, where the clerk's script only branches to the shop
after the Rocket Hideout, so the shop list was not attached to any map either.

Three layers, each skipped (and reported as skipped) when its input is absent:
  data   data/rom/*.json and data/availability.json          always (also in the Pages workflow)
  site   dist/                                               after tools/build.py
  rom    the game folder                                     local only; the ROM is never in the repository
Nothing is written.
"""
import argparse, json, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import availability
from romx import B, BUILD

ROOT = Path(__file__).resolve().parent.parent
res = []


def ok(name, cond, detail=""):
    res.append(bool(cond))
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail and not cond else ""), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game)
    J = lambda p: json.loads((ROOT / p).read_text())
    av, marts, gives, dex = J("data/availability.json"), J("data/rom/marts.json"), J("data/rom/gives.json"), J("data/dex.json")
    rep, sp = av["report"], av["species"]

    print("item aliases")
    ids = availability.item_ids({"ITEM_UPGRADE": 228, "ITEM_UP_GRADE": 228, "ITEM_DUBIOUS_DISC": 232, "gItems": 0x08123456}, "")
    ok("two constants of one item resolve to the same id", ids["ITEM_UP_GRADE"] == ids["ITEM_UPGRADE"] == 228 and "gItems" not in ids)
    ids = availability.item_ids({"ITEM_UPGRADE": 228}, "    ITEM_UPGRADE = 228,\n    ITEM_UP_GRADE = ITEM_UPGRADE, // Pre-Gen VIII name\n#define ITEM_OLD_UPGRADE ITEM_UP_GRADE\n")
    ok("an alias the symbol table lacks is taken from items.h, through a chain", ids.get("ITEM_UP_GRADE") == 228 and ids.get("ITEM_OLD_UPGRADE") == 228, ids)
    names = availability.rom_item_names({228: "ITEM_UPGRADE", 232: "ITEM_DUBIOUS_DISC"})
    ok("ROM display names map back to ids", names == {"Upgrade": 228, "Dubious Disc": 232}, names)
    ok("the audit lists the Up-Grade under both constants", rep["item_aliases"].get("228") == ["ITEM_UPGRADE", "ITEM_UP_GRADE"], rep["item_aliases"].get("228"))
    ev = rep["evolution_items"]
    for i, n in rep["item_aliases"].items():
        if i in ev:
            ok(f"aliased evolution item {ev[i]['item']} ({' = '.join(n)}) has a source", ev[i]["sources"])
    no_src = sorted(v["item"] for v in ev.values() if not v["sources"])
    ok("evolution items without any source are only the known ones", no_src == ["Prism Scale"], no_src)     # Feebas also evolves by Beauty; Milotic is obtainable

    print("NPC gifts")
    g = [x for x in gives if x["item"] == "Upgrade" and x["how"] == "gift"]
    ok("the ROM gift list has the Silph Co Up-Grade", [x["sym"] for x in g] == ["SaffronCity_SilphCo_EventScript_Officer"], g)
    src = lambda i: {(s["how"], s["map"]) for s in ev[str(i)]["sources"]}
    ok("the audit counts that gift as an Up-Grade source", ("gift", "SaffronCity_SilphCo_hns") in src(228), src(228))
    ok("the audit counts the Route 42 hidden Dubious Disc", ("hidden item", "Route42_hns") in src(232), src(232))

    print("shops opened by a script branch")
    m = [x for x in marts if x["list_sym"] == "MahoganyTown_Pokemart"]
    ok("the Mahogany shop list is attached to its map", len(m) == 1 and m[0]["map"] == "MahoganyTown_Shop_hns", m)
    ok("it is reached through the clerk's branch, not directly", m and m[0].get("via") == "MahoganyTown_Shop_EventScript_Granny" and m[0]["sym"] == "MahoganyTown_Shop_EventScript_GrannyShop", m)
    ok("it stocks the Up-Grade and the Dubious Disc", m and {"Upgrade", "Dubious Disc"} <= set(m[0]["items"]), m and m[0]["items"])
    ok("the audit counts the shop for both items", ("shop", "MahoganyTown_Shop_hns") in src(228) and ("shop", "MahoganyTown_Shop_hns") in src(232))
    ok("shops run directly by a clerk are still attached", sum(1 for x in marts if not x.get("via")) >= 37, len(marts))
    ok("every shop list sits on a map", all(x["map"] for x in marts))

    print("result")
    p2, pz = sp["SPECIES_PORYGON2"], sp["SPECIES_PORYGON_Z"]
    how = lambda v: [(x["from"], x["detail"]) for x in v["methods"] if x["kind"] == "evolution"]
    ok("Porygon2 is obtainable: Porygon + Up-Grade", p2["status"] == "obtainable" and how(p2) == [("SPECIES_PORYGON", "Use Upgrade or Trade holding Upgrade")], how(p2))
    ok("Porygon-Z is obtainable: Porygon2 + Dubious Disc", pz["status"] == "obtainable" and how(pz) == [("SPECIES_PORYGON2", "Use Dubious Disc or Trade holding Dubious Disc")], how(pz))
    ok("neither needs a link trade", not p2["methods"][0]["link_trade_only"] and not pz["methods"][0]["link_trade_only"])
    ok("no evolution is blocked for want of an item", not any("has no source" in w for b in rep["evolution_blocks"].values() for e in b for w in e["why"]), rep["evolution_blocks"])
    pub = [k for k, v in sp.items() if v["status"] == "obtainable"]
    ok("the public Pokédex is the game's own list: 482 entries", len(pub) == 482 and all(sp[k]["in_game_dex"] for k in pub) and not [k for k, v in sp.items() if v["in_game_dex"] and v["status"] != "obtainable"], len(pub))

    print("site")
    dist = ROOT / "dist"
    if not (dist / "pokemon").is_dir():
        print("  skip  dist/ is not built")
    else:
        text = lambda p: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", (dist / p).read_text(encoding="utf-8"))))
        for k, need in (("SPECIES_PORYGON2", "Use Upgrade"), ("SPECIES_PORYGON_Z", "Use Dubious Disc")):
            f = f'pokemon/{dex[k]["slug"]}/index.html'
            ok(f"{f} exists and gives the method", (dist / f).is_file() and need in text(f) and "not obtainable" not in text(f))
        fam = text(f'pokemon/{dex["SPECIES_PORYGON"]["slug"]}/index.html')
        ok("Porygon's family no longer marks its evolutions as not obtainable", "not obtainable" not in fam and "Porygon2" in fam)
        up, dd = text("items/upgrade/index.html"), text("items/dubious-disc/index.html")
        ok("the Up-Grade page names Silph Co and the Mahogany shop", "Silph Co" in up and "Mahogany" in up, up[:300])
        ok("the Dubious Disc page names Route 42 and the Mahogany shop", "Route 42" in dd and "Mahogany" in dd, dd[:300])
        idx = json.loads((dist / "assets/search-index.json").read_text(encoding="utf-8"))
        urls = {e["u"] for e in idx}
        ok("search finds Porygon2 and Porygon-Z", all(f'/pokemon/{dex[k]["slug"]}/' in urls for k in ("SPECIES_PORYGON2", "SPECIES_PORYGON_Z")))
        ok("the Pokédex index lists them", all(f'id="{dex[k]["slug"]}"' in (dist / "pokemon/index.html").read_text(encoding="utf-8") for k in ("SPECIES_PORYGON2", "SPECIES_PORYGON_Z")))

    print("rom")
    rom = game / BUILD["folder"] / BUILD["rom"]
    if not rom.is_file():
        print("  skip  the game folder is not here")
    else:
        b = rom.read_bytes()
        S = json.loads((game / BUILD["symbols"]).read_text())
        at = lambda n: S[n] - B
        ids = availability.item_ids(S, (game / "include/constants/items.h").read_text())
        ok("the linked symbol table gives both Up-Grade constants one id", ids["ITEM_UP_GRADE"] == ids["ITEM_UPGRADE"])
        up, dd = ids["ITEM_UPGRADE"], ids["ITEM_DUBIOUS_DISC"]
        o = at("SaffronCity_SilphCo_EventScript_Officer")
        ok("Silph Co officer: giveitem Up-Grade in the ROM", b"\x1a\x00\x80" + struct.pack("<H", up) + b"\x1a\x01\x80\x01\x00\x09\x00" in b[o:o + 40], b[o:o + 40].hex(" "))
        o = at("MahoganyTown_Shop_EventScript_Granny")
        ok("Mahogany clerk: a conditional goto leads to the shop", b"\x06\x04" + struct.pack("<I", S["MahoganyTown_Shop_EventScript_GrannyShop"]) in b[o:o + 40], b[o:o + 40].hex(" "))
        o = at("MahoganyTown_Shop_EventScript_GrannyShop")
        ok("the shop branch opens MahoganyTown_Pokemart", b"\x86" + struct.pack("<I", S["MahoganyTown_Pokemart"]) in b[o:o + 16])
        o = at("MahoganyTown_Pokemart")
        stock = []
        while struct.unpack_from("<H", b, o)[0] and len(stock) < 40:
            stock.append(struct.unpack_from("<H", b, o)[0]); o += 2
        ok("its stock in the ROM has the Up-Grade and the Dubious Disc", up in stock and dd in stock, stock)

    print(f"\n{sum(res)} of {len(res)} checks passed")
    sys.exit(0 if all(res) else 1)


if __name__ == "__main__":
    main()
