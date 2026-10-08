"""Project Blonde guide - the site's model of the game.

Joins the ROM extraction (data/rom, data/dex.json, data/megas.json) with the editorial content
(content/**) into the things pages are made of: species, places, items, trainers, chapters.
Anything editorial that points at data the game does not contain is recorded in ERRORS and stops the build.
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, CONTENT, SITE, DIST = ROOT / "data", ROOT / "content", ROOT / "site", ROOT / "dist"
CFG = {"base": ""}
J = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
esc = lambda s: html.escape(str(s), quote=True)
u = lambda path: CFG["base"] + path
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().replace("é", "e").replace("’", "").replace("'", "")).strip("-")
ERRORS, WARNINGS = [], []


def check(cond, msg):
    if not cond:
        ERRORS.append(msg)
    return cond


# ----------------------------------------------------------------------------- raw data
BUILD = J(DATA / "rom/manifest.json")
VERSION = f'{BUILD["build"]["public"]} (build {BUILD["build"]["version"]})'       # how the game version is named on every page
world, TR, enc = J(DATA / "rom/world.json"), J(DATA / "rom/trainers.json"), J(DATA / "rom/encounters.json")
_sec = J(DATA / "rom/sections.json")
SECNAME, SECXY = {int(k): v for k, v in _sec["names"].items()}, {int(k): v for k, v in _sec["coords"].items()}
GIVES, MARTS = J(DATA / "rom/gives.json"), J(DATA / "rom/marts.json")
DEX, MEGAS, ITEMDATA = J(DATA / "dex.json"), J(DATA / "megas.json"), J(DATA / "items.json")
STATICS = J(DATA / "statics.json") if (DATA / "statics.json").exists() else []
PLATES, WORLDMAP = J(DATA / "plates.json"), J(DATA / "worldmap.json")
site = J(CONTENT / "site.json")
RELEASES, PLAY = J(CONTENT / "releases.json"), J(CONTENT / "play.json")
FEATURES = J(CONTENT / "features.json") if (CONTENT / "features.json").exists() else []
MEGA_SRC = J(CONTENT / "mega-stones.json") if (CONTENT / "mega-stones.json").exists() else {"sources": []}

TYPE_COLOR = {"Normal": "#9a9a7a", "Fire": "#d9652b", "Water": "#4f8fd0", "Grass": "#5a9a3e", "Electric": "#c9a21a", "Ice": "#5fb3b3",
              "Fighting": "#b8473e", "Poison": "#9b4faa", "Ground": "#b08a3c", "Flying": "#8d84d9", "Psychic": "#d6497c", "Bug": "#8a9a1f",
              "Rock": "#9a8236", "Ghost": "#7d6aaa", "Dragon": "#6a4fe0", "Dark": "#6b5a52", "Steel": "#8a8aa3", "Fairy": "#c9739a"}
METHOD = {"walk": "Walking", "surf": "Surfing", "rock-smash": "Rock Smash", "old-rod": "Old Rod", "good-rod": "Good Rod", "super-rod": "Super Rod"}
TODS = ["morning", "day", "evening", "night"]
REGION_NAME = {"johto": "Johto", "kanto": "Kanto", "hoenn": "Hoenn", "alola": "Alola isles", "sinjoh": "Sinjoh", "far": "Far-off places"}
SMALL = {"Of", "The", "And", "To", "In", "On", "At"}


def nice(name):
    """Game strings are upper-case; the guide prints them as names."""
    t = " ".join(w if re.match(r"^(S\.S\.|B?\d+F|[IVX]+|TM\d+|HM\d+|PC|HP|PP|BP|E4)$", w) else w.capitalize() for w in str(name).replace("’", "'").split(" "))
    t = re.sub(r"\b(\w)'S\b", lambda m: m.group(1) + "'s", t)
    t = re.sub(r"(?<=[-'&.])([a-z])(?=[a-z]{2})", lambda m: m.group(1).upper(), t)
    t = " ".join(w.lower() if i and w in SMALL else w for i, w in enumerate(t.split(" ")))
    return t.replace("Mt. ", "Mt. ").replace("Pokémon", "Pokémon").replace("Pokemon", "Pokémon").replace("Poke ", "Poké ").replace("Tate&liza", "Tate & Liza").replace("Ltsurge", "Lt. Surge")


# ----------------------------------------------------------------------------- species
for d in DEX.values():
    d["display"] = nice(d["name"].replace("♀", "♀").replace("♂", "♂"))
    if d["kind"] == "regional":
        d["display_full"] = f'{d["display"]} ({d["regional"]})'
    elif d["kind"] in ("mega", "form"):
        base = DEX[d["of"]]
        fn = d.get("form_name", "")
        d["display_full"] = (f'Mega {nice(base["name"])}' + (f' {fn.replace("Mega", "").strip()}' if fn.replace("Mega", "").strip() else "")) if d["kind"] == "mega" and not d.get("primal") else f'{nice(base["name"])} ({fn})'
    else:
        d["display_full"] = d["display"]
# The public Pokédex lists Pokémon a player can legitimately obtain in this build, not every species the engine defines.
# tools/availability.py decides that from evidence; the build refuses to run on an audit made for another build.
AVAIL = J(DATA / "availability.json")
AV = AVAIL["species"]
check(AVAIL["report"]["build"]["sha256"] == BUILD["build"]["sha256"], "data/availability.json was computed for a different game build: re-run tools/availability.py")
ENTRIES = {k for k, d in DEX.items() if d["kind"] in ("species", "regional")}       # every species and regional form the engine defines
PAGES = {k for k in ENTRIES if AV.get(k, {}).get("status") == "obtainable"}          # the public Pokédex: entries with their own page
UNREACHABLE = set(AVAIL["report"]["maps_unreachable"])
GATED = J(CONTENT / "availability-rules.json")["gated"]
FORMS = {}
for d in DEX.values():
    if d.get("of"):
        FORMS.setdefault(d["of"], []).append(d)
REGIONALS = {}
for d in DEX.values():
    if d["kind"] == "regional" and d.get("base"):
        REGIONALS.setdefault(d["base"], []).append(d)
_by_name = {}
for d in sorted(DEX.values(), key=lambda d: d["num"]):
    _by_name.setdefault(re.sub(r"[^a-z0-9]", "", d["name"].lower()), d)


def sp(key):
    """Species record from a SPECIES_ constant or a display name."""
    return DEX.get(key) or _by_name.get(re.sub(r"[^a-z0-9]", "", str(key).lower()))


def page_of(d):
    """The species whose page shows this record (forms live on their base species' page)."""
    p = d if d["id"] in PAGES else DEX.get(d.get("of"))
    return p if p and p["id"] in PAGES else None


def sp_url(d):
    p = page_of(d)
    return u(f"/pokemon/{p['slug']}/") if p else None


def sp_link(d, text=None):
    """A link to the Pokémon's page when it has one (it is obtainable); plain text otherwise, so nothing implies it can be caught."""
    t = esc(text or d["display_full"])
    return f'<a href="{sp_url(d)}">{t}</a>' if sp_url(d) else t


# ----------------------------------------------------------------------------- places
def map_region(m):
    return m["region"] if m["region"] in ("johto", "kanto", "hoenn") else "far"


OUTDOOR = ("city", "town", "route", "ocean_route")
KIND_ORDER = ["Towns & cities", "Routes", "Caves & dungeons", "Special areas"]
PLACES = {}
for _k, _m in world.items():
    if not _m["place"]:
        continue
    _p = PLACES.setdefault(_m["sec"], {"id": _m["sec"], "name": nice(_m["place"]), "region": map_region(_m), "maps": []})
    _p["maps"].append(_k)
_used = {}
for _p in PLACES.values():
    _p["maps"].sort(key=lambda k: (world[k]["type"] not in OUTDOOR, world[k]["group"], world[k]["num"]))
    _types = [world[m]["type"] for m in _p["maps"]]
    _p["kind"] = ("Towns & cities" if any(t in ("city", "town") for t in _types) else "Routes" if any(t in ("route", "ocean_route") for t in _types)
                  else "Caves & dungeons" if any(t in ("underground", "underwater") for t in _types) or any(world[m]["cave"] for m in _p["maps"]) else "Special areas")
    _s = slug(_p["name"])
    _used[(_p["region"], _s)] = _used.get((_p["region"], _s), 0) + 1
    _p["slug"] = _s if _used[(_p["region"], _s)] == 1 else f'{_s}-{_p["id"]}'
    _p["url"] = f'/world/{_p["region"]}/{_p["slug"]}/'
    _p["xy"] = SECXY.get(_p["id"])
MAP_PLACE = {m: p for p in PLACES.values() for m in p["maps"]}
for _p in PLACES.values():        # dungeons with no cell on the Town Map borrow the position of the place that leads into them
    if not _p["xy"]:
        for _m in world.values():
            if _m["sec"] != _p["id"] and SECXY.get(_m["sec"]) and any(w["to"] in _p["maps"] for w in _m["events"]["warps"]) and map_region(_m) == _p["region"]:
                _p["xy"], _p["xy_from"] = SECXY[_m["sec"]], nice(_m["place"])
                break


def table_species(mapkey):
    rec = enc.get(mapkey)
    return sorted({r["id"] for t in rec["tables"].values() for rows in t.values() for r in rows}) if rec else []


for _p in PLACES.values():
    _p["wild"] = sorted({s for m in _p["maps"] for s in table_species(m)})
    _p["items"] = [(o["item"], m, "ball") for m in _p["maps"] for o in world[m]["events"]["objects"] if o.get("item")] + \
                  [(h["item"], m, "hidden") for m in _p["maps"] for h in world[m]["events"]["hidden"]]
    _p["trainers"] = [t for m in _p["maps"] for t in world[m]["trainers"]]
    _p["chapters"] = []

# ----------------------------------------------------------------------------- where each species lives
WHERE = {}
for _mk, _rec in enc.items():
    if "#" in _mk or _mk not in world or _mk in UNREACHABLE:
        continue
    for _method, _tods in _rec["tables"].items():
        for _tod, _rows in _tods.items():
            for _r in _rows:
                WHERE.setdefault(_r["id"], []).append({"map": _mk, "method": _method, "time": _tod, "min": _r["min"], "max": _r["max"], "rate": _r["rate"]})
for _s in STATICS:
    WHERE.setdefault(_s["species"], [])


# ----------------------------------------------------------------------------- trainers
def trainer(tid):
    return TR.get(str(tid))


def tname(t):
    n = t["name"]
    if n in ("?ぶ", "???") and t["class"] == "PKMN TRAINER":
        return "Silver"
    return nice(n)


def tclass(t):
    return nice(t["class"]).replace("Pkmn", "Pokémon").replace("Pokéfan", "Poké Fan").replace("Pokémaniac", "Poké Maniac")


TRAINER_MAPS = {}
for _mk, _m in world.items():
    for _t in _m["trainers"]:
        TRAINER_MAPS.setdefault(_t, []).append(_mk)
MAJOR_CLASSES = {"LEADER", "ELITE FOUR", "CHAMPION", "PKMN TRAINER", "AQUA LEADER", "MAGMA LEADER", "AQUA ADMIN", "MAGMA ADMIN", "ROCKET ADMIN", "KIMONO GIRL",
                 "MYSTERY MAN", "SALON MAIDEN", "DOME ACE", "PALACE MAVEN", "ARENA TYCOON", "FACTORY HEAD", "PIKE QUEEN", "PYRAMID KING", "WINSTRATE"}

# ----------------------------------------------------------------------------- chapters (The Road)
chapmap = J(CONTENT / "chapters.json")
REGIONS = {r["id"]: r for r in chapmap["regions"]}
CH = {}
for _f in sorted((CONTENT / "walkthrough").glob("*.json")):
    for _c in J(_f)["chapters"]:
        CH[(_c["region"], _c["slug"])] = _c
LABEL = {i[0]: i[1] for g in site["checklist"] for i in g["items"]}
_secid = {v.upper().replace("’", "'"): k for k, v in SECNAME.items()}


def chapter_url(region, slug_):
    return f"/postgame/{slug_}/" if region == "postgame" else f"/walkthrough/{region}/{slug_}/"


LEAGUES = set()
JOURNEY = []
for _rid, _r in REGIONS.items():
    for _slug in _r["chapters"]:
        _c = CH.get((_rid, _slug))
        if not check(_c is not None, f"chapters.json lists {_rid}/{_slug} but no chapter content exists"):
            continue
        _cands = [k for k, v in SECNAME.items() if v.upper().replace("’", "'") == str(_c.get("at", "")).upper()]
        _cands.sort(key=lambda k: (k >= 126) != (_rid == "hoenn"))
        _at = next((k for k in _cands if k in PLACES), None)
        _pl = PLACES.get(_at)
        if _c.get("at"):
            check(_pl is not None, f"chapter {_rid}/{_slug}: place '{_c['at']}' is not a map section in the ROM")
        _maps = []
        for _m in _c.get("maps", []):
            if _m.endswith("*"):
                _hit = [k for k in world if k.startswith(_m[:-1])]
                check(bool(_hit), f"chapter {_rid}/{_slug}: no map in the ROM starts with '{_m[:-1]}'")
                _maps += _hit
            elif check(_m in world, f"chapter {_rid}/{_slug}: map '{_m}' is not in the ROM"):
                _maps.append(_m)
        _c["maps"] = list(dict.fromkeys(_maps))
        for _b in _c.get("bosses", []):
            for _v in _b["ids"]:
                check(str(_v[1] if isinstance(_v, list) else _v) in TR, f"chapter {_rid}/{_slug}: trainer {_v} is not in the ROM")
        if _c.get("league"):
            LEAGUES.add(_slug)
        _xy = _pl["xy"] if _pl else None
        _j = {"k": f"{_rid}/{_slug}", "n": len(JOURNEY) + 1, "r": _rid, "ch": _c, "live": True, "xy": _xy["xy"] if _xy else None, "map": _xy["map"] if _xy else None,
              "title": _c["title"], "url": chapter_url(_rid, _slug), "plate": _c.get("plate"), "place": _pl}
        JOURNEY.append(_j)
        for _m in dict.fromkeys(MAP_PLACE[m]["id"] for m in _c.get("maps", []) if m in MAP_PLACE):
            PLACES[_m]["chapters"].append(_j)
TOTAL = len(JOURNEY)
BADGES = {rid: [i[0] for g in site["checklist"] if g["id"] == rid for i in g["items"] if i[0].startswith("badge")] for rid in REGIONS}
jhref = lambda j: u(j["url"])
for _rid in REGIONS:
    _bj = [j for j in JOURNEY if j["r"] == _rid and j["ch"].get("badge")]
    check(len(_bj) == len(BADGES[_rid]), f"{_rid}: {len(_bj)} badge chapters but {len(BADGES[_rid])} badges in the checklist")
    for _j, _b in zip(_bj, BADGES[_rid]):
        _j["bid"] = _b
MAP_CHAPTER = {}
for _j in JOURNEY:
    for _m in _j["ch"].get("maps", []):
        MAP_CHAPTER.setdefault(_m, _j)


def journey_public():
    """What the page script needs to place the reader on the road. Spoiler goals are withheld."""
    out = []
    for j in JOURNEY:
        c = j["ch"]
        out.append({"k": j["k"], "n": j["n"], "r": REGIONS[j["r"]]["name"], "rid": j["r"], "t": j["title"], "g": "" if c.get("spoiler") else c["goal"],
                    "h": jhref(j), "live": True, "map": j["map"], "b": c.get("badge"), "bid": j.get("bid"), "plate": j["plate"],
                    "x": j["xy"][0] / 240 * 100 if j["xy"] else None, "y": j["xy"][1] / 160 * 100 if j["xy"] else None,
                    "at": j["place"]["name"] if j["place"] else "", "ms": c.get("milestone", "")})
    return out


# ----------------------------------------------------------------------------- items
ITEMS = {}


def _item(name):
    return ITEMS.setdefault(name, {"name": name, "sources": []})


for _p in PLACES.values():
    for _name, _m, _how in _p["items"]:
        _item(_name)["sources"].append({"place": _p, "area": world[_m]["name"], "map": _m, "how": _how})
_keys = sorted(world, key=len, reverse=True)
_bare = {k[:-4]: k for k in world if k.endswith("_hns")}
_alias = {"Cianwood": "CianwoodCity_hns"}


def sym_map(sym):
    """Map a script symbol back to the map it belongs to (the build's labels start with the map's name)."""
    if not sym or "Frlg" in sym:
        return None
    m = re.match(r"^Ho[A-Za-z0-9]*?_(.+)$", sym)
    if m:
        rest = m.group(1)
        return next((k for k in _keys if not k.endswith("_hns") and (rest == k or rest.startswith(k + "_"))), None)
    for b in sorted(_bare, key=len, reverse=True):
        if sym == b or sym.startswith(b + "_"):
            return _bare[b]
    return next((k for k in _keys if k.endswith("_hns") and sym.startswith(k + "_")), None)


UNPLACED_GIFTS = []
for _g in GIVES:
    if _g["how"] != "gift":
        continue
    _mk = sym_map(_g["sym"])
    if _mk and _mk in MAP_PLACE:
        _src = {"place": MAP_PLACE[_mk], "area": world[_mk]["name"], "map": _mk, "how": "gift", "sym": _g["sym"]}
        if not any(s["how"] == "gift" and s["map"] == _mk for s in _item(_g["item"])["sources"]):
            _item(_g["item"])["sources"].append(_src)
    else:
        UNPLACED_GIFTS.append(_g)
for _m in MARTS:
    if _m["map"] in MAP_PLACE:
        for _name in _m["items"]:
            _item(_name)["sources"].append({"place": MAP_PLACE[_m["map"]], "area": world[_m["map"]]["name"], "map": _m["map"], "how": "shop"})
_norm = lambda n: re.sub(r"[^a-z0-9]", "", n.lower())
_canon = {_norm(n): n for n in ITEMDATA}
_canon.update({_norm(n): n for n in ITEMS})
ITEM_ALIAS = {"expshares": "Exp Share Small", "devongoods": "Devon Parts"}
NOT_ITEMS = {"Radio Card", "Radio Upgrade", "Ash’s Pikachu", "Castform", "Egg"}       # rewards that are not Bag items


def canon_item(n):
    k = _norm(n)
    return _canon.get(_norm(ITEM_ALIAS.get(k, n)), n)


for _j in JOURNEY:
    for _it in _j["ch"].get("items", []):
        _it[0] = canon_item(_it[0])
        _i = _item(_it[0])
        _i.setdefault("notes", []).append({"chapter": _j, "text": _it[1]})
for _mg in MEGAS:
    if _mg["stone"]:
        _item(_mg["stone"])["mega"] = _mg
POCKET = {"Tm Hm": "TMs & HMs", "Poke Balls": "Poké Balls", "Key Items": "Key Items", "Berries": "Berries", "Items": "Items", "Medicine": "Medicine", "Battle Items": "Battle items"}
_desc = {}
for _n, _d in ITEMDATA.items():
    _desc[re.sub(r"[^a-z0-9]", "", _n.lower())] = _d
for _i in ITEMS.values():
    _n = _i["name"]
    _k = re.sub(r"[^a-z0-9]", "", (re.sub(r"^(TM|HM)\d+ ", r"\1 ", _n)).lower())
    _d = _desc.get(_k) or _desc.get(re.sub(r"[^a-z0-9]", "", _n.lower())) or {}
    _i["desc"] = _d.get("desc")
    _i["pocket"] = "TMs & HMs" if re.match(r"^(TM|HM)\d", _n) else "Mega Stones" if _i.get("mega") else POCKET.get(_d.get("pocket"), _d.get("pocket") or "Items")
    _i["slug"] = slug(_n)
    _i["display"] = {"Ss Ticket": "S.S. Ticket", "Exp Share Small": "Exp. Share S", "Exp Share": "Exp. Share", "Go Goggles": "Go-Goggles", "TM89 U Turn": "TM89 U-turn", "Devon Parts": "Devon Goods",
                     "Squirt Bottle": "SquirtBottle", "Secret Potion": "SecretPotion", "Energypowder": "Energy Powder", "Ragecandybar": "RageCandyBar", "Kings Rock": "King's Rock"}.get(_n) or \
        _n.replace("Poke ", "Poké ").replace("Hp ", "HP ").replace("Pp ", "PP ")
    _i["url"] = f'/items/{_i["slug"]}/'

MAP_SLUG = {k: m["slug"] for k, m in world.items()}
