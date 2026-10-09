"""Project Blonde guide - the Legendary & Mythical field guide (one page type, /postgame/legendaries/).

Content : content/legendaries.json (hand-written, one entry per obtainable Pokémon)
Evidence: data/legendaries.json   (tools/legendaries.py: ROM flags, availability audit, byte checks)
The page keeps its place on the road as a postgame chapter; build.py calls build() instead of build_chapter().
"""
from site_core import *

GUIDE = J(CONTENT / "legendaries.json")
AUDIT = J(DATA / "legendaries.json")
MEGA_OFFERED = J(DATA / "megastones.json")["offered"]
URL = "/postgame/legendaries/"
REGION = {"johto": "Johto", "kanto": "Kanto", "hoenn": "Hoenn", "alola": "Alola isles", "sinjoh": "Sinjoh"}
TYPE = {"static": "Fixed encounter", "roaming": "Roaming", "ticket": "Ticket island", "quest": "Quest", "special": "Form change"}
STAGE = {"story": "During the story", "milestone": "After a milestone", "postgame": "Postgame"}
EVID = {"played": ("played", "Played", "Caught in the completed natural playthrough of the game."),
        "mixed": ("mixed", "Partly played", "The scene that starts this was played in the natural playthrough. The encounter itself is read from the game’s scripts."),
        "script": ("source", "From game scripts", "Read from the game’s own event scripts and checked against the release build. Not reached in the natural playthrough, so directions on the ground were not walked.")}
BY_K = {j["k"]: j for j in JOURNEY}
BY_SPECIES = {e["species"]: e for e in GUIDE["entries"]}
QUESTS = {q["id"]: q for q in GUIDE["quests"]}


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower().replace("é", "e").replace("’", ""))).strip()


def display(e):
    """Ho-Oh, Galarian Articuno: the name as a player says it."""
    d = DEX[e["species"]]
    n = d["display"].replace("Ho-oh", "Ho-Oh")
    return {"Galar": "Galarian "}.get(d.get("regional"), "") + n


def fmt(s):
    def chapter(m):
        j = BY_K.get(m[1])              # a chapter that is not on the road yet is named, not linked
        return f'<a href="{jhref(j)}">{m[2]}</a>' if j else m[2]

    def tag(m):
        kind, key, text = m[1], m[2], m[3]
        if kind == "item":
            i = ITEMS.get(key)
            return f'<a href="{u(i["url"])}">{esc(text or i["display"])}</a>' if i else esc(text or key)
        if kind == "map":
            p = MAP_PLACE.get(key)
            check(key in world, f"legendaries: map '{key}' is not in the ROM")
            label = text or world[key]["name"]
            return f'<a href="{u(p["url"])}#m-{world[key]["slug"]}">{esc(label)}</a>' if p else esc(label)
        if kind == "mon":
            e = BY_SPECIES.get(key)
            check(e is not None, f"legendaries: no entry for '{key}'")
            return f'<a href="#{e["id"]}" data-lg-open>{esc(text or display(e))}</a>'
        if kind == "quest":
            check(key in QUESTS, f"legendaries: no shared section '{key}'")
            return f'<a href="#{key}" data-lg-open>{esc(text or QUESTS[key]["title"])}</a>'
        check(False, f"legendaries: unknown tag '{kind}'")
        return esc(text or key)

    s = re.sub(r"\[\[([a-z0-9/-]+)\|([^\]]+)\]\]", chapter, s)
    s = re.sub(r"\{\{(\w+):([^}|]+)(?:\|([^}]+))?\}\}", tag, s)
    return re.sub(r"\|\|(.+?)\|\|", r'<span class="blur" tabindex="0" role="button" aria-label="Reveal spoiler">\1</span>', s)


def evid(b):
    cls, lab, tip = EVID[b]
    return f'<span class="basis b-{cls}" title="{esc(tip)}">{lab}</span>'


def markers(mk):
    if not mk:
        return []
    mk = mk if isinstance(mk[0], list) else [mk]
    return [{"x": x, "y": y, "kind": "item" if "ball" in note.lower() else "objective", "label": label, "note": note} for x, y, label, note in mk]


def mapfig(mapkey, mk, caption):
    m = world[mapkey]
    ms = markers(mk)
    focus = f'{(ms[0]["x"] + .5) / m["w"]:.3f},{(ms[0]["y"] + .5) / m["h"]:.3f}' if ms else ""
    return map_viewer(mapkey, markers=ms, caption=caption, focus=focus, label="Where")


def links(e):
    d = DEX[e["species"]]
    out = [f'<a href="{u("/pokemon/" + d["slug"] + "/")}"><small>Pokédex</small><b>{esc(display(e))}</b>{ARROW}</a>']
    seen = set()
    for mk in [e["map"]] + e.get("maps", []):
        p = MAP_PLACE.get(mk)
        if p and p["id"] not in seen:
            seen.add(p["id"])
            out.append(f'<a href="{u(p["url"])}#m-{world[mk]["slug"]}"><small>Atlas</small><b>{esc(p["name"])}</b>{ARROW}</a>')
    for k in e.get("chapters", []):
        j = BY_K.get(k)
        if j:
            out.append(f'<a href="{jhref(j)}"><small>Chapter {j["n"]}</small><b>{esc(j["title"])}</b>{ARROW}</a>')
    for n in e.get("items", []):
        i = ITEMS.get(n)
        if i:
            out.append(f'<a href="{u(i["url"])}"><small>Item</small><b>{esc(i["display"])}</b>{ARROW}</a>')
    stones = [o["stone"] for o in MEGA_OFFERED if o["mega"].startswith(e["species"] + "_MEGA")]
    if stones:
        out.append(f'<a href="{u("/items/mega-stones/")}"><small>Mega Stone</small><b>{esc(" / ".join(stones))}</b>{ARROW}</a>')
    return '<div class="chlinks lg-links">' + "".join(out) + "</div>"


def entry(e):
    d = DEX[e["species"]]
    name = display(e)
    check(d["id"] in PAGES, f'legendaries: {e["id"]} has no public Pokédex page')
    hay = _norm(" ".join([name, " ".join(d["types"]), REGION[e["region"]], TYPE[e["type"]], STAGE[e["stage"]], e["when"], e["summary"], " ".join(e.get("items", [])),
                          "legendary mythical", "roamer roams" if e["type"] == "roaming" else ""]))
    nm = _norm(name)
    rom = AUDIT["entries"][e["species"]]["rom"]
    check(all(r["found"] for r in rom), f'legendaries: {e["id"]} has an unverified ROM row; run tools/legendaries.py')
    f = e["facts"]
    kv = [("Level", esc(e["level"])), ("Catch rate", str(d["catch_rate"]) if e["type"] != "special" else "Not a battle"), ("Method", TYPE[e["type"]]), ("Available", esc(e["when"]))] + [(k, esc(v)) for k, v in f.items()] + [("Evidence", evid(e["basis"]))]
    lst = lambda xs: "".join(f"<li>{fmt(x)}</li>" for x in xs)
    body = f"""<div class="lg-body">
 <div class="lg-main">
  <section><p class="label accent">Where to start</p><p class="lg-start">{fmt(e["start"])}</p></section>
  <section><p class="label">What you need</p><ul class="plain">{lst(e["need"])}</ul></section>
  <section><p class="label">What to do</p><ol class="route lg-steps">{"".join(f"<li><span>{fmt(x)}</span></li>" for x in e["steps"])}</ol></section>
  <section><p class="label">The encounter</p><ul class="plain">{lst(e["encounter"])}</ul></section>
  <section><p class="label">Afterwards</p><ul class="plain">{lst(e["after"])}</ul></section>
 </div>
 <aside class="lg-side">{art_img(d, 96, name)}
  <dl class="kv wide">{"".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in kv)}</dl>
  {links(e)}
 </aside>
 <div class="lg-map">{mapfig(e["map"], e.get("marker"), "Drawn from the game’s own map data. Tile coordinates are x,y from the top-left.")}</div>
 <p class="muted evline">Source: {esc(e["ev"])}. Level and species confirmed in the {esc(VERSION)} ROM.</p>
</div>"""
    form = f' <small>{esc(d["regional"])}</small>' if d.get("regional") else ""
    return (f'<li id="{e["id"]}" data-n="{nm}" data-nc="{nm.replace(" ", "")}" data-f="{esc(hay)}" data-region="{e["region"]}" data-type="{e["type"]}" data-stage="{e["stage"]}">'
            f'<details class="lg"><summary>{icon_img(d, 32)}<span class="lg-n"><b>{esc(name)}</b>{form}</span>{types(d)}'
            f'<span class="lg-w lg-sp">{esc(e["summary"])}</span><span class="lg-when s-{e["stage"]}">{esc(e["when"])}</span></summary>{body}</details></li>')


def quest(q):
    lst = lambda xs: "".join(f"<li>{fmt(x)}</li>" for x in xs)
    inner = "".join(f"<p>{fmt(p)}</p>" for p in q.get("p", []))
    if q.get("need"):
        inner += f'<p class="label">What you need</p><ul class="plain">{lst(q["need"])}</ul>'
    if q.get("steps"):
        inner += f'<p class="label">What to do</p><ol class="route lg-steps">{"".join(f"<li><span>{fmt(x)}</span></li>" for x in q["steps"])}</ol>'
    if q.get("after"):
        inner += f'<p class="label">Notes</p><ul class="plain">{lst(q["after"])}</ul>'
    side = ""
    if q.get("maps"):
        seen, out = set(), []
        for mk in q["maps"]:
            p = MAP_PLACE.get(mk)
            if p and p["id"] not in seen:
                seen.add(p["id"])
                out.append(f'<a href="{u(p["url"])}#m-{world[mk]["slug"]}"><small>Atlas</small><b>{esc(p["name"])}</b>{ARROW}</a>')
        side = '<div class="chlinks lg-links">' + "".join(out) + "</div>"
    fig = ""
    if q.get("marker"):
        mk, x, y, label, note = q["marker"]
        fig = f'<div class="lg-map">{mapfig(mk, [x, y, label, note], "Drawn from the game’s own map data.")}</div>'
    return (f'<details class="lg lg-q" id="{q["id"]}"><summary><span class="lg-n"><b>{esc(q["title"])}</b></span><span class="lg-w">{esc(q["sub"])}</span></summary>'
            f'<div class="lg-body"><div class="lg-main prose">{inner}</div><aside class="lg-side"><dl class="kv wide"><div><dt>Evidence</dt><dd>{evid(q["basis"])}</dd></div></dl>{side}</aside>{fig}'
            f'<p class="muted evline">Source: {esc(q["ev"])}.</p></div></details>')


def seg(key, label, opts):
    btn = "".join(f'<button data-lg-filter="{key}" data-v="{v}" aria-pressed="{"true" if not v else "false"}">{esc(t)}</button>' for v, t in [("", "All")] + opts)
    return f'<div class="lg-group"><span class="label" id="lg-{key}">{label}</span><div class="seg wrapok" role="group" aria-labelledby="lg-{key}">{btn}</div></div>'


def build(Jn, journey_bar):
    c, n = Jn["ch"], AUDIT["counts"]
    check(n["failed"] == 0, "legendaries: the completeness audit has failing checks; run tools/legendaries.py")
    check({e["species"] for e in GUIDE["entries"]} == set(AUDIT["entries"]), "legendaries: guide and audit disagree; run tools/legendaries.py")
    bar, pv, nx, here = journey_bar(Jn)
    rows = "".join(entry(e) for e in GUIDE["entries"])
    used = lambda key, table: [(k, v) for k, v in table.items() if any(e[key] == k for e in GUIDE["entries"])]
    rules = "".join(f"<div><dt>{esc(a)}</dt><dd>{fmt(b)}</dd></div>" for a, b in GUIDE["rules"])
    cls = {}
    for x in AUDIT["unobtainable"]:
        cls.setdefault("Mythical" if x["class"] == "Mythical" else "Legendary", []).append(x["name"])
    absent = "".join(f'<p><b>{k}</b> <span class="muted">({len(v)})</span><br>{esc(", ".join(v))}</p>' for k, v in cls.items())
    absent += f'<p><b>Ultra Beasts</b> <span class="muted">({len(AUDIT["ultra_beasts"])})</span><br>{esc(", ".join(x["name"] for x in AUDIT["ultra_beasts"]))}</p>'
    notes = "".join(f"<li><b>{esc(a)}.</b> {esc(b)}</li>" for a, b in GUIDE["absent"]["notes"])
    foot_prev = f'<a href="{jhref(pv)}"><small>Previous · Chapter {pv["n"]}</small><b>{esc(pv["ch"]["title"])}</b></a>' if pv else "<span></span>"
    foot_next = f'<a class="r" href="{jhref(nx)}"><small>Next · Chapter {nx["n"]}</small><b>{esc(nx["ch"]["title"])}</b></a>' if nx else "<span></span>"
    jsheet = (f'<details><summary>Journey</summary><div class="sheet"><p class="label">{REGIONS[Jn["r"]]["name"]} · Chapter {Jn["n"]} of {TOTAL}</p>'
              + (f'<a href="{jhref(pv)}">Previous<span>{esc(pv["ch"]["title"])}</span></a>' if pv else "") + (f'<a href="{jhref(nx)}">Next<span>{esc(nx["ch"]["title"])}</span></a>' if nx else "")
              + f'<a href="{here}">See it on the road<span>Chapter {Jn["n"]}</span></a></div></details>')
    dock = (f'<nav class="dock four" aria-label="Legendary guide">{jsheet}<a href="#find">Find</a><a href="#shared">Quests</a>'
            f'<details><summary>Contents</summary><div class="sheet"><p class="label">On this page</p><a href="#rules">Before you go</a><a href="#find">The index</a><a href="#shared">Shared quests and rules</a><a href="#absent">Not in the game</a></div></details></nav>')
    stat = (f'<dl class="lg-stats"><div><dt>Obtainable</dt><dd>{n["obtainable"]}</dd></div><div><dt>During the story</dt><dd>{n["story"]}</dd></div>'
            f'<div><dt>After a milestone</dt><dd>{n["milestone"]}</dd></div><div><dt>Postgame</dt><dd>{n["postgame"]}</dd></div><div><dt>Roaming</dt><dd>{n["roaming"]}</dd></div></dl>')
    body = f"""{bar}
<link rel="stylesheet" href="{u("/assets/legends.css")}">
<header class="phead lg-head"><div class="wrap"><p class="label">Postgame · Chapter {Jn["n"]} of {TOTAL} · Field guide</p><h1>Legendary &amp; Mythical Pokémon</h1>
 <p class="lead">{fmt(GUIDE["intro"][0])}</p><p class="lead lg-lead2">{fmt(GUIDE["intro"][1])}</p>{stat}
 <p class="headlinks"><a class="link" href="{u("/pokemon/")}">Pokédex{ARROW}</a><a class="link" href="{u("/world/")}">World atlas{ARROW}</a><a class="link" href="{u("/postgame/after-the-credits/")}">After the credits{ARROW}</a><a class="link" href="{u("/items/mega-stones/")}">Mega Stones{ARROW}</a></p></div></header>
<div class="wrap listpage" data-legends>
 <section id="rules" class="lg-rules"><p class="label">Before you go</p><dl>{rules}</dl></section>
 <section id="find">
  <div class="filterbar lg-find"><label class="field">{SEARCH}<span class="sr">Search legendary Pokémon</span><input type="search" data-lg-q placeholder="Search by name — try “suicune”, “regi” or “tapu”" autocomplete="off" spellcheck="false" aria-controls="legends"></label>
   <p class="count" data-lg-count aria-live="polite"></p><button class="link lg-spoil" data-spoiler-toggle>Spoilers: hidden</button></div>
  <details class="lg-filters"><summary><span>Filters</span><span class="lg-active" data-lg-active></span></summary><div class="lg-groups">
   {seg("region", "Region", used("region", REGION))}{seg("type", "Encounter", used("type", TYPE))}{seg("stage", "Availability", used("stage", STAGE))}</div></details>
  <p class="muted lg-hint">Locations are blurred until you open an entry. Turn spoilers on to see them all.</p>
  <ol class="lg-index" id="legends">{rows}</ol>
  <p class="empty" data-lg-empty hidden>No legendary Pokémon match that. <button class="link" data-lg-reset>Clear the search and filters</button></p>
 </section>
 <section id="shared" class="lg-shared"><p class="label">Reference</p><h2>Shared quests and rules</h2><p class="muted">Two things many entries above depend on.</p>{"".join(quest(q) for q in GUIDE["quests"])}</section>
 <section id="absent" class="lg-absent"><p class="label">Reference</p><h2>Not in the game</h2><p class="muted">{esc(GUIDE["absent"]["lead"])}</p>
  <ul class="plain">{notes}</ul>
  <details class="qa"><summary><b>All {n["unobtainable"]} Legendary and Mythical Pokémon you cannot obtain</b></summary><div class="lg-absent-list">{absent}</div></details></section>
 <section class="onward lg-onward">
  <label class="check done-check"><input type="checkbox" data-chapter="{Jn["k"]}"><span>Mark this chapter complete</span></label>
  <p class="muted evline">{n["audited"]} Legendary and Mythical species in the game’s data were checked: {n["obtainable"]} can be obtained and each has an entry above; {n["unobtainable"]} cannot. {n["checks"]} automated checks against the ROM and the Pokédex availability audit, {n["failed"]} failing. Game: {esc(VERSION)}.</p>
  <nav class="pager" aria-label="Chapters">{foot_prev}{foot_next}</nav>
 </section>
</div>
<script src="{u("/assets/legends.js")}" defer></script>"""
    write(Jn["url"], layout("Legendary & Mythical Pokémon — where and how to catch every one", body, desc=f'Step-by-step guides to all {n["obtainable"]} Legendary and Mythical Pokémon you can catch in Project Blonde: location, requirements, level and what happens afterwards.',
                            path="/walkthrough/", dock=dock, attrs=f'data-chapter-key="{Jn["k"]}"'))


def search_entries():
    """Rows for the global search: one per Pokémon and one per shared section."""
    out = [{"t": "Legendary & Mythical Pokémon", "k": "Walkthrough", "u": URL, "d": f'Field guide · all {AUDIT["counts"]["obtainable"]} you can catch', "x": "legendary legendaries mythical legends catch where how guide roaming ticket", "p": 8}]
    for e in GUIDE["entries"]:
        out.append({"t": f"How to get {display(e)}", "k": "Walkthrough", "u": f'{URL}#{e["id"]}', "d": f'Legendary guide · {REGION[e["region"]]} · {e["when"]}',
                    "x": " ".join([display(e), "legendary mythical catch where find", TYPE[e["type"]], " ".join(e.get("items", []))]), "p": 5})
    for q in GUIDE["quests"]:
        out.append({"t": q["title"], "k": "Walkthrough", "u": f'{URL}#{q["id"]}', "d": f'Legendary guide · {q["sub"]}', "x": "legendary sinjoh plates arceus regi respawn return hall of fame league", "p": 4})
    return out


def species_link(d):
    """A line for a Pokémon's own page, pointing at its field-guide entry."""
    e = BY_SPECIES.get(d["id"])
    return f'<p class="bestline"><span class="label">Field guide</span><b><a href="{u(URL)}#{e["id"]}">How to get {esc(display(e))}, step by step</a></b></p>' if e else ""


def place_note(p):
    """For an atlas page: the guide entries whose encounter, or whose marked starting point, is in this place."""
    hit = [e for e in GUIDE["entries"] if any(MAP_PLACE.get(m) is p for m in [e["map"]] + e.get("maps", []))]
    if not hit:
        return ""
    rows = "".join(f'<a href="{u(URL)}#{e["id"]}"><small>Field guide</small><b>How to get {esc(display(e))}</b>{ARROW}</a>' for e in hit)
    return f'<section class="inwalk"><p class="label">Legendary Pokémon</p><div class="chlinks">{rows}</div><p class="muted"><a href="{u(URL)}">The whole Legendary &amp; Mythical guide</a></p></section>'
