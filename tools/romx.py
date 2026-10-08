#!/usr/bin/env python3
"""Project Blonde guide - ROM extraction: what actually ships.

    python3 tools/romx.py [--game ../blonde]

Reads the release-candidate ROM (read-only) with the symbol table of the linked build and decodes the
engine's own tables: every map header and its events, wild encounter headers, the three trainer tables,
map-section names, item-ball / gift scripts and Poké Mart stock. Hoenn exists only in the ROM and the
build layers, so this - not the source tree - is the authority for anything a player can meet.

Output: data/rom/*.json. Every record carries `src` (table or script symbol + ROM address).
Nothing in the game folder is written.
"""
import argparse, bisect, hashlib, json, re, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rom"
B = 0x08000000
BUILD = {
    "version": "v105",
    "public": "v1.0 release candidate",
    "folder": "Heart & Soul - Hoenn Dialogue Events v105 Title Version v1.0 and Wattson Line",
    "rom": "Pokemon - Heart & Soul (Blonde).gba",
    "sha256": "d76ce7db778f09ad9085e6c11a535e6c7c8f4271de1def30d98af46698d5513a",
    "symbols": "qa/natural-run-v102/harness/sym-v84.json",   # nm of the linked v84 ELF; v85..v105 are binary layers on top of it (v103..v105 change script, text and the title sheet only, no table)
}
TRAINER_SZ, MON_SZ, HNS_ROWS = 52, 36, 635
HO_LEGACY_FIRST, HO_EXT_FIRST = 634, 1152                     # qa/gym-rematch-yes-no-v84/trainer_capacity.h
TIMES = ["morning", "day", "evening", "night"]
KINDS = (("land", 12), ("water", 5), ("rock", 5), ("fish", 10))
LAND = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]
WATER = [60, 30, 5, 4, 1]
RODS = {"old-rod": ([0, 1], [70, 30]), "good-rod": ([2, 3, 4], [60, 20, 20]), "super-rod": ([5, 6, 7, 8, 9], [40, 40, 15, 4, 1])}
NAME_FIX = {"MR_MIME": "Mr. Mime", "HO_OH": "Ho-Oh", "NIDORAN_F": "Nidoran♀", "NIDORAN_M": "Nidoran♂", "FARFETCHD": "Farfetch'd",
            "PORYGON_Z": "Porygon-Z", "MIME_JR": "Mime Jr.", "PORYGON2": "Porygon2"}


def title(const, prefix=""):
    s = const[len(prefix):] if const.startswith(prefix) else const
    return NAME_FIX.get(s) or " ".join(w.capitalize() for w in s.split("_"))


def item_name(const):
    s = const.replace("ITEM_", "")
    m = re.match(r"(TM|HM)_(.+)", s)
    if m:
        return f"{m.group(1)} {title(m.group(2))}"
    return re.sub(r"\b(Hp|Pp|Tm|Hm)\b", lambda m: m.group(1).upper(), title(s))


def defines(path, prefix):
    out = {}
    for m in re.finditer(r"^#define\s+(%s\w+)\s+(\(?[^/\n]+)" % prefix, path.read_text(errors="replace"), re.M):
        try:
            out[m[1]] = int(eval(m[2].strip(), {}, dict(out)))
        except Exception:
            pass
    return out


class Rom:
    def __init__(self, game):
        p = game / BUILD["folder"] / BUILD["rom"]
        self.b = p.read_bytes()
        got = hashlib.sha256(self.b).hexdigest()
        if got != BUILD["sha256"]:
            sys.exit(f"ROM hash mismatch: {got} (expected {BUILD['version']} {BUILD['sha256']})")
        self.S = json.loads((game / BUILD["symbols"]).read_text())
        addr = sorted((v, k) for k, v in self.S.items() if isinstance(v, int) and B <= v < B + len(self.b))
        self.addrs = [a for a, _ in addr]
        self.names = [n for _, n in addr]
        self.rev = {}
        for a, n in addr:
            self.rev.setdefault(a, n)
        cm = {}
        for line in (game / "charmap.txt").read_text(encoding="utf-8").splitlines():
            m = re.match(r"^'(.)'\s*=\s*([0-9A-Fa-f]{2})\s*$", line)
            if m:
                cm.setdefault(int(m[2], 16), m[1])
        cm[0] = " "
        self.cm = cm

    def ok(self, a): return B <= a < B + len(self.b) - 4
    def u8(self, a): return self.b[a - B]
    def u16(self, a): return struct.unpack_from("<H", self.b, a - B)[0]
    def s16(self, a): return struct.unpack_from("<h", self.b, a - B)[0]
    def u32(self, a): return struct.unpack_from("<I", self.b, a - B)[0]
    def s32(self, a): return struct.unpack_from("<i", self.b, a - B)[0]

    def text(self, a, limit=64):
        out = ""
        for i in range(limit):
            c = self.u8(a + i)
            if c == 0xFF:
                break
            out += self.cm.get(c, "?")
        return out

    def sym_at(self, a):
        """Nearest symbol at or before a ROM address."""
        i = bisect.bisect_right(self.addrs, a) - 1
        return self.names[i] if i >= 0 else None

    def enum(self, prefix):
        return {v: k for k, v in sorted(self.S.items(), reverse=True) if k.startswith(prefix) and isinstance(v, int) and v < 0x10000}


def map_name(sym):
    return {"HoOpening_LittlerootHeader": "LittlerootTown"}.get(sym) or re.sub(r"^HoRe_|_Header$", "", sym)


def pretty(name):
    n = name.replace("_hns", "").replace("Mahoganytown", "MahoganyTown").replace("Pokecenter", "PokemonCenter")
    n = re.sub(r"_(B?\d+F)", r" \1", n).replace("_", " ")
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)
    n = re.sub(r"(Route|Tower|Cave|Islands|Zone|Room|House|Puzzle) ?(\d+)", r"\1 \2", n)
    n = re.sub(r"(\d)R\b", r"\1R", n)
    return n.replace("Mt ", "Mt. ").replace("Low Tide", "(low tide)").replace("S S ", "S.S. ").replace("Pokemon", "Pokémon").replace("  ", " ").strip()


def region_of(sec):
    if sec >= 126: return "hoenn"
    if 9 <= sec <= 14: return "alola"
    if 109 <= sec <= 113: return "sinjoh"
    if sec >= 63: return "johto"
    return "kanto"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=str(ROOT.parent / "blonde"))
    ap.add_argument("--no-maps", action="store_true", help="skip rendering map images")
    args = ap.parse_args()
    game = Path(args.game).resolve()
    R = Rom(game)
    S = R.S
    OUT.mkdir(parents=True, exist_ok=True)
    SPECIES = {v: k for k, v in defines(game / "include/constants/species.h", "SPECIES_").items() if not k.endswith(("_COUNT", "_START", "_END"))}
    for k, v in defines(game / "include/constants/species.h", "SPECIES_").items():   # prefer the plain constant when several share a number
        if k in ("SPECIES_NONE",) or len(k) < len(SPECIES.get(v, k)):
            SPECIES[v] = k
    ITEM, ABIL = R.enum("ITEM_"), R.enum("ABILITY_")
    mv = (game / "include/constants/moves.h").read_text()
    MOVE = {i: n for i, n in enumerate(re.findall(r"^\s+(MOVE_\w+)(?:\s*=\s*\w+)?,", mv[mv.index("enum __attribute__((packed)) Move") if "enum __attribute__((packed)) Move" in mv else mv.index("enum Move"):], re.M))}
    for k, n in list(MOVE.items()):        # the header is the authority for names; the linked enum values are the authority for numbers
        if R.S.get(n) is not None and R.S[n] != k:
            MOVE = {R.S[x]: x for x in MOVE.values() if isinstance(R.S.get(x), int)}
            break
    for k in list(ITEM):
        if ITEM[k].endswith("_COUNT"):
            ITEM.pop(k)
    TCLASS, TPIC, MTYPE = R.enum("TRAINER_CLASS_"), R.enum("TRAINER_PIC_FRONT_"), R.enum("MAP_TYPE_")
    GFX = {v: k for k, v in defines(game / "include/constants/event_objects.h", "OBJ_EVENT_GFX_").items()}
    OPP = {v: k for k, v in defines(game / "include/constants/opponents_hns.h", "TRAINER_").items() if "COUNT" not in k}
    FLAG = {}
    for f in ("include/constants/flags.h", "include/constants/flags_hns.h"):
        if (game / f).exists():
            for k, v in defines(game / f, "FLAG_").items():
                FLAG.setdefault(v, k)
    sp = lambda i: SPECIES.get(i, f"SPECIES_{i}")
    th = (game / "include/constants/tms_hms.h").read_text()
    hns = th[th.index("#if IS_HNS"):th.index("#else")]
    TMS = re.findall(r"F\((\w+)\)", hns[:hns.index("FOREACH_HM")])
    HMS = re.findall(r"F\((\w+)\)", hns[hns.index("FOREACH_HM"):])
    MACHINE = {S["ITEM_TM01"] + i: f"TM{i + 1:02d} {title(m)}" for i, m in enumerate(TMS)}
    MACHINE.update({S["ITEM_HM01"] + i: f"HM{i + 1:02d} {title(m)}" for i, m in enumerate(HMS)})
    MACHINE[902] = "HM09 Dive"       # added past ITEMS_COUNT by the v47 Dive layer; the natural run received it as item 902 from Steven
    ITEM[902] = "ITEM_HM09"
    it = lambda i: MACHINE.get(i) or (item_name(ITEM[i]) if i in ITEM else f"Item {i}")

    # ---------------------------------------------------------------- map sections
    secs = {}
    ent = S["gRegionMapEntries"]
    for i in range(206):
        p = R.u32(ent + 8 * i + 4)
        if R.ok(p):
            secs[i] = R.text(p).strip()

    # ---------------------------------------------------------------- maps
    groups, a = [], S["gMapGroups"]
    while R.ok(R.u32(a)):
        groups.append(R.u32(a)); a += 4
    bounds = sorted(set(groups)) + [S["gMapGroups"]]
    hdr = {}          # (group, num) -> header address
    for g, p in enumerate(groups):
        end = min(x for x in bounds if x > p)
        for n in range((end - p) // 4):
            h = R.u32(p + 4 * n)
            if R.ok(h) and h in R.rev:      # groups keep empty slots for maps that were not imported
                hdr[(g, n)] = h
    key = {gn: map_name(R.rev[h]) for gn, h in hdr.items()}
    world = {}
    DIRS = {1: "down", 2: "up", 3: "left", 4: "right", 5: "dive", 6: "emerge"}
    for (g, n), h in hdr.items():
        name = key[(g, n)]
        lay, evp, conp = R.u32(h), R.u32(h + 4), R.u32(h + 12)
        sec = R.u8(h + 0x14)
        ev = {"objects": [], "warps": [], "signs": [], "hidden": [], "triggers": []}
        if R.ok(evp):
            no, nw, nc, nb = R.u8(evp), R.u8(evp + 1), R.u8(evp + 2), R.u8(evp + 3)
            op, wp, cp, bp = (R.u32(evp + 4 + 4 * i) for i in range(4))
            for i in range(no):
                o = op + 24 * i
                gfx = R.u16(o + 1)
                rec = {"n": R.u8(o), "x": R.s16(o + 4), "y": R.s16(o + 6), "gfx": GFX.get(gfx, str(gfx)).replace("OBJ_EVENT_GFX_", ""),
                       "script": R.u32(o + 16), "flag": R.u16(o + 20), "tt": R.u16(o + 12)}
                if R.u8(o + 3) == 0:      # OBJ_KIND_NORMAL (clones carry a target instead of a script)
                    ev["objects"].append(rec)
            for i in range(nw):
                w = wp + 8 * i
                ev["warps"].append({"n": i, "x": R.s16(w), "y": R.s16(w + 2), "to": key.get((R.u8(w + 7), R.u8(w + 6)))})
            for i in range(nc):
                c = cp + 16 * i
                ev["triggers"].append({"x": R.s16(c), "y": R.s16(c + 2), "script": R.u32(c + 12)})
            for i in range(nb):
                b = bp + 12 * i
                kind = R.u8(b + 5)
                if kind == 7:             # BG_EVENT_HIDDEN_ITEM
                    v = R.u32(b + 8)
                    ev["hidden"].append({"x": R.u16(b), "y": R.u16(b + 2), "item": it(v & 0x7FF), "flag": (v >> 11) & 0x1FFF})
                else:
                    ev["signs"].append({"x": R.u16(b), "y": R.u16(b + 2), "script": R.u32(b + 8)})
        conns = []
        if R.ok(conp):
            for i in range(R.s32(conp)):
                c = R.u32(conp + 4) + 12 * i
                conns.append({"dir": DIRS.get(R.u8(c), "?"), "offset": R.s32(c + 4), "to": key.get((R.u8(c + 8), R.u8(c + 9)))})
        world[name] = {"key": name, "name": pretty(name), "group": g, "num": n, "sec": sec, "place": secs.get(sec, ""), "region": region_of(sec),
                       "type": MTYPE.get(R.u8(h + 0x17), "").replace("MAP_TYPE_", "").lower(), "cave": R.u8(h + 0x15),
                       "w": R.s32(lay) if R.ok(lay) else 0, "h": R.s32(lay + 4) if R.ok(lay) else 0, "layout": lay,
                       "connections": conns, "events": ev, "src": f"gMapGroups[{g}][{n}] {R.rev[h]} @ {h:#x}"}

    # ---------------------------------------------------------------- trainers
    def read_trainer(a, tid, src):
        party = R.u32(a + 8)
        size = R.u8(a + 43)
        if not R.ok(party) or not size:
            return None
        mons = []
        for i in range(size):
            m = party + MON_SZ * i
            mons.append({"species": sp(R.u16(m + 20)), "level": R.u8(m + 26), "item": it(R.u16(m + 22)) if R.u16(m + 22) else None,
                         "ability": title(ABIL.get(R.u16(m + 24), ""), "ABILITY_") if R.u16(m + 24) else None,
                         "moves": [title(MOVE.get(x, f"MOVE_{x}"), "MOVE_") for x in struct.unpack_from("<4H", R.b, m + 12 - B) if x]})
        cls = R.u8(a + 28)
        cp = S["gTrainerClasses"] + 16 * cls
        return {"id": tid, "n": tid, "const": OPP.get(tid) if tid < HNS_ROWS - 1 else None, "name": R.text(a + 31, 11).strip(), "class": R.text(cp, 13).strip().replace("ウエ", "PKMN"),
                "class_id": TCLASS.get(cls, ""), "money": R.u8(cp + 13), "pic": TPIC.get(R.u8(a + 30), "").replace("TRAINER_PIC_FRONT_", "").lower(),
                "double": bool(R.u8(a + 42) & 3), "items": [it(x) for x in struct.unpack_from("<4H", R.b, a + 12 - B) if x], "party": mons, "src": src}

    trainers = {}
    base = S["gTrainers"] + HNS_ROWS * TRAINER_SZ          # gTrainers[DIFFICULTY_NORMAL]
    for i in range(1, HO_LEGACY_FIRST):
        t = read_trainer(base + TRAINER_SZ * i, i, f"gTrainers[NORMAL][{i}]")
        if t:
            trainers[str(i)] = t
    for i in range(204):
        t = read_trainer(S["HoCampaignTrainers"] + TRAINER_SZ * i, HO_LEGACY_FIRST + i, f"HoCampaignTrainers[{i}]")
        if t:
            trainers[str(t["id"])] = t
    ext, cnt = R.u32(S["gHoExtTrainers"]), R.u32(S["gHoExtTrainers"] + 4)
    for i in range(cnt):
        t = read_trainer(ext + TRAINER_SZ * i, HO_EXT_FIRST + i, f"HoExtTrainerRecords[{i}]")
        if t:
            trainers[str(t["id"])] = t

    # trainers standing on each map: trainerbattle commands reachable from that map's object / trigger scripts
    def battles(a, span=420):
        out = []
        i = a
        while i < a + span and R.ok(i + 32):
            if R.u8(i) == 0x5C:
                ta, tb = R.u16(i + 3), R.u16(i + 18)
                ptrs = [R.u32(i + 5), R.u32(i + 9), R.u32(i + 13)]
                if str(ta) in trainers and all(p == 0 or R.ok(p) for p in ptrs) and R.ok(ptrs[0]) and (tb == 0 or str(tb) in trainers):
                    out.append(ta)
                    if tb:
                        out.append(tb)
                    i += 32
                    continue
            i += 1
        return out

    for m in world.values():
        seen = []
        for o in m["events"]["objects"]:
            o["trainers"] = []
            if R.ok(o["script"]):
                hits = battles(o["script"], 40 if o["tt"] else 420)
                o["trainers"] = [h for h in dict.fromkeys(hits)][: (2 if o["tt"] else 6)]
                for h in o["trainers"]:
                    if h not in seen:
                        seen.append(h)
        m["trainers"] = seen

    # ---------------------------------------------------------------- item balls, gifts (script scan, attributed by symbol)
    # finditem / giveitem = setorcopyvar VAR_0x8000, item ; setorcopyvar VAR_0x8001, n ; callstd STD_FIND_ITEM(1) / STD_OBTAIN_ITEM(0)
    pat = re.compile(rb"\x1a\x00\x80(..)\x1a\x01\x80(..)\x09([\x00\x01])", re.S)
    gives = []
    for m in pat.finditer(R.b):
        item = struct.unpack("<H", m.group(1))[0]
        if item in ITEM and item:
            a = B + m.start()
            gives.append({"item": it(item), "n": struct.unpack("<H", m.group(2))[0], "how": "ball" if m.group(3) == b"\x01" else "gift", "addr": a, "sym": R.sym_at(a)})
    ball_at = {g["addr"]: g for g in gives if g["how"] == "ball"}
    for m in world.values():
        for o in m["events"]["objects"]:
            g = ball_at.get(o["script"])
            if g:
                o["item"] = g["item"]
                g["map"] = m["key"]

    # ---------------------------------------------------------------- Poké Marts: pokemart <ptr> -> u16 item list ending in 0
    marts = []
    for m in re.finditer(rb"\x86(....)", R.b, re.S):
        p = struct.unpack("<I", m.group(1))[0]
        if not R.ok(p) or p % 2:
            continue
        lst, q = [], p
        while R.ok(q) and len(lst) < 40:
            v = R.u16(q)
            if v == 0:
                break
            if v not in ITEM:
                lst = None
                break
            lst.append(v); q += 2
        a = B + m.start()
        sym = R.sym_at(a) or ""
        if lst and len(lst) >= 2 and len(set(lst)) == len(lst) and re.search(r"(?i)mart|shop|clerk|store|herb|vendor|seller|sale|stand|counter|market|pharmacy|energy|mulch|decor", sym + " " + (R.sym_at(p) or "")):
            marts.append({"sym": sym, "list_sym": R.sym_at(p), "addr": a, "items": [it(x) for x in lst]})
    # a clerk only counts if an object on a shipped map runs that script, directly or through a branch of its own script
    # (the Mahogany shop sells only after the Rocket Hideout: Granny -> goto_if_ge VAR_MAHOGANY_TOWN_STATE, 14 -> GrannyShop)
    def branches(sym, depth=4):
        """Script labels an object script can reach through goto / call / goto_if / call_if, as (label, hops)."""
        seen, todo = {sym: 0}, [sym]
        while todo:
            cur = todo.pop()
            if seen[cur] >= depth:
                continue
            a = S[cur]
            i = bisect.bisect_right(R.addrs, a)
            end = min(R.addrs[i] if i < len(R.addrs) else a + 600, a + 600)
            for j in re.finditer(rb"(?:[\x04\x05]|[\x06\x07][\x00-\x05])(...[\x08\x09])", R.b[a - B:end - B], re.S):
                t = R.rev.get(struct.unpack("<I", j.group(1))[0])
                if t and t not in seen:
                    seen[t] = seen[cur] + 1; todo.append(t)
        return seen

    direct = {}
    for w in world.values():
        for o in w["events"]["objects"]:
            if R.rev.get(o["script"]):
                direct.setdefault(R.rev[o["script"]], w["key"])
    reached = {}
    for sym, mk in direct.items():
        for t, hops in branches(sym).items():
            if hops and t not in direct and (t not in reached or hops < reached[t][1]):
                reached[t] = (mk, hops, sym)
    for m in marts:
        m["map"] = direct.get(m["sym"])
        if not m["map"] and m["sym"] in reached:
            m["map"], _, m["via"] = reached[m["sym"]]         # "via" = the object script whose branch opens this shop
    marts = [m for m in marts if m["map"]]

    # ---------------------------------------------------------------- wild encounters
    enc = {}
    a = S["gWildMonHeaders"]
    i = 0
    while R.u8(a) != 0xFF or R.u8(a + 1) != 0xFF:
        g, n = R.u8(a), R.u8(a + 1)
        name = key.get((g, n))
        rec = {"map": name, "tables": {}, "src": f"gWildMonHeaders[{i}] @ {a:#x}"}
        for t, tod in enumerate(TIMES):
            for k, (kind, cnt) in enumerate(KINDS):
                p = R.u32(a + 4 + t * 20 + 4 * k)
                if not R.ok(p):
                    continue
                tab = R.u32(p + 4)
                rate = R.u8(p)
                mons = [(R.u8(tab + 4 * j), R.u8(tab + 4 * j + 1), sp(R.u16(tab + 4 * j + 2))) for j in range(cnt)]
                if kind == "fish":
                    groups_ = {rod: [(mons[j], r) for j, r in zip(idx, rates)] for rod, (idx, rates) in RODS.items()}
                else:
                    groups_ = {{"land": "walk", "water": "surf", "rock": "rock-smash"}[kind]: list(zip(mons, LAND if kind == "land" else WATER))}
                for method, slots in groups_.items():
                    agg = {}
                    for (lo, hi, s), r in slots:
                        if s == "SPECIES_NONE":
                            continue
                        e = agg.setdefault(s, {"id": s, "min": lo, "max": hi, "rate": 0})
                        e["min"], e["max"], e["rate"] = min(e["min"], lo, hi), max(e["max"], lo, hi), e["rate"] + r
                    if agg:
                        rec["tables"].setdefault(method, {})[tod] = sorted(agg.values(), key=lambda e: -e["rate"])
                        rec.setdefault("density", {})[method] = rate
        for t, tod in enumerate(TIMES):          # fifth list of each period: the three hidden (DexNav) slots
            p = R.u32(a + 4 + t * 20 + 16)
            if R.ok(p):
                tab = R.u32(p + 4)
                hid = [{"id": sp(R.u16(tab + 4 * j + 2)), "min": R.u8(tab + 4 * j), "max": R.u8(tab + 4 * j + 1)} for j in range(3) if R.u16(tab + 4 * j + 2)]
                if hid:
                    rec.setdefault("hidden", {})[tod] = hid
        if name and (rec["tables"] or rec.get("hidden")):
            if name in enc:        # a second header for the same map (kept: the engine uses the first match)
                rec["dup"] = True
                enc.setdefault(name + "#2", rec)
            else:
                enc[name] = rec
        a += 4 + 4 * 20
        i += 1

    for m in world.values():
        for o in m["events"]["objects"]:
            o["script"] = R.rev.get(o["script"]) or (f"{o['script']:#x}" if o["script"] else None)
            o["flag"] = FLAG.get(o["flag"], o["flag"]) if o["flag"] else None
        for k in ("signs", "triggers"):
            for e in m["events"][k]:
                e["script"] = R.rev.get(e["script"]) or (f"{e['script']:#x}" if e["script"] else None)

    # ---------------------------------------------------------------- Town Map coordinates per section (by name, from worldmap.py)
    wm = json.loads((ROOT / "data/worldmap.json").read_text())
    coords = {}
    for key_, m in wm.items():
        byname = {m["names"][k].upper(): m["sections"][k] for k in m["sections"]}
        for sid, nm in secs.items():
            if (key_ == "hoenn") == (sid >= 126) and nm.upper() in byname:
                coords[sid] = {"map": key_, "xy": byname[nm.upper()]}

    # ---------------------------------------------------------------- maps to PNG
    if not args.no_maps:
        import romrender
        rr = romrender.Renderer(R, game)
        out = ROOT / "site/assets/game/maps"
        out.mkdir(parents=True, exist_ok=True)
        for m in world.values():
            m["slug"] = re.sub(r"[^a-z0-9]+", "-", m["name"].lower()).strip("-")
        seen = {}
        for m in world.values():
            if m["slug"] in seen:
                m["slug"] += f"-{m['group']}-{m['num']}"
            seen[m["slug"]] = 1
            im = rr.render(m["layout"]) if R.ok(m["layout"]) else None
            m["img"] = bool(im)
            if im:
                im.convert("P", palette=1, colors=255).save(out / f"{m['slug']}.png", optimize=True)
        print("rendered", sum(m["img"] for m in world.values()), "maps; tiles not found for", sorted(getattr(rr, "missing", [])))

    # ---------------------------------------------------------------- warps performed by scripts (boats, lifts, events): edges the warp tables do not show
    script_warps = []
    for m in re.finditer(rb"[\x39\x3a\x3b\x3d](..)\xff(..)(..)", R.b, re.S):
        g, n = m.group(1)[0], m.group(1)[1]
        to = key.get((g, n))
        if not to:
            continue
        x, y = struct.unpack("<H", m.group(2))[0], struct.unpack("<H", m.group(3))[0]
        if x < world[to]["w"] and y < world[to]["h"]:
            a_ = B + m.start()
            script_warps.append({"sym": R.sym_at(a_), "addr": a_, "to": to, "x": x, "y": y})
    dump = lambda name, obj: (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    dump("world.json", world)
    dump("trainers.json", trainers)
    dump("encounters.json", enc)
    dump("sections.json", {"names": secs, "coords": coords})
    dump("gives.json", gives)
    dump("marts.json", marts)
    dump("scriptwarps.json", script_warps)
    man = {"build": BUILD, "maps": len(world), "by_region": {r: sum(1 for m in world.values() if m["region"] == r) for r in ("johto", "kanto", "hoenn", "alola", "sinjoh")},
           "trainers": len(trainers), "encounter_maps": len(enc), "sections": len(secs), "item_balls": sum(1 for g in gives if g["how"] == "ball"),
           "gift_scripts": sum(1 for g in gives if g["how"] == "gift"), "hidden_items": sum(len(m["events"]["hidden"]) for m in world.values()), "marts": len(marts)}
    dump("manifest.json", man)
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
