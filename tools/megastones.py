#!/usr/bin/env python3
"""Mega Stones: every stone the game can hand to the player, and a completeness check.

    python3 tools/megastones.py [--game ../blonde]      (after romx.py and dex.py)

Reads, read-only:
  data/scripts/hns_mega_stone_menus.inc   the three lists Elm's aide offers (the script that is linked into the ROM)
  src/data/items.h                        every item defined with HOLD_EFFECT_MEGA_STONE
  data/rom/*.json                         item balls, hidden items, gift scripts and Mart stock decoded from the ROM
Checks that each offered item id sits in the ROM next to the aide's menu, then writes data/megastones.json.
"""
import argparse, json, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import romx

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game).resolve()
    R = romx.Rom(game)
    megas = json.loads((ROOT / "data/megas.json").read_text())
    by_item = {m["item_id"]: m for m in megas if m.get("stone")}
    defined = re.findall(r"\[(ITEM_\w+)\] =\n(?:(?!\n    \[).)*?HOLD_EFFECT_MEGA_STONE", (game / "src/data/items.h").read_text(errors="replace"), re.S)
    text = (game / "data/scripts/hns_mega_stone_menus.inc").read_text()
    offered = []
    for region in ("Kanto", "Johto", "Hoenn"):
        block = text[text.index(f"HnsMega_EventScript_{region}::"):]
        block = block[:block.index("goto HnsMega_EventScript_ChooseStone")]
        for sp, item in re.findall(r"dynmultipush HnsMega_Text_(SPECIES_\w+), (ITEM_\w+)", block):
            offered.append({"item_id": item, "stone": romx.item_name(item), "mega": sp, "list": region})
    # the same item ids must be present in the ROM inside the aide's region scripts
    for region in ("Kanto", "Johto", "Hoenn"):
        a = R.S[f"HnsMega_EventScript_{region}"]
        chunk = R.b[a - romx.B: a - romx.B + 400]
        for o in (x for x in offered if x["list"] == region):
            o["in_rom"] = struct.pack("<H", R.S[o["item_id"]]) in chunk
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    names = {romx.item_name(i) for i in defined}
    other = []
    for m in world.values():
        for o in m["events"]["objects"]:
            if o.get("item") in names:
                other.append({"stone": o["item"], "how": "item ball", "map": m["key"]})
        for h in m["events"]["hidden"]:
            if h["item"] in names:
                other.append({"stone": h["item"], "how": "hidden item", "map": m["key"]})
    for g in json.loads((ROOT / "data/rom/gives.json").read_text()):
        if g["item"] in names and g["how"] == "gift":
            other.append({"stone": g["item"], "how": "gift script", "sym": g["sym"]})
    for m in json.loads((ROOT / "data/rom/marts.json").read_text()):
        for i in m["items"]:
            if i in names:
                other.append({"stone": i, "how": "shop", "map": m["map"]})
    users = {}
    for t in json.loads((ROOT / "data/rom/trainers.json").read_text()).values():
        for mon in t["party"]:
            if mon.get("item") in names:
                users.setdefault(mon["item"], []).append(t["id"])
    got = {o["item_id"] for o in offered}
    out = {"offered": offered, "other_sources": other, "defined": [{"item_id": i, "stone": romx.item_name(i), "mega": by_item.get(i, {}).get("mega"), "species": by_item.get(i, {}).get("species")} for i in defined],
           "not_obtainable": [romx.item_name(i) for i in defined if i not in got and romx.item_name(i) not in {x["stone"] for x in other}],
           "held_by_trainers": users,
           "check": {"defined": len(defined), "offered_by_aide": len(offered), "offered_found_in_rom": sum(1 for o in offered if o.get("in_rom")),
                     "offered_without_form_link": [o["stone"] for o in offered if o["item_id"] not in by_item], "other_sources": len(other)}}
    (ROOT / "data/megastones.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out["check"]), "not obtainable:", len(out["not_obtainable"]))


if __name__ == "__main__":
    main()
