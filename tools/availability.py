#!/usr/bin/env python3
"""Project Blonde guide - which Pokémon a player can legitimately obtain.

    python3 tools/availability.py [--game ../blonde]      (after romx.py and dex.py)

The public Pokédex must list Pokémon obtainable in the approved build, not every species the engine defines.
This tool decides that from evidence and writes data/availability.json plus AVAILABILITY-AUDIT.md.

Evidence, in the order it is gathered:
  1. Wild tables of the shipped ROM (data/rom/encounters.json: land, Surf, Rock Smash, three rods, four times of day),
     counted only on maps that can be reached from the player's bedroom through warps, map connections and script warps.
  2. Event scripts the ROM was built from (H&S map scripts, shared scripts, the Hoenn overlay): gift Pokémon, eggs,
     fixed and boss encounters; in-game trades a script actually starts; roamers; the regional-form converter in Bill's house.
  3. Rules in content/availability-rules.json: sources checked by hand (with the evidence), retired sources, gated areas.
  4. Closure, repeated until nothing changes: evolutions whose method, items, places and partners exist in this game
     (read from the ROM's own evolution tables), and Day Care eggs.

Classes:  obtainable  - at least one piece of evidence of kinds 1-3, or reached by closure from one
          uncertain   - only weak evidence (a species named in a script variable or menu) or an evolution method that
                        could not be confirmed; listed in the audit, NOT shown in the public Pokédex
          excluded    - no acquisition evidence: engine-only species, trainer-only species, unreachable or retired sources
Nothing in the game folder is written.
"""
import argparse, collections, json, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import romx
from romx import B, title, item_name

ROOT = Path(__file__).resolve().parent.parent
SZ = 268
START = "NewBarkTown_PlayersHouse_2F_hns"
STRONG = {"givemon": "gift", "giveegg": "egg", "setwildbattle": "static", "setwildbattleshiny": "static", "seteventmon": "static", "setwildbossbattle": "static"}
WEAK = {"setvar", "dynmultipush", "case", "bufferspeciesname"}
EXCLUDE_SHARED = re.compile(r"debug|test|battle_frontier|battle_pike|battle_pyramid|battle_factory|battle_dome|battle_palace|battle_arena|battle_tower|trainer_hill|cable_club|contest|apprentice|battle_tent|mystery_event|gabby_and_ty|secret_base|tv\.inc|gift_|lilycove_lady|safari_zone\.inc|roulette|pokedex_rating|move_tutors|field_move|std_msgbox|obtain_item|new_game|players_house|rival_graphics|trainer_battle|berry|day_care|flash|pc_transfer|record_mix|shared_secret")
TIME = {0: "morning", 1: "day", 2: "evening", 3: "night"}
LABEL = {"wild": "Wild encounter", "static": "Static encounter", "gift": "Gift Pokémon", "egg": "Gift Egg", "trade": "In-game trade", "roamer": "Roaming Pokémon",
         "converter": "Regional-form converter", "evolution": "Evolution", "breeding": "Breeding", "verified": "Event"}


def item_ids(S, header=""):
    """Every item constant -> numeric id, aliases included (ITEM_UP_GRADE and ITEM_UPGRADE are both 228).
    The linked symbol table is the authority; `NAME = OTHER_NAME` rows of items.h cover an alias the table lacks."""
    ids = {k: v for k, v in S.items() if k.startswith("ITEM_") and isinstance(v, int) and v < 0x10000}
    grow = True
    while grow:
        grow = False
        for k, v in re.findall(r"^\s*(?:#define\s+)?(ITEM_\w+)\s*=?\s*(ITEM_\w+)\s*,?\s*(?://.*)?$", header, re.M):
            if k not in ids and v in ids:
                ids[k] = ids[v]; grow = True
    return ids


def rom_item_names(ITEM):
    """Display name used in data/rom/*.json -> item id (romx names an item after the constant its id resolves to)."""
    return {item_name(c): i for i, c in ITEM.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    game = Path(ap.parse_args().game).resolve()
    R = romx.Rom(game)
    S = R.S
    dex = json.loads((ROOT / "data/dex.json").read_text())
    world = json.loads((ROOT / "data/rom/world.json").read_text())
    enc = json.loads((ROOT / "data/rom/encounters.json").read_text())
    gives = json.loads((ROOT / "data/rom/gives.json").read_text())
    marts = json.loads((ROOT / "data/rom/marts.json").read_text())
    swarps = json.loads((ROOT / "data/rom/scriptwarps.json").read_text())
    rules = json.loads((ROOT / "content/availability-rules.json").read_text())
    num2id = {d["num"]: k for k, d in dex.items()}
    SP = romx.defines(game / "include/constants/species.h", "SPECIES_")
    alias = {k: num2id[v] for k, v in SP.items() if v in num2id}       # several constants share a number (SPECIES_DEOXYS = SPECIES_DEOXYS_NORMAL)
    for k, v in re.findall(r"^#define\s+(SPECIES_\w+)\s+(SPECIES_\w+)\s*$", (game / "include/constants/species.h").read_text(), re.M):
        if k not in alias and v in alias:
            alias[k] = alias[v]
    ITEM = R.enum("ITEM_")
    for k in list(ITEM):
        if ITEM[k].endswith("_COUNT"):
            ITEM.pop(k)
    ITEM_ID = item_ids(S, (game / "include/constants/items.h").read_text())
    mv = (game / "include/constants/moves.h").read_text()
    MOVE = {S[n]: n for n in re.findall(r"^\s+(MOVE_\w+)(?:\s*=\s*\w+)?,", mv, re.M) if isinstance(S.get(n), int)}

    # ------------------------------------------------------------ 1. which maps can be reached
    keys = sorted(world, key=len, reverse=True)
    bare = {k[:-4]: k for k in world if k.endswith("_hns")}

    def sym_map(sym):
        if not sym or "Frlg" in sym:
            return None
        m = re.match(r"^Ho[A-Za-z0-9]*?_(.+)$", sym)
        if m:
            rest = m.group(1)
            return next((k for k in keys if not k.endswith("_hns") and (rest == k or rest.startswith(k + "_"))), None)
        for b in sorted(bare, key=len, reverse=True):
            if sym == b or sym.startswith(b + "_"):
                return bare[b]
        return next((k for k in keys if k.endswith("_hns") and sym.startswith(k + "_")), None)

    edges = collections.defaultdict(set)
    for k, m in world.items():
        for w in m["events"]["warps"]:
            if w["to"]:
                edges[k].add(w["to"])
        for c in m["connections"]:
            if c["to"]:
                edges[k].add(c["to"])
    unattributed = collections.defaultdict(set)
    for w in swarps:
        src = sym_map(w["sym"]) or next((v for k, v in rules["script_warp_sources"].items() if (w["sym"] or "").startswith(k)), None)
        if src:
            edges[src].add(w["to"])
        else:
            unattributed[w["to"]].add(w["sym"])
    for a, b, _why in rules["extra_edges"]:
        edges[a].add(b)
    reach, stack = {START}, [START]
    while stack:
        for t in edges[stack.pop()]:
            if t in world and t not in reach:
                reach.add(t); stack.append(t)
    unreached = sorted(set(world) - reach)

    # ------------------------------------------------------------ items a player can get (for item evolutions)
    # Items are compared by numeric id, never by constant name: one item can have several constants
    # (ITEM_UPGRADE = ITEM_UP_GRADE = 228), and the scripts and the evolution table do not agree on which one they use.
    name2id = rom_item_names(ITEM)
    item_src = collections.defaultdict(list)       # item id -> [{"how", "map"}]
    unknown_items = set()

    def got(item, how, mk):
        i = item if isinstance(item, int) else name2id.get(item, ITEM_ID.get(item))
        if i is None:
            if not re.match(r"(TM|HM)\d", str(item)):      # machines carry their move's name in data/rom and take no part in evolutions
                unknown_items.add(str(item))
        elif {"how": how, "map": mk} not in item_src[i]:
            item_src[i].append({"how": how, "map": mk})

    for k in sorted(reach):
        for o in world[k]["events"]["objects"]:
            if o.get("item"):
                got(o["item"], "item ball", k)
        for h in world[k]["events"]["hidden"]:
            got(h["item"], "hidden item", k)
    for m in marts:                                 # ROM shop lists, including shops a clerk opens through a branch of the script
        if m["map"] in reach:
            for i in m["items"]:
                got(i, "shop", m["map"])
    for g in gives:                                 # ROM giveitem commands (NPC gifts and event rewards), placed by their script label
        mk = sym_map(g["sym"]) if g["how"] == "gift" else None
        if mk in reach:
            got(g["item"], "gift", mk)
    files = sorted((game / "data/maps").glob("*_hns/scripts.inc")) + [game / "qa/gym-rematch-yes-no-v84/map_events_overlay.s"] + sorted((game / "data/scripts").glob("*.inc"))
    texts = {}
    for f in files:
        if f.parent.name == "scripts" and EXCLUDE_SHARED.search(f.name):
            continue
        if f.parent.name.endswith("_hns") and f.parent.name not in reach:
            continue
        texts[f] = f.read_text(errors="replace")
        for it in re.findall(r"^\s*(?:giveitem|additem|finditem|pokemart\w*\s+\w+|\.2byte)\s+(ITEM_\w+)", texts[f], re.M):
            got(it, "script", f.parent.name if f.name == "scripts.inc" else f.name)
    have_items = set(item_src)                      # numeric ids

    # ------------------------------------------------------------ 2. direct sources
    src = collections.defaultdict(list)      # species id -> [evidence]
    weak = collections.defaultdict(list)
    retired = {tuple(x) for x in rules["retired"]}
    blocked = []

    def add(sid, kind, where, detail, evidence, map_=None):
        if (sid, map_) in retired:
            blocked.append({"species": sid, "why": "source retired in Project Blonde", "where": map_, "evidence": evidence})
            return
        src[sid].append({"kind": kind, "where": where, "map": map_, "detail": detail, "evidence": evidence})

    for mk, rec in enc.items():
        if "#" in mk or mk not in world:
            continue
        for method, tods in rec["tables"].items():
            for tod, rows in tods.items():
                for r in rows:
                    if r["id"] not in dex:
                        continue
                    if mk not in reach:
                        blocked.append({"species": r["id"], "why": "wild table on a map no warp, connection or script leads to", "where": mk, "evidence": rec["src"]})
                        continue
                    add(r["id"], "wild", world[mk]["name"], f'{method}, {tod}, Lv. {r["min"]}–{r["max"]}, {r["rate"]}%', rec["src"], mk)
    for f, text in texts.items():
        shared = f.parent.name == "scripts"
        overlay = f.name.endswith(".s")
        label = ""
        nocatch = False                         # FLAG_NO_WILD_CATCHING set and not yet cleared: the battle that follows cannot end in a capture
        for line in text.splitlines():
            m = re.match(r"^(\w+):", line)
            if m:
                label = m.group(1)
            if ".string" in line:
                continue
            if re.search(r"setflag\s+FLAG_NO_WILD_CATCHING", line):
                nocatch = True
            elif re.search(r"clearflag\s+FLAG_NO_WILD_CATCHING", line) or re.match(r"\s*(end|return)\b", line):
                nocatch = False
            m = re.match(r"\s*(\w+)\s+(.*)", line)
            if not m or (m.group(1) not in STRONG and m.group(1) not in WEAK) or re.search(r"Debug|_Test\b|EventScript_Test", label):
                continue
            mk = (sym_map(label) if overlay else None) if (overlay or shared) else f.parent.name
            for name in re.findall(r"SPECIES_\w+", m.group(2)):
                name = alias.get(name)
                if name not in dex:
                    continue
                ev = f"{f.relative_to(game)}:{label}"
                where = world[mk]["name"] if mk in world else ("Hoenn (event script)" if overlay else "shared script")
                lv = re.search(r"SPECIES_\w+\s*,\s*(\d+)", m.group(2))
                if m.group(1) in STRONG and STRONG[m.group(1)] == "static" and nocatch:
                    blocked.append({"species": name, "why": "scripted battle with catching disabled (FLAG_NO_WILD_CATCHING)", "where": mk, "evidence": ev})
                elif m.group(1) in STRONG and not shared and (mk is None or mk in reach):
                    add(name, STRONG[m.group(1)], where, f'{m.group(1)}{", Lv. " + lv.group(1) if lv else ""}', ev, mk)
                elif m.group(1) in STRONG and mk is not None and mk not in reach:
                    blocked.append({"species": name, "why": "script on an unreachable map", "where": mk, "evidence": ev})
                else:
                    weak[name].append({"cmd": m.group(1), "where": where, "map": mk, "evidence": ev})
    used = set()
    for text in texts.values():
        used |= set(re.findall(r"INGAME_TRADE_\w+", text))
    tr = (game / "src/data/trade.h").read_text()
    for m in re.finditer(r"\[(INGAME_TRADE_\w+)\]\s*=\s*\{(.*?)\n\s*\},", tr, re.S):
        s1 = re.search(r"\.species\s*=\s*(SPECIES_\w+)", m.group(2))
        want = re.search(r"\.requestedSpecies\s*=\s*(SPECIES_\w+)", m.group(2))
        if s1 and m.group(1) in used and alias.get(s1.group(1)) in dex:
            add(alias[s1.group(1)], "trade", "In-game trade", f'for {title(want.group(1), "SPECIES_") if want else "another Pokémon"}', f"src/data/trade.h:{m.group(1)}")
    for name in sorted(set(re.findall(r"TryAddRoamer\((SPECIES_\w+)", (game / "src/roamer.c").read_text()))):
        name = alias.get(name)
        if name in dex:
            add(name, "roamer", "Roams the region", "released by a story event", "src/roamer.c:TryAddRoamer")
    fs = (game / "src/field_specials.c").read_text()
    fs = fs[fs.index("} sRegionalFormTable[] = {"):]
    convert = [(alias.get(a), alias.get(b)) for a, b in re.findall(r"\{\s*(SPECIES_\w+),\s*(SPECIES_\w+)\s*\}", fs[:fs.index("};")])]
    conv_ok = "Route25_BillsHouse_hns" in reach and "special ConvertToRegionalForm" in (game / "data/maps/Route25_BillsHouse_hns/scripts.inc").read_text()
    for v in rules["verified"]:          # sources read by hand: they promote weak evidence, never invent a source
        if v["species"] in dex:
            add(v["species"], v["kind"], v["where"], v["detail"], v["evidence"], v.get("map"))

    # ------------------------------------------------------------ evolution tables and breeding data, from the ROM
    base = S["gSpeciesInfo"]
    evo, rev, egg, gender = collections.defaultdict(list), collections.defaultdict(list), {}, {}
    for sid, d in dex.items():
        a = base + SZ * d["num"]
        egg[sid] = (R.u8(a + 22), R.u8(a + 23))
        gender[sid] = R.u8(a + 18)
        p = R.u32(a + 164)
        n = 0
        while R.ok(p) and R.u16(p) != 0xFFFF and n < 16:
            method, param, to = R.u16(p), R.u16(p + 2), R.u16(p + 4)
            conds, q = [], R.u32(p + 8)
            while q and R.ok(q) and R.u16(q) != 39 and len(conds) < 8:
                conds.append((R.u16(q), R.u16(q + 2), R.u16(q + 4), R.u16(q + 6))); q += 8
            if to in num2id:
                e = {"from": sid, "to": num2id[to], "method": method, "param": param, "conds": conds}
                rev[num2id[to]].append(e)
                if method != 0:
                    evo[sid].append(e)
            p += 12; n += 1
    regions = {r for k in reach if k.endswith("_hns") for r in re.findall(r'"region": "REGION_(\w+)"', (game / "data/maps" / k / "map.json").read_text()) if (game / "data/maps" / k / "map.json").exists()}
    regions |= {"HOENN"} if any(not k.endswith("_hns") for k in reach) else set()
    REGION = dict(enumerate(["NONE", "KANTO", "JOHTO", "HOENN", "SINNOH", "UNOVA", "KALOS", "ALOLA", "GALAR", "HISUI", "PALDEA"]))
    secs_reach = {world[k]["sec"] for k in reach}

    def feasible(e, have):
        """(ok, uncertain, text, reasons) for one evolution edge."""
        why, unsure, bits = [], [], []
        m, p = e["method"], e["param"]
        if m in (1, 6):
            bits.append(f"Level {p}" if p else "Level up")
        elif m == 2:
            bits.append("Trade")
        elif m == 3:
            ic = ITEM.get(p, "ITEM_?")
            bits.append(f"Use {item_name(ic)}")
            if p not in have_items:
                why.append(f"{item_name(ic)} has no source in the game")
        elif m == 4:
            bits.append("Appears when its partner evolves, with a free party slot and a Poké Ball")
        elif m == 7:
            bits.append("After a battle")
        elif m == 8:
            bits.append("Spin in the overworld")
        else:
            bits.append("Special event")
            unsure.append("script-triggered evolution; trigger not confirmed")
        for c, a1, a2, a3 in e["conds"]:
            if c in (7, 36):
                ic = ITEM.get(a1, "ITEM_?")
                bits.append(("holding " if c == 7 else f"with {a2} × ") + item_name(ic))
                if a1 not in have_items:
                    why.append(f"{item_name(ic)} has no source in the game")
            elif c in (37, 38):
                r = REGION.get(a1, "?")
                bits.append(("in " if c == 37 else "outside ") + r.title())
                if c == 37 and r not in regions:
                    why.append(f"needs the {r.title()} region, which has no maps in this game")
            elif c == 16:
                bits.append(f"with {title(num2id.get(a1, 'SPECIES_?'), 'SPECIES_')} in the party")
                if num2id.get(a1) not in have:
                    why.append("needs a party Pokémon that is not obtainable (yet)")
            elif c == 20:
                bits.append(f"traded for {title(num2id.get(a1, 'SPECIES_?'), 'SPECIES_')}")
                if num2id.get(a1) not in have:
                    why.append("needs a trade partner species that is not obtainable (yet)")
            elif c == 18:
                bits.append("at a specific place")
                if a1 not in secs_reach:
                    why.append("needs a map section that cannot be reached")
            elif c == 17:
                bits.append("on a specific map")
            elif c in (11, 12, 13, 14, 15):
                bits.append("with high " + {11: "Beauty", 12: "Coolness", 13: "Smartness", 14: "Toughness", 15: "Cuteness"}[c])
                if rules["contest_stats"]["map"] not in reach:
                    why.append("needs a contest stat, and no Berry Blender can be reached")
            elif c == 1: bits.append(f"in the {TIME.get(a1, '')}".replace("in the night", "at night").replace("in the day", "during the day"))
            elif c == 2: bits.append(f"except in the {TIME.get(a1, '')}".replace("in the night", "at night"))
            elif c == 3: bits.append("with high friendship")
            elif c == 0: bits.append("female only" if a1 == 254 else "male only")
            elif c == 19: bits.append(f"knowing {title(MOVE.get(a1, 'MOVE_?'), 'MOVE_')}")
            else: bits.append("under a further condition")
        return (not why, bool(unsure), " ".join(bits), why + unsure)

    def egg_species(sid):
        """The species an egg of this parent hatches into: the engine walks back through the evolution tables (EVO_NONE rows included)."""
        cur, seen = sid, set()
        while cur not in seen:
            seen.add(cur)
            pre = sorted((e["from"] for e in rev.get(cur, []) if not dex[e["from"]].get("mega")), key=lambda k: dex[k]["num"])
            if not pre:
                break
            cur = pre[0]
        return cur

    # ------------------------------------------------------------ 4. closure
    have = {s for s, v in src.items() if v}
    via, evo_block = {}, collections.defaultdict(list)
    daycare = sorted(k for k in reach if "DayCare" in k or "Daycare" in k)
    order = lambda group: sorted(group, key=lambda k: (dex[k]["num"], k))       # fixed order: the same audit twice gives the same file
    changed = True
    while changed:
        changed = False
        for s in order(have):
            for e in evo[s]:
                ok, unsure, text, reasons = feasible(e, have)
                if e["to"] in have:
                    continue
                if ok and not unsure:
                    have.add(e["to"]); via[e["to"]] = {"kind": "evolution", "from": s, "detail": text}; changed = True
            if conv_ok:
                for a, b in convert:
                    if a == s and b in dex and b not in have:
                        have.add(b); via[b] = {"kind": "converter", "from": a, "detail": "Bill’s grandfather’s machine in Bill’s house, Route 25"}; changed = True
        ditto = "SPECIES_DITTO" in have
        if daycare:
            for s in order(have):
                if 15 in egg[s] or dex[s].get("mega") or dex[s]["kind"] == "mega":
                    continue
                if gender[s] in (255, 0) and not ditto:
                    continue
                child = egg_species(s)
                if child not in have and child in dex:
                    have.add(child); via[child] = {"kind": "breeding", "from": s, "detail": "Day Care egg" + (" (with Ditto)" if gender[s] in (255, 0) else "")}; changed = True
    # every other feasible route to a species that is already obtainable (so a page can say "wild, or evolve X")
    also = collections.defaultdict(list)
    for s in order(have):
        for e in rev.get(s, []):
            if e["method"] and e["from"] in have:
                ok, unsure, text, _ = feasible(e, have)
                if ok and not unsure:
                    also[s].append({"kind": "evolution", "from": e["from"], "detail": text})
    if daycare:
        for s in order(have):
            if 15 in egg[s] or dex[s]["kind"] == "mega" or (gender[s] in (255, 0) and "SPECIES_DITTO" not in have):
                continue
            c = egg_species(s)
            if c in have and not any(x["kind"] == "breeding" for x in also[c]):
                also[c].append({"kind": "breeding", "from": s, "detail": "Day Care egg"})
    # what stays out, and why
    uncertain = {}
    for s in dex:
        if s in have:
            continue
        notes = []
        for e in rev.get(s, []):
            if e["method"] == 0:
                continue
            ok, unsure, text, reasons = feasible(e, have)
            if e["from"] in have:
                if ok and unsure:
                    notes.append({"kind": "evolution", "from": e["from"], "detail": text, "missing": reasons})
                else:
                    evo_block[s].append({"from": e["from"], "detail": text, "why": reasons})
        if weak.get(s):
            notes.append({"kind": "weak script evidence", "refs": weak[s][:6], "missing": ["the species is named in a script variable, menu or text buffer; no command that gives or starts a battle with it was found"]})
        if notes:
            uncertain[s] = notes
    # uncertain species carry their evolutions with them
    grow = True
    while grow:
        grow = False
        for s in list(uncertain):
            for e in evo[s]:
                if e["to"] not in have and e["to"] not in uncertain:
                    uncertain[e["to"]] = [{"kind": "evolution", "from": s, "detail": feasible(e, have)[2], "missing": ["its pre-evolution is itself uncertain"]}]; grow = True

    # ------------------------------------------------------------ per-entry records (the Pokédex lists species and regional forms; other forms sit on their species' page)
    obt = (game / "src/pokemon.c").read_text()
    obt = obt[obt.index("sObtainableToNationalOrder[OBTAINABLE_DEX_COUNT] ="):]
    ingame = set(re.findall(r"OBTAINABLE_TO_NATIONAL\((\w+)\)", obt[:obt.index("};")]))
    natname = {}
    dx = (game / "include/constants/pokedex.h").read_text()
    dx = dx[dx.index("enum NationalDexOrder"):]
    for i, n in enumerate(re.findall(r"^\s*NATIONAL_DEX_(\w+)\s*,", dx[:dx.index("};")], re.M)):
        natname[i] = n
    out = {}
    forms_of = collections.defaultdict(list)
    for s, d in dex.items():
        if d.get("of"):
            forms_of[d["of"]].append(s)
    trainer_use = collections.Counter()
    for t in json.loads((ROOT / "data/rom/trainers.json").read_text()).values():
        for m in t["party"]:
            trainer_use[m["species"]] += 1
    for s, d in dex.items():
        if d["kind"] not in ("species", "regional"):
            continue
        methods = list(src.get(s, []))
        for f in forms_of[s]:                   # a form obtained directly (Castform, a gift Pikachu in a cap) is this species, obtained
            if dex[f]["kind"] == "form":
                methods += [dict(m, form=dex[f].get("form_name") or f) for m in src.get(f, [])]
        if s in via and via[s]["kind"] == "converter":
            methods.append({"kind": "converter", "where": "Bill’s house, Route 25", "map": "Route25_BillsHouse_hns", "detail": via[s]["detail"], "from": via[s]["from"], "evidence": "src/field_specials.c:sRegionalFormTable; data/maps/Route25_BillsHouse_hns/scripts.inc (special ConvertToRegionalForm)"})
        evs = {}
        for x in also.get(s, []):
            if x["kind"] == "evolution":
                evs.setdefault(x["from"], []).append(x["detail"])
        for f_, hows in evs.items():
            hows = sorted(dict.fromkeys(hows), key=lambda h: h.startswith("Trade"))
            methods.append({"kind": "evolution", "where": "", "map": None, "from": f_, "detail": " or ".join(hows), "link_trade_only": all(h.startswith("Trade") for h in hows), "evidence": "ROM gSpeciesInfo evolution table"})
        for x in also.get(s, []):
            if x["kind"] == "breeding":
                methods.append({"kind": "breeding", "where": "Day Care", "map": None, "from": x["from"], "detail": x["detail"], "evidence": "ROM egg groups and evolution table; Day Care on " + ", ".join(daycare[:2])})
        if methods or s in have:
            status = "obtainable"
        elif s in uncertain:
            status = "uncertain"
        else:
            status = "excluded"
        kinds = list(dict.fromkeys(m["kind"] for m in methods))
        reason = None
        if status == "excluded":
            if evo_block.get(s):
                reason = "evolution blocked: " + "; ".join(sorted({w for b in evo_block[s] for w in b["why"]}))
            elif any(b["species"] == s for b in blocked):
                reason = "; ".join(sorted({b["why"] for b in blocked if b["species"] == s}))
            elif trainer_use.get(s) or any(trainer_use.get(f) for f in forms_of[s]):
                reason = "used by Trainers only; no acquisition source"
            else:
                reason = "defined in the engine only; no encounter, gift, trade, evolution or egg leads to it"
        maps = sorted({m["map"] for m in methods if m.get("map")})
        regs = sorted({("hoenn" if not k.endswith("_hns") else world[k]["region"]) for k in maps})
        out[s] = {"status": status, "methods": methods[:60], "kinds": kinds, "primary": LABEL.get(kinds[0]) if kinds else None, "regions": regs,
                  "in_game_dex": natname.get(d["dex"]) in ingame, "reason": reason, "uncertain": uncertain.get(s), "n_sources": len(methods)}
    # items an evolution asks for, with every place the item comes from, and the constants that share each id
    names_of = collections.defaultdict(list)
    for k, v in sorted(ITEM_ID.items()):
        names_of[v].append(k)
    evo_items = {}
    for s_, edges_ in evo.items():
        for e in edges_:
            for i in ([e["param"]] if e["method"] == 3 else []) + [a1 for c, a1, _a2, _a3 in e["conds"] if c in (7, 36)]:
                if not i:
                    continue
                r = evo_items.setdefault(str(i), {"item": item_name(ITEM.get(i, "ITEM_?")), "constants": names_of.get(i, []), "sources": item_src.get(i, []), "used_by": []})
                if s_ in have and [s_, e["to"]] not in r["used_by"]:
                    r["used_by"].append([s_, e["to"]])
    rep = {
        "evolution_items": {k: v for k, v in sorted(evo_items.items(), key=lambda kv: int(kv[0])) if v["used_by"]},
        "item_aliases": {str(i): n for i, n in sorted(names_of.items()) if len(n) > 1},
        "unknown_item_names": sorted(unknown_items),
        "build": json.loads((ROOT / "data/rom/manifest.json").read_text())["build"],
        "engine_species_rows": 1573, "dex_records": len(dex), "entries_considered": len(out),
        "maps": len(world), "maps_reachable": len(reach), "maps_unreachable": unreached,
        "script_warps_unattributed": {k: sorted(x for x in v if x) for k, v in unattributed.items() if k not in reach},
        "regions_present": sorted(regions), "day_care_maps": daycare, "ditto": "SPECIES_DITTO" in have, "converter": conv_ok,
        "blocked_sources": blocked, "evolution_blocks": {k: v for k, v in evo_block.items() if k not in have},
        "weak_only": {k: v[:4] for k, v in weak.items() if k not in have},
        "counts": {st: sum(1 for v in out.values() if v["status"] == st) for st in ("obtainable", "uncertain", "excluded")},
    }
    (ROOT / "data/availability.json").write_text(json.dumps({"report": rep, "species": out}, indent=1, ensure_ascii=False))
    ob = [s for s, v in out.items() if v["status"] == "obtainable"]
    print(json.dumps({"reachable_maps": f'{len(reach)}/{len(world)}', **rep["counts"], "base": sum(1 for s in ob if dex[s]["kind"] == "species"), "regional": sum(1 for s in ob if dex[s]["kind"] == "regional"),
                      "in_game_dex_but_not_obtainable": sorted(s for s, v in out.items() if v["in_game_dex"] and v["status"] != "obtainable"),
                      "obtainable_but_not_in_game_dex": len([s for s in ob if not out[s]["in_game_dex"]])}, indent=1))


if __name__ == "__main__":
    main()
