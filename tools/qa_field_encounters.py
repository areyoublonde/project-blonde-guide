"""Targeted checks of tree/rock encounter data and generated player-facing rows.

Run after build.py. Pass --game ../blonde to also compare all shared slots with
the approved ROM; omit it on the publishing runner, which has no ROM.
"""
import argparse
import collections
import json
import re
from pathlib import Path

import model as M


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game")
    args = ap.parse_args()
    report = M.J(M.DATA / "rom/field-encounters.json")
    assert report["build"]["sha256"] == M.BUILD["build"]["sha256"]
    shared = {"headbutt", "rock-smash"}
    expected = {"AzaleaTown_hns": 10, "Route42_hns": 15, "Mahoganytown_hns": 15,
                **{f"Route{n}_hns": 20 for n in (26, 44, 45, 47, 48)},
                "Route28_hns": 40, "MtSilver_Outside_hns": 40, "MtSilver_MountainSide_hns": 40}
    heracross = [x for x in M.WHERE["SPECIES_HERACROSS"] if x["method"] in shared]
    assert {x["map"] for x in heracross} == set(expected)
    assert all(x["method"] == "headbutt" and x["min"] == x["max"] == expected[x["map"]]
               and x["rate"] == 5 for x in heracross)
    for mk, ev in report["maps"].items():
        rec = M.enc[mk]
        assert set(rec["tables"]) & shared == set(ev["methods"]), mk
        if not ev["methods"]:
            assert rec["unavailable_tables"]["rock-smash"], mk
    for mk in ("Route32_hns", "VermilionCity_hns"):
        assert M.enc[mk]["tables"]["headbutt"] == M.enc[mk]["tables"]["rock-smash"]
    for mk in ("CianwoodCity_hns", "CliffEdgeCave_hns", "GraniteCave_B2F", "Route111"):
        assert set(M.enc[mk]["tables"]) & shared == {"rock-smash"}
    for av in M.AV.values():
        for method in av["methods"]:
            kind = method["detail"].split(",", 1)[0]
            if method["kind"] == "wild" and kind in shared:
                assert kind in M.enc[method["map"]]["tables"], method
    html = (M.DIST / "pokemon/heracross/index.html").read_text()
    rows = re.findall(r"<tr>.*?</tr>", html, re.S)
    tree_rows = [r for r in rows if 'data-l="How">Headbutt<' in r]
    assert len(tree_rows) == len(expected)
    assert not any('data-l="How">Rock Smash<' in r for r in rows)
    assert not any("Route 46" in r or "Blackthorn City" in r for r in rows)
    azalea = next(r for r in tree_rows if "Azalea Town" in r)
    assert 'data-l="Level">10<' in azalea and 'data-l="Chance">5%<' in azalea
    pineco = (M.DIST / "pokemon/pineco/index.html").read_text()
    route32 = [r for r in re.findall(r"<tr>.*?</tr>", pineco, re.S) if ">Route 32<" in r]
    assert len(route32) == 2 and any(">Headbutt<" in r for r in route32) and any(">Rock Smash<" in r for r in route32)
    azalea_page = (M.DIST / "world/johto/azalea-town/index.html").read_text()
    assert 'class="label method">Headbutt<' in azalea_page
    assert 'class="label method">Rock Smash<' not in azalea_page
    if args.game:
        import romx
        R = romx.Rom(Path(args.game).resolve())
        # Check the entire affected table slice, including unused entries.
        # Compare numeric species, levels and slot weights independently of labels.
        for mk, ev in report["maps"].items():
            rec = M.enc[mk]
            table = next((rec["tables"][k] for k in shared if k in rec["tables"]), None)
            if table is None:
                table = rec["unavailable_tables"]["rock-smash"]
            index = int(re.search(r"\[(\d+)\]", rec["src"])[1])
            header = R.S["gWildMonHeaders"] + index * 84
            assert (R.u8(header), R.u8(header + 1)) == (M.world[mk]["group"], M.world[mk]["num"])
            for time, name in enumerate(romx.TIMES):
                info = R.u32(header + 12 + time * 20)
                if not info:
                    assert name not in table
                    continue
                slots = R.u32(info + 4)
                actual = collections.defaultdict(lambda: [255, 0, 0])
                for i, rate in enumerate((60, 30, 5, 4, 1)):
                    a = slots + 4 * i
                    species = R.u16(a + 2)
                    if not species:
                        continue
                    row = actual[species]
                    row[0], row[1], row[2] = min(row[0], R.u8(a)), max(row[1], R.u8(a + 1)), row[2] + rate
                want = {M.DEX[x["id"]]["num"]: [x["min"], x["max"], x["rate"]] for x in table[name]}
                assert dict(actual) == want, (mk, name)
    print(f"PASS: {len(report['maps'])} shared tables; 11 Heracross Headbutt locations; mixed/rock-only maps; availability and rendered pages" + ("; ROM slot comparison" if args.game else ""))


if __name__ == "__main__":
    main()
