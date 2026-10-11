"""Resolve the shared rock/tree table to the interactions present in each ROM map.

Run this after an existing extraction to refresh only the shared encounter tables:
    python3 tools/field_encounters.py --game ../blonde
Then regenerate availability.py and build.py. No ROM or map image is written.
"""
import argparse
import copy
import json
import struct
from pathlib import Path

from romrender import packed

ROOT = Path(__file__).resolve().parent.parent
SHARED = ("headbutt", "rock-smash")


def resolve(R, encounters, world):
    evidence = {}
    for key, rec in encounters.items():
        raw = next((rec["tables"][m] for m in SHARED if m in rec["tables"]), None)
        if raw is None:
            raw = rec.get("unavailable_tables", {}).get("rock-smash")
        if raw is None or key not in world or "#" in key:
            continue
        m = world[key]
        header = R.u32(R.u32(R.S["gMapGroups"] + 4 * m["group"]) + 4 * m["num"])
        layout = R.u32(header)
        version = R.u8(layout + 24)
        width, height = R.u32(layout), R.u32(layout + 4)
        trees = []
        # HNS tree behaviour is 0xf0. Imported Emerald layouts have their own
        # behaviour namespace; do not interpret donor values as HNS trees.
        if version == 2:
            blocks = struct.unpack(f"<{width * height}H", packed(R, R.u32(layout + 12), width * height * 2))
            attributes = [R.u32(R.u32(layout + off) + 16) for off in (16, 20)]
            for i, block in enumerate(blocks):
                tile = block & 0x3ff
                secondary = tile >= 640
                attr = R.u16(attributes[secondary] + 2 * (tile - 640 if secondary else tile))
                if attr & 0xff == 0xf0:
                    trees.append([i % width, i // width])
        events = R.u32(header + 4)
        objects = R.u32(events + 4)
        rocks = []
        scripted_trees = []
        for i in range(R.u8(events)):
            obj = objects + 24 * i
            if R.u8(obj + 3) != 0:  # clones do not carry an interaction script
                continue
            script = R.u32(obj + 16)
            xy = [R.s16(obj + 4), R.s16(obj + 6)]
            if not (0 <= xy[0] < width and 0 <= xy[1] < height):
                continue
            if script == R.S["EventScript_RockSmash"]:
                rocks.append(xy)
            elif script == R.S["EventScript_Headbutt"]:
                scripted_trees.append(xy)
        methods = (["headbutt"] if trees or scripted_trees else []) + (["rock-smash"] if rocks else [])
        # Only HNS tables need relabelling. Preserve donor tables, with a guard
        # proving that their existing Rock Smash label has a real interaction.
        if version != 2:
            assert rocks, f"Unresolved donor shared encounter table: {key}"
        density = next((rec.get("density", {}).get(method) for method in SHARED
                        if method in rec.get("density", {})), rec.get("unavailable_density"))
        def replace_shared(values, replacement):
            result = {}
            inserted = False
            for name, value in values.items():
                if name in SHARED:
                    if not inserted:
                        result.update(replacement)
                        inserted = True
                else:
                    result[name] = value
            if not inserted:
                result.update(replacement)
            return result

        rec["tables"] = replace_shared(rec["tables"], {method: copy.deepcopy(raw) for method in methods})
        rec["density"] = replace_shared(rec.get("density", {}),
                                        {method: density for method in methods} if density is not None else {})
        rec.pop("unavailable_tables", None)
        rec.pop("unavailable_density", None)
        if not methods:
            # Retain the ROM evidence without advertising an unusable source.
            rec["unavailable_tables"] = {"rock-smash": raw}
            rec["unavailable_density"] = density
        evidence[key] = {"methods": methods, "headbutt_tile_count": len(trees),
                         "first_headbutt_tile": trees[0] if trees else None,
                         "headbutt_objects": scripted_trees, "rock_smash_object_count": len(rocks),
                         "first_rock_smash_object": rocks[0] if rocks else None,
                         "map_header": hex(header), "layout": hex(layout), "table": rec["src"]}
    return evidence


def main():
    import romx
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    args = ap.parse_args()
    R = romx.Rom(Path(args.game).resolve())
    manifest = json.loads((ROOT / "data/rom/manifest.json").read_text())
    assert manifest["build"]["sha256"] == romx.BUILD["sha256"], "Extraction and ROM builds differ"
    path = ROOT / "data/rom/encounters.json"
    encounters = json.loads(path.read_text())
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    evidence = resolve(R, encounters, world)
    path.write_text(json.dumps(encounters, indent=1, ensure_ascii=False))
    report = {"build": romx.BUILD, "verification": "ROM tables, metatile behaviours and object scripts; not a gameplay test",
              "maps": evidence}
    (ROOT / "data/rom/field-encounters.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps({"maps": len(evidence), "headbutt": sum("headbutt" in x["methods"] for x in evidence.values()),
                      "rock_smash": sum("rock-smash" in x["methods"] for x in evidence.values()),
                      "no_interaction": sum(not x["methods"] for x in evidence.values())}))


if __name__ == "__main__":
    main()
