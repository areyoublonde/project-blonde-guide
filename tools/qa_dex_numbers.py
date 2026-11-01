#!/usr/bin/env python3
"""The Pokédex numbers the site prints, against data/pokedex-numbers.json (the ROM's tables).

    python3 tools/qa_dex_numbers.py [--dist dist]        the built pages (no game folder; runs in CI)
    python3 tools/qa_dex_numbers.py --url <base-url>     the same over HTTP, including that every Pokémon page opens
    -> exit 1 on any failure

A row or heading passes only if its printed text equals the record: list order, the first and last rows, every boundary where the
numbers skip, regional forms sharing their base species' number, and exactly one number per row and page."""
import argparse, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N = json.loads((ROOT / "data/pokedex-numbers.json").read_text(encoding="utf-8"))
DEX = json.loads((ROOT / "data/dex.json").read_text(encoding="utf-8"))
AV = json.loads((ROOT / "data/availability.json").read_text(encoding="utf-8"))["species"]
PUBLIC = {k: DEX[k] for k, v in AV.items() if v["status"] == "obtainable"}
err = []


def run(read):
    index = read("/pokemon/")
    ol = re.search(r'<ol class="dex" id="dex">(.*?)</ol>', index, re.S).group(1)
    li = re.findall(r'<li id="([a-z0-9-]+)"[^>]*>(.*?)</li>', ol, re.S)
    by_slug = {d["slug"]: d for d in PUBLIC.values()}
    if {s for s, _ in li} != set(by_slug) or len(li) != len(PUBLIC):
        err.append(f"list has {len(li)} rows; missing {sorted(set(by_slug) - {s for s, _ in li})[:5]}; extra {sorted({s for s, _ in li} - set(by_slug))[:5]}")
    shown = []
    for s, html in li:
        nums = re.findall(r'<span class="dexno">#(\d+)</span>', html)
        e = N["entries"].get(str(by_slug[s]["dex"])) if s in by_slug else None
        if len(nums) != 1 or not e or nums[0] != f'{e["no"]:03d}':
            err.append(f"/pokemon/ {s}: shows {nums}, the game shows {e and e['no']}")
        shown.append((int(nums[0]) if nums else 0, by_slug.get(s, {}).get("dex", 0)))
    if shown != sorted(shown):
        err.append("list is not in the game's order")
    no = [x for x, _ in shown]
    print(f"list: {len(li)} rows, first #{no[0]:03d} {li[0][0]}, last #{no[-1]:03d} {li[-1][0]}; {len(set(no))} numbers; skips {[(a, b) for a, b in zip(no, no[1:]) if b > a + 1]}")
    if no[0] != N["counts"]["first"] or no[-1] != N["counts"]["last"] or len(set(no)) != N["counts"]["numbers_shown"]:
        err.append("first, last or distinct count differs from the ROM record")
    pages = 0
    for k, d in PUBLIC.items():
        h = read(f'/pokemon/{d["slug"]}/')
        pages += 1
        m = re.findall(r"<h1>(.*?)</h1>", h, re.S)
        want = N["entries"][str(d["dex"])]["no"]
        if len(m) != 1 or f'<span class="dexno">#{want:03d}</span>' not in m[0] or len(re.findall(r'class="dexno"', h)) != 1:
            err.append(f'{d["slug"]}: heading {m[:1]}, the game shows {want}')
    print(f"pages: {pages} Pokémon pages opened and checked")
    # Forms the game's data defines: Primal Reversions on their base pages; Paldean Tauros as the game's Pokédex shows it, with its three breeds
    for slug, name, orb, art in (("kyogre", "Primal Kyogre", "Blue Orb", "kyogre-primal"), ("groudon", "Primal Groudon", "Red Orb", "groudon-primal")):
        h = read(f"/pokemon/{slug}/")
        if f"<b>{name}</b>" not in h or orb not in h or f"pokemon/{art}.png" not in h:
            err.append(f"{slug}: {name}, {orb} or its art is missing")
    h = read("/pokemon/tauros-paldea/")
    want = DEX[next(k for k, d in DEX.items() if d["num"] == N["entries"]["1079"]["row"])]
    line = re.search(r'<p class="typeline">(.*?)</p>', h, re.S).group(1)
    if re.findall(r'class="type"[^>]*>([^<]+)<', line) != want["types"] or want["text"].split(".")[0].replace("’", "") not in h.replace("’", ""):
        err.append(f"tauros-paldea: heading does not show the row the game's Pokédex shows ({want['id']})")
    for b in ("Aqua Breed", "Blaze Breed", "Combat Breed"):
        if f"<b>{b}</b>" not in h:
            err.append(f"tauros-paldea: {b} is missing")
    if "for None" in h:
        err.append("tauros-paldea: a trade names no species")
    for r in (e for e in N["entries"].values() if e["regional_of"]):
        if r["no"] != N["entries"][str(r["regional_of"])]["no"]:
            err.append(f"{r['name']}: regional form does not share its base number")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=str(ROOT / "dist"))
    ap.add_argument("--url")
    a = ap.parse_args()
    if a.url:
        def read(p):
            with urllib.request.urlopen(urllib.request.Request(a.url.rstrip("/") + p, headers={"User-Agent": "qa-dex-numbers"}), timeout=30) as r:
                assert r.status == 200, p
                return r.read().decode("utf-8")
    else:
        read = lambda p: (Path(a.dist) / p.strip("/") / "index.html").read_text(encoding="utf-8")
    run(read)
    print(f"{len(err)} problems")
    for e in err[:40]:
        print("  ", e)
    sys.exit(1 if err else 0)
