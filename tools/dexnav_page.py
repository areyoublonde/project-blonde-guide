"""Project Blonde guide - the illustrated DexNav manual (one page type, /features/dexnav/).

Content    : content/dexnav.json (hand-written; `[code]` marks a sentence read from the game's code, not seen in play)
Screenshots: site/assets/game/dexnav/*.png, native 240x160 mGBA captures of the release build
build.py calls build() for the `dexnav` feature instead of the generic feature template.
"""
from site_core import *

GUIDE = J(CONTENT / "dexnav.json")
URL = "/features/dexnav/"
SHOTS = SITE / "assets" / "game" / "dexnav"
W, H = 240, 160
CODE = '<abbr class="dn-code" title="Read from the game’s code or data. Not seen happen in testing.">code</abbr>'
SECTIONS = [("what", "What is DexNav?"), ("unlock", "How to unlock it"), ("use", "How to use DexNav"), ("list", "Understanding the Pokémon list"),
            ("after", "What happens after selecting a Pokémon?"), ("where", "Where DexNav works"), ("tips", "Tips and limitations"), ("faq", "Frequently asked questions")]
BY_K = {j["k"]: j for j in JOURNEY}


def fmt(s):
    s = re.sub(r"\{(/[^|}]*)\|([^}]+)\}", lambda m: f'<a href="{u(m[1])}">{m[2]}</a>', s)
    return s.replace("[code]", CODE)


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>|\[code\]", "", re.sub(r"\{/[^|}]*\|([^}]+)\}", r"\1", s))).strip()


def shot(name, alt, cap="", cls=""):
    check((SHOTS / f"{name}.png").exists(), f"dexnav: screenshot {name}.png is missing")
    return (f'<figure class="dn-fig {cls}"><button class="dn-shot" type="button" data-zoom aria-label="Enlarge screenshot: {esc(cap or alt)}">'
            f'<img class="px" src="{u(f"/assets/game/dexnav/{name}.png")}" width="{W}" height="{H}" alt="{esc(alt)}" loading="lazy" decoding="async"></button>'
            f'{"<figcaption>" + fmt(cap) + "</figcaption>" if cap else ""}</figure>')


def yn(v):
    k = {"Yes": "y", "No": "n"}.get(v, "m")
    return f'<span class="dn-yn dn-{k}">{esc(v)}</span>'


def sec(i, title, inner, sid):
    return f'<section id="{sid}" class="dn-sec"><p class="label"><b>{i:02d}</b> {esc(title.rstrip("?"))}</p><h2>{esc(title)}</h2>{inner}</section>'


def build(f, basis_html):
    g = GUIDE
    toc = "".join(f'<li><a href="#{k}">{esc(t)}</a></li>' for k, t in SECTIONS)
    # 01 what
    why = "".join(f"<div><dt>{esc(a)}</dt><dd>{fmt(b)}</dd></div>" for a, b in g["what"]["why"])
    what = (f'<div class="dn-two"><div class="prose">{"".join(f"<p>{fmt(p)}</p>" for p in g["what"]["paras"])}<p class="dn-note">{fmt(g["what"]["limits"])}</p></div>'
            f'<dl class="dn-why">{why}</dl></div>')
    # 02 unlock
    j = BY_K.get(g["unlock"]["chapter"])
    check(j is not None, "dexnav: unlock chapter is not on the road")
    unlock = (f'<p class="dn-answer">{fmt(g["unlock"]["answer"])}</p><div class="prose">{"".join(f"<p>{fmt(p)}</p>" for p in g["unlock"]["paras"])}'
              f'<p class="muted dn-small">{fmt(g["unlock"]["checked"])}</p></div>'
              f'<p><a class="link" href="{jhref(j)}">Chapter {j["n"]}: {esc(j["title"])}{ARROW}</a></p>')
    # 03 use
    steps = ""
    for n, s in enumerate(g["steps"], 1):
        steps += (f'<li class="dn-step" id="step-{n}">{shot(s["img"], s["alt"], f"Step {n}. " + plain(s["title"]) + ".")}'
                  f'<div class="dn-steptext"><p class="dn-n" aria-hidden="true">{n:02d}</p><h3><span class="sr">Step {n}: </span>{fmt(s["title"])}</h3>'
                  f'{"".join(f"<p>{fmt(p)}</p>" for p in s["body"])}<p class="dn-next"><span class="label">Next</span>{fmt(s["next"])}</p></div></li>')
    keys = lambda rows: "".join(f"<tr><td><kbd>{esc(a)}</kbd></td><td>{fmt(b)}</td></tr>" for a, b in rows)
    r = g["register"]
    use = (f'<p class="lead dn-lead">Seven steps, each with a screenshot from the game. Select any screenshot to enlarge it.</p><ol class="dn-steps">{steps}</ol>'
           f'<div class="dn-sub" id="buttons"><h3>Buttons</h3><div class="dn-two even"><table class="tbl dn-keys"><caption>On the DexNav screen</caption><tbody>{keys(g["buttons"]["screen"])}</tbody></table>'
           f'<table class="tbl dn-keys"><caption>In the field</caption><tbody>{keys(g["buttons"]["field"])}</tbody></table></div></div>'
           f'<div class="dn-sub" id="register"><h3>The R shortcut: register a Pokémon</h3><div class="dn-side">{shot(r["img"], r["alt"], "Registered: the top bar now reads Search LEDYBA.")}'
           f'<div class="prose">{"".join(f"<p>{fmt(p)}</p>" for p in r["paras"])}</div></div></div>')
    # 04 list
    L = g["list"]
    dl = lambda rows: '<dl class="kv wide dn-kv">' + "".join(f"<div><dt>{esc(a)}</dt><dd>{fmt(b)}</dd></div>" for a, b in rows) + "</dl>"
    lst = (f'<div class="dn-side">{shot(L["img"], L["alt"], L["caption"])}<div><h3>The three rows</h3>{dl(L["rows"])}</div></div>'
           f'<div class="dn-two even"><div><h3>What the icons mean</h3>{dl(L["icons"])}</div><div><h3>The panel on the right</h3>{dl(L["panel"])}</div></div>'
           f'<div class="dn-sub"><h3>What decides the list</h3><ul class="dn-list">{"".join(f"<li>{fmt(x)}</li>" for x in L["notes"])}</ul></div>')
    # 05 after
    A = g["after"]
    ends = "".join(f'<li>{shot(i, A["ends_alt"][i], "", "sm") if i else ""}<div><h4>{esc(a)}</h4><p>{fmt(b)}</p></div></li>' for a, b, i in A["ends"])
    trow = lambda rows, heads: ('<div class="dn-scroll"><table class="tbl dn-tbl"><thead><tr>' + "".join(f"<th>{h}</th>" for h in heads) + "</tr></thead><tbody>"
                                + "".join(f'<tr><td>{esc(a)}</td><td data-l="{heads[1]}">{yn(b)}</td><td>{fmt(c)}</td></tr>' for a, b, c in rows) + "</tbody></table></div>")
    after = (f'<div class="prose">{"".join(f"<p>{fmt(p)}</p>" for p in A["paras"])}</div>'
             f'<div class="dn-sub"><h3>How a search ends</h3><ol class="dn-ends">{ends}</ol></div>'
             f'<div class="dn-sub" id="chain"><h3>Chains</h3><ul class="dn-list">{"".join(f"<li>{fmt(x)}</li>" for x in A["chain"])}</ul></div>'
             f'<div class="dn-sub" id="effects"><h3>What a search changes, and what it does not</h3>{trow(A["table"], ["About the Pokémon", "Changed?", "Detail"])}</div>')
    # 06 where
    Wh = g["where"]
    figs = "".join(shot(i, alt, cap) for i, cap, alt in Wh["figs"])
    where = f'<div class="dn-gallery">{figs}</div>{trow(Wh["table"], ["Place", "Works?", "Detail"])}<div class="dn-sub"><h3>Regions</h3><p class="prose">{fmt(Wh["regions"])}</p></div>'
    # 07 tips
    tips = '<ol class="dn-tips">' + "".join(f"<li><h3>{fmt(a)}</h3><p>{fmt(b)}</p></li>" for a, b in g["tips"]) + "</ol>"
    # 08 faq
    faq = '<div class="dn-faq">' + "".join(f'<div id="faq-{i}"><h3>{fmt(q)}</h3><p>{fmt(a)}</p></div>' for q, a, i in g["faq"]) + "</div>"
    parts = dict(what=what, unlock=unlock, use=use, list=lst, after=after, where=where, tips=tips, faq=faq)
    body_secs = "".join(sec(n, t, parts[k], k) for n, (k, t) in enumerate(SECTIONS, 1))
    rel = "".join(f'<li><a href="{u(a)}"><b>{esc(b)}</b><span>{esc(c)}</span></a></li>' for a, b, c in g["related"])
    body = f"""
<link rel="stylesheet" href="{u("/assets/dexnav.css")}">
<article class="entry guide dn"><div class="wrap">
 <nav class="crumbs"><a href="{u("/features/")}">Features</a></nav>
 <header class="entry-head nomedia"><div><p class="label">Feature guide · {basis_html}</p><h1>DexNav</h1><p class="lead">{fmt(g["lead"])}</p>
  <p class="muted dn-small dn-key">Everything on this page was done in the running game unless it is marked {CODE}, which means it was read from the game’s code or data.</p></div></header>
 <nav class="dn-toc" aria-label="On this page"><p class="label">On this page</p><ol>{toc}</ol></nav>
 {body_secs}
 <section id="related" class="dn-sec"><p class="label">Related</p><h2>Keep reading</h2><ul class="dn-rel">{rel}</ul></section>
 <p class="muted evline">Source: {esc(g["ev"])}.</p>
</div></article>
<dialog class="dn-zoom" aria-label="Screenshot"><figure><img class="px" alt="" width="{W}" height="{H}"><figcaption></figcaption></figure>
 <div class="dn-zbar"><button type="button" data-zprev aria-label="Previous screenshot">←</button><span class="dn-zcount" aria-live="polite"></span><button type="button" data-znext aria-label="Next screenshot">→</button><button type="button" data-zclose>Close</button></div></dialog>
<script src="{u("/assets/dexnav.js")}" defer></script>"""
    write(URL, layout("DexNav", body, desc=plain(g["lead"]), path="/features/"))


def search_entries():
    """Rows for the global search: the manual, its sections and each question."""
    g = GUIDE
    out = [{"t": "How to use DexNav", "k": "Feature", "u": f"{URL}#use", "d": "DexNav guide · seven illustrated steps", "x": "dexnav dex nav search find track wild pokemon tutorial steps register chain", "p": 6},
           {"t": "How to unlock DexNav", "k": "Feature", "u": f"{URL}#unlock", "d": plain(g["unlock"]["answer"]), "x": "dexnav unlock get obtain where when start menu", "p": 5},
           {"t": "DexNav chains and shiny odds", "k": "Feature", "u": f"{URL}#chain", "d": "DexNav guide · what a chain does", "x": "dexnav chain shiny odds level bonus streak", "p": 4},
           {"t": "Where DexNav works", "k": "Feature", "u": f"{URL}#where", "d": "Grass, caves, water, fishing, regions", "x": "dexnav grass cave water surf surfing fishing rock smash region johto kanto hoenn", "p": 4}]
    for q, a, i in g["faq"]:
        out.append({"t": plain(q), "k": "Feature", "u": f"{URL}#faq-{i}", "d": "DexNav guide · " + plain(a)[:80], "x": "dexnav question faq " + i, "p": 3})
    return out


def place_line(has_lists):
    """One line under a place's encounter tables: these are the lists DexNav reads."""
    return f'<p class="dnline"><a class="link" href="{u(URL)}">Track one of these with DexNav{ARROW}</a></p>' if has_lists else ""
