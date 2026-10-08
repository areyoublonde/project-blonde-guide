#!/usr/bin/env python3
"""The game's own credits, as the owner edits them: qa/hgss-credits-build-v85/data/credits_text.txt -> data/credits.json.
The guide prints these and nothing else; no contributor is typed by hand."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
game = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "blonde"
PRIVATE = {"friends", "special_thanks"}      # personal dedications: shown in the game, never written to the public site or repository
out, cur = [], None
for line in (game / "qa/hgss-credits-build-v85/data/credits_text.txt").read_text(encoding="utf-8").splitlines():
    line = line.rstrip()
    if line.startswith(";") or not line.strip():
        continue
    if line.startswith("@section"):
        cur = {"id": line.split()[1], "heads": [], "names": []}
        out.append(cur)
    elif cur is not None and line.startswith("#"):
        h = line[1:].strip()
        if h not in cur["heads"]:
            cur["heads"].append(h)
    elif cur is not None and "{PLAYER}" not in line:
        cur["names"].append(line.strip())
out = [s for s in out if s["id"] not in PRIVATE]
(ROOT / "data/credits.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(len(out), "credit sections,", sum(len(s["names"]) for s in out), "names")
