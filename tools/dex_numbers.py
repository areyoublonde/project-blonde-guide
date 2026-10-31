#!/usr/bin/env python3
"""Project Blonde guide - the Pokédex number of every public Pokémon, read from the latest approved ROM.

    python3 tools/dex_numbers.py [--workspace ../..]      writes data/pokedex-numbers.json; nothing in the game folder is written

This file is the one source of the numbers the site prints. They are the numbers the game draws in its Pokédex in National mode
(`CreateMonDexNum`, `PrintMonInfo`: NationalToObtainableOrder(GetDexGroupNumber(n))), not National Dex numbers and not species ids:
  no        = position in sObtainableToNationalOrder of the entry, or of its base species for a regional form (sDexRegionalGroups)
  position  = the entry's own position in that list (what the Summary screen prints, the same as `no` except for regional forms)
  johto     = the number in the Pokédex's Johto mode, when the entry is in that list
  national  = gSpeciesInfo[].natDexNum, the key used across the guide's data
Tables are 4-byte enums except sDexRegionalGroups (pairs of u16). Runtime proof is in qa-evidence/pokedex-numbers/."""
import argparse, json, re, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B, SZ = 0x08000000, 268
GROUPS = 55                 # rows of sDexRegionalGroups (src/data/pokedex_regional_groups.h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(ROOT.parent))
    a = ap.parse_args()
    vsc = Path(a.workspace).resolve()
    latest = json.loads((vsc / "output/project-blonde-v1.4/V1.4-LATEST.json").read_text())
    rom = (vsc / latest["latest_rom"]).read_bytes()
    import hashlib
    sha = hashlib.sha256(rom).hexdigest()
    assert sha == latest["latest_sha256"], "ROM differs from V1.4-LATEST.json"
    S = json.loads((vsc / "output/project-blonde-v1.4-rc1-20261019/symbols-v1.4.json").read_text())
    u16 = lambda p: struct.unpack_from("<H", rom, p - B)[0]
    table = lambda first, nxt: [x for x in struct.unpack_from(f"<{(S[nxt] - S[first]) // 4}I", rom, S[first] - B) if x]
    national = table("sNationalToSpeciesOrder", "sObtainableToNationalOrder")
    listed = table("sObtainableToNationalOrder", "sJohtoToNationalOrder")
    johto = table("sJohtoToNationalOrder", "sHoennToNationalOrder")
    info = S["gSpeciesInfo"]
    assert rom[info + SZ - B: info + SZ - B + 6] == bytes([45, 49, 49, 45, 65, 65]), "gSpeciesInfo layout changed"
    nat = lambda sp: u16(info + SZ * sp + 60)
    cm = {}
    for line in (vsc / "blonde/charmap.txt").read_text(errors="replace").splitlines():
        m = re.match(r"\s*'(.+?)'\s*=\s*([0-9A-Fa-f]{2})\s*$", line)
        if m:
            cm.setdefault(int(m.group(2), 16), m.group(1).replace("\\'", "'"))
    name = lambda sp: "".join(cm[c] for c in rom[info + SZ * sp + 44 - B: info + SZ * sp + 57 - B].split(b"\xff")[0])
    base = {}
    for i in range(GROUPS):
        original, regional = u16(S["sDexRegionalGroups"] + 4 * i), u16(S["sDexRegionalGroups"] + 4 * i + 2)
        base[nat(regional)] = nat(original)
    assert len(national) == 1080 and len(listed) == 482 and len(johto) == 282 and len(set(listed)) == 482 and len(set(johto)) == 282
    pos = {n: i + 1 for i, n in enumerate(listed)}
    jo = {n: i + 1 for i, n in enumerate(johto)}
    entries = {}
    for n in listed:
        sp = national[n - 1]
        assert nat(sp) == n, (n, sp)
        b = base.get(n, n)
        entries[str(n)] = {"no": pos[b], "position": pos[n], "johto": jo.get(b), "national": n, "name": name(sp).replace("’", "'"), "regional_of": b if b != n else None}
    numbers = sorted({e["no"] for e in entries.values()})
    out = {"source": {"revision": latest["latest_revision"], "rom_sha256": sha, "tables": ["sObtainableToNationalOrder", "sJohtoToNationalOrder", "sNationalToSpeciesOrder", "sDexRegionalGroups", "gSpeciesInfo"]},
           "counts": {"national_slots": len(national), "list_entries": len(listed), "regional_forms": sum(1 for e in entries.values() if e["regional_of"]), "numbers_shown": len(numbers), "johto": len(johto), "first": numbers[0], "last": numbers[-1]},
           "entries": entries}
    (ROOT / "data/pokedex-numbers.json").write_text(json.dumps(out, indent=0, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out["counts"]))


if __name__ == "__main__":
    main()
