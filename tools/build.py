#!/usr/bin/env python3
"""Project Blonde guide - static site builder. One function per page type.

    python3 tools/build.py [--base /sub-path]

Inputs : data/** (romx.py, dex.py, statics.py, megastones.py, worldmap.py, plates.py), content/**, site/assets/*
Output : dist/ and CONTENT-COVERAGE.md, WALKTHROUGH-CHAPTER-MAP.md
"""
import argparse, shutil, sys
from site_core import *
import legend_page
import dexnav_page

MEGASTONES = J(DATA / "megastones.json")
ABOUT = J(CONTENT / "about.json")
BASIS = {"played": ("Played", "Every step on this page was carried out in the completed natural playthrough of the game."),
         "mixed": ("Partly played", "Part of this page was played in the natural playthrough; the rest comes from game data and is marked."),
         "source": ("From game data", "This page is built from the game’s data and the project’s audits. It was not reached in the natural playthrough, so routes and conditions are not confirmed."),
         "accepted": ("Owner-accepted", "Described from the build the owner accepted; not re-opened in the natural playthrough."),
         "data": ("From game data", "Read from the game’s own tables and text."),
         "script": ("From game scripts", "This page is confirmed from the story scripts and text in the release build, and from the project’s automated tests where marked. It was not reached in the natural playthrough, so directions on the ground were not walked."),
         "tested": ("Tested in play", "Checked in the running release build with ordinary button presses, on private copies of the playthrough saves. Anything read from the game’s code instead is marked on the page."),
         "fixture": ("Fixture-tested", "Read from the game’s scripts and exercised by the project’s automated tests, which set each stage up directly. Not reached in the natural playthrough.")}
REGION_ORDER = ["johto", "kanto", "hoenn", "far"]
ilink = lambda name: (f'<a href="{u(ITEMS[name]["url"])}">{esc(ITEMS[name]["display"])}</a>' if name in ITEMS else esc(name))
plink = lambda p: f'<a href="{u(p["url"])}">{esc(p["name"])}</a>'


def maplink(mk):
    p = MAP_PLACE.get(mk)
    return f'<a href="{u(p["url"])}#m-{world[mk]["slug"]}">{esc(world[mk]["name"])}</a>' if p else esc(world[mk]["name"])


def basis_tag(b):
    lab, tip = BASIS[b]
    return f'<span class="basis b-{b}" title="{esc(tip)}">{lab}</span>'


# ============================================================ 1-2  HOME (new / returning)
def build_home():
    rel = next(r for r in RELEASES["releases"] if r["version"] == RELEASES["current"])
    legs = ""
    for rid, r in REGIONS.items():
        js = [j for j in JOURNEY if j["r"] == rid]
        tk = "".join(f'<a href="{jhref(j)}" data-ch="{j["k"]}" class="{"gym" if j["ch"].get("badge") else ""}" data-tip="{j["n"]:02d} · {esc(j["title"] if not j["ch"].get("spoiler") else r["name"] + " chapter")}" aria-label="Chapter {j["n"]}"></a>' for j in js)
        legs += f'<div class="leg-s" style="--n:{len(js)}"><b>{r["name"]}</b><div class="ticks">{tk}</div></div>'
    region_line = '<p class="regline" data-now="badges"></p>'
    new = (f'<div data-if="none"><p class="label accent">New here</p><h1>Play Project Blonde</h1><p class="meta">Johto, Kanto and Hoenn in one Game Boy Advance adventure</p>'
           f'<p class="goal">Get it running on your phone or computer, then follow a guide written from a complete playthrough of this game.</p>'
           f'<div class="actions"><a class="btn" href="{u("/play/")}">Get started{ARROW}</a><a class="link" href="{u(JOURNEY[0]["url"])}">Already playing? Start at Chapter 1</a></div>'
           f'<nav class="quiet" aria-label="Discover"><a href="{u("/about/")}">What is Project Blonde?</a><a href="{u("/walkthrough/")}">The walkthrough</a><a href="{u("/world/")}">Explore the world</a></nav></div>')
    stage = '<div class="wm mini" data-home-map hidden>' + town_map("jk", []) + town_map("hoenn", []) + '<span class="you"></span></div>'
    counts = f'{TOTAL} chapters · {len(PAGES):,} Pokémon · {len(PLACES)} places · {len(TRAINER_PAGE_LIST)} major battles'
    body = f"""
<section class="hero">{plate("new-bark-town", cls="p-new")}<div class="plate p-pos" data-pos-plate aria-hidden="true"><img alt="" data-plates="{u("/assets/game/plates/")}"><div class="mist"></div></div>
 <div class="wrap"><div class="hero-text now">{now_known(extra=region_line)}{new}</div>{stage}</div>
</section>
<section class="rail"><div class="wrap">
 <header class="rowhead"><p class="label">The road</p><p class="readout" data-readout data-default="{TOTAL} chapters · Johto to Kanto by sea · Kanto to Hoenn by road">{TOTAL} chapters · Johto to Kanto by sea · Kanto to Hoenn by road</p></header>
 <div class="legs">{legs}</div>
</div></section>
<section class="finder"><div class="wrap">
 <button class="big" data-search-open>{SEARCH}<span>Find a place, a Pokémon, a Trainer, an item…</span><kbd>/</kbd></button>
 <p class="aside" data-if="known">Stuck somewhere? <a href="{u("/stuck/")}">Get unstuck</a>. Setting up a new device? <a href="{u("/play/")}">Download &amp; Play</a>.</p>
 <p class="aside" data-if="none">{counts}. Written for {esc(VERSION)}.</p>
 <nav class="homelinks" aria-label="Sections"><a href="{u("/walkthrough/")}"><b>Walkthrough</b><span>{TOTAL} chapters in order</span></a><a href="{u("/pokemon/")}"><b>Pokédex</b><span>Where to find every Pokémon</span></a>
  <a href="{u("/world/")}"><b>World atlas</b><span>{BUILD["maps"]} area maps</span></a><a href="{u("/trainers/")}"><b>Trainers</b><span>Leaders, rivals, bosses</span></a>
  <a href="{u("/items/")}"><b>Items &amp; HMs</b><span>Every pick-up and shop</span></a><a href="{u("/items/mega-stones/")}"><b>Mega Stones</b><span>All {len(MEGASTONES["offered"])} and how to get them</span></a>
  <a href="{u("/features/")}"><b>Features</b><span>How this game differs</span></a><a href="{u("/stuck/")}"><b>Stuck?</b><span>Next step from where you are</span></a></nav>
</div></section>"""
    write("/", layout("", body, desc="The companion guide to Pokémon Project Blonde: play it, follow the road, find anything.", path="/home", dock="none"))


# ============================================================ 3  WALKTHROUGH - THE ROAD
def road_leg(rid):
    r = REGIONS[rid]
    rows = ""
    for j in (x for x in JOURNEY if x["r"] == rid):
        ch = j["ch"]
        cls = " ".join(filter(None, ["gym" if ch.get("badge") else "", "league" if ch.get("league") else ""]))
        tag = f'<span class="m">{esc(ch["badge"])}</span>' if ch.get("badge") else (f'<span class="m">{esc(ch["milestone"])}</span>' if ch.get("milestone") else "")
        rows += f'<li id="ch-{j["n"]}" class="{cls}" data-ch="{j["k"]}"><span class="dot"></span><span class="n">{j["n"]:02d}</span><a class="t" href="{u(j["url"])}">{esc(ch["title"])}</a>{tag}</li>'
    bl = ""
    if BADGES[rid]:
        pips = "".join(f'<i data-seg="{i}"></i>' for i in BADGES[rid])
        bl = f'<span class="badgeline"><span class="d">{pips}</span><span data-count="{",".join(BADGES[rid])}">0 of {len(BADGES[rid])} Badges</span></span>'
    return f'<section class="leg" id="{rid}" data-region="{rid}" data-view="{r.get("map") or "none"}"><header><h2><i></i>{r["name"]}</h2>{bl}</header><p class="legblurb">{esc(r["blurb"])}</p><ol class="road">{rows}</ol></section>'


def crossing(rid):
    x = chapmap["crossings"][rid]
    img = f'<img src="{u("/assets/game/plates/" + x["plate"] + ".jpg")}" alt="" loading="lazy">' if x.get("plate") else ""
    text = f'<span class="blur" tabindex="0" role="button" aria-label="Reveal spoiler">{esc(x["text"])}</span>' if x.get("spoiler") else esc(x["text"])
    cls = "major" if rid == "hoenn" else ("plain" if not x.get("plate") else "")
    return (f'<div class="crossing {cls}" data-view="{"jk" if rid != "postgame" else "none"}">{img}<div><p class="label">Crossing</p><h3>{esc(x["title"])}</h3><p>{text}</p>'
            f'<p class="fromto"><span>{esc(x["from"])}</span><b>{esc(x["to"])}</b></p></div></div>')


def road_stage():
    layers = ""
    for key in ("jk", "hoenn"):
        dots = [(j["xy"][0], j["xy"][1], f'data-leg="{j["r"]}" data-ch="{j["k"]}"', j["title"]) for j in JOURNEY if j["map"] == key and j["xy"]]
        layers += town_map(key, dots)
    return (f'<aside class="stage" data-view="jk" data-leg="johto" aria-label="Town Map"><div class="wm">{layers}<span class="you"></span></div>'
            f'<p class="caption"><span data-stage-label>Johto &amp; Kanto · the game\'s Town Map</span><span>stops in chapter order</span></p></aside>')


def build_road():
    first = JOURNEY[0]
    start = (f'<div data-if="none"><p class="label accent">The road starts here</p><h1>{esc(first["ch"]["title"])}</h1><p class="meta">Johto · Chapter 1 of {TOTAL}</p>'
             f'<p class="goal">{esc(first["ch"]["goal"])}</p>'
             f'<div class="actions"><a class="btn" href="{u(first["url"])}">Start reading{ARROW}</a><a class="link" href="{u("/play/")}">Not playing yet?</a></div></div>')
    road = "".join((crossing(rid) if rid in chapmap["crossings"] else "") + road_leg(rid) for rid in REGIONS)
    jumps = "".join(f'<a href="#{rid}">{r["name"]}<span>{sum(1 for j in JOURNEY if j["r"] == rid)} chapters</span></a>' for rid, r in REGIONS.items())
    dock = (f'<nav class="dock two" aria-label="Journey"><a data-now="href" href="{u(first["url"])}"><small data-now="barlabel">Start</small><b data-now="bartitle">{esc(first["title"])}</b></a>'
            f'<details><summary>Jump</summary><div class="sheet"><p class="label">Jump to</p><a data-if="known" data-now="here" href="#ch-1">Where I am<span data-now="short"></span></a>{jumps}</div></details></nav>')
    body = f'<div class="journey">{road_stage()}<div class="roadcol"><div class="now">{now_known()}{start}</div>{road}</div></div>'
    write("/walkthrough/", layout("Walkthrough", body, desc=f"The whole journey in order: {TOTAL} chapters across Johto, Kanto, Hoenn and the postgame.", path="/walkthrough/", dock=dock))
    for rid, r in REGIONS.items():      # short region pages keep the documented URL scheme alive
        js = [j for j in JOURNEY if j["r"] == rid]
        rows = "".join(f'<li class="{"gym" if j["ch"].get("badge") else ""}" data-ch="{j["k"]}"><span class="dot"></span><span class="n">{j["n"]:02d}</span><a class="t" href="{u(j["url"])}">{esc(j["title"])}</a><span class="m">{esc(j["ch"].get("badge") or j["ch"].get("milestone") or "")}</span></li>' for j in js)
        body = head("Walkthrough", r["name"], esc(r["blurb"])) + f'<div class="wrap listpage"><ol class="road flat">{rows}</ol><p><a class="link" href="{u("/walkthrough/")}#{rid}">See it on the road{ARROW}</a></p></div>'
        write("/postgame/" if rid == "postgame" else f"/walkthrough/{rid}/", layout(f'{r["name"]} walkthrough', body, desc=r["blurb"], path="/walkthrough/"))


# ============================================================ 4  CHAPTER
def journey_bar(Jn):
    pv = JOURNEY[Jn["n"] - 2] if Jn["n"] > 1 else None
    nx = JOURNEY[Jn["n"]] if Jn["n"] < TOTAL else None
    link = lambda j, cls: (f'<a class="{cls}" href="{jhref(j)}">{ARROW if cls == "pv" else ""}<span>{esc(j["ch"]["title"])}</span>{ARROW if cls == "nx" else ""}</a>' if j else f'<span class="{cls}"></span>')
    here = u("/walkthrough/#ch-%d" % Jn["n"])
    bar = (f'<nav class="jbar" aria-label="Journey"><div class="wrap">{link(pv, "pv")}<a class="mid" href="{here}"><span>{REGIONS[Jn["r"]]["name"]}</span>'
           f'<span class="ticks">{ticks([j for j in JOURNEY if j["r"] == Jn["r"]], Jn)}</span><span>Chapter {Jn["n"]} of {TOTAL}</span></a>{link(nx, "nx")}</div></nav>')
    return bar, pv, nx, here


def expand_refs():
    """Editorial shorthand in chapter prose: [[region/slug|text]] links another chapter, ||text|| hides a story spoiler until tapped."""
    by_k = {j["k"]: j for j in JOURNEY}

    def fix(s):
        def link(m):
            if not check(m[1] in by_k, f"content links to chapter '{m[1]}', which is not on the road"):
                return m[2]
            return f'<a href="{jhref(by_k[m[1]])}">{m[2]}</a>'
        s = re.sub(r"\[\[([a-z0-9/-]+)\|([^\]]+)\]\]", link, s)
        return re.sub(r"\|\|(.+?)\|\|", r'<span class="blur" tabindex="0" role="button" aria-label="Reveal spoiler">\1</span>', s)

    for j in JOURNEY:
        c = j["ch"]
        c["need"] = [fix(x) for x in c.get("need", [])]
        c["quick"] = [[q[0], fix(q[1])] for q in c["quick"]]
        c["stuck"] = [[q, fix(a)] for q, a in c.get("stuck", [])]
        for s in c["steps"]:
            s["p"] = [fix(x) for x in s["p"]]


def chapter_boss_ids(c):
    return {(v[1] if isinstance(v, list) else v) for b in c.get("bosses", []) for v in b["ids"]}


def build_chapter(Jn):
    c, rid, r = Jn["ch"], Jn["r"], REGIONS[Jn["r"]]
    bar, pv, nx, here = journey_bar(Jn)
    pl = Jn["place"]
    facts = [("Region", r["name"]), ("Where", plink(pl) if pl else "—")]
    if c.get("badge"):
        facts += [("Badge", esc(c["badge"])), ("Gym Leader", esc(c["leader"]))]
    lv = [m["level"] for t in chapter_boss_ids(c) for m in trainer(t)["party"]]
    if lv:
        facts.append(("Boss levels", f"{min(lv)}–{max(lv)}"))
    facts.append(("Evidence", basis_tag(c["basis"])))
    need = "".join(f"<li>{x}</li>" for x in c.get("need", []))
    checks = ""
    if Jn.get("bid"):
        checks += f'<label class="check"><input type="checkbox" data-check="{Jn["bid"]}"><span>{esc(LABEL[Jn["bid"]])}</span></label>'
    quick = "".join(f'<li><b>{q[0]}</b><span>{q[1]}</span></li>' for q in c["quick"])
    outdoor = [m for m in c["maps"] if world[m]["type"] in OUTDOOR or world[m]["type"] in ("underground", "underwater")] or c["maps"]
    cand = [m for m in c["maps"] if world[m].get("img")]
    home_ = [m for m in cand if pl and MAP_PLACE.get(m) is pl and world[m]["type"] != "indoor"]
    mainmap = (home_ or [m for m in cand if world[m]["type"] != "indoor"] or cand or [None])[0]
    bosses = c.get("bosses", [])
    boss_ids = chapter_boss_ids(c)
    wild_maps = [m for m in c["maps"] if m in enc]
    item_rows = [(o["item"], m, "Item ball") for m in c["maps"] for o in world[m]["events"]["objects"] if o.get("item")] + [(h["item"], m, "Hidden") for m in c["maps"] for h in world[m]["events"]["hidden"]]
    tr_maps = [(m, [t for t in world[m]["trainers"] if t not in boss_ids]) for m in c["maps"]]
    tr_maps = [(m, ts) for m, ts in tr_maps if ts]
    shops = [m for m in MARTS if m["map"] in c["maps"]]
    sections = [(s["id"], s["t"]) for s in c["steps"]]
    if bosses: sections.append(("battles", "Battles"))
    if c.get("stuck"): sections.append(("stuck", "If you get stuck"))
    if wild_maps: sections.append(("wild", "Wild Pokémon"))
    if c.get("items") or item_rows: sections.append(("items", "Items"))
    if tr_maps: sections.append(("trainers", "Trainers"))
    sections.append(("places", "Places"))
    toc = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in sections)
    steps = ""
    for n, s in enumerate(c["steps"], 1):
        steps += f'<section class="step" id="{s["id"]}"><p class="label"><b>{n:02d}</b> Walkthrough{" " + basis_tag(s["basis"]) if s.get("basis") else ""}</p><h2>{esc(s["t"])}</h2><div class="prose">' + "".join(f"<p>{p}</p>" for p in s["p"]) + "</div></section>"
    battles = "".join(battle(b) for b in bosses)
    stuck = "".join(f'<details class="qa" id="q-{slug(q)[:48]}"><summary><b>{esc(q)}</b></summary><div><p>{a}</p></div></details>' for q, a in c.get("stuck", []))
    wild = "".join(enc_rows(m) for m in wild_maps)
    key_items = "".join(f'<li data-key><b>{ilink(n)}</b><span>{t}</span></li>' for n, t in c.get("items", []))
    found = "".join(f'<li><b>{ilink(n)}</b><span>{maplink(m)} · {how}</span></li>' for n, m, how in item_rows)
    shop_html = "".join(f'<li><b>{maplink(m["map"])}</b><span>{", ".join(ilink(i) for i in m["items"])}</span></li>' for m in shops)
    trs = "".join(f'<h3>{maplink(m)}</h3><ul class="trainers">{"".join(trainer_row(t) for t in ts)}</ul>' for m, ts in tr_maps)
    places = {}
    for m in c["maps"]:
        if m in MAP_PLACE:
            places.setdefault(MAP_PLACE[m]["id"], MAP_PLACE[m])
    pl_html = "".join(f'<a href="{u(p["url"])}"><small>{p["kind"].rstrip("s") if p["kind"] != "Towns & cities" else "Town"}</small><b>{esc(p["name"])}</b>{ARROW}</a>' for p in places.values())
    nxt = c["next"]
    seg = '<div class="seg" role="group" aria-label="Reading mode"><button data-mode-btn="quick" aria-pressed="false">Quick</button><button data-mode-btn="full" aria-pressed="true">Full</button></div>'
    foot_prev = f'<a href="{jhref(pv)}"><small>Previous · Chapter {pv["n"]}</small><b>{esc(pv["ch"]["title"])}</b></a>' if pv else "<span></span>"
    foot_next = f'<a class="r" href="{jhref(nx)}"><small>Next · Chapter {nx["n"]}</small><b>{esc(nx["ch"]["title"])}</b></a>' if nx else "<span></span>"
    jsheet = (f'<details><summary>Journey</summary><div class="sheet"><p class="label">{r["name"]} · Chapter {Jn["n"]} of {TOTAL}</p>'
              + (f'<a href="{jhref(pv)}">Previous<span>{esc(pv["ch"]["title"])}</span></a>' if pv else "") + (f'<a href="{jhref(nx)}">Next<span>{esc(nx["ch"]["title"])}</span></a>' if nx else "")
              + f'<a href="{here}">See it on the road<span>Chapter {Jn["n"]}</span></a></div></details>')
    dock = f'<nav class="dock four" aria-label="Chapter">{jsheet}<a href="#route">Route</a><a href="#map">Map</a><details><summary>Contents</summary><div class="sheet"><p class="label">On this page</p><a href="#objective">Objective</a>{toc}<a href="#onward">Next destination</a></div></details></nav>'
    hero = plate(c["plate"]) if c.get("plate") in PLATES else (f'<div class="plate mapplate" aria-hidden="true"><img class="px" src="{u("/assets/game/maps/" + world[mainmap]["slug"] + ".png")}" alt=""><div class="mist"></div></div>' if mainmap else "")
    mapsec = f'<section class="wrap" id="map">{map_viewer(mainmap, caption="Drawn from the game’s own map data. Tile coordinates are shown as x,y from the top-left.")}</section>' if mainmap else '<span id="map"></span>'
    basis_note = "" if c["basis"] == "played" else f'<p class="notice basisnote">{BASIS[c["basis"]][1]}</p>'
    nxt_link = f'<a class="btn" href="{jhref(nx)}">{esc(nx["ch"]["title"])}{ARROW}</a>' if nx else f'<a class="btn" href="{u("/walkthrough/")}">Back to the road{ARROW}</a>'
    body = f"""{bar}
<section class="cfirst">{hero}
 <div class="wrap cgrid">
  <div class="cwhere" id="objective">
   <p class="label">{r["name"]} · Chapter {Jn["n"]} of {TOTAL}</p>
   <h1>{esc(c["title"])}</h1><p class="sub">{esc(c.get("sub", ""))}</p>
   <div class="objective"><p class="label accent">Objective</p><h2>{esc(c["goal"])}</h2>{"<p class=label>You need</p><ul class=plain>" + need + "</ul>" if need else ""}{checks}</div>
   <dl class="kv">{"".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts)}</dl>{basis_note}
  </div>
  <div class="cdo" id="route">
   <div class="rowhead"><p class="label">Quick route</p>{seg}</div>
   <ol class="route">{quick}</ol>
   <a class="then" href="#onward"><small>Then</small><b>{esc(nxt[0])}</b><span>{esc(nxt[1])}</span>{ARROW}</a>
  </div>
 </div>
</section>
{mapsec}
<div class="wrap cbody full-only">
 <aside class="side" aria-label="On this page"><div><p class="label">Full walkthrough</p><nav class="toc">{toc}</nav></div></aside>
 <article class="main">
  {steps}
  {"<section class=step id=battles><p class=label>Important battles</p><h2>Battles</h2>" + battles + "</section>" if battles else ""}
  {"<section class=step id=stuck><p class=label>Common sticking points</p><h2>If you get stuck</h2>" + stuck + "</section>" if stuck else ""}
  {"<section class=step id=wild><div class=rowhead><div><p class=label>Reference</p><h2>Wild Pokémon</h2></div>" + TOD + "</div>" + wild + "</section>" if wild else ""}
  {"<section class=step id=items><p class=label>Reference</p><h2>Items</h2>" + ("<ul class=items>" + key_items + "</ul>" if key_items else "") + ("<h3>On the ground</h3><ul class=items>" + found + "</ul>" if found else "") + ("<h3>Shops</h3><ul class=items>" + shop_html + "</ul>" if shop_html else "") + "</section>" if (key_items or found or shop_html) else ""}
  {"<section class=step id=trainers><p class=label>Reference</p><h2>Trainers</h2><p class=muted>From the game’s trainer data, by area.</p>" + trs + "</section>" if trs else ""}
  <section class="step" id="places"><p class="label">Reference</p><h2>Places in this chapter</h2><div class="chlinks">{pl_html}</div></section>
 </article>
</div>
<section class="wrap onward" id="onward">
 <p class="label">Next destination</p><h2>{esc(nxt[0])}</h2><p class="via">{esc(nxt[1])}</p>
 <div class="actions">{nxt_link}</div>
 <label class="check done-check"><input type="checkbox" data-chapter="{Jn["k"]}"><span>Mark this chapter complete</span></label>
 <p class="muted evline">Source: {esc(c.get("ev", ""))}. Game: {esc(VERSION)}.</p>
 <nav class="pager" aria-label="Chapters">{foot_prev}{foot_next}</nav>
</section>"""
    write(Jn["url"], layout(f'{c["title"]} — {r["name"]} walkthrough', body, desc=c["goal"], path="/walkthrough/", dock=dock,
                            attrs=f'data-has-mode data-mode="full" data-chapter-key="{Jn["k"]}"'))


# ============================================================ 5-6  POKEMON
STATIC_BY = {}
for _s in STATICS:
    STATIC_BY.setdefault(_s["species"], []).append(_s)
RETIRED = {("SPECIES_KYOGRE", "Route19_Cave_hns"), ("SPECIES_GROUDON", "SeafoamIslands_SecretCave_hns"), ("SPECIES_RAYQUAZA", "EmbeddedTower_hns")}
USED_BY = {}
NOCATCH = {(b["species"], b["where"]) for b in AVAIL["report"]["blocked_sources"] if "catching disabled" in b["why"]}
MLABEL = {"wild": "Wild encounter", "static": "Static encounter", "gift": "Gift Pokémon", "egg": "Gift Egg", "trade": "In-game trade", "roamer": "Roaming Pokémon",
          "converter": "Form converter", "evolution": "Evolution", "breeding": "Breeding", "verified": "Event"}
MKEY = {"wild": "wild", "static": "event", "gift": "event", "egg": "event", "trade": "event", "roamer": "event", "converter": "event", "evolution": "evolve", "breeding": "breed"}


def gate_note(mk):
    g = next((g for g in GATED if mk and any(mk.startswith(pre) for pre in g["maps"])), None)
    return g


def progression(d):
    """Earliest point on the road where the game's data offers this Pokémon, and whether every source lies beyond the main story."""
    av = AV[d["id"]]
    maps = [m["map"] for m in av["methods"] if m.get("map") and m["kind"] in ("wild", "static", "gift", "egg", "converter")]
    chs = sorted({MAP_CHAPTER[m]["n"] for m in maps if m in MAP_CHAPTER})
    first = next(j for j in JOURNEY if j["n"] == chs[0]) if chs else None
    gates = [g for g in (gate_note(m) for m in maps) if g]
    return first, gates, maps


def where_summary(d):
    locs = WHERE.get(d["id"], [])
    names = []
    for l in sorted(locs, key=lambda l: -l["rate"]):
        n = MAP_PLACE[l["map"]]["name"] if l["map"] in MAP_PLACE else world[l["map"]]["name"]
        if n not in names:
            names.append(n)
    return names


def how_summary(d):
    """One line for the index: where it is caught, or how else it is obtained. Never 'not available'."""
    av = AV[d["id"]]
    names = where_summary(d)
    if names:
        return ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")
    for m in av["methods"]:
        if m["kind"] in ("static", "gift", "egg", "converter"):
            return f'{MLABEL[m["kind"]]}: {m["where"]}'
        if m["kind"] == "trade":
            return f'In-game trade {m["detail"]}'
        if m["kind"] == "roamer":
            return "Roaming Pokémon"
    ev = next((m for m in av["methods"] if m["kind"] == "evolution"), None)
    if ev:
        return f'Evolve {DEX[ev["from"]]["display_full"]}: {ev["detail"]}'
    br = next((m for m in av["methods"] if m["kind"] == "breeding"), None)
    if br:
        return f'Breed {DEX[br["from"]]["display_full"]} at the Day Care'
    return MLABEL.get(av["kinds"][0], "") if av["kinds"] else ""


def build_pokemon():
    rows = ""
    entries = sorted((DEX[k] for k in PAGES), key=lambda d: (d["dex"], d["num"]))
    for d in entries:
        av = AV[d["id"]]
        names = where_summary(d)
        regions = sorted({map_region(world[m["map"]]) for m in av["methods"] if m.get("map") in world})
        keys = sorted({MKEY[k] for k in av["kinds"]})
        if "wild" not in keys and "event" not in keys:
            keys.append("nowild")
        form = (d.get("regional") or "") + (" alolan" if d.get("regional") == "Alola" else " galarian" if d.get("regional") == "Galar" else " hisuian" if d.get("regional") == "Hisui" else " paldean" if d.get("regional") == "Paldea" else "")
        label = f' <small>{esc(d["regional"])}</small>' if d["kind"] == "regional" else ""
        hay = " ".join([d["display"], form, " ".join(d["types"]), " ".join(names), " ".join(MLABEL[k] for k in av["kinds"])]).lower()
        hay = re.sub(r"[^a-z0-9 ]+", " ", hay.replace("é", "e").replace("♀", " f").replace("♂", " m")) + " " + re.sub(r"[^a-z0-9]+", "", d["display"].lower().replace("é", "e"))
        rows += (f'<li id="{d["slug"]}" data-f="{esc(hay)}" data-r="{" ".join(regions + keys)}">'
                 f'{icon_img(d, 32)}<b><a href="{u("/pokemon/" + d["slug"] + "/")}">{esc(d["display"])}</a>{label}</b>{types(d)}<span class="w">{esc(how_summary(d))}</span></li>')
    n_base, n_reg = sum(1 for d in entries if d["kind"] == "species"), sum(1 for d in entries if d["kind"] == "regional")
    body = head("Pokédex", "Where to find them", f"{len(entries)} Pokémon you can obtain in Project Blonde: {n_base} species and {n_reg} regional forms. Each is here because the game’s own data shows a way to get it: a wild encounter, an event, a gift, a trade, an evolution or an egg. Species the engine defines but the game never offers are left out.",
                f'<p class="headlinks"><a class="link" href="{u("/features/evolution-methods/")}">Trade evolutions without trading{ARROW}</a><a class="link" href="{u("/items/mega-stones/")}">Mega Stones{ARROW}</a><a class="link" href="{u(legend_page.URL)}">Legendary &amp; Mythical guide{ARROW}</a><a class="link" href="{u(dexnav_page.URL)}">Track one with DexNav{ARROW}</a></p>') + f"""
<div class="wrap listpage">
 <div class="filterbar"><label class="field">{SEARCH}<span class="sr">Filter Pokémon</span><input type="search" data-filter-list="#dex" placeholder="Name, type or place — try “pikachu”, “alolan” or “route 119”" autocomplete="off" aria-controls="dex"></label>
  <div class="seg wrapok" role="group" aria-label="Show"><button data-region-filter="" aria-pressed="true">All</button><button data-region-filter="johto" aria-pressed="false">Johto</button><button data-region-filter="kanto" aria-pressed="false">Kanto</button><button data-region-filter="hoenn" aria-pressed="false">Hoenn</button><button data-region-filter="far" aria-pressed="false">Far-off</button><button data-region-filter="wild" aria-pressed="false">Wild</button><button data-region-filter="event" aria-pressed="false">Event, gift or trade</button><button data-region-filter="nowild" aria-pressed="false">Evolution or egg only</button></div>
  <p class="count" data-filter-count aria-live="polite"></p></div>
 <ol class="dex" id="dex">{rows}</ol>
 <p class="empty" data-filter-empty hidden>No Pokémon match that. Check the spelling, clear the filters above, or try a type or part of a place name.</p>
</div>"""
    write("/pokemon/", layout("Pokédex", body, desc=f"The {len(entries)} Pokémon obtainable in Project Blonde, with locations, levels, chances, evolutions and forms.", path="/pokemon/"))
    for d in entries:
        build_species(d)


def family(d):
    root, guard = d, 0
    while root.get("evolves_from") and root["evolves_from"]["from"] in DEX and guard < 6:
        root = DEX[root["evolves_from"]["from"]]; guard += 1
    out, seen = [], set()

    def walk(n, depth=0):
        if n["id"] in seen or depth > 5:
            return
        seen.add(n["id"])
        inner = f'{art_img(n, 64, n["display_full"])}<b>{esc(n["display_full"])}</b>' + ("" if n["id"] in PAGES else "<small class=na>not obtainable</small>")
        out.append(f'<a href="{sp_url(n)}" {"aria-current=true" if n is d else ""}>{inner}</a>' if n["id"] in PAGES else f"<div>{inner}</div>")
        tos = {}
        for e in n["evolves_to"]:
            tos.setdefault(e["to"], []).append(e["how"])
        for to, hows in tos.items():
            if to in DEX and DEX[to]["kind"] in ("species", "regional"):
                out.append(f'<span class="how">{esc(" or ".join(dict.fromkeys(hows)))}</span>')
                walk(DEX[to], depth + 1)
    walk(root)
    return f'<div class="evo">{"".join(out)}</div>' if len(out) > 1 else '<p class="muted">Does not evolve.</p>'


def where_table(d):
    locs = WHERE.get(d["id"], [])
    seen = {}
    for l in locs:
        seen.setdefault((l["map"], l["method"]), {})[l["time"]] = l
    rows, dots = "", {"jk": [], "hoenn": []}
    placed = set()
    for (mp, method), tods in sorted(seen.items(), key=lambda kv: -max(x["rate"] for x in kv[1].values())):
        lo, hi = min(x["min"] for x in tods.values()), max(x["max"] for x in tods.values())
        have = [t for t in TODS if t in tods]
        when = "Any time" if len(have) == len(enc[mp]["tables"][method]) and len(have) > 1 else ", ".join(t.capitalize() for t in have)
        if len(enc[mp]["tables"][method]) == 1:
            when = "Any time"
        rates = sorted({x["rate"] for x in tods.values()})
        rate = f"{rates[0]}%" if len(rates) == 1 else f"{rates[0]}–{rates[-1]}%"
        p = MAP_PLACE.get(mp)
        rows += (f'<tr><td>{maplink(mp)}<small>{REGION_NAME.get(world[mp]["region"], "")}</small></td><td data-l="How">{METHOD[method]}</td><td data-l="Level">{lo if lo == hi else f"{lo}–{hi}"}</td>'
                 f'<td data-l="When">{when}</td><td data-l="Chance">{rate}</td></tr>')
        if p and p["xy"] and p["id"] not in placed:
            placed.add(p["id"])
            dots[p["xy"]["map"]].append((p["xy"]["xy"][0], p["xy"]["xy"][1], 'class="on"', p["name"]))
    return rows, dots


def build_species(d):
    rows, dots = where_table(d)
    locs = WHERE.get(d["id"], [])
    best = max(locs, key=lambda l: l["rate"]) if locs else None
    bestline = f'<p class="bestline"><span class="label">Best chance</span><b>{maplink(best["map"])}</b> · {METHOD[best["method"]].lower()} · {best["time"]} · {best["rate"]}%</p>' if best else ""
    av = AV[d["id"]]
    first, gates, _maps = progression(d)
    how = ""
    for m in av["methods"]:
        k = m["kind"]
        if k == "wild":
            continue
        if k == "evolution":
            pre = DEX[m["from"]]
            txt = f'Evolve {sp_link(pre)}: {esc(m["detail"])}' + (" <small>(link trade only)</small>" if m.get("link_trade_only") else "")
        elif k == "breeding":
            txt = f'Leave {sp_link(DEX[m["from"]])} at the Day Care; the egg hatches into {esc(d["display_full"])}'
        elif k == "converter":
            txt = f'Take {sp_link(DEX[m["from"]])} to Bill’s house on Route 25: the machine there changes it into its regional form'
        elif k == "trade":
            txt = f'An in-game trade {esc(m["detail"])}'
        elif k == "roamer":
            txt = "Roams the region after a story event releases it"
        else:
            where = maplink(m["map"]) if m.get("map") in world else esc(m["where"])
            lv = re.search(r"Lv\. (\d+)", m["detail"])
            txt = f'{where}{" · Level " + lv.group(1) if lv else ""}{" · " + esc(m["form"]) + " form" if m.get("form") else ""}'
            g = gate_note(m.get("map"))
            if g:
                txt += f' <small>(needs {esc(g["needs"])})</small>'
        how += f'<li><b>{MLABEL[k]}</b><span>{txt}</span></li>'
    if rows:
        table = f'<table class="tbl"><thead><tr><th>Place</th><th>How</th><th>Level</th><th>When</th><th>Chance</th></tr></thead><tbody>{rows}</tbody></table>'
    else:
        table = '<p class="muted">Not a wild encounter: no encounter table lists it. It is obtained as shown below.</p>'
    if how:
        table += f'<h3 class="howh">{"Other ways to obtain it" if rows else "How to obtain it"}</h3><ul class="items howlist">{how}</ul>'
    prog = []
    if first:
        prog.append(f'Earliest on the road: <a href="{jhref(first)}">Chapter {first["n"]}, {esc(first["title"]) if not first["ch"].get("spoiler") else REGIONS[first["r"]]["name"]}</a>')
    elif any(k in av["kinds"] for k in ("wild", "static", "gift", "egg")):
        prog.append("Found only in areas outside the walkthrough’s route (see the place pages)")
    if gates:
        prog.append("Some sources need " + ", ".join(dict.fromkeys(g["needs"] for g in gates)))
    kinds_line = " · ".join(MLABEL[k] for k in av["kinds"])
    table += f'<p class="muted availline"><span class="basis b-played">Obtainable</span> {kinds_line}{". " + ". ".join(prog) if prog else ""}. Sources are read from the game’s encounter tables, scripts and evolution data; unless a walkthrough chapter describes one, it was not confirmed by play.</p>'
    table += legend_page.species_link(d)
    figs = ""
    for key, lab in (("jk", "Johto–Kanto"), ("hoenn", "Hoenn")):
        if dots[key]:
            figs += f'<figure class="wherefig"><div class="wm static">{town_map(key, dots[key], label=f"{lab} Town Map with locations marked")}</div><figcaption>{len(dots[key])} place{"s" * (len(dots[key]) != 1)} on the {lab} Town Map</figcaption></figure>'
    st = d["stats"]
    stats = "".join(f'<div><dt>{l}</dt><dd>{st[k]}</dd></div>' for k, l in [("hp", "HP"), ("atk", "Atk"), ("def", "Def"), ("spa", "Sp. Atk"), ("spd", "Sp. Def"), ("spe", "Speed")])
    total = sum(st.values())
    ab = ", ".join(dict.fromkeys(d["abilities"])) or "—"
    hidden = f' · Hidden: {esc(d["hidden_ability"])}' if d.get("hidden_ability") and d["hidden_ability"] not in d["abilities"] else ""
    forms = ""
    regs = REGIONALS.get(d["id"], []) + ([DEX[d["base"]]] if d.get("base") else []) + [x for x in REGIONALS.get(d.get("base"), []) if x is not d]
    if regs:
        regs = [x for x in regs if x["id"] in PAGES]
        if regs:
            forms += '<div class="formrow">' + "".join(f'<a href="{sp_url(x)}">{art_img(x, 64, x["display_full"])}<b>{esc(x["display_full"])}</b><span>{types(x)}</span></a>' for x in regs) + "</div><p class=muted>Regional forms are separate Pokédex entries with their own ways to obtain them.</p>"
    megas = [x for x in FORMS.get(d["id"], []) if x["kind"] == "mega"]
    for x in megas:
        link = next((m for m in MEGAS if m["mega"] == x["id"]), None)
        stone = link and link.get("stone")
        offered = stone and any(o["stone"] == stone for o in MEGASTONES["offered"])
        how = (f'Holds {ilink(stone)}' + ("" if offered else " — <b>not obtainable</b> in the current build") if stone else (f'Knows {esc(link["move"])}' if link else "Form change"))
        xs = x["stats"]
        forms += (f'<div class="megarow">{art_img(x, 64, x["display_full"])}<div><b>{esc(x["display_full"])}</b> {types(x)}<p class="muted">{how} · Ability: {esc(", ".join(dict.fromkeys(x["abilities"])))}'
                  f' · HP {xs["hp"]} / Atk {xs["atk"]} / Def {xs["def"]} / Sp. Atk {xs["spa"]} / Sp. Def {xs["spd"]} / Speed {xs["spe"]}</p></div></div>')
    others = [x for x in FORMS.get(d["id"], []) if x["kind"] == "form"]
    if others:
        forms += '<p class="muted">Other forms in the game’s data: ' + ", ".join(esc(x.get("form_name") or x["display_full"]) for x in others[:24]) + ("…" if len(others) > 24 else "") + ".</p>"
    moves = "".join(f'<li><span>{"Evo" if lv == 0 else lv}</span>{esc(mv)}</li>' for lv, mv in d["moves"])
    used = "".join(f'<li><a href="{u(url)}">{esc(title)}</a> · Lv. {lv}</li>' for title, url, lv in USED_BY.get(d["id"], [])[:12])
    chs = []
    for l in locs:
        j = MAP_CHAPTER.get(l["map"])
        if j and j not in chs:
            chs.append(j)
    chs.sort(key=lambda j: j["n"])
    road = "".join(f'<li><a href="{jhref(j)}#wild">Chapter {j["n"]}, {esc(j["title"])}</a></li>' for j in chs[:6])
    crumb = f'<a href="{u("/pokemon/")}">Pokédex</a>' + (f'<a href="{sp_url(DEX[d["base"]])}">{esc(DEX[d["base"]]["display"])}</a>' if d.get("base") and DEX[d["base"]]["id"] in PAGES else "")
    title = d["display_full"]
    label = (f'{esc(d["regional"])} form · ' if d["kind"] == "regional" else "") + (esc(d.get("category") or "") + " Pokémon")
    body = f"""
<article class="entry"><div class="wrap">
 <nav class="crumbs">{crumb}</nav>
 <header class="entry-head"><div class="art">{art_img(d, 192, title)}</div>
  <div><p class="label">{label}</p><h1>{esc(title)}</h1><p class="typeline">{types(d)}</p><p class="lead">{esc(d.get("text") or "")}</p></div></header>
 <section class="entry-where"><div><p class="label">Where to find</p><h2>In the game</h2>{bestline}{table}</div><div class="figs">{figs}</div></section>
 {"<section><p class=label>Forms</p><h2>Forms and Mega Evolution</h2>" + forms + "</section>" if forms else ""}
 <section class="entry-cols"><div><p class="label">Evolution</p><h2>Family</h2>{family(d)}</div>
  <div><p class="label">In battle</p><h2>Base stats</h2><dl class="statrow">{stats}</dl><p class="muted">Total {total} · Abilities: {esc(ab)}{hidden} · Catch rate {d["catch_rate"]}</p></div></section>
 <section class="entry-cols">{"<div><p class=label>On the road</p><h2>Where it turns up</h2><ul class=plain>" + road + "</ul></div>" if road else ""}{"<div><p class=label>Opponents</p><h2>Who uses it</h2><ul class=plain>" + used + "</ul></div>" if used else ""}</section>
 {"<section><details class=spoiler><summary>Level-up moves (" + str(len(d["moves"])) + ")</summary><ol class=movelist>" + moves + "</ol><p class=muted>Any of these can be relearned for free with START Relearn.</p></details></section>" if moves else ""}
</div></article>"""
    write(f"/pokemon/{d['slug']}/", layout(title, body, desc=f"Where to find {title} in Project Blonde, with levels, chances, evolution and forms.", path="/pokemon/"))


# ============================================================ 7-8  TRAINERS
TRAINER_PAGE_LIST = []      # [(url, boss, journey)]
GROUPS = [("Gym Leaders", {"LEADER"}), ("Elite Four & Champions", {"ELITE FOUR", "CHAMPION"}), ("Rivals & friends", {"PKMN TRAINER"}),
          ("Team Rocket, Aqua & Magma", {"ROCKET ADMIN", "AQUA LEADER", "MAGMA LEADER", "AQUA ADMIN", "MAGMA ADMIN"}), ("Other story battles", set())]


def boss_trainers(b):
    return [trainer(v[1] if isinstance(v, list) else v) for v in b["ids"]]


def index_trainers():
    used = set()
    for j in JOURNEY:
        for b in j["ch"].get("bosses", []):
            s = b["id"]
            reg = j["r"]
            url = f"/trainers/{reg}/{s}/"
            check(url not in used, f"duplicate trainer page {url}")
            used.add(url)
            TRAINER_PAGE_LIST.append((url, b, j))
            for t in boss_trainers(b):
                TRAINER_PAGE.setdefault(t["id"], url)
                for m in t["party"]:
                    d = sp(m["species"])
                    pg = page_of(d) if d else None
                    if pg:
                        USED_BY.setdefault(pg["id"], []).append((b["title"], url, m["level"]))


def build_trainers():
    sections = ""
    for gname, classes in GROUPS:
        rows = ""
        for url, b, j in TRAINER_PAGE_LIST:
            ts = boss_trainers(b)
            cls = ts[0]["class"]
            if (classes and cls not in classes) or (not classes and any(cls in c for _, c in GROUPS if c)):
                continue
            lv = [m["level"] for t in ts for m in t["party"]]
            sizes = sorted({len(t["party"]) for t in ts})
            megas = any(any(x.get("stone") == m.get("item") for x in MEGAS) for t in ts for m in t["party"])
            rows += (f'<li id="{b["id"]}" data-ch="{j["k"]}" data-f="{esc((b["title"] + " " + j["title"] + " " + REGIONS[j["r"]]["name"]).lower())}" data-r="{j["r"]}"><span class="pic">{trainer_pic(ts[0], 48)}</span><span class="n">{j["n"]:02d}</span>'
                     f'<b><a href="{u(url)}">{esc(b["title"])}</a></b><span class="w">{esc(b.get("place") or j["title"])}</span>'
                     f'<span class="w">{"–".join(map(str, sizes))} Pokémon · Lv. {min(lv)}–{max(lv)}{" · Mega" if megas else ""}</span><span class="m">Chapter {j["n"]}</span></li>')
        if rows:
            sections += f'<section class="leg kind"><header><h2>{gname}</h2></header><ol class="people">{rows}</ol></section>'
    body = head("Trainers", "Who stands in your way", f"{len(TRAINER_PAGE_LIST)} major battles in the order the road meets them: Gym Leaders, the Elite Four and Champions, rivals, team bosses and rematches. Teams are read from the game’s trainer tables. Ordinary Trainers are listed on each place’s page.") + f"""
<div class="wrap listpage">
 <div class="filterbar"><label class="field">{SEARCH}<span class="sr">Filter Trainers</span><input type="search" data-filter-list=".people" placeholder="A name, a place or a region" autocomplete="off"></label>
  <div class="seg wrapok" role="group" aria-label="Region"><button data-region-filter="" aria-pressed="true">All</button><button data-region-filter="johto" aria-pressed="false">Johto</button><button data-region-filter="kanto" aria-pressed="false">Kanto</button><button data-region-filter="hoenn" aria-pressed="false">Hoenn</button><button data-region-filter="postgame" aria-pressed="false">Postgame</button></div><p class="count" data-filter-count></p></div>
 {sections}<p class="empty" data-filter-empty hidden>No Trainer matches that.</p></div>"""
    write("/trainers/", layout("Trainers", body, desc="Every Gym Leader, Elite Four member, Champion, rival and boss in Project Blonde with full teams.", path="/trainers/"))
    for i, (url, b, j) in enumerate(TRAINER_PAGE_LIST):
        ts = boss_trainers(b)
        t0 = ts[0]
        c = j["ch"]
        pz = prize(t0)
        maps = list(dict.fromkeys(m for t in ts for m in TRAINER_MAPS.get(t["id"], [])))
        where = b.get("place") or (", ".join(world[m]["name"] for m in maps[:2]) if maps else "Not confirmed")
        kv = [("Where", esc(where) + (" · " + ", ".join(maplink(m) for m in maps[:2]) if maps else "")),
              ("When", f'{REGIONS[j["r"]]["name"]} · <a href="{jhref(j)}#battles">Chapter {j["n"]}, {esc(j["title"])}</a>'),
              ("Requires", "; ".join(c.get("need", [])) or "—"),
              ("Format", ("Double Battle" if t0["double"] else "Single Battle") + f' · {len(t0["party"])} Pokémon'),
              ("Class", esc(tclass(t0)))]
        if b.get("rewards"):
            kv.append(("Reward", ", ".join(ilink(canon_item(x)) if canon_item(x) in ITEMS else esc(x) for x in b["rewards"])))
        if pz:
            kv.append(("Prize money", f"¥{pz:,}"))
        kv.append(("Evidence", basis_tag(c["basis"])))
        pvb, nxb = (TRAINER_PAGE_LIST[i - 1] if i else None), (TRAINER_PAGE_LIST[i + 1] if i + 1 < len(TRAINER_PAGE_LIST) else None)
        adj = lambda x, lab, cls="": (f'<a class="{cls}" href="{u(x[0])}"><small>{lab}</small><b>{esc(x[1]["title"])}</b></a>' if x else "<span></span>")
        body = f"""
<article class="entry person"><div class="wrap">
 <nav class="crumbs"><a href="{u("/trainers/")}">Trainers</a><span>{REGIONS[j["r"]]["name"]}</span></nav>
 <header class="entry-head"><div class="art portrait">{trainer_pic(t0, 192)}</div>
  <div><p class="label">{esc(tclass(t0))}</p><h1>{esc(b["title"])}</h1>
  <dl class="kv wide">{"".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in kv)}</dl></div></header>
 <section>{battle(dict(b, nolink=True, id="team"), "h2")}</section>
 <p class="muted">Team, levels, held items, abilities and moves are read from the trainer tables of {esc(VERSION)}. Where no moves are listed the Pokémon uses its latest level-up moves.</p>
 <nav class="pager" aria-label="Battles">{adj(pvb, "Previous battle")}{adj(nxb, "Next battle", "r")}</nav>
</div></article>"""
        write(url, layout(f'{b["title"]} — {b.get("place") or j["title"]}', body, desc=f'{b["title"]}: team, levels, moves and rewards in Project Blonde.', path="/trainers/"))


# ============================================================ 9-10  WORLD
def build_world():
    panels = {"jk": "", "hoenn": ""}
    dots = {"jk": [], "hoenn": []}
    for p in PLACES.values():
        if p["xy"]:
            dots[p["xy"]["map"]].append((p["xy"]["xy"][0], p["xy"]["xy"][1], f'data-place="{p["slug"]}" class="link"', p["name"]))
    for key, regions in (("jk", ("johto", "kanto", "far")), ("hoenn", ("hoenn",))):
        for kind in KIND_ORDER:
            ps = sorted([p for p in PLACES.values() if p["kind"] == kind and p["region"] in regions], key=lambda p: (REGION_ORDER.index(p["region"]), [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p["name"])]))
            rows = ""
            for p in ps:
                bits = [f'{len(p["maps"])} area{"s" * (len(p["maps"]) != 1)}']
                if p["wild"]: bits.append(f'{len(p["wild"])} wild Pokémon')
                if p["items"]: bits.append(f'{len(p["items"])} items')
                if p["trainers"]: bits.append(f'{len(p["trainers"])} Trainers')
                rows += f'<li id="{p["slug"]}" data-place="{p["slug"]}" data-f="{esc(p["name"].lower() + " " + REGION_NAME[p["region"]].lower())}" data-r="{p["region"]}"><b>{plink(p)}</b><span class="w">{REGION_NAME[p["region"]]}</span><span class="w">{" · ".join(bits)}</span></li>'
            if rows:
                panels[key] += f'<section class="kind"><h2>{kind}<small>{len(ps)}</small></h2><ol class="places">{rows}</ol></section>'
    body = f"""
<div class="journey atlas"><aside class="stage" data-view="jk" data-leg="all" aria-label="Town Map"><div class="wm">{town_map("jk", dots["jk"])}{town_map("hoenn", dots["hoenn"])}</div>
  <p class="caption"><span data-stage-label>Johto &amp; Kanto · the game's Town Map</span><span data-place-readout>{len(PLACES)} places</span></p></aside>
 <div class="roadcol"><div class="now"><p class="label">World atlas</p><h1>What is here?</h1><p class="goal">Every place in the game with its area maps, wild Pokémon, items, Trainers and shops, read from the game’s own data. {BUILD["maps"]} maps in {len(PLACES)} places.</p></div>
  <div class="filterbar"><label class="field">{SEARCH}<span class="sr">Filter places</span><input type="search" data-filter-list=".places" placeholder="Find a place" autocomplete="off"></label>
   <div class="seg" role="group" aria-label="Map"><button data-atlas="jk" aria-pressed="true">Johto, Kanto &amp; far-off</button><button data-atlas="hoenn" aria-pressed="false">Hoenn</button></div></div>
  <div data-atlas-panel="jk">{panels["jk"]}</div>
  <div data-atlas-panel="hoenn" hidden>{panels["hoenn"]}</div>
  <p class="empty" data-filter-empty hidden>No place matches that.</p>
 </div></div>"""
    write("/world/", layout("World atlas", body, desc="An atlas of Project Blonde: every place on the Town Map and what is there.", path="/world/"))
    for p in PLACES.values():
        build_place(p)


DIRN = {"up": "North", "down": "South", "left": "West", "right": "East", "dive": "Dive", "emerge": "Surface"}


def rich(mk):
    m = world[mk]
    return (m["type"] != "indoor" or mk in enc or m["trainers"] or any(o.get("item") for o in m["events"]["objects"]) or m["events"]["hidden"]
            or sum(1 for w in m["events"]["warps"] if w["to"] == mk) >= 6)


def build_place(p):
    conns, seen = "", set()
    for mk in p["maps"]:
        for c in world[mk]["connections"]:
            to = c["to"]
            if to and to in MAP_PLACE and MAP_PLACE[to] is not p and (c["dir"], MAP_PLACE[to]["id"]) not in seen:
                seen.add((c["dir"], MAP_PLACE[to]["id"]))
                conns += f'<div><dt>{DIRN.get(c["dir"], c["dir"])}</dt><dd>{plink(MAP_PLACE[to])}</dd></div>'
    inside = {}
    for mk in p["maps"]:
        for w in world[mk]["events"]["warps"]:
            to = w["to"]
            if to and to in MAP_PLACE and MAP_PLACE[to] is not p:
                inside.setdefault(MAP_PLACE[to]["id"], MAP_PLACE[to])
    doors = "".join(f'<div><dt>Door</dt><dd>{plink(x)}</dd></div>' for x in list(inside.values())[:8])
    services = [s for s, pat in (("Pokémon Center", r"Pok.mon ?Center|Pokecenter"), ("Poké Mart", r"Mart\b|Department|Shop"), ("Gym", r"Gym")) if any(re.search(pat, world[m]["name"]) for m in p["maps"])]
    chs = "".join(f'<a href="{jhref(j)}"><small>Chapter {j["n"]}</small><b>{esc(j["ch"]["title"]) if not j["ch"].get("spoiler") else "A later chapter"}</b>{ARROW}</a>' for j in p["chapters"])
    fig = ""
    if p["xy"]:
        key = p["xy"]["map"]
        fig = f'<figure class="wherefig"><div class="wm static">{town_map(key, [(p["xy"]["xy"][0], p["xy"]["xy"][1], "class=on", p["name"])], label=p["name"] + " on the Town Map")}</div><figcaption>On the {"Hoenn" if key == "hoenn" else "Johto–Kanto"} Town Map{" (shown at " + esc(p["xy_from"]) + ", which leads here)" if p.get("xy_from") else ""}</figcaption></figure>'
    secs, plain, toc = "", [], ""
    for mk in p["maps"]:
        m = world[mk]
        if not rich(mk):
            st0 = "".join(f' · {sp(x["species"])["display_full"] if sp(x["species"]) else x["species"]} ({ {"battle": "fixed encounter", "gift": "gift", "egg": "egg"}[x["kind"]]}{", Lv. " + str(x["level"]) if x["level"] and x["level"] > 1 else ""})' for x in STATICS if x["map"] == mk)
            gifts = sorted({i["display"] for i in ITEMS.values() for sx in i["sources"] if sx["map"] == mk and sx["how"] == "gift"})
            plain.append(f'<span id="m-{m["slug"]}">{esc(m["name"])}{esc(st0)}{" · gives " + esc(", ".join(gifts)) if gifts else ""}</span>')
            continue
        items = "".join(f'<li><b>{ilink(o["item"])}</b><span>Item ball · tile {o["x"]},{o["y"]}</span></li>' for o in m["events"]["objects"] if o.get("item")) + \
                "".join(f'<li><b>{ilink(h["item"])}</b><span>Hidden · tile {h["x"]},{h["y"]}</span></li>' for h in m["events"]["hidden"])
        trs = "".join(trainer_row(t) for t in m["trainers"])
        shop = "".join(f'<li><b>Shop</b><span>{", ".join(ilink(i) for i in s["items"])}</span></li>' for s in MARTS if s["map"] == mk)
        st = "".join(f'<li><b>{sp_link(sp(s["species"])) if sp(s["species"]) else esc(s["species"])}</b><span>{ {"battle": "Fixed encounter", "gift": "Gift", "egg": "Egg"}[s["kind"]]}{", Level " + str(s["level"]) if s["level"] and s["level"] > 1 else ""}{" — retired" if (s["species"], mk) in RETIRED else ""}{" — a training or boss battle; it cannot be caught here" if (s["species"], mk) in NOCATCH else ""}</span></li>' for s in STATICS if s["map"] == mk)
        toc += f'<a href="#m-{m["slug"]}">{esc(m["name"])}</a>'
        secs += (f'<section class="area" id="m-{m["slug"]}"><p class="label">{esc(m["type"].replace("_", " ") or "area")} · {m["w"]}×{m["h"]} tiles</p><h2>{esc(m["name"])}</h2>{"<p class=notice>No warp, connection or script in the current game leads to this map. Its data is shown for reference only; nothing here counts as obtainable.</p>" if mk in UNREACHABLE else ""}{map_viewer(mk)}'
                 f'{enc_rows(mk, "Wild Pokémon")}'
                 f'{"<h3>Items</h3><ul class=items>" + items + shop + "</ul>" if items or shop else ""}'
                 f'{"<h3>Fixed encounters and gifts</h3><ul class=items>" + st + "</ul>" if st else ""}'
                 f'{"<h3>Trainers</h3><ul class=trainers>" + trs + "</ul>" if trs else ""}</section>')
    for mk in p["maps"]:      # shops in plain interiors still matter
        if not rich(mk):
            for s in MARTS:
                if s["map"] == mk:
                    secs += f'<section class="area" id="shop-{world[mk]["slug"]}"><p class="label">Shop</p><h2>{esc(world[mk]["name"])}</h2><ul class="items one"><li><b>Sells</b><span>{", ".join(ilink(i) for i in s["items"])}</span></li></ul></section>'
    any_enc = any(mk in enc for mk in p["maps"])
    body = f"""
<article class="entry place"><div class="wrap">
 <nav class="crumbs"><a href="{u("/world/")}">World</a><span>{REGION_NAME[p["region"]]}</span></nav>
 <header class="entry-head nomedia"><div><p class="label">{p["kind"]} · {REGION_NAME[p["region"]]}</p><h1>{esc(p["name"])}</h1>
   <dl class="kv wide">{"<div><dt>Services</dt><dd>" + ", ".join(services) + "</dd></div>" if services else ""}{conns}{doors}<div><dt>In the data</dt><dd>{len(p["maps"])} area{"s" * (len(p["maps"]) != 1)} · {len(p["wild"])} wild Pokémon · {len(p["items"])} items · {len(p["trainers"])} Trainers</dd></div></dl></div>{fig}</header>
 {"<section class=inwalk><p class=label>On the road</p><div class=chlinks>" + chs + "</div></section>" if chs else "<p class=muted>No walkthrough chapter passes through here; this page is built from game data alone.</p>"}
 {legend_page.place_note(p)}
 {"<nav class=areanav aria-label=Areas>" + toc + "</nav>" if toc.count("<a") > 1 else ""}
 {"<div class=rowhead><p class=label>Time of day for every table on this page</p>" + TOD + "</div>" if any_enc else ""}
 {dexnav_page.place_line(any(m in ("walk", "surf") for mk in p["maps"] if mk in enc for m in enc[mk]["tables"]))}
 {secs}
 {"<section><p class=label>Also here</p><ul class='plain alsohere muted'>" + "".join(f"<li>{x}</li>" for x in plain) + "</ul></section>" if plain else ""}
</div></article>"""
    write(p["url"], layout(f'{p["name"]} — {REGION_NAME[p["region"]]}' + (f' ({p["id"]})' if p["slug"].endswith(str(p["id"])) else ""), body, desc=f'{p["name"]}: area maps, wild Pokémon, items, Trainers and shops in Project Blonde.', path="/world/"))


# ============================================================ 11-12  ITEMS + MEGA STONES
HOWLAB = {"ball": "Item ball", "hidden": "Hidden item", "gift": "Given by someone here", "shop": "Sold"}
PRICE = {}


def item_summary(i):
    places = list(dict.fromkeys(s["place"]["name"] for s in i["sources"]))
    if places:
        return ", ".join(places[:2]) + (f" +{len(places) - 2}" if len(places) > 2 else "")
    if i.get("notes"):
        return i["notes"][0]["chapter"]["title"]
    if i.get("mega"):
        return "Elm’s lab aide" if any(o["stone"] == i["name"] for o in MEGASTONES["offered"]) else "Not obtainable"
    return ""


def build_items():
    for o in MEGASTONES["defined"]:      # every Mega Stone gets a row and a page, obtainable or not
        if o["stone"] in {m["stone"] for m in MEGAS if m.get("stone")}:
            ITEMS.setdefault(o["stone"], {"name": o["stone"], "sources": [], "mega": next(m for m in MEGAS if m.get("stone") == o["stone"]), "desc": None, "pocket": "Mega Stones",
                                          "slug": slug(o["stone"]), "display": o["stone"], "url": f'/items/{slug(o["stone"])}/'})
    order = ["Key Items", "TMs & HMs", "Mega Stones", "Items", "Medicine", "Poké Balls", "Berries", "Battle items"]
    pockets = sorted({i["pocket"] for i in ITEMS.values()}, key=lambda p: (order.index(p) if p in order else 99, p))
    rows = ""
    for i in sorted(ITEMS.values(), key=lambda i: i["display"]):
        n = len(i["sources"]) + len(i.get("notes", []))
        places = " ".join(dict.fromkeys(s["place"]["name"] for s in i["sources"]))
        rows += (f'<li id="{i["slug"]}" data-f="{esc((i["display"] + " " + i["pocket"] + " " + places).lower())}" data-r="{esc(i["pocket"])}"><b><a href="{u(i["url"])}">{esc(i["display"])}</a></b><span class="w">{esc(i["pocket"])}</span>'
                 f'<span class="w">{esc(item_summary(i))}</span><span class="m">{n} source{"s" * (n != 1)}</span></li>')
    chips = '<button data-region-filter="" aria-pressed="true">All</button>' + "".join(f'<button data-region-filter="{esc(p)}" aria-pressed="false">{esc(p)}</button>' for p in pockets)
    n_ball = sum(1 for i in ITEMS.values() for s in i["sources"] if s["how"] in ("ball", "hidden"))
    body = head("Items", "Where do I get it?", f'{len(ITEMS)} items with {n_ball} pick-ups on the ground, plus gifts and the stock of {len({m["map"] for m in MARTS})} shops, read from the game. Key gifts are described in the chapter where they happen.',
                f'<p class="headlinks"><a class="link" href="{u("/items/mega-stones/")}">Mega Stones{ARROW}</a><a class="link" href="{u("/features/shared-hms/")}">How HMs work{ARROW}</a></p>') + f"""
<div class="wrap listpage">
 <div class="filterbar"><label class="field">{SEARCH}<span class="sr">Filter items</span><input type="search" data-filter-list="#items" placeholder="Item or place — try “surf” or “lilycove”" autocomplete="off"></label>
  <div class="seg wrapok" role="group" aria-label="Pocket">{chips}</div><p class="count" data-filter-count></p></div>
 <ol class="itemlist flat" id="items">{rows}</ol><p class="empty" data-filter-empty hidden>Nothing matches that.</p>
</div>"""
    write("/items/", layout("Items", body, desc="Every item pick-up, gift and shop in Project Blonde.", path="/items/"))
    for i in ITEMS.values():
        build_item(i)
    build_megastones()


def build_item(i):
    by_how = {}
    for s in i["sources"]:
        by_how.setdefault(s["how"], []).append(s)
    src = ""
    for how in ("gift", "ball", "hidden", "shop"):
        if how in by_how:
            lis = "".join(f'<li><b>{maplink(s["map"])}</b><span>{plink(s["place"])} · {REGION_NAME[s["place"]["region"]]}</span></li>' for s in by_how[how])
            src += f'<h3>{HOWLAB[how]} <small>{len(by_how[how])}</small></h3><ul class="items">{lis}</ul>'
    notes = "".join(f'<li data-key><b><a href="{jhref(n["chapter"])}">Chapter {n["chapter"]["n"]}, {esc(n["chapter"]["title"])}</a></b><span>{n["text"]}</span></li>' for n in i.get("notes", []))
    mg = i.get("mega")
    mega_html = ""
    if mg:
        base, form = DEX[mg["species"]], DEX[mg["mega"]]
        offered = next((o for o in MEGASTONES["offered"] if o["stone"] == i["name"]), None)
        a = MEGA_SRC["aide"]
        users = [t for t in MEGASTONES["held_by_trainers"].get(i["name"], []) if t in TRAINER_PAGE]
        if offered:
            kv = [("Pokémon", f'{sp_link(base)} → {esc(form["display_full"])}'), ("Where", esc(a["where"])), ("Who", esc(a["who"]) + f' · the <b>{offered["list"]} Stones</b> list'),
                  ("Requires", esc(a["requires"])), ("Cost", esc(a["cost"])), ("Missable", esc(a["missable"])), ("Available", esc(a["region"])), ("Other sources", "None in the game’s data: no item ball, hidden item, gift script or shop carries it.")]
        else:
            kv = [("Pokémon", f'{sp_link(base)} → {esc(form["display_full"])}'), ("Status", "<b>Not obtainable.</b> The item is defined in the game, but the aide does not offer it and no item ball, hidden item, gift or shop carries it.")]
        if users:
            kv.append(("Used against you by", ", ".join(dict.fromkeys(f'<a href="{u(TRAINER_PAGE[t])}">{esc(tname(trainer(t)))}</a>' for t in users))))
        mega_html = f'<dl class="kv wide answers">{"".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in kv)}</dl><p><a class="link" href="{u("/items/mega-stones/")}">All Mega Stones{ARROW}</a> <a class="link" href="{u("/features/mega-evolution/")}">How Mega Evolution works{ARROW}</a></p>'
    none = "" if (src or notes or mg) else '<p class="muted">No source was found in the game’s data.</p>'
    hm = f'<p><a class="link" href="{u("/features/shared-hms/")}">How HMs work in Project Blonde{ARROW}</a></p>' if i["name"].startswith("HM") else ""
    body = f"""
<article class="entry"><div class="wrap">
 <nav class="crumbs"><a href="{u("/items/")}">Items</a><span>{esc(i["pocket"])}</span></nav>
 <header class="entry-head nomedia"><div><p class="label">{esc(i["pocket"])}</p><h1>{esc(i["display"])}</h1>{"<p class=lead>“" + esc(i["desc"]) + "”</p>" if i.get("desc") else ""}</div></header>
 {mega_html}
 {"<section><p class=label>In the walkthrough</p><h2>How you get it</h2><ul class=items>" + notes + "</ul></section>" if notes else ""}
 {"<section><p class=label>From the game’s data</p><h2>Every source</h2>" + src + "</section>" if src else ""}{none}{hm}
</div></article>"""
    write(i["url"], layout(i["display"], body, desc=f'Where to get {i["display"]} in Project Blonde.', path="/items/"))


def build_megastones():
    ring, a = MEGA_SRC["ring"], MEGA_SRC["aide"]
    rj = next(j for j in JOURNEY if j["k"] == ring["chapter"])
    rows = ""
    for o in MEGASTONES["offered"]:
        mg = next(m for m in MEGAS if m.get("stone") == o["stone"])
        base, form = DEX[mg["species"]], DEX[mg["mega"]]
        rows += (f'<li id="{slug(o["stone"])}" data-f="{esc((o["stone"] + " " + base["display"] + " " + " ".join(form["types"]) + " " + o["list"]).lower())}" data-r="{o["list"].lower()}">{icon_img(base, 32)}<b><a href="{u(ITEMS[o["stone"]]["url"])}">{esc(o["stone"])}</a></b>'
                 f'<span class="w">{sp_link(base, form["display_full"])}</span>{types(form)}<span class="w">Elm’s lab aide · {o["list"]} Stones list</span><span class="m ok">Obtainable</span></li>')
    not_rows = ""
    for name in MEGASTONES["not_obtainable"]:
        mg = next((m for m in MEGAS if m.get("stone") == name), None)
        not_rows += f'<li><b>{ilink(name)}</b><span class="w">{esc(DEX[mg["mega"]]["display_full"]) if mg else "No Mega form linked in this build"}</span></li>'
    ck = MEGASTONES["check"]
    documented = len(MEGASTONES["offered"])
    ok = ck["offered_by_aide"] == ck["offered_found_in_rom"] == documented and not ck["offered_without_form_link"]
    diffs = "".join(f"<li>{esc(x)}</li>" for x in MEGA_SRC["differences"])
    body = head("Mega Stones", "Every Mega Stone, and how to get it", f'{documented} Mega Stones can be obtained in Project Blonde. All of them come from one person: the aide in Professor Elm’s lab, free, once you hold the Mega Ring. Nothing below is assumed from the official games.') + f"""
<div class="wrap listpage megapage">
 <section class="q4 three"><section><p class="label"><b>01</b> Get the Mega Ring</p><p><b>{esc(ring["where"])}.</b> {esc(ring["how"])}</p><p><a class="link" href="{jhref(rj)}">Chapter {rj["n"]}, {esc(rj["title"])}{ARROW}</a></p></section>
  <section><p class="label"><b>02</b> Collect stones</p><p><b>{esc(a["where"])}.</b> {esc(a["who"])}. You need: {esc(a["requires"][0].lower() + a["requires"][1:])} {esc(a["cost"])}</p></section>
  <section><p class="label"><b>03</b> Mega Evolve</p><p>Give the stone to the matching Pokémon to hold. In battle open FIGHT, press <b>START</b>, then choose a move. Once per battle; the stone is not used up.</p><p><a class="link" href="{u("/features/mega-evolution/")}">Mega Evolution guide{ARROW}</a></p></section></section>
 <dl class="kv wide answers"><div><dt>Missable?</dt><dd>{esc(a["missable"])}</dd></div><div><dt>Region</dt><dd>{esc(a["region"])}</dd></div><div><dt>Alternative sources</dt><dd>None. The game’s item balls, hidden items, gift scripts and shop lists were all scanned: {ck["other_sources"]} carry a Mega Stone.</dd></div>
  <div><dt>Rayquaza</dt><dd>Needs no stone. It Mega Evolves when it knows Dragon Ascent, which START Relearn teaches for free.</dd></div></dl>
 <div class="filterbar"><label class="field">{SEARCH}<span class="sr">Filter Mega Stones</span><input type="search" data-filter-list="#megas" placeholder="A stone, a Pokémon or a type" autocomplete="off"></label>
  <div class="seg wrapok" role="group" aria-label="List"><button data-region-filter="" aria-pressed="true">All</button><button data-region-filter="kanto" aria-pressed="false">Kanto Stones</button><button data-region-filter="johto" aria-pressed="false">Johto Stones</button><button data-region-filter="hoenn" aria-pressed="false">Hoenn Stones</button></div><p class="count" data-filter-count></p></div>
 <ol class="megalist" id="megas">{rows}</ol><p class="empty" data-filter-empty hidden>No Mega Stone matches that.</p>
 <section><p class="label">Differences</p><h2>How this differs from the official games</h2><ul class="plain bullets">{diffs}</ul></section>
 <section><p class="label">Completeness check</p><h2>Game data against this page</h2>
  <table class="tbl"><tbody><tr><td>Mega Stones defined as items in the game</td><td>{ck["defined"]}</td></tr><tr><td>Offered by Elm’s aide (script lists)</td><td>{ck["offered_by_aide"]}</td></tr>
  <tr><td>Of those, item ids found in the shipped ROM beside the aide’s menus</td><td>{ck["offered_found_in_rom"]}</td></tr><tr><td>Other sources found (item balls, hidden items, gifts, shops)</td><td>{ck["other_sources"]}</td></tr>
  <tr><td>Documented on this page as obtainable</td><td>{documented}</td></tr><tr><td>Result</td><td><b>{"Match: every obtainable stone is documented, and nothing is documented that the game does not give." if ok else "MISMATCH — see the build log"}</b></td></tr></tbody></table>
  <details class="spoiler"><summary>{len(MEGASTONES["not_obtainable"])} Mega Stones exist in the data but cannot be obtained</summary><p class="muted">These items are defined in the game, but no script, shop or pick-up gives them. Some are held by opponents.</p><ol class="megalist plainlist">{not_rows}</ol></details></section>
 <p class="muted evline">Sources: {esc(a["ev"])}; {esc(ring["ev"])}. Game: {esc(VERSION)}.</p>
</div>"""
    check(ok, "Mega Stones: the aide's script lists, the ROM and the site disagree")
    write("/items/mega-stones/", layout("Mega Stones", body, desc="Every obtainable Mega Stone in Project Blonde, where to get it, and how to get the Mega Ring.", path="/items/"))


# ============================================================ 13-14  FEATURES
def trade_evos():
    rows = ""
    for d in sorted(DEX.values(), key=lambda d: d["dex"]):
        if d["kind"] not in ("species", "regional"):
            continue
        tos = {}
        for e in d["evolves_to"]:
            tos.setdefault(e["to"], []).append(e["how"])
        for to, hows in tos.items():
            if any(h.startswith("Trade") for h in hows) and to in DEX:
                alt = [h for h in hows if not h.startswith("Trade")]
                if d["id"] not in PAGES or to not in PAGES:
                    continue
                rows += (f'<tr><td>{sp_link(d)} → {sp_link(DEX[to])}</td><td data-l="By trade">{esc(next(h for h in hows if h.startswith("Trade")))}</td>'
                         f'<td data-l="Without trading">{esc(" or ".join(alt)) if alt else "<b>No alternative in the data</b>"}</td></tr>')
    return f'<table class="tbl"><thead><tr><th>Evolution</th><th>By trade</th><th>Without trading</th></tr></thead><tbody>{rows}</tbody></table>'


def build_features():
    rows = "".join(f'<li id="{f["id"]}"><b><a href="{u("/features/" + f["id"] + "/")}">{f["title"]}</a></b><span class="w wide">{f["blurb"]}</span><span class="m">{BASIS[f["basis"]][0]}</span></li>' for f in FEATURES)
    body = head("Features", "How this game works", "The systems that make Project Blonde its own game. Each guide says what it is, how to use it, when it unlocks and its limits, and whether that was seen in play or read from the game.") + f'<div class="wrap listpage"><ol class="people feat">{rows}</ol></div>'
    write("/features/", layout("Features", body, desc="Guides to Project Blonde’s own systems.", path="/features/"))
    for f in FEATURES:
        if f["id"] == "dexnav":         # the illustrated manual is its own page type
            dexnav_page.build(f, basis_tag(f["basis"]))
            continue
        how = "".join(f"<li>{x}</li>" for x in f["how"])
        table = ""
        if f.get("table"):
            table = '<section><p class="label">Options</p><table class="tbl"><tbody>' + "".join(f"<tr><td><b>{esc(a)}</b></td><td>{b}</td></tr>" for a, b in f["table"]) + "</tbody></table></section>"
        auto = f'<section><p class="label">From the game’s evolution data</p><h2>Every trade evolution and its alternative</h2>{trade_evos()}</section>' if f.get("auto") == "trade-evos" else ""
        more = "".join(f"<p>{x}</p>" for x in f.get("more", []))
        links = "".join(f'<p><a class="link" href="{u(a)}">{esc(b)}{ARROW}</a></p>' for a, b in f.get("links", []))
        body = f"""
<article class="entry guide"><div class="wrap">
 <nav class="crumbs"><a href="{u("/features/")}">Features</a></nav>
 <header class="entry-head nomedia"><div><p class="label">Feature guide · {basis_tag(f["basis"])}</p><h1>{f["title"]}</h1><p class="lead">{f["what"]}</p></div></header>
 <div class="q4"><section><p class="label"><b>01</b> How do I use it?</p><ol class="quick">{how}</ol></section>
  <section><p class="label"><b>02</b> When does it unlock?</p><p>{f["when"]}</p></section>
  <section><p class="label"><b>03</b> Any limits?</p><p>{f["limits"]}</p></section></div>
 {table}{auto}{"<section class=prose><p class=label>Worth knowing</p>" + more + "</section>" if more else ""}{links}
 <p class="muted evline">{esc(BASIS[f["basis"]][1])} Source: {esc(f["ev"])}.</p>
</div></article>"""
        write(f"/features/{f['id']}/", layout(f["title"], body, desc=re.sub(r"<[^>]+>", "", f["blurb"]), path="/features/"))


# ============================================================ 15  STUCK?
def build_stuck():
    qa = ""
    n = 0
    for q in site["stuck"]:
        ans = q.get("a", "") + (f'<p><a class="link" href="{u(q["link"][0])}">{q["link"][1]}{ARROW}</a></p>' if q.get("link") else "")
        qa += f'<details class="qa" id="{q["id"]}" data-ch="" data-f="{esc((q["q"] + " " + q["tags"]).lower())}"><summary><b>{esc(q["q"])}</b><span class="m">Any time</span></summary><div><p>{ans}</p></div></details>'
        n += 1
    for j in JOURNEY:
        for q, a in j["ch"].get("stuck", []):
            qid = f'{j["ch"]["slug"]}-{slug(q)[:40]}'
            f_ = (q + " " + re.sub(r"<[^>]+>", "", a) + " " + j["title"]).lower()
            qa += (f'<details class="qa" id="{qid}" data-ch="{j["k"]}" data-f="{esc(f_)}"><summary><b>{esc(q)}</b><span class="m">Ch. {j["n"]}</span></summary>'
                   f'<div><p>{a}</p><p><a class="link" href="{jhref(j)}">Chapter {j["n"]}, {esc(j["title"])}{ARROW}</a></p></div></details>')
            n += 1
    opts = '<option value="">No Badge yet</option>'
    for rid in ("johto", "kanto", "hoenn"):
        opts += f'<optgroup label="{REGIONS[rid]["name"]}">' + "".join(f'<option value="{j["k"]}">{esc(j["ch"]["badge"])} — {esc(j["ch"]["leader"])}</option>' for j in JOURNEY if j["r"] == rid and j["ch"].get("badge")) + "</optgroup>"
    locs = '<option value="">Choose where you are</option>' + "".join(f'<optgroup label="{r["name"]}">' + "".join(f'<option value="{j["k"]}">{esc(j["title"] if not j["ch"].get("spoiler") else "Chapter " + str(j["n"]) + " (later story)")}</option>' for j in JOURNEY if j["r"] == rid) + "</optgroup>" for rid, r in REGIONS.items())
    body = f"""
<div class="wrap stuck">
 <header><p class="label accent">Stuck?</p><h1>What's stopping you?</h1>
  <label class="field xl">{SEARCH}<span class="sr">Describe the problem</span><input type="search" data-stuck-q placeholder="Type it the way you'd say it — “gym door is blocked”" autocomplete="off"></label></header>
 <div class="stuck-cols">
  <section class="locate"><p class="label">Or start from where you are</p><h2>Where are you?</h2>
   <label class="pick"><span class="label">Place or chapter</span><select data-stuck-chapter aria-label="Where you are">{locs}</select></label>
   <label class="pick"><span class="label">Last Badge earned</span><select data-stuck-badge aria-label="Last Badge earned">{opts}</select></label>
   <p class="hint" data-if="known">Set from your saved position: <b data-now="title"></b>.</p>
   <div class="nextstep" data-nextstep hidden><p class="label accent">Your next step</p><h3 data-ns-title></h3><p data-ns-goal></p><p class="muted" data-ns-need></p><p><a class="btn" data-ns-href href="#">Open the chapter{ARROW}</a></p><p class="muted" data-ns-done></p></div>
   <div class="stretch" data-stretch hidden><p class="label">The road from here</p><ol class="road" data-stretch-list></ol><p class="nextbadge" data-stretch-next></p></div></section>
  <section class="answers"><p class="label" data-answers-label>Common blockers</p><div data-answers>{qa}</div>
   <p class="empty" data-stuck-empty hidden>No written answer matches. <button class="link" data-search-open>Search the whole guide{ARROW}</button></p></section>
 </div>
 <p class="muted evline">{n} answers. Each comes from the chapter it is filed under, written from the completed playthrough; none suggests a route the game has not opened yet at that point.</p>
 <p class="helpline"><span class="muted">Game won’t start, or a save problem?</span><a class="link" href="{u("/play/#trouble")}">Download &amp; Play troubleshooting{ARROW}</a>{discord_link("link dc", "Ask on Discord")}</p>
</div>"""
    need = {j["k"]: [re.sub(r"<[^>]+>", "", x) for x in j["ch"].get("need", [])] for j in JOURNEY}
    extra = f'<script type="application/json" id="needs">{json.dumps(need, ensure_ascii=False, separators=(",", ":"))}</script>'
    write("/stuck/", layout("Stuck?", body + extra, desc="Get unstuck in Project Blonde: ask a question or start from where you are.", path="/stuck/"))
    return n


# ============================================================ 16  PROGRESS
def build_progress():
    opts = "".join(f'<optgroup label="{r["name"]}">' + "".join(f'<option value="{j["k"]}">{j["n"]:02d} · {esc(j["ch"]["title"] if not j["ch"].get("spoiler") else "Chapter " + str(j["n"]))}</option>' for j in JOURNEY if j["r"] == rid) + "</optgroup>" for rid, r in REGIONS.items())
    legs = ""
    for g in site["checklist"]:
        rid = g["id"]
        badges = [i for i in g["items"] if i[0].startswith("badge")]
        other = [i for i in g["items"] if not i[0].startswith("badge")]
        bl = "".join(f'<label class="bcheck"><input type="checkbox" data-check="{i[0]}"><i></i><span class="{"blur" if len(i) > 2 else ""}">{esc(i[1].split(" — ")[0])}<small>{esc(i[1].split(" — ")[1]) if " — " in i[1] else ""}</small></span></label>' for i in badges)
        ol = "".join(f'<label class="check"><input type="checkbox" data-check="{i[0]}"><span class="{"blur" if len(i) > 2 else ""}">{esc(i[1])}</span></label>' for i in other)
        cnt = f'<span class="badgeline"><span data-count="{",".join(b[0] for b in badges)}"></span></span>' if badges else ""
        js = [j for j in JOURNEY if j["r"] == rid]
        chl = "".join(f'<label class="check small"><input type="checkbox" data-chapter="{j["k"]}"><span class="{"blur" if j["ch"].get("spoiler") else ""}">{j["n"]:02d} · {esc(j["title"])}</span></label>' for j in js)
        legs += (f'<section class="leg" data-region="{rid}"><header><h2><i></i>{g["title"]}</h2>{cnt}<span class="badgeline" data-chapcount="{rid}"></span></header><div class="ticks wide">{ticks(js)}</div>'
                 f'{"<div class=bgrid>" + bl + "</div>" if bl else ""}{"<div class=milestones><p class=label>" + ("Objectives" if rid == "postgame" else "Milestones") + "</p>" + ol + "</div>" if ol else ""}'
                 f'<details class="chapdone"><summary>Chapters completed</summary><div class="milestones">{chl}</div></details></section>')
    body = f"""
<div class="wrap progress">
 <header class="now"><div data-if="known"><p class="label accent">You are here</p><h1 data-now="title"></h1><p class="meta" data-now="meta"></p><p class="regline" data-now="badges"></p>
   <div class="actions"><a class="btn" data-now="href" href="{u("/walkthrough/")}">Continue{ARROW}</a></div></div>
  <div data-if="none"><p class="label accent">My progress</p><h1>Where are you on the road?</h1><p class="goal">Open any chapter and the guide remembers it. Or set your position here.</p></div>
  <label class="setpos"><span class="label">Current chapter</span><select data-set-pos><option value="">Not set</option>{opts}</select></label></header>
 {legs}
 <section class="keep"><p class="label">Your data</p><h2>Stays on this device</h2><p class="muted">Progress is stored in this browser only. Nothing is sent anywhere and nothing is synced between devices: to move it, export a file here and import it on the other device. This tracks the guide, not your save file.</p>
  <div class="actions"><button class="btn ghost" data-export>Export progress file</button><label class="btn ghost">Import progress file<input type="file" accept="application/json,.json" data-import class="sr"></label><button class="btn ghost" data-clear>Clear</button><button class="btn ghost" data-spoiler-toggle>Spoilers: hidden</button></div>
  <p class="muted" data-io-msg aria-live="polite"></p></section>
</div>"""
    write("/progress/", layout("My progress", body, desc="Track your chapter, Badges, milestones and postgame objectives. Stored on this device; export and import supported.", path="/progress/", dock="none"))


# ============================================================ 17-18  PLAY
def release_state(rel):
    """The one decision about whether a download may be shown. Anything short of a complete, released record is the pre-release state."""
    dist, dl, pt = RELEASES["distribution"], rel["download"], rel["patch"]
    assert BUILD["build"]["public"].startswith(rel["public_version"]) and BUILD["build"]["version"] == rel["internal_build"], "releases.json does not describe the build the guide was extracted from"
    if rel["status"] != "released":
        assert not dl["url"], "releases.json: a download URL is set but the release is not marked released"
        return "prerelease"
    assert dl["url"] and rel["sha256"] and rel["date"] and dist["method"] in ("direct", "patch"), "releases.json: a released version needs date, download.url, sha256 and a distribution method"
    assert dl["url"].startswith("https://"), "releases.json: download.url must be https"
    if dist["method"] == "patch":
        assert all(pt[k] for k in ("format", "base_game", "base_checksum", "tool", "tool_url")), "releases.json: patch distribution needs every patch field"
    return dist["method"]


def build_play():
    rel = next(r for r in RELEASES["releases"] if r["version"] == RELEASES["current"])
    dist, pt, state = RELEASES["distribution"], rel["patch"], release_state(rel)
    pv, live = esc(rel["public_version"]), state != "prerelease"
    help_dc = discord_link("btn ghost dcbtn", "Ask on Discord")
    # --- current release
    if state == "patch":
        filetype = f'{esc(pt["format"])} patch for {esc(pt["base_game"])}'
        needs = f'Your own copy of {esc(pt["base_game"])} (<code>{esc(pt["base_checksum"])}</code>) and <a href="{esc(pt["tool_url"])}" rel="noopener">{esc(pt["tool"])}</a>'
    else:
        filetype, needs = esc(rel["file"]["type"]), ("Nothing else: one file" if state == "direct" else "Announced with the release")
    rows = [("Game", "Pokémon Project Blonde"), ("Version", f'{pv} <span class="muted">· build {esc(rel["internal_build"])}</span>'), ("Status", esc(rel["status_short"]) + ("" if live else " · not released")),
            ("Released", esc(rel["date"]) if live else "Not announced"), ("File", f'{filetype} · {esc(rel["file"]["size"])}'), ("You need", needs),
            ("SHA-256", f'<code class="sum">{esc(rel["sha256"])}</code>' if live else "Published with the release"),
            ("Saves", esc(rel["save_compatibility_short"]) + f' <a href="#update">How to update</a>'), ("Link version", f'<code>{esc(rel["link_protocol"])}</code>')]
    dl = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in rows)
    hl = "".join(f"<li>{esc(x)}</li>" for x in rel["highlights"])
    # --- the primary action: a real download when released, otherwise the place where the release will be announced
    if live:
        what = "patch" if state == "patch" else "game"
        primary = f'<a class="btn" data-download href="{esc(rel["download"]["url"])}">Download {pv} {what}{ARROW}</a>'
        status_line = f'<b>{pv}</b><span class="chip ok">{esc(rel["status_short"])}</span><span>{esc(rel["date"])}</span>'
        hero_note = esc(dist["notes"][state])
    else:
        primary = discord_link("btn dcbtn", "Get release news on Discord")
        status_line = f'<b>{pv}</b><span class="chip">{esc(rel["status_short"])}</span><span>Not released yet</span>'
        hero_note = "There is no download yet. The release will be announced on the Project Blonde Discord, and the download will appear on this page." if primary else "There is no download yet. It will appear on this page when the release is announced."
    if state == "patch":
        get = (f'<p class="lead">{esc(dist["notes"]["patch"])}</p><ol class="quick">'
               f'<li>Have your own copy of <b>{esc(pt["base_game"])}</b> ready. Its checksum must be <code>{esc(pt["base_checksum"])}</code>.</li>'
               f'<li>Download the Project Blonde {pv} patch ({esc(pt["format"])}): <a data-download href="{esc(rel["download"]["url"])}">{esc(rel["download"]["file_name"] or "download")}</a>.</li>'
               f'<li>Open <a href="{esc(pt["tool_url"])}" rel="noopener">{esc(pt["tool"])}</a>, choose your base game and the patch, and apply it.</li>'
               f'<li>Check that the new .gba file’s SHA-256 is <code class="sum">{esc(rel["sha256"])}</code>.</li><li>Open the new .gba in your emulator: <a href="#devices">device setup</a>.</li></ol>')
    elif state == "direct":
        get = (f'<p class="lead">{esc(dist["notes"]["direct"])}</p><div class="actions">{primary}</div>'
               f'<p class="notice">After downloading, check that the file’s SHA-256 is <code class="sum">{esc(rel["sha256"])}</code>.</p>')
    else:
        get = (f'<p class="lead"><b>{pv} is not released yet.</b> It is a release candidate still being checked, so this page offers no file, and how the game will be distributed has not been announced.</p>'
               f'<p class="notice">When it is released, this step will carry the download, its checksum and any patching steps. Only a file whose checksum matches the one published here is the real release.</p>'
               + (f'<div class="actions">{discord_link("btn ghost dcbtn", "Hear about the release on Discord")}</div>' if DISCORD.get("url") else ""))
    devs = "".join(f'<a href="{u("/play/setup/" + d["id"] + "/")}"><b>{d["name"]}</b><span class="ok">{esc(d["emulator"])}</span>{ARROW}</a>' for d in PLAY["devices"])
    sv, up = PLAY["save"], PLAY["update"]
    cmp_rows = "".join("<tr>" + "".join(f'<td data-l="{l}">{c}</td>' for l, c in zip(["", "How", "Makes", "Portable", "Use it for"], r)) + "</tr>" for r in sv["rows"])
    topics = "".join(f'<div id="{t["id"]}"><p class="label">{esc(t["label"])}</p><h3>{t["title"]}</h3>{"".join(f"<p>{x}</p>" for x in t["text"])}{"<ol class=quick>" + "".join(f"<li>{x}</li>" for x in t["steps"]) + "</ol>" if t.get("steps") else ""}</div>' for t in PLAY["topics"])
    rules = "".join(f"<div><dt>{esc(a)}</dt><dd>{b}</dd></div>" for a, b in up["rules"])
    updev = "".join(f'<details class="qa upd" name="update-device" id="update-{d["id"]}"><summary><b>{esc(d["name"])}</b><span class="m">{esc(d["emulator"])}</span></summary>'
                    f'<div><ol class="quick">{"".join(f"<li>{x}</li>" for x in d["steps"])}</ol><p><a class="link" href="{u("/play/setup/" + d["id"] + "/")}">Full {esc(d["name"])} setup guide{ARROW}</a></p></div></details>' for d in up["devices"])
    notes = "".join(f"<li>{n}</li>" for n in rel["notes"])
    fixed = "".join(f"<li><b>{esc(a)}</b> — {b}</li>" for a, b in RELEASES["fixed"])
    known = "".join(f"<li>{x}</li>" for x in RELEASES["known"])
    trouble = "".join(f'<details class="qa"><summary><b>{a}</b></summary><div><p>{b}</p></div></details>' for a, b in PLAY["trouble"])
    support = (f'<div class="support"><div><p class="label">Still stuck?</p><p>Ask in the {esc(DISCORD["server"])} Discord server. Say which device and emulator you use and which version the title screen shows.</p></div>{help_dc}</div>' if help_dc else "")
    body = f"""
<div class="wrap play" data-release-state="{state}">
 <header class="relhero"><div><p class="label accent">Download &amp; Play</p><h1>Pokémon Project Blonde</h1>
   <p class="relline">{status_line}</p>
   <p class="lead">Johto, Kanto and Hoenn in one Game Boy Advance adventure. Everything you need to get it, play it on your phone or computer, and keep your save safe.</p>
   <div class="actions">{primary}<a class="link" href="#devices">Set up your device{ARROW}</a></div>
   <p class="notice">{hero_note}</p></div>
  <figure class="titleart"><img class="px" src="{u("/assets/game/title/title-" + rel["public_version"] + ".png")}" width="240" height="160" alt="The Project Blonde title screen, showing version {pv} under PRESS START"></figure></header>
 <section id="release" class="relgrid"><div><p class="label">Current release</p><h2>{pv} {esc(rel["status_short"]).lower()}</h2><ul class="plain bullets">{hl}</ul>
   <p><a class="link" href="{u(rel["release_notes_url"])}">Release notes{ARROW}</a></p></div><dl class="kv wide release">{dl}</dl></section>
 <ol class="stages">
  <li id="devices"><p class="label"><b>01</b> Choose your device</p><div class="devices">{devs}</div></li>
  <li id="get"><p class="label"><b>02</b> Get the game</p><div class="getbody">{get}</div></li>
  <li id="go"><p class="label"><b>03</b> Start the journey</p><p class="lead">The road begins in New Bark Town. The guide remembers where you are from the first chapter you open.</p><p><a class="link" href="{u(JOURNEY[0]["url"])}">Chapter 1: {esc(JOURNEY[0]["title"])}{ARROW}</a></p></li>
 </ol>
 <section id="save"><p class="label">Save your game</p><h2>{sv["title"]}</h2><p class="lead">{sv["lead"]}</p>
  <table class="tbl cmp"><thead><tr><th></th><th>How</th><th>What it makes</th><th>Portable?</th><th>Use it for</th></tr></thead><tbody>{cmp_rows}</tbody></table></section>
 <section id="update"><p class="label">Updating</p><h2>{esc(up["title"])}</h2><p class="lead">{up["lead"]}</p>
  <dl class="kv wide rules">{rules}</dl>
  <p class="label pick">Steps for your device</p>{updev}
  <div class="entry-cols aftercare"><div><h3>{esc(up["check_title"])}</h3><ul class="plain bullets">{"".join(f"<li>{x}</li>" for x in up["check"])}</ul><p class="muted">{up["check_after"]}</p></div>
   <div id="rollback"><h3>{esc(up["rollback_title"])}</h3><ol class="quick">{"".join(f"<li>{x}</li>" for x in up["rollback"])}</ol></div></div>
  <p class="notice wide">{up["caveat"]}</p></section>
 <section><p class="label">Keep playing</p><div class="topics">{topics}</div></section>
 <section id="trouble"><p class="label">Troubleshooting</p><h2>Common problems</h2>{trouble}{support}</section>
 <section id="changelog" class="entry-cols"><div><p class="label">This version</p><h2>What this build is</h2><ul class="plain bullets">{notes}</ul></div>
  <div><p class="label">Fixed since earlier builds</p><ul class="plain bullets">{fixed}</ul><p class="label" style="margin-top:28px">Known quirks in this version</p><ul class="plain bullets">{known}</ul></div></section>
</div>"""
    write("/play/", layout("Download & Play", body, desc="Download and play Pokémon Project Blonde on iPhone, Android, Windows or Mac: current release, emulator setup, saving, and updating without losing your save.", path="/play/", dock="none"))
    for d in PLAY["devices"]:
        devnav = "".join(f'<a href="{u("/play/setup/" + x["id"] + "/")}" {"aria-current=page" if x is d else ""}>{x["name"]}</a>' for x in PLAY["devices"])
        n = len(d["steps"])
        quick = "".join(f"<li>{q}</li>" for q in d["quick"])
        terms = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in PLAY["terms"])
        steps = ""
        for k, st in enumerate(d["steps"], 1):
            note = callout({"type": "tip", "title": st["note"][0], "text": st["note"][1]}) if st.get("note") else ""
            steps += f'<li id="step-{k}" data-step="{esc(st["t"])}"><p class="label"><b>{k:02d}</b> Step {k} of {n}</p><h2>{st["t"]}</h2>{"".join(f"<p>{p}</p>" for p in st["p"])}{note}</li>'
        probs = "".join(f'<details class="qa"><summary><b>{a}</b></summary><div><p>{b}</p></div></details>' for a, b in d["problems"])
        jump = "".join(f'<a href="#step-{k}"><b>{k:02d}</b>{esc(st["t"])}</a>' for k, st in enumerate(d["steps"], 1))
        alts = "".join(f"<li>{a}</li>" for a in d.get("alternatives", []))
        srcs = " · ".join(f'<a href="{esc(h)}" rel="noopener">{esc(t)}</a>' for t, h in d["sources"])
        inner = f"""<div class="cols"><aside class="pin"><p class="label">Play on</p><h1>{d["name"]}</h1><p class="lead">With {d["emulator"]}, {d["emulator_note"]} Needs {d["requires"]}.</p>
   <p class="label qs">Quick start</p><ol class="quick">{quick}</ol>
   <nav class="stepnav" aria-label="Steps">{jump}</nav>
   <p class="srcline">Checked {esc(d["checked"])} against: {srcs}.</p></aside>
  <div class="path"><section class="terms-sec"><p class="label">Before you start</p><h2>Four words you'll see</h2><dl class="kv wide">{terms}</dl></section>
   <ol class="steps">{steps}</ol>
   <section><p class="label">If something's wrong</p><h2>First-launch problems</h2>{probs}<p class="helpline"><a class="link" href="{u("/play/#trouble")}">More troubleshooting{ARROW}</a>{discord_link("link dc", "Ask on Discord")}</p></section>
   {"<section><p class=label>Alternatives</p><ul class='plain bullets'>" + alts + "</ul></section>" if alts else ""}
   <section><p class="label">Later on</p><h2>Updating the game</h2><p class="lead">A new version never has to cost you your progress.</p><p><a class="link" href="{u("/play/#update-" + d["id"])}">Update steps for {d["name"]}{ARROW}</a></p></section>
   <section class="onward"><p class="label">You're set</p><h2>Start the journey</h2><p class="lead">The road begins in New Bark Town.</p><p><a class="btn" href="{u(JOURNEY[0]["url"])}">Open Chapter 1{ARROW}</a></p></section></div></div>"""
        dock = f'<nav class="dock stepper" aria-label="Steps"><button data-step-prev aria-label="Previous step">{ARROW}</button><div><small data-step-n>Step 1 of {n}</small><b data-step-t>{esc(d["steps"][0]["t"])}</b></div><button data-step-next aria-label="Next step">{ARROW}</button></nav>'
        body = f'<div class="wrap setup"><div class="devpick"><p class="label">Where do you want to play?</p><nav class="devnav" aria-label="Device">{devnav}</nav></div>{inner}</div>'
        write(f"/play/setup/{d['id']}/", layout(f"Play on {d['name']}", body, desc=f"Set up Project Blonde on {d['name']} with {d['emulator']}.", path="/play/", dock=dock))


# ============================================================ 19  SEARCH + about
def credits_html():
    """The game's own credits roll, section by section, exactly as the owner maintains it."""
    out, stop = "", False
    for s in J(DATA / "credits.json"):
        if s["id"].startswith("emerald") or s["id"] == "thank_you":
            stop = True
        if stop or not s["names"]:
            continue
        out += f'<div><dt>{esc(" · ".join(h for h in s["heads"] if h != "Credits"))}</dt><dd>{esc(", ".join(s["names"]))}</dd></div>'
    return (f'<section id="credits"><p class="label">Credits</p><h2>Acknowledgements</h2><p class="prose">These are the project and source credits from the game’s own credits roll. The roll in the game also carries personal dedications, which are left to the game, and ends with the full staff credits of Pokémon Emerald Version, on which the engine is built.</p>'
            f'<dl class="kv wide credits">{out}</dl></section>')


def build_misc():
    body = f"""<div class="wrap searchpage" data-search-page><h1 class="label">Search</h1><label class="field xl">{SEARCH}<span class="sr">Search</span><input type="search" placeholder="A place, a Pokémon, a Trainer, an item, a question…" autocomplete="off"></label><div class="results"></div></div>"""
    write("/search/", layout("Search", body, path="/search/"))
    secs = ""
    for s in ABOUT["sections"]:
        inner = "".join(f"<p>{p}</p>" for p in s.get("p", []))
        if s.get("list"):
            inner += '<ul class="plain bullets">' + "".join(f"<li>{x}</li>" for x in s["list"]) + "</ul>"
        if s.get("credits"):
            inner += '<dl class="kv wide credits">' + "".join(f"<div><dt>{esc(a)}</dt><dd>{b}</dd></div>" for a, b in s["credits"]) + "</dl>"
        secs += f'<section id="{s["id"]}"><p class="label">{esc(s["label"])}</p><h2>{esc(s["title"])}</h2><div class="prose">{inner}</div></section>'
    facts = [("Regions", "Johto, Kanto, Hoenn, plus Alola’s isles and Sinjoh"), ("Walkthrough", f"{TOTAL} chapters"), ("Pokédex", f"{len(PAGES):,} entries"), ("Area maps", str(BUILD["maps"])), ("Trainers in the data", f'{BUILD["trainers"]:,}'),
             ("Guide written for", VERSION)]
    body = head("About", "What is Project Blonde?", ABOUT["lead"]) + f"""
<div class="wrap about"><dl class="kv wide">{"".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts)}</dl>{secs}{credits_html()}</div>"""
    write("/about/", layout("About", body, desc="What Project Blonde is, how this guide was made, and credits.", path="/about/"))
    body = head("Not found", "That page isn’t on the road", "The link may be old, or the page may have moved.") + f'<div class="wrap"><div class="actions"><a class="btn" href="{u("/")}">Home{ARROW}</a><button class="btn ghost" data-search-open>Search the guide</button></div></div>'
    (DIST / "404.html").write_text(layout("Not found", body, path="/404"), encoding="utf-8")


def build_search_index():
    idx = []
    add = lambda t, k, url, d="", x="", p=0: idx.append({"t": t, "k": k, "u": url, "d": d, "x": x, "p": p})
    for j in JOURNEY:
        c = j["ch"]
        x = " ".join(filter(None, [c.get("leader", ""), c.get("badge", ""), c.get("sub", ""), " ".join(world[m]["name"] for m in c["maps"][:14])]))
        add(c["title"], "Walkthrough", j["url"], f"{REGIONS[j['r']]['name']} · Chapter {j['n']} of {TOTAL}", x, 6)
        for s in c["steps"]:
            add(s["t"], "Walkthrough", f"{j['url']}#{s['id']}", f"{c['title']} · Chapter {j['n']}", "", 2)
        for q, a in c.get("stuck", []):
            add(q, "Stuck?", f"/stuck/#{c['slug']}-{slug(q)[:40]}", re.sub(r"<[^>]+>", "", a)[:120], c["title"], 3)
    for q in site["stuck"]:
        add(q["q"], "Stuck?", f"/stuck/#{q['id']}", re.sub(r"<[^>]+>", "", q.get("a", ""))[:120], q["tags"], 4)
    for k in PAGES:
        d = DEX[k]
        names = where_summary(d)
        add(d["display_full"], "Pokémon", f"/pokemon/{d['slug']}/", ("Found at " + ", ".join(names[:3]) + ("…" if len(names) > 3 else "")) if names else how_summary(d), " ".join(d["types"]) + " " + (d.get("regional") or ""), 3 if names else 2)
    for url, b, j in TRAINER_PAGE_LIST:
        ts = boss_trainers(b)
        add(b["title"], "Trainer", url, f'{b.get("place") or j["title"]} · Chapter {j["n"]}', " ".join(dict.fromkeys(mon_name(m) for t in ts for m in t["party"])) + " " + tclass(ts[0]), 5)
    for p in PLACES.values():
        add(p["name"], "World", p["url"], f"{p['kind']} · {REGION_NAME[p['region']]}", " ".join(world[m]["name"] for m in p["maps"][:10]), 4)
    for i in ITEMS.values():
        add(i["display"], "Item", i["url"], item_summary(i)[:90], i["pocket"], 3 if i["pocket"] in ("Key Items", "TMs & HMs", "Mega Stones") else 1)
    add("Mega Stones", "Item", "/items/mega-stones/", f'All {len(MEGASTONES["offered"])} obtainable stones and the Mega Ring', "mega stone ring evolution aide elm", 7)
    for f in FEATURES:
        add(f["title"], "Feature", f"/features/{f['id']}/", re.sub(r"<[^>]+>", "", f["blurb"]), "feature guide how " + f["id"].replace("-", " "), 4)
    for d in PLAY["devices"]:
        add(f"Play on {d['name']}", "Play", f"/play/setup/{d['id']}/", f"Set up with {d['emulator']}", "install emulator setup download " + d["emulator"] + " " + d.get("short", ""), 3)
    for t in PLAY["topics"]:
        add(re.sub(r"<[^>]+>", "", t["title"]), "Play", f"/play/#{t['id']}", t["label"], "save backup update restore link " + t["id"], 3)
    add("Download & Play", "Play", "/play/", "Current release, setup, saving and updating", "download install rom emulator save backup update release version patch discord play project blonde", 5)
    add("How to update without losing your save", "Play", "/play/#update", "Back up, update, restore, roll back", "update new version save backup restore rollback patch sav", 4)
    idx.extend(legend_page.search_entries())
    idx.extend(dexnav_page.search_entries())
    add("My progress", "Guide", "/progress/", "Your chapter, Badges and milestones", "checklist progress tracker export import")
    add("About & credits", "Guide", "/about/", "What Project Blonde is, and who made it", "credits about acknowledgements")
    (DIST / "assets" / "search-index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(idx)


# ============================================================ reports
def write_reports(n_search, n_stuck):
    L = ["# Walkthrough chapter map", "", "_Generated by `tools/build.py` from `content/chapters.json` and `content/walkthrough/*.json`. Edit those, not this file._", "",
         "**Basis**: `played` = every step was carried out in the natural playthrough · `mixed` = partly played · `source` = from game data and audits only.", ""]
    for rid, r in REGIONS.items():
        L += [f"## {r['name']}", "", "| # | Chapter | URL | Milestone | Basis | Evidence |", "|---|---|---|---|---|---|"]
        for j in (x for x in JOURNEY if x["r"] == rid):
            c = j["ch"]
            L.append(f"| {j['n']} | {c['title']} | `{j['url']}` | {c.get('badge') or c.get('milestone') or ''} | {c['basis']} | {c.get('ev', '')} |")
        L.append("")
    L += [f"**Total: {TOTAL} chapters.**", ""]
    (ROOT / "WALKTHROUGH-CHAPTER-MAP.md").write_text("\n".join(L), encoding="utf-8")
    pages = WRITTEN_PAGES
    kinds = [("Home", lambda p: p == "/"), ("Walkthrough index and region pages", lambda p: p in ("/walkthrough/", "/postgame/") or re.fullmatch(r"/walkthrough/\w+/", p)),
             ("Chapters", lambda p: re.fullmatch(r"/(walkthrough/\w+|postgame)/[\w-]+/", p) and p not in ("/walkthrough/",)), ("Pokédex index", lambda p: p == "/pokemon/"), ("Pokémon entries", lambda p: re.fullmatch(r"/pokemon/[^/]+/", p)),
             ("Trainers index", lambda p: p == "/trainers/"), ("Trainer pages", lambda p: re.fullmatch(r"/trainers/\w+/[^/]+/", p)), ("World atlas", lambda p: p == "/world/"), ("Place pages", lambda p: re.fullmatch(r"/world/\w+/[^/]+/", p)),
             ("Items index", lambda p: p == "/items/"), ("Mega Stones", lambda p: p == "/items/mega-stones/"), ("Item pages", lambda p: re.fullmatch(r"/items/[^/]+/", p) and p != "/items/mega-stones/"),
             ("Features hub", lambda p: p == "/features/"), ("Feature guides", lambda p: re.fullmatch(r"/features/[^/]+/", p)), ("Stuck?", lambda p: p == "/stuck/"), ("Progress", lambda p: p == "/progress/"),
             ("Play", lambda p: p == "/play/"), ("Device setup", lambda p: p.startswith("/play/setup/")), ("Search", lambda p: p == "/search/"), ("About", lambda p: p == "/about/")]
    expected = {"Chapters": TOTAL, "Pokémon entries": len(PAGES), "Trainer pages": len(TRAINER_PAGE_LIST), "Place pages": len(PLACES), "Item pages": len(ITEMS), "Feature guides": len(FEATURES), "Device setup": len(PLAY["devices"])}
    rows, tot = [], 0
    for name, fn in kinds:
        n = sum(1 for p in pages if fn(p))
        tot += n
        e = expected.get(name, n)
        rows.append(f"| {name} | {e} | {n} | {'✅' if n == e else '❌'} |")
    by_basis = {}
    for j in JOURNEY:
        by_basis[j["ch"]["basis"]] = by_basis.get(j["ch"]["basis"], 0) + 1
    ent = [DEX[k] for k in PAGES]
    n_wild = sum(1 for d in ent if WHERE.get(d["id"]))
    places_no_ch = sum(1 for p in PLACES.values() if not p["chapters"])
    C = ["# Content coverage", "", f"_Generated by `tools/build.py`. Game: {VERSION} (`{BUILD['build']['sha256'][:12]}…`)._", "",
         "## Pages", "", "| Page type | Expected | Generated | |", "|---|---|---|---|"] + rows + ["", f"**{tot} pages generated** ({len(pages)} written). Search index: {n_search} entries. Stuck? answers: {n_stuck}.", "",
         "## Walkthrough", "", f"- {TOTAL} chapters: " + ", ".join(f"{v} {k}" for k, v in by_basis.items()) + ".",
         f"- {sum(len(j['ch'].get('bosses', [])) for j in JOURNEY)} major battles with teams from the ROM; {sum(len(j['ch'].get('stuck', [])) for j in JOURNEY)} sticking-point answers.",
         "- Chapters marked `source` or `mixed` say so on the page and do not describe routes that were not played.", "",
         "## Pokédex", "", f"- {len(ent)} obtainable entries ({sum(1 for d in ent if d['kind'] == 'species')} species, {sum(1 for d in ent if d['kind'] == 'regional')} regional forms); {sum(1 for d in DEX.values() if d['kind'] == 'mega')} Mega forms and {sum(1 for d in DEX.values() if d['kind'] == 'form')} other forms shown on their species' page.",
         f"- {n_wild} have wild encounter tables on reachable maps ({BUILD['encounter_maps']} encounter headers, four times of day); the rest are obtained by event, gift, trade, evolution or egg.",
         f"- {len(ENTRIES) - len(PAGES)} species and forms the engine defines are **not** in the public Pokédex because the game offers no way to obtain them. See `AVAILABILITY-AUDIT.md`.", "",
         "## World", "", f"- {len(PLACES)} places from {BUILD['maps']} maps; all {sum(1 for m in world.values() if m.get('img'))} maps rendered from game data.",
         f"- {places_no_ch} places are not on any chapter's route and are data-only pages.", "",
         "## Items", "", f"- {len(ITEMS)} items; {BUILD['item_balls']} item balls, {BUILD['hidden_items']} hidden items, {len(MARTS)} shop lists on live maps.",
         f"- {BUILD['gift_scripts']} gift scripts in the ROM; {BUILD['gift_scripts'] - len(UNPLACED_GIFTS)} attributed to a map by script label, {len(UNPLACED_GIFTS)} not attributed (shared scripts, unused donor scripts) and therefore not listed.",
         f"- Mega Stones: {MEGASTONES['check']['defined']} defined, {MEGASTONES['check']['offered_by_aide']} obtainable (all from Elm's aide; ROM cross-check {MEGASTONES['check']['offered_found_in_rom']}/{MEGASTONES['check']['offered_by_aide']}), {len(MEGASTONES['not_obtainable'])} not obtainable.", "",
         "## Known gaps (stated on the site, not hidden)", "",
         "- Unlock conditions and routes for: Steven and Wally's final battles, Johto Leader rematches (Fighting Dojo), post-League legendaries, the Alola isles, Sinjoh, Battle Tents, Trainer Hill, Battle Frontier. Teams, maps and encounter data are shown; how to reach them is not, because the natural run did not play them.",
         "- Seven of the eight Hoenn Gym rematches: teams from the ROM, not fought in the run.", "- Poké Mart prices and the progress-scaled stock of standard Johto / Kanto Marts (shared clerk script) are not extracted; department stores and Hoenn Marts are.",
         "- TM / tutor compatibility per species is not listed (level-up moves are).", "- Link Play: verified on two linked mGBA cores only. No setup is published for Delta or Android.",
         "- DexNav: tested in play on the release build for its own manual (/features/dexnav/); not used in the natural playthrough.", "- Fixed encounters and gifts come from event scripts; three retired ones (Kyogre, Groudon, Rayquaza in their old Heart & Soul sites) are labelled.", "",
         "## Broken references", "", ("None: the build stops if content names a map, place, trainer or item the game data does not contain." if not ERRORS else "\n".join(f"- {e}" for e in ERRORS)), ""]
    (ROOT / "CONTENT-COVERAGE.md").write_text("\n".join(C), encoding="utf-8")
    return tot


def validate_availability(idx):
    """Checks that run on every build: the public Pokédex must agree with the availability audit everywhere."""
    R = {}
    def chk(name, bad):
        bad = list(bad)
        R[name] = len(bad)
        for b in bad[:5]:
            ERRORS.append(f"availability: {name}: {b}")
    chk("public entry without acquisition evidence", (k for k in PAGES if not AV[k]["methods"]))
    chk("public entry not classified obtainable", (k for k in PAGES if AV[k]["status"] != "obtainable"))
    chk("entry missing from the audit", (k for k in ENTRIES if k not in AV))
    chk("regional form not classified on its own", (k for k in ENTRIES if DEX[k]["kind"] == "regional" and (k not in AV or AV[k] is AV.get(DEX[k].get("base")))))
    chk("regional form shown with its base form's sources", (k for k in PAGES if DEX[k]["kind"] == "regional" and DEX[k].get("base") in AV and AV[k]["methods"] and AV[k]["methods"] == AV[DEX[k]["base"]]["methods"]))
    chk("method names a map the ROM does not contain", (f'{k}: {m["map"]}' for k in PAGES for m in AV[k]["methods"] if m.get("map") and m["map"] not in world))
    chk("method on an unreachable map", (f'{k}: {m["map"]}' for k in PAGES for m in AV[k]["methods"] if m.get("map") in UNREACHABLE))
    chk("evolution or egg from a parent that is not obtainable", (f'{k} <- {m["from"]}' for k in PAGES for m in AV[k]["methods"] if m["kind"] in ("evolution", "breeding", "converter") and m.get("from") not in PAGES and DEX.get(m.get("from"), {}).get("of") not in PAGES))
    chk("entry obtainable only through a chain with no root source", (k for k in PAGES if not _rooted(k, set())))
    pub = {u_ for u_ in WRITTEN_PAGES if re.fullmatch(r"/pokemon/[^/]+/", u_)}
    want = {f"/pokemon/{DEX[k]['slug']}/" for k in PAGES}
    chk("Pokémon page without a public entry", pub - want)
    chk("public entry without a page", want - pub)
    sidx = {e["u"] for e in idx if e["k"] == "Pokémon"}
    chk("search index lists a Pokémon that is not public", sidx - want)
    chk("public Pokémon missing from the search index", want - sidx)
    slugs = [DEX[k]["slug"] for k in PAGES]
    chk("duplicate Pokédex slug", {x for x in slugs if slugs.count(x) > 1})
    pairs = [(DEX[k]["dex"], DEX[k].get("regional")) for k in PAGES]
    chk("duplicate species / form record", {x for x in pairs if pairs.count(x) > 1})
    chk("wild table species without a public page on a reachable map", (f'{mk}: {r["id"]}' for mk, rec in enc.items() if mk in world and mk not in UNREACHABLE and "#" not in mk for t in rec["tables"].values() for rows in t.values() for r in rows if sp(r["id"]) and not page_of(sp(r["id"]))))
    chk("Mega Stone offered for a Pokémon that is not obtainable", (o["stone"] for o in MEGASTONES["offered"] if next(m for m in MEGAS if m.get("stone") == o["stone"])["species"] not in PAGES))
    chk("in-game Pokédex entry excluded without a recorded reason", (k for k in ENTRIES if AV[k]["in_game_dex"] and k not in PAGES and not AV[k]["reason"]))
    chk("obtainable entry that the game's own Pokédex does not list", (k for k in PAGES if not AV[k]["in_game_dex"]))
    return R


def _rooted(k, seen):
    if k in seen:
        return False
    seen.add(k)
    ms = AV.get(k, {}).get("methods", [])
    if any(m["kind"] in ("wild", "static", "gift", "egg", "trade", "roamer", "verified") for m in ms):
        return True
    return any(_rooted(m["from"] if m["from"] in AV else DEX.get(m["from"], {}).get("of"), seen) for m in ms if m.get("from"))


def write_availability_audit(checks):
    rep_, ent = AVAIL["report"], sorted(ENTRIES, key=lambda k: (DEX[k]["dex"], DEX[k]["num"]))
    ob = [k for k in ent if k in PAGES]
    ex = [k for k in ent if k not in PAGES]
    kinds = {}
    for k in ob:
        for x in set(AV[k]["kinds"]):
            kinds[x] = kinds.get(x, 0) + 1
    prim = {}
    for k in ob:
        prim[AV[k]["kinds"][0]] = prim.get(AV[k]["kinds"][0], 0) + 1
    areas = {}
    for k in ob:
        for m in AV[k]["methods"]:
            if m.get("map") in world:
                areas.setdefault(REGION_NAME.get(world[m["map"]]["region"], world[m["map"]]["region"]), set()).add(k)
    reasons = {}
    for k in ex:
        reasons.setdefault(AV[k]["reason"] or AV[k]["status"], []).append(k)
    nm = lambda k: DEX[k]["display_full"]
    L = ["# Pokémon availability audit", "", f"_Generated by `tools/build.py` from `data/availability.json` (`tools/availability.py`). Game: {VERSION}, SHA-256 `{BUILD['build']['sha256']}`._", "",
         "**Rule.** The Project Blonde public Pokédex must represent Pokémon legitimately obtainable in the current approved game build, not every species defined by the underlying ROM engine. Every future release must revalidate Pokémon availability before the website is redeployed.", "",
         "## Totals", "", "| | |", "|---|---|",
         f"| Species rows in the engine (`gSpeciesInfo`) | {rep_['engine_species_rows']:,} |", f"| Records with a Pokédex number (species, regional forms, Mega and other forms) | {rep_['dex_records']:,} |",
         f"| Species and regional forms considered | {len(ent):,} ({sum(1 for k in ent if DEX[k]['kind'] == 'species'):,} species + {sum(1 for k in ent if DEX[k]['kind'] == 'regional')} regional forms) |",
         f"| **Obtainable species** | **{sum(1 for k in ob if DEX[k]['kind'] == 'species')}** |", f"| **Obtainable regional forms** | **{sum(1 for k in ob if DEX[k]['kind'] == 'regional')}** |",
         f"| **Obtainable species / form combinations (public Pokédex)** | **{len(ob)}** |", f"| Not obtainable (kept out of the public Pokédex) | {len(ex)} |",
         f"| Uncertain | {sum(1 for k in ent if AV[k]['status'] == 'uncertain')} |", f"| Entries on the website before this audit | 1,067 |", f"| Entries removed from the website | {1067 - sum(1 for k in ob if 'ROM row only' not in DEX[k]['src'])} |",
         f"| Entries added (obtainable, but missing from the old species data) | {sum(1 for k in ob if 'ROM row only' in DEX[k]['src'])}: {', '.join(nm(k) for k in ob if 'ROM row only' in DEX[k]['src'])} |",
         f"| The game's own Pokédex list (`sObtainableToNationalOrder`) | 482 entries: {sum(1 for k in ent if AV[k]['in_game_dex'])} species / forms, of which {sum(1 for k in ob if AV[k]['in_game_dex'])} are obtainable |",
         f"| Obtainable entries the game's own Pokédex does not list | {sum(1 for k in ob if not AV[k]['in_game_dex'])} |", "",
         "The total was not chosen in advance. It is what the evidence below produces, and it equals the game's own Pokédex list minus the entries named under *In the game's Pokédex but not obtainable*.", "",
         "## How availability is decided", "",
         f"1. **Reachable maps.** {rep_['maps_reachable']} of {rep_['maps']} maps can be reached from the player's bedroom through warp tiles, map connections, script warps (boats, lifts, events) and {len(J(CONTENT / 'availability-rules.json')['extra_edges'])} hand-recorded links (each with its evidence in `content/availability-rules.json`). A source on any other map does not count.",
         "2. **Wild tables** of the shipped ROM on those maps: land, Surf, Rock Smash and the three rods, in all four times of day. The ROM has no populated hidden (DexNav) slot.",
         "3. **Event scripts** the ROM was built from: `givemon`, `giveegg`, `setwildbattle`, `seteventmon`, `setwildbossbattle`; in-game trades that a script starts; roamers; the regional-form converter in Bill's house. A scripted battle that runs while `FLAG_NO_WILD_CATCHING` is set is **not** a source.",
         "4. **Hand-verified sources** in the rules file, used only where a script names the species in a variable (the Game Corner prize counter).",
         "5. **Closure**, repeated until nothing changes: every evolution in the ROM's own tables whose level, item, place, partner, region and contest-stat conditions can be met in this game, and Day Care eggs (the egg species is found the way the engine finds it, by walking back through the evolution tables).", "",
         "A species named only in a script variable, menu or text buffer is *weak evidence* and never makes an entry obtainable by itself.", "",
         "## Acquisition methods represented", "", "| Method | Entries that can be obtained this way | Entries for which it is the first-listed method |", "|---|---|---|"]
    for x in ("wild", "static", "gift", "egg", "trade", "roamer", "converter", "evolution", "breeding"):
        L.append(f"| {MLABEL[x]} | {kinds.get(x, 0)} | {prim.get(x, 0)} |")
    L += ["", "## Areas covered", "", "| Area | Obtainable entries with a source there |", "|---|---|"] + [f"| {a} | {len(v)} |" for a, v in sorted(areas.items(), key=lambda kv: -len(kv[1]))]
    L += ["", "Gated areas (the item's source is in the scripts; none of these was reached in the natural playthrough):", ""] + [f"- {', '.join(g['maps'])}: needs {g['needs']} — {g['item_source']}" for g in GATED]
    L += ["", "## Regional forms", "", "| Region | Obtainable | Not obtainable |", "|---|---|---|"]
    for r in ("Alola", "Galar", "Hisui", "Paldea"):
        a_ = [k for k in ent if DEX[k].get("regional") == r]
        L.append(f"| {r} | {len([k for k in a_ if k in PAGES])}: {', '.join(nm(k).replace(' (' + r + ')', '') for k in a_ if k in PAGES)} | {len([k for k in a_ if k not in PAGES])}: {', '.join(nm(k).replace(' (' + r + ')', '') for k in a_ if k not in PAGES) or '—'} |")
    L += ["", "The fifteen Galarian forms are obtained only through the converter in Bill's house (source: `sRegionalFormTable`, `special ConvertToRegionalForm`); the game has no Galar maps.", "",
          "## In the game's Pokédex but not obtainable", ""]
    L += [f"- **{nm(k)}** — {AV[k]['reason']}" for k in ent if AV[k]["in_game_dex"] and k not in PAGES] or ["- none"]
    L += ["", "## Sources that were found and rejected", "", "| Pokémon | Why the source does not count | Where |", "|---|---|---|"]
    seen = set()
    for b in rep_["blocked_sources"]:
        key_ = (b["species"], b["why"], b["where"])
        if key_ in seen or b["species"] not in DEX:
            continue
        seen.add(key_)
        L.append(f"| {nm(b['species'])} | {b['why']} | {world[b['where']]['name'] if b['where'] in world else b['where']} |")
    L += ["", "## Excluded entries, by reason", ""]
    for r, ks in sorted(reasons.items(), key=lambda kv: len(kv[1])):
        L += [f"### {r} ({len(ks)})", "", ", ".join(nm(k) for k in ks), ""]
    L += ["## Unresolved or uncertain", ""]
    unc = [k for k in ent if AV[k]["status"] == "uncertain"]
    L += [f"- {nm(k)}: {json.dumps(AV[k]['uncertain'], ensure_ascii=False)[:300]}" for k in unc] or ["- No entry is classed uncertain."]
    L += ["- **Not confirmed by play.** The natural playthrough is not an availability list. Most sources here are established from the ROM's tables and the scripts, not by catching each Pokémon. In particular the gated areas above, the converter in Bill's house, the Game Corner prizes, the post-League legendary encounters, raising Beauty for Milotic (Berry Blender in the Contest Lobby) and Day Care eggs were not exercised.",
          "- **Link-trade evolutions** are counted as possible (two copies of the game can trade, and a trade evolves), but no obtainable entry depends on one: each has a level or item alternative.",
          "- **Scripts versus ROM.** Event scripts are read from the source tree and the Hoenn overlay that the linked build was made from, not disassembled from the ROM. Wild tables, evolution data, egg groups and maps are read from the ROM itself.",
          f"- **Unreachable maps** ({len(rep_['maps_unreachable'])}): " + ", ".join(sorted({world[m]['place'].title() or m for m in rep_['maps_unreachable']})) + ". No obtainable entry depends on them.", "",
          "## Automated checks (run on every build)", "", "| Check | Failures |", "|---|---|"] + [f"| {k} | {v} |" for k, v in checks.items()]
    L += ["", "## Full list of obtainable entries", "", "| # | Pokémon | Methods | Regions |", "|---|---|---|---|"]
    L += [f"| {DEX[k]['dex']} | {nm(k)} | {', '.join(MLABEL[x] for x in AV[k]['kinds'])} | {', '.join(AV[k]['regions']) or '—'} |" for k in ob]
    (ROOT / "AVAILABILITY-AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    CFG["base"] = ap.parse_args().base.rstrip("/")
    expand_refs()
    for j in JOURNEY:       # every key item named in a chapter must be an item the game defines
        for n, _ in j["ch"].get("items", []):
            check(ITEMS[n].get("desc") or ITEMS[n]["sources"] or n in NOT_ITEMS, f'chapter {j["k"]}: item "{n}" is not an item in the game data')
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE / "assets", DIST / "assets")
    (DIST / ".nojekyll").write_text("")
    index_trainers()
    build_home(); build_road()
    for j in JOURNEY:
        legend_page.build(j, journey_bar) if j["k"] == "postgame/legendaries" else build_chapter(j)       # the field guide is its own page type
    build_pokemon(); build_trainers(); build_world(); build_items(); build_features()
    n_stuck = build_stuck()
    build_progress(); build_play(); build_misc()
    n = build_search_index()
    checks = validate_availability(json.loads((DIST / "assets" / "search-index.json").read_text(encoding="utf-8")))
    write_availability_audit(checks)
    tot = write_reports(n, n_stuck)
    if ERRORS:
        print("CONTENT ERRORS — fix before publishing:")
        for e in ERRORS:
            print("  -", e)
        sys.exit(1)
    print(f"built {len(WRITTEN_PAGES)} pages, {n} search entries, {TOTAL} chapters -> {DIST}")


if __name__ == "__main__":
    main()
