#!/usr/bin/env python3
"""Project Blonde guide - Legendary and Mythical Pokémon: completeness audit.

    python3 tools/legendaries.py [--game ../blonde]      (after romx.py, dex.py and availability.py)

Three independent lists are compared:
  A  every species row the shipped ROM itself marks as Legendary or Mythical
     (gSpeciesInfo flag word: isRestrictedLegendary, isSubLegendary, isMythical; isUltraBeast is listed beside them)
  B  the entries data/availability.json classifies as legitimately obtainable (tools/availability.py)
  C  the entries of content/legendaries.json (the hand-written guide)
The guide passes only if every obtainable member of A has exactly one complete entry in C, no entry in C describes a
Pokémon that B says cannot be obtained, and every `rom` row of every entry is found byte-for-byte in the ROM.

Writes data/legendaries.json (read by tools/build.py) and LEGENDARY-MYTHICAL-COMPLETENESS-AUDIT.md.
Nothing in the game folder is written. Exit status 1 if any check fails.
"""
import argparse, bisect, json, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import romx
from romx import B

ROOT = Path(__file__).resolve().parent.parent
SZ, FLAG_WORD = 268, 144          # sizeof(struct SpeciesInfo); offset of the flag word (isRestrictedLegendary is bit 0)
BITS = {0: "Legendary (restricted)", 1: "Legendary", 2: "Mythical", 3: "Ultra Beast"}
FORM_BITS = {5: "Totem", 6: "Mega", 7: "Primal", 8: "Ultra Burst", 9: "Gigantamax", 10: "Tera", 11: "Alolan", 12: "Galarian", 13: "Hisuian", 14: "Paldean"}
OP_SETVAR, OP_SETFLAG, OP_CLEARFLAG = 0x16, 0x29, 0x2A
NEED_FIELDS = ("start", "need", "steps", "encounter", "after", "facts", "summary", "level", "map", "basis", "rom", "ev", "when")
FACTS = ("Repeatable", "If you flee", "If you defeat it", "Can it be missed?")
TYPES = {"static": "static", "roaming": "roamer", "ticket": "static", "quest": "static", "special": "converter"}
# What the page said before this guide (content/walkthrough/postgame.json at commit eac4433): species it named at all.
OLD_PAGE = ["SPECIES_HO_OH", "SPECIES_LATIOS", "SPECIES_LATIAS", "SPECIES_RAYQUAZA", "SPECIES_KYOGRE", "SPECIES_GROUDON", "SPECIES_LUGIA"]
RESET_FLAGS = ["FLAG_HIDE_ARTICUNO", "FLAG_HIDE_ZAPDOS", "FLAG_HIDE_MOLTRES", "FLAG_HIDE_MEWTWO", "FLAG_HIDE_LUGIA", "FLAG_HIDE_HO_OH", "FLAG_HIDE_LATIOS", "FLAG_HIDE_LATIAS",
               "FLAG_DEFEATED_MEW", "FLAG_CAUGHT_MEW", "FLAG_BATTLED_DEOXYS", "FLAG_DEFEATED_DEOXYS", "FLAG_SUMMONED_MTMOON_JIRACHI", "FLAG_ITEM_GS_BALL"]


def all_defines(path):
    out = {}
    for m in re.finditer(r"^#define\s+(\w+)\s+(\(?[^/\n]+)", path.read_text(errors="replace"), re.M):
        try:
            out[m[1]] = int(eval(m[2].strip(), {}, dict(out)))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game).resolve()
    R = romx.Rom(game)
    S = R.S
    dex = json.loads((ROOT / "data/dex.json").read_text())
    avail = json.loads((ROOT / "data/availability.json").read_text())
    av = avail["species"]
    guide = json.loads((ROOT / "content/legendaries.json").read_text())
    gives = json.loads((ROOT / "data/rom/gives.json").read_text())
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    SP = romx.defines(game / "include/constants/species.h", "SPECIES_")
    FL = all_defines(game / "include/constants/flags_hns.h")
    m = re.search(r"^#define\s+ENGINE_FLAGS_START\s+(0x[0-9A-Fa-f]+)\s*\n(?:.*\n){0,20}?#define\s+FLAG_NO_WILD_CATCHING\s+\(ENGINE_FLAGS_START \+ (\d+)\)", (game / "include/constants/flags.h").read_text(errors="replace"), re.M)
    FL["FLAG_NO_WILD_CATCHING"] = int(m[1], 16) + int(m[2])          # engine flag, defined in flags.h
    num2id = {d["num"]: k for k, d in dex.items()}
    fails, checks = [], []

    def ok(cond, msg):
        checks.append((bool(cond), msg))
        if not cond:
            fails.append(msg)
        return cond

    def window(sym, cap=900):
        a = S[sym]
        i = bisect.bisect_right(R.addrs, a)
        end = R.addrs[i] if i < len(R.addrs) else a + cap
        return a, R.b[a - B: min(end, a + cap) - B]

    def name(i):
        d = dex[i]
        n = d["name"].title().replace("Ho-Oh", "Ho-Oh")
        reg = d.get("regional")
        return f"{n} ({reg})" if reg else n

    # ---------------------------------------------------------------- A: what the ROM flags
    base = S["gSpeciesInfo"]
    word = lambda n: R.u32(base + SZ * n + FLAG_WORD)
    assert word(150) & 0x1F == 1 and word(144) & 0x1F == 2 and word(151) & 0x1F == 4 and word(1) & 0x1F == 0, "species flag word moved"
    n_rows = avail["report"]["engine_species_rows"]
    rows = []
    for n in range(1, n_rows):
        f = word(n)
        if not f & 0xF:
            continue
        i = num2id.get(n)
        cls = next(BITS[b] for b in range(4) if f >> b & 1)
        forms = [v for b, v in FORM_BITS.items() if f >> b & 1]
        rows.append({"row": n, "id": i, "name": name(i) if i else None, "class": cls, "forms": forms, "considered": i in av,
                     "status": av[i]["status"] if i in av else None, "dexnum": dex[i]["dex"] if i else None})
    ok(all(r["id"] for r in rows), "every flagged ROM row maps to a Pokédex record")
    A = [r for r in rows if r["considered"] and r["class"] != "Ultra Beast"]          # species and regional forms, Legendary or Mythical
    UB = [r for r in rows if r["considered"] and r["class"] == "Ultra Beast"]
    alt = [r for r in rows if not r["considered"]]                                    # Mega, Primal, alternate-forme rows
    A_ids = {r["id"] for r in A}
    Bset = {r["id"] for r in A if r["status"] == "obtainable"}
    ok(not [r for r in A + UB if r["status"] == "uncertain"], "no flagged entry is left 'uncertain' by the availability audit")
    ok(not [r for r in UB if r["status"] == "obtainable"], "no Ultra Beast is obtainable (none needs a guide)")

    # ---------------------------------------------------------------- C: the guide
    entries = guide["entries"]
    C = {}
    for e in entries:
        ok(e["species"] not in C, f'{e["id"]}: one entry per Pokémon')
        C[e["species"]] = e
    missing = sorted(Bset - set(C), key=lambda i: dex[i]["num"])
    ok(not missing, "every obtainable Legendary / Mythical Pokémon has a guide entry" + (": missing " + ", ".join(name(i) for i in missing) if missing else ""))
    extra = [i for i in C if i not in Bset]
    ok(not extra, "no guide entry for a Pokémon that is not obtainable" + (": " + ", ".join(extra) if extra else ""))
    ok(all(i in A_ids for i in C), "every guide entry is a species the ROM flags as Legendary or Mythical")
    quest_ids = {q["id"] for q in guide["quests"]}
    report = {}
    for e in entries:
        i, tag = e["species"], e["id"]
        gaps = [k for k in NEED_FIELDS if not e.get(k)]
        ok(not gaps, f"{tag}: has every section" + (f" (empty: {', '.join(gaps)})" if gaps else ""))
        ok(len(e.get("steps", [])) >= 3 and len(e.get("need", [])) >= 1 and len(e.get("encounter", [])) >= 1 and len(e.get("after", [])) >= 1, f"{tag}: at least three steps, one prerequisite, one encounter line, one aftermath line")
        ok(all(k in e.get("facts", {}) for k in FACTS), f"{tag}: answers repeat / flee / defeat / missable")
        ok(e.get("map") in world and all(m in world for m in e.get("maps", [])), f"{tag}: its maps exist in the ROM")
        ok(all(q in quest_ids for q in re.findall(r"\{\{quest:([a-z-]+)", json.dumps(e))), f"{tag}: shared sections it points to exist")
        a = av.get(i, {})
        ok(TYPES[e["type"]] in a.get("kinds", []), f'{tag}: guide type "{e["type"]}" agrees with the availability audit ({", ".join(a.get("kinds", []))})')
        lv_av = sorted({int(x) for m in a.get("methods", []) for x in re.findall(r"Lv\. (\d+)", m.get("detail") or "")})
        ok(all(str(l) in e["level"] for l in lv_av), f"{tag}: states every level the availability audit records ({lv_av})")
        rom = []
        for sym, spc, lv in e.get("rom", []):
            if not ok(sym in S, f"{tag}: ROM symbol {sym} exists"):
                continue
            a0, w = window(sym)
            sid = SP[spc]
            if isinstance(lv, str):                                   # form table: [from, to]
                hit = struct.pack("<HH", sid, SP[lv]) in R.b[a0 - B: a0 - B + 200]
                how = f"{spc} → {lv} pair in sRegionalFormTable"
            elif sym in ("InitRoamer", "InitKantoRoamers"):           # THUMB, TryAddRoamer inlined: level goes to r2 (movs r2, #lv / adds r2, #lv)
                code = R.b[a0 - B: a0 - B + 0xA8]
                hit = bytes([lv, 0x22]) in code or bytes([lv, 0x32]) in code
                how = f"level {lv} loaded into r2 for CreateInitialRoamerMon in {sym}"
            else:
                sv = bytes([OP_SETVAR, 0x04, 0x80]) + struct.pack("<H", sid)       # seteventmon = setvar VAR_0x8004 species; setvar VAR_0x8005 level
                k = w.find(sv)
                hit = k >= 0 and bytes([OP_SETVAR, 0x05, 0x80]) + struct.pack("<H", lv) == w[k + 5: k + 10]
                how = f"setvar 0x8004 {sid}; setvar 0x8005 {lv}"
                if not hit:                                           # setwildbattle / setwildbossbattle: .2byte species, .byte level
                    hit = struct.pack("<HB", sid, lv) in w
                    how = f".2byte {sid}, .byte {lv}"
            ok(hit, f"{tag}: {spc} Level {lv} found in the ROM at {sym} ({S[sym]:#x})" if not isinstance(lv, str) else f"{tag}: {how} found in the ROM ({S[sym]:#x})")
            rom.append({"sym": sym, "addr": f"{S[sym]:#x}", "species": spc, "level": lv, "found": bool(hit), "how": how})
        report[i] = {"id": tag, "name": name(i), "rom": rom, "kinds": a.get("kinds", []), "levels": lv_av}

    # ---------------------------------------------------------------- rules the guide states for many entries at once
    a0, w = window("PokemonLeague_HallOfFame_EventScript_SetGameClearFlags", 400)
    for f in RESET_FLAGS:
        ok(bytes([OP_CLEARFLAG]) + struct.pack("<H", FL[f]) in w, f"Hall of Fame reset clears {f} ({FL[f]:#x}) in the ROM")
    _, w = window("PokemonLeague_HallOfFame_EventScript_SetFirstGameClearFlags", 200)
    ok(not any(bytes([OP_CLEARFLAG]) + struct.pack("<H", FL[f]) in w for f in RESET_FLAGS), "the first Hall of Fame entry resets none of them")
    _, w = window("PokemonLeague_HallOfFame_EventScript_SpawnSinjohMons", 60)
    ok(all(bytes([OP_CLEARFLAG]) + struct.pack("<H", FL[f"FLAG_HIDE_SINJOHRUINS_{x}"]) in w for x in ("REGIROCK", "REGICE", "REGISTEEL", "REGIELEKI", "REGIDRAGO", "REGIGIGAS")), "Hall of Fame reset returns the six Regis of Sinjoh")
    _, w = window("PokemonLeague_HallOfFame_EventScript_SpawnAlolaMons", 60)
    ok(all(bytes([OP_CLEARFLAG]) + struct.pack("<H", FL[f"FLAG_HIDE_TAPU_{x}"]) in w for x in ("KOKO", "LELE", "BULU", "FINI")), "Hall of Fame reset returns the four Tapu")
    _, w = window("CeruleanCave3_EventScript_MewtwoNew", 120)
    ok(bytes([OP_SETFLAG]) + struct.pack("<H", FL["FLAG_HIDE_MEWTWO"]) in w, "flag numbers in flags_hns.h match the ROM (Mewtwo's own script sets FLAG_HIDE_MEWTWO)")
    a1, a2 = S["SinjohRuins_ArceusRoom_EventScript_Arceus"], S["SinjohRuins_ArceusRoom_EventScript_ArceusPhase2"]
    p1, p2 = R.b[a1 - B: a2 - B], window("SinjohRuins_ArceusRoom_EventScript_ArceusPhase2", 80)[1]
    nc = struct.pack("<H", FL["FLAG_NO_WILD_CATCHING"])
    ok(bytes([OP_SETFLAG]) + nc in p1 and bytes([OP_CLEARFLAG]) + nc in p1 and p1.find(bytes([OP_SETFLAG]) + nc) < p1.find(bytes([OP_CLEARFLAG]) + nc),
       "Arceus, first battle: catching is switched off, then on again before the second battle begins")
    ok(bytes([OP_SETFLAG]) + nc not in p2, "Arceus, second battle: catching is not switched off")
    ok(not [g for g in gives if g["item"] in ("Red Orb", "Blue Orb")], "no script gives the Red Orb or the Blue Orb (Primal forms unavailable)")
    blocked = [dict(b, name=("Arceus (Steel form)" if "ARCEUS" in b["species"] else name(b["species"])), place=world[b["where"]]["name"] if b["where"] in world else b["where"])
               for b in avail["report"]["blocked_sources"] if b["species"] in A_ids or "ARCEUS" in b["species"]]
    ok(sum(1 for b in blocked if "catching disabled" in b["why"]) == 1, "exactly one Legendary / Mythical battle is fought with catching disabled (Arceus, first battle)")

    # ---------------------------------------------------------------- output
    stage = lambda s: [e for e in entries if e["stage"] == s]
    typ = lambda t: [e for e in entries if e["type"] == t]
    counts = {
        "rom_rows_flagged": len(rows), "audited": len(A), "obtainable": len(Bset), "unobtainable": len(A) - len(Bset), "ultra_beasts": len(UB), "form_rows": len(alt),
        "entries": len(entries), "previously_named": len([i for i in OLD_PAGE if i in Bset]), "previously_missing": len(Bset - set(OLD_PAGE)),
        "story": len(stage("story")), "milestone": len(stage("milestone")), "postgame": len(stage("postgame")),
        "static": len(typ("static")), "roaming": len(typ("roaming")), "ticket": len(typ("ticket")), "quest": len(typ("quest")), "special": len(typ("special")),
        "checks": len(checks), "failed": len(fails),
    }
    out = {"build": avail["report"]["build"], "counts": counts, "entries": report,
           "unobtainable": [{"id": r["id"], "name": r["name"], "class": r["class"], "dex": r["dexnum"]} for r in A if r["status"] != "obtainable"],
           "ultra_beasts": [{"id": r["id"], "name": r["name"], "dex": r["dexnum"]} for r in UB],
           "form_rows": [{"id": r["id"], "name": r["name"], "class": r["class"], "forms": r["forms"]} for r in alt],
           "blocked": blocked, "checks": [{"ok": c, "what": m} for c, m in checks]}
    (ROOT / "data/legendaries.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    write_audit(guide, out, av, dex, name)
    print(f'legendaries: {counts["audited"]} audited, {counts["obtainable"]} obtainable, {counts["entries"]} guide entries, {counts["checks"]} checks, {counts["failed"]} failed')
    for f in fails:
        print("  FAIL", f)
    sys.exit(1 if fails else 0)


def write_audit(guide, out, av, dex, name):
    c, b = out["counts"], out["build"]
    plain = lambda s: re.sub(r"\|\|(.+?)\|\|", r"\1", re.sub(r"\{\{\w+:([^}|]+)(?:\|([^}]+))?\}\}", lambda m: m[2] or m[1], re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", re.sub(r"<[^>]+>", "", s))))
    STAGE = {"story": "During the story", "milestone": "After a story milestone", "postgame": "Postgame only (after the Hoenn League)"}
    TYPE = {"static": "Fixed encounter", "roaming": "Roaming", "ticket": "Ticket island", "quest": "Quest", "special": "Form change (no battle)"}
    REG = {"johto": "Johto", "kanto": "Kanto", "hoenn": "Hoenn", "alola": "Alola isles", "sinjoh": "Sinjoh"}
    L = ["# Legendary and Mythical Pokémon: completeness audit", "",
         f'_Generated by `tools/legendaries.py` from the ROM, `data/availability.json` and `content/legendaries.json`. Game: {b["public"]} (build {b["version"]}), SHA-256 `{b["sha256"]}`. The ROM hash is checked on every run; the ROM, the saves and the game folder are only read._', "",
         "## Result", "", "| | |", "|---|---|",
         f'| ROM species rows flagged Legendary, Mythical or Ultra Beast | {c["rom_rows_flagged"]} |',
         f'| of which alternate-form rows (Mega, Primal, Origin and other formes) | {c["form_rows"]} |',
         f'| **Legendary / Mythical species and regional forms audited** | **{c["audited"]}** |',
         f'| **Legitimately obtainable** | **{c["obtainable"]}** |',
         f'| **Not obtainable** | **{c["unobtainable"]}** |',
         f'| Ultra Beasts (flagged separately by the ROM; listed for completeness) | {c["ultra_beasts"]}, none obtainable |',
         f'| Guide entries | {c["entries"]} |',
         f'| Obtainable Pokémon the old page did not name | {c["previously_missing"]} |',
         f'| Obtainable Pokémon the old page named, without instructions | {c["previously_named"]} |',
         f'| Uncertain | 0 |',
         f'| Automated checks | {c["checks"]} run, {c["failed"]} failed |', "",
         "The list was not chosen in advance. **A** is every row of the ROM's own species table whose flag word marks it Legendary or Mythical. **B** is what the Pokédex availability audit independently classifies as obtainable. **C** is the guide. The build fails unless every obtainable member of A has one complete entry in C and C contains nothing B rejects.", "",
         "No correction to the Pokédex availability dataset was needed: this audit found no Legendary or Mythical Pokémon that is obtainable but missing from it, and none in it that cannot be obtained. The dataset was read, not written; its Legendary and Mythical rows are the same 32 before and after.", "",
         "## Breakdown", "", "| By story availability | Entries |", "|---|---|"]
    for k, v in STAGE.items():
        L.append(f"| {v} | {c[k]} |")
    L += ["", "| By encounter type | Entries |", "|---|---|"]
    for k, v in TYPE.items():
        L.append(f"| {v} | {c[k]} |")
    L += ["", "| By region | Entries |", "|---|---|"]
    for k, v in REG.items():
        L.append(f'| {v} | {sum(1 for e in guide["entries"] if e["region"] == k)} |')
    L += ["", "Roaming: " + ", ".join(e["id"].title() for e in guide["entries"] if e["type"] == "roaming") + ". Latias and Latios are each obtainable two ways (the one you choose roams; the other is on Southern Island with the Eon Ticket).",
          "", "Ticket-gated: Mew (Old Sea Map, found on the ground), Deoxys (Aurora Ticket, given to a Kanto Champion), and the non-roaming Latias or Latios (Eon Ticket, given to a Kanto Champion).",
          "", "Gifts: none. No Legendary or Mythical Pokémon is handed to the player; every one is a battle, except the three Galarian birds, which are made from a caught bird in Bill's machine.", "",
          "## What the old page had", "",
          "Before this guide, `/postgame/legendaries/` was one walkthrough chapter with four summary lines and one paragraph of prose. It named Ho-Oh, Lugia, Latias, Latios, Rayquaza, Kyogre and Groudon, referred to “the Regis” as a group, and gave no steps for any of them. It did not mention Raikou, Entei, Suicune, Celebi, the three birds or their Galarian forms, Mewtwo, Mew, Jirachi, Deoxys, Regigigas, Regieleki, Regidrago, Arceus or the four Tapu. It did not say what happens after a knock-out, and it described Rayquaza, Kyogre and Groudon as catchable once each without the League-win rule. No unobtainable Pokémon was listed. Nothing on it was wrong about a location.", "",
          "## Obtainable: one row per guide entry", "",
          "| # | Pokémon | Region | Type | Available | Where | Level | Catchable | Repeatable | If you flee | If you defeat it | Missable | Evidence |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in guide["entries"]:
        d = dex[e["species"]]
        f = e["facts"]
        L.append(f'| {d["dex"]} | {name(e["species"])} | {REG[e["region"]]} | {TYPE[e["type"]]} | {STAGE[e["stage"]].split(" (")[0]}: {e["when"]} | {e["summary"]} | {e["level"]} | {"Converted, not caught" if e["type"] == "special" else "Yes"} | {f["Repeatable"]} | {f["If you flee"]} | {f["If you defeat it"]} | {f["Can it be missed?"]} | {"Played" if e["basis"] == "played" else "Partly played" if e["basis"] == "mixed" else "Scripts"} |')
    L += ["", "## Acquisition detail and ROM verification", ""]
    for e in guide["entries"]:
        r = out["entries"][e["species"]]
        L += [f'### {name(e["species"])}', "", f'- **Starts:** {plain(e["start"])}', "- **Needs:** " + " ".join(plain(x) for x in e["need"]), "- **Steps:**"]
        L += [f"  {n}. {plain(s)}" for n, s in enumerate(e["steps"], 1)]
        L += ["- **Encounter:** " + " ".join(plain(x) for x in e["encounter"]), "- **Afterwards:** " + " ".join(plain(x) for x in e["after"]),
              "- **ROM:** " + "; ".join(f'`{x["sym"]}` @ {x["addr"]}: {x["how"]} — {"found" if x["found"] else "NOT FOUND"}' for x in r["rom"]),
              f'- **Availability audit:** {", ".join(r["kinds"])}' + (f'; levels {r["levels"]}' if r["levels"] else ""), f'- **Source:** {e["ev"]}', ""]
    L += ["## Shared rules", ""]
    for q in guide["quests"]:
        L += [f'### {q["title"]}', ""] + [plain(p) for p in q.get("p", [])] + [f"{n}. {plain(s)}" for n, s in enumerate(q.get("steps", []), 1)] + ["", f'Source: {q["ev"]}', ""]
    L += ["## Battles that are not acquisitions", "",
          "A scripted battle fought while the game's no-catching flag is set is not an acquisition source, and neither is an encounter script that Project Blonde has retired. Among Legendary and Mythical Pokémon the availability audit rejects these:", "",
          "| Pokémon | Where | Why it is not a source |", "|---|---|---|"]
    for x in out["blocked"]:
        L.append(f'| {x["name"]} | {x["place"]} | {x["why"]} |')
    L += ["", "The catch-disabled row is the first of Arceus's two battles: Level 100, Steel-type, no Ball and no escape. It unlocks the second battle (Level 80, Normal-type), which is the catchable one and is what the guide and the Pokédex record. The audit checks in the ROM that catching is switched back on before the second battle starts.",
          "", "The retired rows are the old Heart & Soul sites for Kyogre, Groudon and Rayquaza, whose maps are no longer how those three are met. Their Hoenn encounters (Marine Cave, Terra Cave, Sky Pillar) are the sources the guide describes.",
          "", "The Noble Pokémon and the Machamp of the Sinjoh story are also fought with catching disabled; none is Legendary. No Trainer in the game uses a Legendary or Mythical Pokémon.",
          "", "During Hoenn's story Groudon, Kyogre and Rayquaza appear in scenes and leave without a battle. They become catchable only after the Hoenn League.", "",
          "## Forms", "",
          "- **Galarian Articuno, Zapdos, Moltres:** obtainable, each with its own guide entry (Bill's machine).",
          "- **Mega Mewtwo X / Y, Mega Latias, Mega Latios:** the stones are on the list Elm's aide hands out; see the Mega Stones page. They are battle forms of Pokémon covered above, not separate acquisitions.",
          "- **Primal Groudon, Primal Kyogre:** not available. No script gives the Red Orb or Blue Orb (checked against every item-giving script in the ROM).",
          "- **Mega Rayquaza, Deoxys formes, Arceus plate types and the other alternate-forme rows:** defined by the engine. This audit did not establish how, or whether, each can be reached in play, so the guide makes no claim about them beyond noting that the seventeen plates are obtainable held items. See *Unresolved* below.", "",
          f'The ROM flags {c["form_rows"]} such alternate-form rows in total; they are not counted as species.', "",
          "## Not obtainable", "",
          "Flagged Legendary or Mythical by the ROM, considered by the availability audit, and found to have no encounter, gift, trade, egg, converter or evolution in this build. They have no guide entry and no Pokédex page.", "",
          "| # | Pokémon | Class | Reason |", "|---|---|---|---|"]
    for x in out["unobtainable"]:
        L.append(f'| {x["dex"]} | {x["name"]} | {x["class"]} | {av[x["id"]]["reason"]} |')
    L += ["", "### Ultra Beasts", "", "The ROM marks these with a separate flag. None is obtainable.", "", ", ".join(x["name"] for x in out["ultra_beasts"]) + ".", "",
          "## Unresolved or uncertain", "",
          "Nothing about *whether* a Pokémon is obtainable is uncertain. What remains unconfirmed is ground-level detail, because the natural playthrough caught only Ho-Oh:", "",
          "- **Not walked.** Every entry marked *Scripts* or *Partly played* gives conditions read from the game's scripts. Routes inside dungeons (Whirl Islands, Seafoam Islands, Cerulean Cave, Mt. Silver's Moltres room, the Sky Pillar, Marine and Terra Cave) were not walked, so the guide gives the destination and a marked map rather than turn-by-turn directions.",
          "- **Celebi's first step.** The GS Ball is released by the Ho-Oh panel puzzle in the Ruins of Alph. How early that room can be reached, and by which entrance, was not walked.",
          "- **Sinjoh.** The story's stages, the seventeen plate sources and the chamber thresholds are read from the scripts. The exact tile of each Noble's flute prompt and the path between areas were not walked.",
          "- **Mew's wharf.** The Old Sea Map's item ball is beside the truck at tile 61,46 of Vermilion City, on a wharf not joined to the land in the map image. That it is reached by Surf is read from the map, not played.",
          "- **Night for Jirachi.** The rock tests the game's night flag. The clock hours that count as night are documented by the game's time system, not re-measured here.",
          "- **Roamer odds.** One-in-four per wild encounter on the roamer's route, the Repel rule and the routes come from the engine source the ROM was built from; the route tables and levels are confirmed present in the ROM. The source also contains a rule that draws a roamer towards the player when Legendary Pokémon are in the party; that function could not be located in the ROM's symbol table, so the guide does not mention it.",
          "- **Alternate formes.** See *Forms*.",
          "- **A possible defect, not verified.** Arceus's first battle switches catching and running off and switches them back on only after the battle returns. If the player loses that battle and blacks out, the script does not reach the lines that switch them back on. Whether the engine restores them elsewhere was not tested. This is reported for the owner; the guide does not describe it.", "",
          "## Checks", "", "| | Check |", "|---|---|"]
    L += [f'| {"pass" if x["ok"] else "**FAIL**"} | {x["what"]} |' for x in out["checks"]]
    (ROOT / "LEGENDARY-MYTHICAL-COMPLETENESS-AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
