#!/usr/bin/env python3
"""Targeted browser checks for the Ash / Alola / Lillie pages. argv: tools dir, base url, chrome port."""
import json, sys, time
sys.path.insert(0, sys.argv[1])
import cdp
import tempfile
_mk = tempfile.mkdtemp
cdp.tempfile.mkdtemp = lambda prefix='': _mk(prefix='story-qa-')      # own profile name: another session's harness kills pb-review-* browsers
BASE, PORT = sys.argv[2].rstrip("/"), int(sys.argv[3])
c = cdp.Chrome(PORT)
fail = 0


def ok(name, cond, detail=""):
    global fail
    fail += 0 if cond else 1
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if not cond else ""), flush=True)


def go(path):
    c.nav(BASE + path); c.wait("document.readyState === 'complete' && location.pathname === %s" % json.dumps(path), 10); time.sleep(0.4)


PAGES = {"/walkthrough/kanto/ash/": 8, "/postgame/alola-isles/": 5, "/postgame/lillie/": 10}
for mobile, (w, h) in ((False, (1440, 900)), (True, (390, 844))):
    c.viewport(w, h, 2 if mobile else 1, mobile)
    tag = "phone" if mobile else "desktop"
    for p, nsteps in PAGES.items():
        go(p)
        r = c.js("""(() => { const de = document.documentElement; return {
          over: de.scrollWidth - de.clientWidth, steps: document.querySelectorAll('section.step[id]:not(#battles):not(#stuck):not(#wild):not(#items):not(#trainers):not(#places)').length,
          h1: [...document.querySelectorAll('h1')].filter(e => e.offsetParent).length, toc: document.querySelectorAll('.toc a').length,
          imgs: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).length,
          battles: document.querySelectorAll('#battles h3').length, basis: document.querySelectorAll('.step .basis').length }; })()""")
        ok(f"{tag} {p}: one h1, no sideways scroll, images decoded", r["h1"] == 1 and r["over"] <= 0 and r["imgs"] == 0, r)
        ok(f"{tag} {p}: {nsteps} walkthrough stages shown with evidence tags", r["steps"] == nsteps and r["basis"] >= nsteps - 2, r)
    go("/postgame/lillie/")
    n = c.js("document.querySelectorAll('.prose .blur').length")
    before = c.js("getComputedStyle(document.querySelector('.prose .blur')).filter")
    c.js("document.querySelector('.prose .blur').click()"); time.sleep(0.2)
    after = c.js("getComputedStyle(document.querySelector('.prose .blur')).filter")
    other = c.js("getComputedStyle(document.querySelectorAll('.prose .blur')[1]).filter")
    ok(f"{tag} Lillie: {n} story spoilers start blurred, one tap reveals only that one", n == 4 and "blur" in before and after == "none" and "blur" in other, (n, before, after, other))
    ok(f"{tag} Lillie: both Aether battles listed with teams", c.js("document.querySelectorAll('#battles h3').length") == 2 and "Magneton" in c.js("document.querySelector('#battles').textContent"))
    href = c.js("document.querySelector('.objective a[href*=\"alola-isles\"]').getAttribute('href')")
    c.js("document.querySelector('.objective a[href*=\"alola-isles\"]').click()"); c.wait("location.pathname.endsWith('/postgame/alola-isles/')", 8)
    ok(f"{tag} Lillie → prerequisite link opens The Alola Isles", c.js("document.querySelector('h1').textContent") == "The Alola Isles", href)
    c.js("document.querySelector('.prose a[href*=\"/postgame/lillie/\"]').click()"); c.wait("location.pathname.endsWith('/postgame/lillie/')", 8)
    ok(f"{tag} Alola Isles → Lillie link works", c.js("document.querySelector('h1').textContent") == "Something in Her Bag")
    go("/walkthrough/")
    order = c.js("[...document.querySelectorAll('.road li[data-ch]')].map(e => e.dataset.ch)")
    i = order.index
    ok(f"{tag} Road: Mt. Silver → Ash → Road to Hoenn in order; Alola and Lillie in the last leg", i("kanto/mt-silver") + 1 == i("kanto/ash") and i("kanto/ash") + 1 == i("hoenn/road-to-hoenn") and i("postgame/alola-isles") + 1 == i("postgame/lillie") and i("postgame/lillie") > i("hoenn/hoenn-league") and len(order) == 60, len(order))
    c.js("document.querySelector('.road li[data-ch=\"postgame/lillie\"] a.t').click()"); c.wait("location.pathname.endsWith('/postgame/lillie/')", 8)
    ok(f"{tag} Road → Lillie by normal navigation", True)
    go("/walkthrough/kanto/mt-silver/")
    c.js("document.querySelector('.pager a.r').click()"); c.wait("location.pathname.endsWith('/kanto/ash/')", 8)
    c.js("document.querySelector('.pager a.r').click()"); c.wait("location.pathname.endsWith('/hoenn/road-to-hoenn/')", 8)
    ok(f"{tag} Next / Next from Mt. Silver reaches Ash then The Road to Hoenn", c.js("location.pathname").endswith("/hoenn/road-to-hoenn/"))
    go("/walkthrough/kanto/fuchsia-city/")
    ok(f"{tag} Fuchsia chapter (Route 13) links to The Alola Isles", c.js("!!document.querySelector('.prose a[href*=\"/postgame/alola-isles/\"]')"))
    go("/walkthrough/hoenn/road-to-hoenn/")
    ok(f"{tag} Road to Hoenn ‘stuck’ entry links back to Ash", c.js("!!document.querySelector('#stuck a[href*=\"/kanto/ash/\"]')"))
    go("/stuck/")
    ok(f"{tag} Stuck? page carries the new Ash, Alola and Lillie answers", c.js("""['ash-i-beat-ash-but-professor-oak','lillie-lillie-is-not-in-the-shop','alola-isles-the-captain-on-route-13'].every(id => [...document.querySelectorAll('details.qa')].some(d => d.id.startsWith(id)))"""))
idx = json.loads(__import__("urllib.request").request.urlopen(BASE + "/assets/search-index.json").read())
hit = lambda q: [e["u"] for e in idx if q in (e["t"] + " " + e.get("x", "") + " " + e.get("d", "")).lower()]
ok("Search index: ‘lillie’, ‘ash’ and ‘alola isles’ reach the new chapters", "/postgame/lillie/" in hit("lillie") and "/walkthrough/kanto/ash/" in hit("ash in viridian") and "/postgame/alola-isles/" in hit("alola isles"))
c.close()
print(f"new-page checks: {fail} failed")
sys.exit(1 if fail else 0)
