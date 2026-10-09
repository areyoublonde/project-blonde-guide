"""Pokémon type and field checks.

  python3 tools/qa_pokemon_data.py --audit [--game ../blonde]   read every public entry's types and abilities again and write data/pokemon-audit.json
  python3 tools/qa_pokemon_data.py [--dist dist]                check data/dex.json and the built pages against that record (no game folder; runs in CI)

The audit does not reuse dex.py's lookup. Expected types are the two type bytes of the entry's gSpeciesInfo row in the ROM, named
by the game's own `enum Type`; a second reading comes from the `.types = MON_TYPES(...)` line of the species source. What is
compared against them is what the site shows: the type labels in the built HTML. Shared with dex.py, and so not independently
proven here: the row size (268 bytes) and the offsets of the type (6, 7) and ability (24) fields."""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "data/pokemon-audit.json"
TYPES = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"]
PUBLIC_COUNT = (440, 42)          # base species, regional forms: the owner-approved public Pokédex (changing it needs approval)
nice = lambda c, p: " ".join(w.capitalize() for w in c[len(p):].split("_"))
full = lambda d: d["name"] + (f' ({d["regional"]})' if d.get("regional") else "")


def public():
    av = json.loads((ROOT / "data/availability.json").read_text())["species"]
    dex = json.loads((ROOT / "data/dex.json").read_text())
    return dex, [k for k, v in av.items() if v["status"] == "obtainable"]


def audit(game):
    sys.path.insert(0, str(ROOT / "tools"))
    import romx
    R = romx.Rom(game)
    dex, pub = public()
    body = re.search(r"enum\s+(?:__attribute__\(\(packed\)\)\s+)?Type\s*\{(.*?)NUMBER_OF_MON_TYPES", (game / "include/constants/pokemon.h").read_text(), re.S).group(1)
    TYPE = {int(v): nice(k, "TYPE_") for k, v in re.findall(r"(TYPE_\w+)\s*=\s*(\d+)", body)}
    src = {}
    for f in sorted((game / "src/data/pokemon/species_info").glob("gen_*_families.h")):
        parts = re.split(r"\n    \[(SPECIES_\w+)\] =\n", f.read_text(encoding="utf-8", errors="replace"))
        for i in range(1, len(parts), 2):
            t = re.search(r"\.types = MON_TYPES\(([^)]*)\)", parts[i + 1])
            ab = re.search(r"\.abilities = \{([^}]*)\}", parts[i + 1])
            src[parts[i]] = ([nice(x.strip(), "TYPE_") for x in t.group(1).split(",")] if t and re.fullmatch(r"[\sA-Z_,]+", t.group(1)) else None,
                             [nice(x.strip(), "ABILITY_") for x in ab.group(1).split(",") if x.strip()] if ab and re.fullmatch(r"[\sA-Z_0-9,]+", ab.group(1)) else None)
    base = R.S["gSpeciesInfo"]
    out, err = {}, []
    for k in pub:
        d = dex[k]
        a = base + d["num"] * 268
        rom = list(dict.fromkeys(TYPE.get(R.u8(a + 6 + i), f"?{R.u8(a + 6 + i)}") for i in range(2)))
        st, sa = src.get(k, (None, None))
        st = list(dict.fromkeys(st)) if st else None
        rec = {"num": d["num"], "slug": d["slug"], "name": full(d), "regional": d.get("regional"), "types": rom, "source_types": st,
               "abilities": d["abilities"], "hidden_ability": d.get("hidden_ability")}
        out[k] = rec
        if d["types"] != rom:
            err.append(f"{k}: dex.json says {d['types']}, the ROM row says {rom}")
        if st and st != rom:
            err.append(f"{k}: source says {st}, the ROM row says {rom}")
        if sa:
            want = [x for x in sa[:2] if x != "None"], (sa[2] if len(sa) > 2 and sa[2] != "None" else None)
            if (d["abilities"], d.get("hidden_ability")) != want:
                err.append(f"{k}: abilities {d['abilities']} / {d.get('hidden_ability')} differ from the source {want}")
    AUDIT.write_text(json.dumps({"build": romx.BUILD["version"], "sha256": romx.BUILD["sha256"], "entries": out}, indent=1, ensure_ascii=False))
    n_src = sum(1 for r in out.values() if r["source_types"])
    print(f"audited {len(out)} public entries against the ROM ({n_src} also against the species source); {len(err)} differences")
    for e in err:
        print("  ", e)
    return 1 if err else 0


def labels(html):
    return re.findall(r'<span class="type"[^>]*>([^<]*)</span>', html)


def check(dist):
    dex, pub = public()
    a = json.loads(AUDIT.read_text())["entries"]
    err = []
    base, reg = sum(1 for k in pub if not dex[k].get("regional")), sum(1 for k in pub if dex[k].get("regional"))
    if (base, reg) != PUBLIC_COUNT:
        err.append(f"public Pokédex is {base} + {reg}, expected {PUBLIC_COUNT[0]} + {PUBLIC_COUNT[1]}")
    if set(pub) != set(a):
        err.append(f"audit record and public list differ: {sorted(set(pub) ^ set(a))[:6]}")
    seen = {}
    for field in ("slug", "num"):
        for k in pub:
            v = (field, dex[k][field])
            if v in seen:
                err.append(f"{k} and {seen[v]} share {field} {dex[k][field]}")
            seen[v] = k
    names = set()
    for k in pub:
        if full(dex[k]) in names:
            err.append(f"{k}: display name {full(dex[k])} is used twice")
        names.add(full(dex[k]))
        if not re.fullmatch(r"[A-Z0-9É♀♂'’.: \-]+", dex[k]["name"]):
            err.append(f"{k}: unexpected characters in the name {dex[k]['name']!r}")
    for k, d in dex.items():                                   # every entry, public or not: it may still appear on a trainer's team
        t = d["types"]
        if not 1 <= len(t) <= 2 or len(set(t)) != len(t) or any(x not in TYPES for x in t):
            err.append(f"{k}: invalid types {t}")
        for f in d["abilities"] + [d.get("hidden_ability") or "Overgrow"]:
            if not f or f in TYPES or "?" in f:
                err.append(f"{k}: invalid ability {f!r}")
        if k in a and t != a[k]["types"]:
            err.append(f"{k}: types {t} differ from the audited ROM value {a[k]['types']}")
    pages = shown = 0
    if dist and Path(dist).exists():
        by_slug = {d["slug"]: d for d in dex.values()}
        for f in Path(dist).rglob("*.html"):
            h = f.read_text(encoding="utf-8")
            rel = f.relative_to(dist)
            for lab in labels(h):
                shown += 1
                if lab not in TYPES:
                    err.append(f"{rel}: type label {lab!r} is not a Pokémon type")
            for slug, row in re.findall(r'<div class="mon"><a href="[^"]*/pokemon/([a-z0-9-]+)/">.*?<span class="types">(.*?)</span></span>', h, re.S):
                if slug in by_slug and labels(row + "</span>") != by_slug[slug]["types"]:
                    err.append(f"{rel}: team row for {slug} shows {labels(row + '</span>')}")
        for k in pub:
            p = Path(dist) / "pokemon" / dex[k]["slug"] / "index.html"
            if not p.exists():
                err.append(f"{k}: no page")
                continue
            pages += 1
            m = re.search(r'<p class="typeline">(.*?)</p>', p.read_text(encoding="utf-8"), re.S)
            if not m or labels(m.group(1)) != a.get(k, {}).get("types"):
                err.append(f"{k}: page shows {labels(m.group(1)) if m else None}, the ROM says {a.get(k, {}).get('types')}")
    print(f"pokémon: {len(pub)} public entries ({base} + {reg}), {len(dex)} records, {pages} pages and {shown} type labels checked; {len(err)} problems")
    for e in err[:60]:
        print("  ", e)
    return 1 if err else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    ap.add_argument("--dist", default=str(ROOT / "dist"))
    args = ap.parse_args()
    sys.exit(audit(Path(args.game).resolve()) if args.audit else check(args.dist))
