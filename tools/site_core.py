"""Project Blonde guide - shared fragments and the page shell (stdlib only).

One shell, one stylesheet, one script for every page. The model of the game lives in model.py;
page types live in build.py.
"""
from model import *

# ----------------------------------------------------------------------------- icons
ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
DISCORD_ICON = '<svg class="dci" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>'
SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
EXPAND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>'
FIT = EXPAND.replace("M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5", "M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5")


# ----------------------------------------------------------------------------- fragments
def icon_img(s, size=24):
    if s and s.get("icon"):
        return f'<img class="px" src="{u("/assets/game/icons/" + s["slug"] + ".png")}" width="{size}" height="{size}" alt="" loading="lazy" decoding="async">'
    return f'<span style="width:{size}px;height:{size}px;display:inline-block"></span>'


def art_img(s, size=56, alt=""):
    if s and s.get("art"):
        return f'<img class="px" src="{u("/assets/game/pokemon/" + s["slug"] + ".png")}" width="{size}" height="{size}" alt="{esc(alt)}" loading="lazy" decoding="async">'
    return f'<span style="width:{size}px;height:{size}px;display:block"></span>'


def types(s):
    return '<span class="types">' + "".join(f'<span class="type" style="--t:{TYPE_COLOR.get(t, "#777")}">{t}</span>' for t in (s or {}).get("types", [])) + "</span>"


def trainer_pic(t, size=64):
    fn = t["pic"]
    if fn and (SITE / "assets/game/trainers" / f"{fn}.png").exists():
        return f'<img class="px" src="{u("/assets/game/trainers/" + fn + ".png")}" width="{size}" height="{size}" alt="">'
    return ""


def count(items):
    seen = {}
    for i in items:
        seen[i] = seen.get(i, 0) + 1
    return [f"{k} ×{v}" if v > 1 else k for k, v in seen.items()]


def mon_name(m):
    d = sp(m["species"])
    return d["display_full"] if d else nice(m["species"].replace("SPECIES_", "").replace("_", " "))


def trainer_row(tid, link=True):
    t = trainer(tid)
    if not check(t is not None, f"unknown trainer {tid}"):
        return ""
    pills = "".join(f'<span class="mon-pill">{icon_img(sp(m["species"]))}{esc(mon_name(m))} <em>{m.get("level", "?")}</em></span>' for m in t["party"])
    bag = f'<div class="bag">Carries {esc(", ".join(count(t["items"])))}</div>' if t["items"] else ""
    dbl = ' <small class="dbl">Double</small>' if t["double"] else ""
    return f'<li class="trow"><div class="who"><small>{esc(tclass(t))}</small>{esc(tname(t))}{dbl}</div><div class="team">{pills}</div>{bag}</li>'


def team_rows(t):
    out = ""
    for m in t["party"]:
        s = sp(m["species"])
        mega = next((x for x in MEGAS if x.get("stone") and x["stone"] == m.get("item")), None)
        meta = " · ".join(x for x in [m.get("ability") and f'Ability: {m["ability"]}', m.get("item") and f'Holds {m["item"]}' + (" (Mega Evolves)" if mega else "")] if x)
        art = art_img(s, 56, mon_name(m))
        if s and sp_url(s):
            art = f'<a href="{sp_url(s)}">{art}</a>'
        moves = "".join(f"<span>{esc(x)}</span>" for x in m["moves"]) or '<span class="muted">Level-up moves</span>'
        out += (f'<div class="mon">{art}<div class="n">{esc(mon_name(m))} <em>Lv. {m.get("level", "?")}</em> {types(s)}</div>'
                f'<div class="meta">{esc(meta)}</div><div class="moves">{moves}</div></div>')
    return f'<div class="team-list">{out}</div>'


def prize(t):
    """Prize money as the engine pays it: class rate x 4 x last Pokémon's level, doubled in Double Battles."""
    if not t["money"] or not t["party"]:
        return None
    return t["money"] * 4 * t["party"][-1]["level"] * (2 if t["double"] else 1)


def battle(b, tag="h3"):
    """A major battle: who, format, team (per variant), what to know."""
    vs = [(v[0], trainer(v[1])) if isinstance(v, list) else ("", trainer(v)) for v in b["ids"]]
    vs = [(l, t) for l, t in vs if t]
    if not vs:
        return ""
    t0 = vs[0][1]
    lv = [m["level"] for _, t in vs for m in t["party"]]
    sizes = sorted({len(t["party"]) for _, t in vs})
    facts = [("Format", "Double Battle" if t0["double"] else "Single Battle"), ("Pokémon", "–".join(map(str, sizes)) if len(sizes) > 1 else str(sizes[0])), ("Levels", f"{min(lv)}–{max(lv)}" if min(lv) != max(lv) else str(lv[0]))]
    if t0["items"]:
        facts.append(("Carries", ", ".join(count(t0["items"]))))
    if b.get("rewards"):
        facts.append(("Rewards", ", ".join(b["rewards"])))
    pz = prize(t0)
    if pz and len(vs) == 1:
        facts.append(("Prize", f"¥{pz:,}"))
    place_ = b.get("place") or ", ".join(dict.fromkeys(world[m]["name"] for m in TRAINER_MAPS.get(t0["id"], [])[:2])) or "Location not confirmed"
    tabs = panels = ""
    if len(vs) > 1:
        tabs = '<div class="tabs" role="tablist" aria-label="Which team">' + "".join(f'<button role="tab" data-tab="v{i}" aria-selected="{str(i == 0).lower()}">{esc(l)}</button>' for i, (l, _) in enumerate(vs)) + "</div>"
    for i, (l, t) in enumerate(vs):
        panels += f'<div data-panel="v{i}" {"hidden" if i else ""}>{team_rows(t)}</div>'
    strat = "".join(f"<li>{x}</li>" for x in b.get("know", []))
    page = TRAINER_PAGE.get(t0["id"])
    more = f'<p class="more"><a class="link" href="{u(page)}">Full page for {esc(b["title"])}{ARROW}</a></p>' if page and not b.get("nolink") else ""
    return (f'<article class="battle" id="{esc(b["id"])}" data-tabs><header>{trainer_pic(t0)}<div><p class="label">Battle · {esc(place_)}</p><{tag}>{esc(b["title"])}</{tag}></div></header>'
            f'<dl class="facts">{"".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts)}</dl>{tabs}{panels}'
            f'{"<div class=know><p class=label>What to know</p><ul>" + strat + "</ul></div>" if strat else ""}{more}</article>')


TRAINER_PAGE = {}     # trainer id -> url, filled by build.py before pages are written


def callout(c):
    label = {"item": "Item", "missable": "Missable", "optional": "Optional", "tip": "Tip", "warning": "Warning", "unlock": "Unlocked", "travel": "Where"}[c["type"]]
    return f'<aside class="note {c["type"]}"><p class="label">{label}</p><h4>{c["title"]}</h4><p>{c["text"]}</p></aside>'


def enc_rows(mapkey, title=None, note=None, tag="h3"):
    """Encounter tables for one map, one panel per time of day. Missing periods fall back to the day table, as the Pokédex does."""
    rec = enc.get(mapkey)
    if not rec:
        return ""
    out = f'<div class="enc"><{tag}>{esc(title or world[mapkey]["name"])}</{tag}>{"<p class=muted>" + esc(note) + "</p>" if note else ""}'
    for tod in TODS:
        body = ""
        for method in METHOD:
            tods = rec["tables"].get(method)
            if not tods:
                continue
            rows = tods.get(tod) or tods.get("day") or next(iter(tods.values()))
            cells = ""
            for r in rows:
                s = sp(r["id"])
                lv = f'{r["min"]}' if r["min"] == r["max"] else f'{r["min"]}–{r["max"]}'
                inner = f'{icon_img(s, 32)}<b>{esc(s["display_full"] if s else r["id"])}</b><span>Lv. {lv}</span><span>{r["rate"]}%</span>'
                cells += f'<a class="enc-row" href="{sp_url(s)}">{inner}</a>' if s and sp_url(s) else f'<div class="enc-row">{inner}</div>'
            if cells:
                body += f'<p class="label method">{METHOD[method]}</p><div class="enc-list">{cells}</div>'
        out += f'<div data-tod-panel="{tod}" {"hidden" if tod != "day" else ""}>{body}</div>'
    return out + "</div>"


TOD = '<div class="seg" role="group" aria-label="Time of day"><button data-tod="morning" aria-pressed="false">Morning</button><button data-tod="day" aria-pressed="true">Day</button><button data-tod="evening" aria-pressed="false">Evening</button><button data-tod="night" aria-pressed="false">Night</button></div>'
COL = {"objective": "#c9603f", "item": "#a8853f", "service": "#4f7fb0", "optional": "#5f8a55", "exit": "#6a625c"}
LBL = {"objective": "Objectives", "item": "Items", "service": "Services", "optional": "Optional", "exit": "Exits"}


def auto_markers(mapkey):
    """Markers straight from the map's own events: item balls, hidden items, doors to named places."""
    m = world[mapkey]
    out = []
    for o in m["events"]["objects"]:
        if o.get("item"):
            out.append({"x": o["x"], "y": o["y"], "kind": "item", "label": o["item"], "note": "Item ball"})
    for h in m["events"]["hidden"]:
        out.append({"x": h["x"], "y": h["y"], "kind": "optional", "label": h["item"], "note": "Hidden item: use the Dowsing Machine or press A on the tile"})
    seen = set()
    for w in m["events"]["warps"]:
        to = w["to"]
        if not to or to == mapkey or to in seen or to not in world or w["x"] < 0:
            continue
        seen.add(to)
        n = world[to]["name"]
        kind = "service" if re.search(r"Pok.mon Center|Mart|Pokecenter", n) else ("objective" if "Gym" in n else "exit")
        short = n.replace(m["place"] and nice(m["place"]) + " ", "") if m["type"] in ("city", "town") else n
        out.append({"x": w["x"], "y": w["y"], "kind": kind, "label": short or n, "note": ""})
    return out


def map_viewer(mapkey, markers=None, caption="", zoom="", focus="", title="", label="Area map"):
    """The working map: titled frame, layer toggles, pan / zoom, full screen, and a text legend."""
    m = world[mapkey]
    if not m.get("img"):
        return ""
    w, h = m["w"] * 16, m["h"] * 16
    markers = auto_markers(mapkey) if markers is None else markers
    order = ["objective", "item", "service", "optional", "exit"]
    markers = sorted(markers, key=lambda k: order.index(k["kind"]))
    kinds, mk, legend = [], "", ""
    for i, k in enumerate(markers, 1):
        if k["kind"] not in kinds:
            kinds.append(k["kind"])
        mk += (f'<button class="mk" data-kind="{k["kind"]}" style="left:{(k["x"] + .5) / m["w"] * 100:.2f}%;top:{(k["y"] + .5) / m["h"] * 100:.2f}%" '
               f'data-label="{esc(k["label"])}" data-note="{esc(k.get("note", ""))}" aria-label="{esc(k["label"])}" aria-expanded="false">{i}</button>')
        legend += f'<li><b style="--c:{COL[k["kind"]]}">{i}</b><span><strong>{esc(k["label"])}</strong>{" — " + esc(k["note"]) if k.get("note") else ""} <small class="xy">{k["x"]},{k["y"]}</small></span></li>'
    selfwarps = [wv for wv in m["events"]["warps"] if wv["to"] == mapkey and wv["x"] >= 0]
    pits = len(selfwarps) >= 6
    pit_html = ""
    if pits:
        pit_html = "".join(f'<i class="pit" hidden style="left:{wv["x"] / m["w"] * 100:.3f}%;top:{wv["y"] / m["h"] * 100:.3f}%;width:{100 / m["w"]:.3f}%;height:{100 / m["h"]:.3f}%"></i>' for wv in selfwarps)
    filters = "".join(f'<button data-filter="{k}" aria-pressed="true">{LBL[k]}</button>' for k in kinds)
    if pits:
        filters += '<button data-filter="pit" aria-pressed="false">Show pitfalls</button>'
    name = title or m["name"]
    return (f'<figure class="mapfig"><div class="mapv" data-zoom="{zoom}" data-focus="{focus}"><div class="mapv-head"><div><span class="label">{esc(label)}</span><b>{esc(name)}</b></div>'
            f'{"<div class=mapv-bar role=toolbar aria-label=Layers>" + filters + "</div>" if filters else ""}'
            f'<button class="mapv-x" data-expand aria-label="Expand map" aria-pressed="false">{EXPAND}</button></div>'
            f'<div class="mapv-body"><div class="mapv-view" tabindex="0" aria-label="Scrollable map of {esc(name)}"><div class="mapv-stage" data-w="{w}"><img class="px" src="{u("/assets/game/maps/" + m["slug"] + ".png")}" width="{w}" height="{h}" alt="Map of {esc(name)}" loading="lazy">{pit_html}{mk}</div></div>'
            f'<div class="mapv-ctl"><button data-zoom="out" aria-label="Zoom out">−</button><button data-zoom="fit" aria-label="Fit to frame">{FIT}</button><button data-zoom="in" aria-label="Zoom in">+</button></div></div>'
            f'{"<div class=mapv-tip aria-live=polite>Select a marker.</div>" if markers else ""}</div>'
            f'{"<details class=legendbox><summary>" + str(len(markers)) + " marked on this map</summary><ol class=legend>" + legend + "</ol></details>" if legend else ""}{"<figcaption>" + esc(caption) + "</figcaption>" if caption else ""}</figure>')


def plate(name, extra="", cls=""):
    return f'<div class="plate {cls}" aria-hidden="true"><img src="{u("/assets/game/plates/" + name + ".jpg")}" alt="" width="{PLATES[name]["w"]}" height="{PLATES[name]["h"]}"><div class="mist"></div>{extra}</div>'


def town_map(key, dots, you=True, label=""):
    """The game's Town Map with dots. dots: [(x, y, attrs, title)] in map pixels."""
    svg = "".join(f'<circle cx="{x}" cy="{y}" r="2" {attrs}><title>{esc(t)}</title></circle>' for x, y, attrs, t in dots)
    return (f'<div data-map="{key}"><img class="px" src="{u("/assets/game/world/" + key + ".png")}" alt="{esc(label)}" width="960" height="640">'
            f'<svg viewBox="0 0 240 160" aria-hidden="true">{svg}</svg></div>')


def now_known(tag="h1", extra=""):
    return (f'<div data-if="known"><p class="label accent">You are here</p><{tag} data-now="title"></{tag}><p class="meta" data-now="meta"></p><p class="goal" data-now="goal"></p>'
            f'<div class="actions"><a class="btn" data-now="href" href="{u("/walkthrough/")}"><span data-now="cta">Continue</span>{ARROW}</a></div>{extra}'
            f'<div class="adj"><a data-now="prev" href="#"><small>Previous</small><b></b></a><a data-now="next" href="#"><small>Next</small><b></b></a></div></div>')


def ticks(js, here=None):
    return "".join(f'<i class="{"gym " if j["ch"].get("badge") else ""}{"here" if j is here else ("done" if here and j["n"] < here["n"] else "")}" data-ch="{j["k"]}"></i>' for j in js)


# ----------------------------------------------------------------------------- community
DISCORD = (site.get("community") or {}).get("discord") or {}


def discord_link(cls="link", label=None, icon_only=False):
    """Every Discord link on the site. The invite lives only in content/site.json; with no URL there, nothing is rendered."""
    if not DISCORD.get("url"):
        return ""
    label = label or DISCORD["label"]
    assert re.fullmatch(r"https://discord\.(gg|com/invite)/[A-Za-z0-9-]+", DISCORD["url"]), "community.discord.url must be a Discord invite"
    inner = DISCORD_ICON + (f'<span class="sr">{esc(label)}</span>' if icon_only else f"<span>{esc(label)}</span>")
    return f'<a class="{cls}" data-discord href="{esc(DISCORD["url"])}" target="_blank" rel="noopener">{inner}</a>'


# ----------------------------------------------------------------------------- shell
def layout(title, body, desc="", path="/", dock="continue", attrs=""):
    nav = "".join(f'<a href="{u(n["href"])}" {"aria-current=page" if path.startswith(n["href"]) else ""}>{n["label"]}</a>' for n in site["nav"])
    more = "".join(f'<a href="{u(n["href"])}" {"aria-current=page" if path.startswith(n["href"]) else ""}>{n["label"]}</a>' for n in site["more"])
    more_on = any(path.startswith(n["href"]) for n in site["more"])
    sheet = (f'<a href="{u("/walkthrough/")}">Walkthrough</a><a href="{u("/world/")}">World</a><a href="{u("/pokemon/")}">Pokémon</a><a href="{u("/trainers/")}">Trainers</a>'
             f'<a href="{u("/items/")}">Items</a><a href="{u("/items/mega-stones/")}">Mega Stones</a><a href="{u("/postgame/legendaries/")}">Legendary Pokémon</a><a href="{u("/features/")}">Features</a><a href="{u("/stuck/")}">Stuck?</a><a href="{u("/progress/")}">My progress</a><a href="{u("/play/")}">Download &amp; Play</a><a href="{u("/about/")}">About</a>{discord_link("dc")}')
    docks = {
        "continue": f'<nav class="dock one" data-if="known" aria-label="Continue"><a data-now="href" href="{u("/walkthrough/")}"><small>Continue</small><b data-now="title"></b></a></nav>',
        "none": "",
    }
    dock_html = docks.get(dock, dock)
    full = f"{title} · Project Blonde Guide" if title else "Project Blonde Guide"
    return f"""<!doctype html>
<html lang="en" data-base="{CFG["base"]}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc or site["tagline"])}">
<meta name="theme-color" content="#0e0d0c">
<link rel="preload" href="{u("/assets/fonts/instrument-var.woff2")}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{u("/assets/app.css")}">
<script>try{{document.documentElement.dataset.pos=JSON.parse(localStorage.getItem("pb-guide:v1")||"{{}}").pos?"known":"none"}}catch(e){{document.documentElement.dataset.pos="none"}}</script>
</head>
<body {attrs}>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap">
 <a class="mark" href="{u("/")}">Project Blonde</a>
 <nav class="nav" aria-label="Main">{nav}<details class="more"><summary {"aria-current=page" if more_on else ""}>More</summary><div>{more}</div></details></nav>
 <div class="util"><a class="cont" data-if="known" data-now="href" href="{u("/walkthrough/")}"><i></i><span data-now="title"></span></a>
  <button data-search-open aria-label="Search">{SEARCH}<span>Search</span><kbd>/</kbd></button>{discord_link("dc", icon_only=True)}<a class="stuck" href="{u("/stuck/")}" {"aria-current=page" if path.startswith("/stuck/") else ""}>Stuck?</a>
  <a class="play" href="{u("/play/")}" {"aria-current=page" if path.startswith("/play/") else ""}>Play</a><button class="menu" data-menu aria-expanded="false" aria-controls="menu">Menu</button></div>
</div></header>
<nav class="menu-sheet" id="menu" aria-label="Menu" hidden>{sheet}</nav>
<main id="main">{body}</main>
<footer class="foot"><div class="wrap"><span>An unofficial, non-commercial fan guide to Pokémon Project Blonde, written for {VERSION}. Not affiliated with Nintendo, Creatures, GAME FREAK or The Pokémon Company.</span>
 <nav aria-label="Footer"><a href="{u("/progress/")}">My progress</a><a href="{u("/play/")}">Download &amp; Play</a><a href="{u("/search/")}">Search</a><a href="{u("/about/")}">About</a>{discord_link("dc")}<button class="link" data-spoiler-toggle>Spoilers: hidden</button></nav></div></footer>
{dock_html}
<dialog class="search" aria-label="Search the guide"><div class="search-top"><label class="field">{SEARCH}<span class="sr">Search</span><input type="search" placeholder="A place, a Pokémon, a Trainer, an item, a question…" autocomplete="off" spellcheck="false"></label><button class="esc" data-search-close>esc</button></div>
<div class="results" role="listbox"></div><div class="search-foot"><span><kbd>↑↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>esc</kbd> close</span></div></dialog>
<script type="application/json" id="journey">{json.dumps(journey_public(), ensure_ascii=False, separators=(",", ":"))}</script>
<script src="{u("/assets/app.js")}" defer></script>
</body></html>"""


WRITTEN_PAGES = []


def write(path, htmltext):
    WRITTEN_PAGES.append(path if path.endswith("/") else path + "/")
    out = DIST / path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(htmltext, encoding="utf-8")


def head(label, title, lead="", extra=""):
    """Plain page head: a label, a restrained title, one sentence."""
    return f'<header class="phead"><div class="wrap"><p class="label">{label}</p><h1>{title}</h1>{"<p class=lead>" + lead + "</p>" if lead else ""}{extra}</div></header>'
