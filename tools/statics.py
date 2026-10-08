#!/usr/bin/env python3
"""Fixed encounters and gift Pokémon, read from the scripts the ROM was built from.

    python3 tools/statics.py [--game ../blonde]

Sources (read-only): data/maps/*_hns/scripts.inc, data/scripts/*.inc (Johto, Kanto, far-off areas) and the Hoenn
event overlay qa/gym-rematch-yes-no-v84/map_events_overlay.s. A record is kept only when its map is in the ROM.
Output: data/statics.json
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAT = re.compile(r"^\s*(setwildbattle|setwildbattleshiny|seteventmon|givemon|giveegg)\s+(SPECIES_\w+)(?:\s*,\s*(\d+))?", re.M)
KIND = {"setwildbattle": "battle", "setwildbattleshiny": "battle", "seteventmon": "battle", "givemon": "gift", "giveegg": "egg"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game).resolve()
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    out = []
    for d in sorted((game / "data/maps").iterdir()):
        f = d / "scripts.inc"
        if d.name in world and f.exists():
            for m in PAT.finditer(f.read_text(errors="replace")):
                out.append({"species": m.group(2), "level": int(m.group(3)) if m.group(3) else None, "kind": KIND[m.group(1)], "shiny": m.group(1).endswith("shiny"),
                            "map": d.name, "src": f"data/maps/{d.name}/scripts.inc"})
    ov = game / "qa/gym-rematch-yes-no-v84/map_events_overlay.s"
    keys = sorted((k for k in world if not k.endswith("_hns")), key=len, reverse=True)
    if ov.exists():
        label = None
        for line in ov.read_text(errors="replace").splitlines():
            lm = re.match(r"^(Ho[A-Za-z0-9]*?_\w+):", line)
            if lm:
                label = lm.group(1)
            m = PAT.match(line)
            if m and label:
                rest = re.sub(r"^Ho[A-Za-z0-9]*?_", "", label)
                mk = next((k for k in keys if rest == k or rest.startswith(k + "_")), None)
                if mk:
                    out.append({"species": m.group(2), "level": int(m.group(3)) if m.group(3) else None, "kind": KIND[m.group(1)], "shiny": False,
                                "map": mk, "src": f"qa/gym-rematch-yes-no-v84/map_events_overlay.s:{label}"})
    seen, uniq = set(), []
    for r in out:
        k = (r["species"], r["level"], r["kind"], r["map"])
        if k not in seen:
            seen.add(k); uniq.append(r)
    (ROOT / "data/statics.json").write_text(json.dumps(uniq, indent=1))
    print(len(uniq), "fixed encounters and gifts;", sum(1 for r in uniq if not r["map"].endswith("_hns")), "in Hoenn")


if __name__ == "__main__":
    main()
