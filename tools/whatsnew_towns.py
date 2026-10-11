#!/usr/bin/env python3
"""Project Blonde guide - the v1.2 town gallery: Hoenn's towns in v1.1 and in v1.2.

    python3 tools/whatsnew_towns.py [--workspace ..]

Source: the verified v1.2 release package (output/project-blonde-v1.2-rc2-20261011): its placement list
(reports/IMPLEMENTED-PLACEMENTS.json), its town test (reports/towns/*.json) and that test's screenshots
(evidence/<town>/before-viewNN.png = public v1.1, after-viewNN.png = public v1.2; the same cell, native 240x160).
Checked here before anything is written: the package ROM is the released v1.2; the placement totals are the release's;
every placement is an object on that cell, with that graphic, in this guide's own extraction of the v1.2 ROM
(data/rom/world.json, tools/romx.py); every town test found no Pokémon object in v1.1; and every species a caption
names is one the town test recorded in that view.

Output: site/assets/game/whatsnew/v1.2/<shot>-v1.1.png and -v1.2.png (copied pixel for pixel), the title screenshot
site/assets/game/title/title-v1.2.png, and data/whatsnew-v1.2.json. Run it after romx.py.
Nothing outside this repository is written.
"""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = {"before": ("v1.1", "v111", "2a3299a0daa04225fc4945ed5835ac673d37be2f990ef4ad37aebd6eb856ac33"),
          "after": ("v1.2", "v113", "7a17f42fca0927417c67e1f6c10312a29c6b438adb7218d25fa78162c7736097")}
PACKAGE = "output/project-blonde-v1.2-rc2-20261011"
TOTALS = {"total": 125, "towns": 16, "talkers": 41, "swimmers": 14}      # release-information.json changelog
GROUPS = [("rooftops", "Rooftops", "Perched on houses and on every Gym."), ("treetops", "Treetops", "Up in the branches, above the paths."),
          ("ground", "On the ground", "On lawns, beaches and in gardens."), ("water", "In the water", "Swimming in ponds, lakes and open sea.")]
# (group, town folder, view number, caption, species the caption names)
SHOTS = [("rooftops", "dewford-town", 2, "A Wingull on a rooftop by the water.", ["Wingull"]),
         ("rooftops", "mossdeep-city", 2, "Solrock and Lunatone on the roof of the Gym.", ["Solrock", "Lunatone"]),
         ("rooftops", "petalburg-city", 4, "A Slakoth dozing on a rooftop.", ["Slakoth"]),
         ("treetops", "mossdeep-city", 1, "Three Beldum among the treetops.", ["Beldum"]),
         ("treetops", "littleroot-town", 2, "A Wurmple in the treetops and a Poochyena beside a house.", ["Wurmple", "Poochyena"]),
         ("treetops", "fortree-city", 3, "A Tropius in the trees below the Gym.", ["Tropius"]),
         ("ground", "littleroot-town", 1, "Zigzagoon wandering between the houses.", ["Zigzagoon"]),
         ("ground", "verdanturf-town", 1, "Roselia among the flowers, and a Skitty.", ["Roselia", "Skitty"]),
         ("ground", "lilycove-city", 1, "Skitty and Azurill out on the grass.", ["Skitty", "Azurill"]),
         ("water", "pacifidlog-town", 1, "Corsola and a Wailmer swimming around the town, and a Wingull on a sea rock.", ["Corsola", "Wailmer", "Wingull"]),
         ("water", "sootopolis-city", 1, "Two Luvdisc in the lake.", ["Luvdisc"]),
         ("water", "petalburg-city", 1, "A Marill in the pond, with a Ralts and a Slakoth on the shore.", ["Marill", "Ralts", "Slakoth"])]
sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workspace", default=str(ROOT.parent))
    P = Path(ap.parse_args().workspace).resolve() / PACKAGE
    assert sha((P / "Pokemon - Project Blonde.gba").read_bytes()) == PUBLIC["after"][2], "not the released v1.2 game"
    manifest = json.loads((ROOT / "data/rom/manifest.json").read_text())
    assert manifest["build"]["sha256"] == PUBLIC["after"][2], "data/rom was not extracted from v1.2: run tools/romx.py first"
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    world = world.get("maps", world)
    I = json.loads((P / "reports/IMPLEMENTED-PLACEMENTS.json").read_text())
    pl = I["placements"]
    assert I["romSha256"] == PUBLIC["after"][2] and {k: I[k] for k in TOTALS} == TOTALS and len(pl) == TOTALS["total"]
    assert sum(p["talks"] for p in pl) == TOTALS["talkers"] and sum(p["sprite"] == "surf sprite" for p in pl) == TOTALS["swimmers"]
    by_id, towns, reports = {p["id"]: p for p in pl}, [], {}
    for name in dict.fromkeys(p["town"] for p in pl):      # the release's own order: the order you reach the towns in
        mine = [p for p in pl if p["town"] == name]
        key, slug = name.replace(" ", ""), name.lower().replace(" ", "-")
        objs = {(o["x"], o["y"], o["gfx"]) for o in world[key]["events"]["objects"]}
        missing = [p["id"] for p in mine if (p["x"], p["y"], str(int(p["graphicsId"], 0))) not in objs]      # "0x4109" for an overworld sprite, "391" for a surf sprite
        assert not missing, f"{name}: not in this guide's extraction of the v1.2 ROM: {missing}"
        T = reports[slug] = json.loads((P / "reports/towns" / f"{slug}.json").read_text())
        assert T["town"] == name and T["placements"] == len(mine) == I["perTown"][name]
        assert next(t for t in T["tests"] if t["name"].startswith("v111 (before): no Pok"))["result"] == "PASS", f"{name}: v1.1 already had Pokémon objects"
        species = {}
        for p in mine: species[p["species"]] = species.get(p["species"], 0) + 1
        towns.append({"town": name, "map": key, "count": len(mine), "talk": sum(p["talks"] for p in mine), "swim": sum(p["sprite"] == "surf sprite" for p in mine),
                      "species": [[s, n] for s, n in species.items()]})
    assert len(towns) == TOTALS["towns"] and sum(t["count"] for t in towns) == TOTALS["total"]

    out = ROOT / "site/assets/game/whatsnew" / PUBLIC["after"][0]; out.mkdir(parents=True, exist_ok=True)
    shots = []
    for group, slug, view, caption, named in SHOTS:
        T = reports[slug]
        seen = {by_id[c]["species"] for c in T["views"][view - 1]["covers"]}
        assert set(named) <= seen, f"{slug} view {view}: the caption names {set(named) - seen}, which the town test did not record in this view"
        files = {}
        for side, word in (("before", "before"), ("after", "after")):
            src = P / "evidence" / slug / f"{word}-view{view:02d}.png"
            im = Image.open(src).convert("RGB")
            assert im.size == (240, 160), src
            name = f"{slug}-{view:02d}-{PUBLIC[side][0]}.png"
            im.save(out / name, optimize=True)
            assert Image.open(out / name).convert("RGB").tobytes() == im.tobytes()
            files[side] = {"file": name, "pixels": sha(im.tobytes())}
        assert files["before"]["pixels"] != files["after"]["pixels"]
        shots.append({"id": f"{slug}-{view:02d}", "group": group, "town": T["town"], "map": T["town"].replace(" ", ""), "cell": T["views"][view - 1]["cell"], "caption": caption, "species": named,
                      "before": files["before"]["file"], "after": files["after"]["file"]})
    assert all(sum(s["group"] == g for s in shots) == 3 for g, _, _ in GROUPS)

    # the title screenshot: the package's capture is an exact 2x enlargement of one native frame
    big = Image.open(P / "evidence/TITLE-RC2.png").convert("RGB")
    title = big.resize((240, 160), Image.NEAREST)
    assert big.size == (480, 320) and title.resize((480, 320), Image.NEAREST).tobytes() == big.tobytes()
    title.save(ROOT / "site/assets/game/title" / f'title-{PUBLIC["after"][0]}.png', optimize=True)

    data = {"_about": "Generated by tools/whatsnew_towns.py - do not edit. Before = public v1.1 (v111), after = public v1.2 (v113); screenshots from the release's own town test, placements checked against data/rom/world.json.",
            "kind": "towns", "before": dict(zip(("public", "build", "sha256"), PUBLIC["before"])), "after": dict(zip(("public", "build", "sha256"), PUBLIC["after"])),
            "counts": TOTALS | {"species": len({p["species"] for p in pl}), "shots": len(shots)},
            "groups": [{"id": g, "title": t, "text": x} for g, t, x in GROUPS], "shots": shots, "towns": towns,
            "verification": {"placements_found_in_guide_extraction": len(pl), "town_tests": {"passed": sum(r["summary"]["passed"] for r in reports.values()), "failed": sum(r["summary"]["failed"] for r in reports.values())}}}
    (ROOT / f'data/whatsnew-{PUBLIC["after"][0]}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"counts": data["counts"], "verification": data["verification"], "towns": {t["town"]: t["count"] for t in towns}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
