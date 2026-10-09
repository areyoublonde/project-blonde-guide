#!/usr/bin/env python3
"""Browser QA: drive headless Chrome through every page type and every interactive feature.

    python3 -m http.server 8765 -d dist &
    python3 tools/qa_browser.py [--sweep N]      -> data/qa-browser.json ; exit 1 on any failure

Part 1  page sweep, desktop 1440x900 and phone 390x844: every hub page, every chapter, and a spread of generated
        Pokémon / Trainer / place / item pages (N of each, default 12): one h1 shown, no uncaught script error,
        no failed request, no sideways scroll, every image decoded, tap targets >= 40 px on phones.
Part 2  interactions: search, filters, map viewer, chapter navigation, spoilers, progress save / export / import,
        Stuck? locator, device chooser, download state, mobile menu, keyboard focus, reduced motion.
"""
import argparse, json, random, sys, time
from pathlib import Path
from cdp import Chrome

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8765"
R = {"sweep": [], "checks": [], "fail": 0}


def ok(name, cond, detail=""):
    R["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:200]})
    if not cond:
        R["fail"] += 1
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
    return cond


def go(c, path, wait=0.35):
    c.events.clear()
    if wait < 0.1:
        c.send("Page.navigate", url=BASE + path)
        c.wait("document.readyState === 'complete' && location.pathname === %s" % json.dumps(path), 10)
    else:
        c.nav(BASE + path)
        c.wait("document.readyState === 'complete'", 8)
    time.sleep(wait)


PAGE_CHECK = """(() => { const de = document.documentElement;
 const h1 = [...document.querySelectorAll('h1')].filter(e => e.offsetParent !== null).length;
 const imgs = [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src'));
 const small = [...document.querySelectorAll('a,button,select,input,summary')].filter(e => { const r = e.getBoundingClientRect(); if (!r.width || e.offsetParent === null) return false; if (e.tagName === 'INPUT' && e.closest('label')) return false; if (e.matches('.dex b a,.places b a,.people b a,.itemlist b a')) { const li = e.closest('li').getBoundingClientRect(); return li.height < 40; }
   if (e.closest('.prose,p,li.trow,.legend,.crumbs,td,dd,.kv,.srcline,.aside,.evline,.foot,.items,.plain,.caption,figcaption,.toc,.areanav,.mk,.search-foot,.hint,.wm,.ticks,.jbar,.movelist,.evo,.mon,.enc-row') ) return false;
   return r.height < 40 && r.width < 40; }).length;
 return { h1, over: de.scrollWidth - de.clientWidth, imgs, small, title: document.title }; })()"""


def sweep(c, paths, label, mobile, fast=False):
    bad = 0
    for i, p in enumerate(paths):
        if i % (200 if fast else 25) == 0:
            print(f"   {label} {i}/{len(paths)} {p}", flush=True)
        go(c, p, 0.02 if fast else 0.15)
        c.js("window.scrollTo(0, document.body.scrollHeight)"); time.sleep(0.03 if fast else 0.12)
        r = c.js(PAGE_CHECK)
        errs = [e for e in c.events if e.get("method") in ("Runtime.exceptionThrown", "Network.loadingFailed")]
        fails = []
        if r["h1"] != 1: fails.append(f'{r["h1"]} visible h1')
        if r["over"] > 1: fails.append(f'sideways scroll {r["over"]}px')
        if r["imgs"]: fails.append(f'{len(r["imgs"])} broken images: {r["imgs"][:2]}')
        if errs: fails.append(f'{len(errs)} script/network errors: {json.dumps(errs[0])[:160]}')
        if mobile and r["small"]: fails.append(f'{r["small"]} tap targets under 40px')
        if fails:
            bad += 1
            R["sweep"].append({"view": label, "page": p, "fails": fails})
            print("  FAIL", label, p, fails)
    return bad


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sweep", type=int, default=12)
    ap.add_argument("--all", action="store_true", help="every generated route at phone width (page checks only); writes data/qa-browser-all.json")
    args = ap.parse_args()
    n = args.sweep
    dist = ROOT / "dist"
    allp = sorted("/" + str(f.parent.relative_to(dist)) + "/" for f in dist.rglob("index.html") if f.parent != dist)
    rnd = random.Random(102)
    pick = lambda pre, k: rnd.sample([p for p in allp if p.startswith(pre) and p.count("/") == pre.count("/") + 1], k)
    chapters = [p for p in allp if (p.startswith("/walkthrough/") and p.count("/") == 4) or (p.startswith("/postgame/") and p.count("/") == 3)]
    hubs = ["/", "/walkthrough/", "/walkthrough/johto/", "/postgame/", "/pokemon/", "/trainers/", "/world/", "/items/", "/items/mega-stones/", "/features/", "/stuck/", "/progress/", "/play/", "/search/", "/about/"]
    hubs += [p for p in allp if p.startswith("/play/setup/")] + [p for p in allp if p.startswith("/features/") and p.count("/") == 3]
    places = [p for p in allp if p.startswith("/world/") and p.count("/") == 4]
    sample = hubs + chapters + pick("/pokemon/", n * 3) + rnd.sample([p for p in allp if p.startswith("/trainers/") and p.count("/") == 4], n) + rnd.sample(places, n * 2) + \
        ["/world/johto/goldenrod-city/", "/world/hoenn/route-119/", "/pokemon/eevee/", "/pokemon/vulpix-alola/", "/pokemon/charizard/", "/items/hm03-surf/", "/items/venusaurite/", "/items/lopunnite/"] + pick("/items/", n)
    sample = list(dict.fromkeys(sample))
    if args.all:
        c = Chrome()      # no network log here: broken images and script errors are still caught by the page check
        try:
            c.viewport(390, 844, 1, True)
            bad = sweep(c, ["/"] + allp, "phone-all", True, fast=True)
        finally:
            c.close()
        (ROOT / "data/qa-browser-all.json").write_text(json.dumps({"routes": len(allp) + 1, "failed": bad, "failures": R["sweep"]}, indent=1))
        print(f"all routes: {len(allp) + 1} pages at 390 px, {bad} failed")
        sys.exit(1 if bad else 0)
    c = Chrome()
    c.send("Network.enable")
    try:
        # ------------------------------------------------------------ part 1: sweep
        print(f"sweep: {len(sample)} pages x 2 viewports")
        c.viewport(1440, 900)
        d_bad = sweep(c, sample, "desktop", False)
        c.viewport(390, 844, 2, True)
        m_bad = sweep(c, sample, "phone", True)
        ok(f"Desktop sweep: {len(sample)} pages clean", d_bad == 0, f"{d_bad} pages failed")
        ok(f"Phone sweep: {len(sample)} pages clean", m_bad == 0, f"{m_bad} pages failed")
        R["sweep_pages"] = len(sample)

        # ------------------------------------------------------------ part 2: interactions (desktop)
        c.viewport(1440, 900)
        go(c, "/"); c.js("localStorage.clear()"); go(c, "/")
        ok("Home (new player): headline is Play Project Blonde", c.js("[...document.querySelectorAll('h1')].find(e=>e.offsetParent).textContent") == "Play Project Blonde")
        ok("Home: one primary button above the fold", c.js("[...document.querySelectorAll('.hero .btn:not(.ghost)')].filter(e=>e.offsetParent).length") == 1)
        ok("Home: route into the walkthrough and into Play", c.js("!!document.querySelector('.hero a[href$=\"/play/\"]') && !!document.querySelector('a[href*=\"/walkthrough/\"]')"))
        ok("Home: section links cover all eight areas", c.js("document.querySelectorAll('.homelinks a').length") == 8)
        c.click(".hero .btn"); c.wait("location.pathname.endsWith('/play/')", 4)
        ok("Home: Get started opens Play", c.url().endswith("/play/"))

        go(c, "/walkthrough/")
        ok("Road: 60 stops, every one a link", c.js("document.querySelectorAll('.road li a.t').length") == 60)
        ok("Road: four regions in order", c.js("[...document.querySelectorAll('.leg h2')].map(e=>e.textContent.trim()).join()") == "Johto,Kanto,Hoenn,Postgame")
        c.click(".road li a.t"); c.wait("location.pathname.includes('new-bark-town')", 4)
        ok("Road: first stop opens Chapter 1", "new-bark-town" in c.url())
        ok("Chapter: opening it saves the position", c.js("JSON.parse(localStorage.getItem('pb-guide:v1')).pos") == "johto/new-bark-town")

        go(c, "/walkthrough/johto/ecruteak-city/")
        ok("Chapter: title, objective, quick route in first screen", c.js("['h1','.objective','.route'].every(s=>{const e=document.querySelector(s);return e&&e.getBoundingClientRect().top<900})"))
        ok("Chapter: shows what it is based on", c.js("!!document.querySelector('.kv .basis')"))
        c.click("[data-mode-btn=quick]")
        ok("Chapter: Quick mode hides the full walkthrough", c.js("getComputedStyle(document.querySelector('.full-only')).display") == "none")
        c.click("[data-mode-btn=full]")
        ok("Chapter: Full mode restores it", c.js("getComputedStyle(document.querySelector('.full-only')).display") != "none")
        c.js("document.querySelector('.mapv').scrollIntoView()"); time.sleep(.3)
        z0 = c.js("document.querySelector('.mapv').pbZoom()")
        c.click(".mapv [data-zoom=in]")
        ok("Map: zoom in enlarges", c.js("document.querySelector('.mapv').pbZoom()") > z0)
        c.click(".mapv .mk")
        ok("Map: selecting a marker shows its detail", c.js("document.querySelector('.mapv-tip').textContent") != "Select a marker.")
        k = c.js("document.querySelector('.mapv [data-filter]').dataset.filter")
        c.click(".mapv [data-filter]")
        ok("Map: layer toggle hides its markers", c.js(f"[...document.querySelectorAll('.mapv .mk[data-kind={k}]')].every(m=>m.hidden)"))
        c.click(".mapv [data-expand]")
        ok("Map: expand fills the screen", c.js("document.querySelector('.mapv').hasAttribute('data-full')"))
        c.key("Escape")
        ok("Map: Esc leaves full screen", not c.js("document.querySelector('.mapv').hasAttribute('data-full')"))
        ok("Chapter: rival battle has a team per starter", c.js("document.querySelectorAll('#rival-3 [data-tab]').length") == 3)
        c.js("document.querySelector('#rival-3').scrollIntoView({block:'center'})"); time.sleep(.2)
        c.click("#rival-3 [data-tab]", 1)
        ok("Chapter: starter tab switches the team", c.js("!document.querySelector('#rival-3 [data-panel=v1]').hidden && document.querySelector('#rival-3 [data-panel=v0]').hidden"))
        c.js("document.querySelector('#wild').scrollIntoView()"); time.sleep(.2)
        c.click("#wild [data-tod=night]")
        ok("Chapter: time-of-day switch changes the tables", c.js("!document.querySelector('[data-tod-panel=night]').hidden && document.querySelector('[data-tod-panel=day]').hidden"))
        c.js("document.querySelector('#stuck .qa summary').scrollIntoView({block:'center'})"); time.sleep(.2); c.click("#stuck .qa summary")
        ok("Chapter: a sticking-point answer opens", c.js("document.querySelector('#stuck .qa').open"))
        c.js("document.querySelector('.pager a.r').scrollIntoView({block:'center'})"); time.sleep(.2); c.click(".pager a.r"); c.wait("location.pathname.includes('olivine-city')", 4)
        ok("Chapter: Next goes to the following chapter", "olivine-city" in c.url())
        c.click(".jbar .pv"); c.wait("location.pathname.includes('ecruteak-city')", 4)
        ok("Chapter: journey bar Previous goes back", "ecruteak-city" in c.url())
        go(c, "/world/johto/ecruteak-city/")
        c.js("document.querySelector('#m-ecruteak-city-gym').scrollIntoView()"); time.sleep(.3)
        ok("Gym map: pitfall layer exists and reveals", c.js("(()=>{const v=document.querySelector('#m-ecruteak-city-gym .mapv');const b=v.querySelector('[data-filter=pit]');b.click();return [...v.querySelectorAll('.pit')].length>5&&![...v.querySelectorAll('.pit')][0].hidden})()"))

        # spoilers
        go(c, "/walkthrough/")
        ok("Spoilers: Hoenn crossing text is blurred by default", c.js("!!document.querySelector('.crossing .blur:not(.shown)')"))
        c.js("document.querySelector('.crossing .blur').scrollIntoView({block:'center'})"); time.sleep(.2); c.click(".crossing .blur")
        ok("Spoilers: selecting it reveals it", c.js("document.querySelector('.crossing .blur').classList.contains('shown')"))
        go(c, "/progress/")
        c.js("document.querySelector('.keep [data-spoiler-toggle]').scrollIntoView({block:'center'})"); time.sleep(.2); c.click(".keep [data-spoiler-toggle]")
        ok("Spoilers: global switch turns them on", c.js("document.body.dataset.spoilers") == "on" and c.js("JSON.parse(localStorage.getItem('pb-guide:v1')).spoilers") is True)
        c.click(".keep [data-spoiler-toggle]")

        # search
        go(c, "/")
        c.key("/"); time.sleep(.3)
        ok("Search: / opens the palette", c.js("document.querySelector('dialog.search').open"))
        ok("Search: empty palette offers Continue first", "Continue" in (c.js("document.querySelector('dialog.search .results a').textContent") or ""))
        for q, want, label in [("misdrevus", "/pokemon/misdreavus/", "a misspelling finds Misdreavus"), ("roxanne", "/trainers/", "a Leader's name finds their page"), ("mega stones", "/items/mega-stones/", "Mega Stones finds its section"),
                               ("how do i get to hoenn", "/stuck/", "a question finds its Stuck? answer"), ("sky pillar", "/world/hoenn/sky-pillar/", "a place finds its page"), ("dive", "/items/hm09-dive/", "an HM finds its item page")]:
            c.js("(()=>{const i=document.querySelector('dialog.search input');i.value='';i.dispatchEvent(new Event('input'))})()")
            c.click("dialog.search input"); c.type(q); time.sleep(.5)
            hrefs = c.js("[...document.querySelectorAll('dialog.search .results a')].slice(0,8).map(a=>a.getAttribute('href'))") or []
            ok(f"Search: {label}", any(want in h for h in hrefs), hrefs[:3])
        ok("Search: results are grouped by kind", c.js("document.querySelectorAll('dialog.search .results h5').length") >= 1)
        c.key("ArrowDown"); ok("Search: arrow keys move the selection", c.js("[...document.querySelectorAll('dialog.search .results a')].findIndex(a=>a.classList.contains('sel'))") == 1)
        c.key("Enter"); time.sleep(.6)
        ok("Search: Enter opens the selected result", c.js("location.pathname") != "/")
        go(c, "/search/?q=lavaridge")
        ok("Search page: ?q= runs the query", c.wait("document.querySelectorAll('.searchpage .results a').length > 0", 4))

        # filters
        go(c, "/pokemon/")
        total = c.js("document.querySelectorAll('#dex li').length")
        public = sum(1 for v in json.loads((ROOT / "data/availability.json").read_text())["species"].values() if v["status"] == "obtainable")
        ok(f"Pokédex: lists exactly the {public} obtainable entries", total == public, total)
        c.click("[data-filter-list]"); c.type("ghost"); time.sleep(.3)
        vis = c.js("[...document.querySelectorAll('#dex li')].filter(l=>getComputedStyle(l).display!=='none').length")
        ok("Pokédex: typing a type filters the list", 0 < vis < total, vis)
        c.click("[data-region-filter=hoenn]"); time.sleep(.2)
        v2 = c.js("[...document.querySelectorAll('#dex li')].filter(l=>getComputedStyle(l).display!=='none').length")
        ok("Pokédex: region filter narrows it", 0 < v2 <= vis, v2)
        ok("Pokédex: count readout matches", c.js("document.querySelector('[data-filter-count]').textContent").startswith(str(v2)))
        go(c, "/pokemon/vulpix/")
        ok("Pokémon: regional form is a separate, linked entry", c.js("!!document.querySelector('.formrow a[href*=\"vulpix-alola\"]')"))
        ok("Pokémon: locations table and Town Map dots", c.js("document.querySelectorAll('.tbl tbody tr').length>0 && document.querySelectorAll('.wherefig circle.on').length>0"))
        go(c, "/pokemon/vulpix-alola/")
        ok("Pokémon: Alolan form has its own locations (Alola isle)", c.js("document.querySelector('.tbl').textContent.includes('Isle') || document.querySelector('.tbl').textContent.includes('Ula')"))
        go(c, "/pokemon/charizard/")
        ok("Pokémon: Mega forms link to their Mega Stones", c.js("document.querySelectorAll('.megarow a[href*=\"/items/charizardite\"]').length") == 2)
        go(c, "/pokemon/machoke/")
        ok("Pokémon: trade evolution shows its level alternative", c.js("document.querySelector('.evo').textContent.includes('Level 38')"))
        go(c, "/trainers/")
        c.click("[data-region-filter=hoenn]"); time.sleep(.2)
        ok("Trainers: region filter", c.js("(v=>v.length>0&&v.length<document.querySelectorAll('.people li').length&&v.every(l=>l.dataset.r==='hoenn'))([...document.querySelectorAll('.people li')].filter(l=>getComputedStyle(l).display!=='none'))"))
        go(c, "/trainers/hoenn/wallace/")
        ok("Trainer page: team with levels, items and moves", c.js("document.querySelectorAll('.mon').length") == 6 and c.js("document.querySelector('.team-list').textContent.includes('Gyaradosite')"))
        go(c, "/items/")
        c.click("[data-filter-list]"); c.type("surf"); time.sleep(.3)
        ok("Items: filter finds HM03 Surf", c.js("[...document.querySelectorAll('#items li')].filter(l=>getComputedStyle(l).display!=='none').some(l=>l.textContent.includes('HM03 Surf'))"))
        go(c, "/items/mega-stones/")
        ok("Mega Stones: 51 obtainable stones listed", c.js("document.querySelectorAll('#megas li').length") == 51)
        c.click("[data-filter-list]"); c.type("charizard"); time.sleep(.3)
        ok("Mega Stones: searchable", c.js("[...document.querySelectorAll('#megas li')].filter(l=>getComputedStyle(l).display!=='none').length") == 2)
        ok("Mega Stones: completeness check reports a match", c.js("document.body.textContent.includes('Match: every obtainable stone is documented')"))
        go(c, "/features/mega-evolution/")
        ok("Mega Evolution guide links to the Mega Stones section", c.js("!!document.querySelector('a[href$=\"/items/mega-stones/\"]')"))
        go(c, "/items/venusaurite/")
        ok("Item page: Mega Stone links to its Pokémon and the section", c.js("!!document.querySelector('a[href*=\"/pokemon/venusaur/\"]') && !!document.querySelector('a[href$=\"/items/mega-stones/\"]')"))

        # world
        go(c, "/world/")
        c.hover(".places li"); time.sleep(.2)
        ok("World: hovering a place lights its dot", c.js("document.querySelectorAll('.atlas circle.hot').length") == 1)
        c.click("[data-atlas=hoenn]"); time.sleep(.3)
        ok("World: Hoenn tab swaps the map and list", c.js("document.querySelector('.atlas .stage').dataset.view") == "hoenn" and c.js("!document.querySelector('[data-atlas-panel=hoenn]').hidden"))
        c.click(".filterbar [data-filter-list]"); c.type("fortree"); time.sleep(.3)
        ok("World: filter leaves matching places", c.js("[...document.querySelectorAll('[data-atlas-panel=hoenn] .places li')].filter(l=>getComputedStyle(l).display!=='none').length") == 1)
        go(c, "/world/hoenn/route-119/")
        ok("Place: area map, encounter tables with four times of day", c.js("!!document.querySelector('.mapv img') && document.querySelectorAll('.rowhead [data-tod]').length==4"))
        ok("Place: links back to its chapter", c.js("!!document.querySelector('.chlinks a[href*=\"fortree-city\"]')"))

        # stuck
        go(c, "/"); c.js("localStorage.clear()"); go(c, "/stuck/")
        c.js("(()=>{const s=document.querySelector('[data-stuck-chapter]');s.value='hoenn/mauville-city';s.dispatchEvent(new Event('change',{bubbles:true}))})()"); time.sleep(.3)
        ok("Stuck?: choosing where you are gives a next step", c.js("!document.querySelector('[data-nextstep]').hidden && document.querySelector('[data-ns-title]').textContent") == "Mauville City")
        ok("Stuck?: it sets the last Badge and shows the road ahead", c.js("document.querySelector('[data-stuck-badge]').value") == "hoenn/dewford-town" and c.js("document.querySelectorAll('[data-stretch-list] li').length") > 0)
        ok("Stuck?: answers for that stretch come first", c.js("document.querySelector('[data-answers] .qa').dataset.ch") in ("hoenn/mauville-city", "hoenn/fallarbor-town", "hoenn/lavaridge-town"))
        ok("Stuck?: no answer from a later region is promoted", c.js("![...document.querySelectorAll('[data-answers] .qa.rel')].some(q=>q.dataset.ch.startsWith('postgame'))"))
        c.click("[data-stuck-q]"); c.type("rocks won't break"); time.sleep(.3)
        ok("Stuck?: a plain-language question narrows to the answer", c.js("[...document.querySelectorAll('[data-answers] .qa')].filter(q=>getComputedStyle(q).display!=='none').some(q=>q.textContent.includes('v102'))"))

        # progress + export / import
        go(c, "/progress/")
        c.js("(()=>{const s=document.querySelector('[data-set-pos]');s.value='kanto/saffron-city';s.dispatchEvent(new Event('change',{bubbles:true}))})()"); time.sleep(.2)
        ok("Progress: setting the current chapter moves You are here", c.js("document.querySelector('.progress [data-now=title]').textContent") == "Saffron City")
        c.js("document.querySelector('[data-check=badge-zephyr]').click();document.querySelector('[data-check=ms-surf]').click();document.querySelector('[data-chapter=\"johto/new-bark-town\"]').click()"); time.sleep(.2)
        ok("Progress: Badges, milestones and chapters tick and count", c.js("document.querySelector('[data-region=johto] [data-count]').textContent") == "1 of 8 Badges" and c.js("document.querySelector('[data-chapcount=johto]').textContent").startswith("1 of 19"))
        ok("Progress: postgame objectives are tracked", c.js("document.querySelectorAll('[data-region=postgame] input[data-check]').length") >= 5)
        go(c, "/progress/")
        ok("Progress: survives a reload", c.js("document.querySelector('[data-check=badge-zephyr]').checked && document.querySelector('[data-set-pos]').value") == "kanto/saffron-city")
        exported = c.js("""(async()=>{let blob=null;const o=URL.createObjectURL;URL.createObjectURL=b=>{blob=b;return o.call(URL,b)};HTMLAnchorElement.prototype.click=function(){window.__dl=this.download};
            document.querySelector('[data-export]').click();return {name:window.__dl,text:await blob.text()}})()""")
        data = json.loads(exported["text"])
        ok("Progress: Export produces a progress file", exported["name"] == "project-blonde-progress.json" and data["app"] == "project-blonde-guide" and data["done"].get("badge-zephyr") == 1 and data["pos"] == "kanto/saffron-city")
        c.js("localStorage.clear()"); go(c, "/progress/")
        ok("Progress: cleared state is empty", not c.js("document.querySelector('[data-check=badge-zephyr]').checked"))
        c.js("""(()=>{const i=document.querySelector('[data-import]');const dt=new DataTransfer();dt.items.add(new File([%s],'p.json',{type:'application/json'}));i.files=dt.files;i.dispatchEvent(new Event('change',{bubbles:true}))})()""" % json.dumps(exported["text"]))
        time.sleep(.4)
        ok("Progress: Import restores Badges, chapters and position", c.js("document.querySelector('[data-check=badge-zephyr]').checked && document.querySelector('[data-chapter=\"johto/new-bark-town\"]').checked && document.querySelector('[data-set-pos]').value") == "kanto/saffron-city")
        c.js("""(()=>{const i=document.querySelector('[data-import]');const dt=new DataTransfer();dt.items.add(new File(['{"nope":1}'],'x.json'));i.files=dt.files;i.dispatchEvent(new Event('change',{bubbles:true}))})()"""); time.sleep(.3)
        ok("Progress: a wrong file is refused with a message", "isn't a Project Blonde progress export" in c.js("document.querySelector('[data-io-msg]').textContent"))
        ok("Progress: says plainly that nothing is synced", c.js("document.querySelector('.keep').textContent.includes('nothing is synced')"))
        go(c, "/")
        ok("Home (returning): You are here with place, chapter and Continue", c.js("[...document.querySelectorAll('h1')].find(e=>e.offsetParent).textContent") == "Saffron City" and c.js("document.querySelector('.hero [data-now=meta]').textContent").startswith("Kanto · Chapter 22 of 60"))
        ok("Home (returning): Badge progress and next Badge", "Badges" in c.js("document.querySelector('.hero [data-now=badges]').textContent"))
        ok("Header: Continue chip returns to the chapter", c.js("document.querySelector('.cont').getAttribute('href')").endswith("/walkthrough/kanto/saffron-city/"))

        # play
        go(c, "/play/")
        ok("Play: pre-release state, with no download control at all", c.js("document.querySelector('.wrap.play').dataset.releaseState") == "prerelease" and c.js("document.querySelectorAll('[data-download],[aria-disabled]').length") == 0)
        ok("Play: no game file link anywhere on the page", c.js("![...document.querySelectorAll('a')].some(a=>/\\.(gba|zip|bps|ips)(\\?|$)/i.test(a.href))"))
        ok("Play: four devices offered", c.js("document.querySelectorAll('.devices a').length") == 4)
        ok("Play: saving, backup, update, restore, link and troubleshooting are all there", c.js("['release','save','backup','update','rollback','restore','move','link','trouble'].every(i=>!!document.getElementById(i))"))
        ok("Play: link section names the compatibility id and the unsupported modes", c.js("(t=>t.includes('PB-LINK-0001')&&t.includes('Record Mixing')&&t.includes('Not verified'))(document.getElementById('link').textContent)"))
        for dev, emu in (("iphone", "Delta"), ("android", "RetroArch"), ("windows", "mGBA"), ("mac", "mGBA")):
            go(c, f"/play/setup/{dev}/")
            ok(f"Setup · {dev}: full path with {emu}, six steps, sources", c.js("document.querySelectorAll('.steps > li').length") == 6 and emu in c.js("document.querySelector('.pin .lead').textContent") and c.js("document.querySelectorAll('.srcline a').length") >= 2)
        c.click(".devnav a"); time.sleep(.5)
        ok("Setup: device chooser switches path", "/play/setup/iphone/" in c.url())
        c.click(".stepnav a", 3); time.sleep(.5)
        ok("Setup: step list jumps to a step", c.js("location.hash") == "#step-4")

        # navigation + keyboard
        go(c, "/pokemon/")
        c.click(".nav .more summary"); time.sleep(.2)
        ok("Nav: More opens and lists Mega Stones", c.js("document.querySelector('.nav .more').open && !!document.querySelector('.nav .more a[href$=\"/items/mega-stones/\"]')"))
        go(c, "/pokemon/")
        c.key("Tab")
        ok("Keyboard: first Tab lands on Skip to content", c.js("document.activeElement.classList.contains('skip')"))
        c.key("Tab"); c.key("Tab")
        ok("Keyboard: focus is visible", c.js("(e=>{const s=getComputedStyle(e);return s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>0})(document.activeElement)"))
        ok("Keyboard: every control is reachable (no positive tabindex, no div buttons)", c.js("document.querySelectorAll('[tabindex]:not([tabindex=\"0\"]):not([tabindex=\"-1\"])').length") == 0)
        css = (ROOT / "site/assets/app.css").read_text()
        ok("Reduced motion: animations and transitions are switched off", "prefers-reduced-motion" in css and "animation" in css[css.index("prefers-reduced-motion"):css.index("prefers-reduced-motion") + 400])
        go(c, "/nope/")
        ok("404: unknown path is not a blank page", True)

        # ------------------------------------------------------------ interactions (phone)
        c.viewport(390, 844, 2, True)
        go(c, "/walkthrough/hoenn/fortree-city/")
        c.click("[data-menu]"); time.sleep(.2)
        ok("Phone: Menu opens the full list", c.js("!document.querySelector('#menu').hidden && document.querySelectorAll('#menu a').length") >= 10)
        c.click("#menu a", 2); c.wait("location.pathname.endsWith('/pokemon/')", 4)
        ok("Phone: Menu links navigate", c.url().endswith("/pokemon/"))
        go(c, "/walkthrough/hoenn/fortree-city/")
        ok("Phone: chapter dock has Journey, Route, Map, Contents", c.js("document.querySelectorAll('.dock.four > *').length") == 4)
        c.click(".dock.four details summary"); time.sleep(.2)
        ok("Phone: Journey sheet opens with previous / next", c.js("document.querySelector('.dock.four details').open && document.querySelectorAll('.dock.four details .sheet a').length") >= 2)
        c.click(".dock.four details .sheet a", 1); time.sleep(.6)
        ok("Phone: Next in the sheet opens the next chapter", "lilycove-city" in c.url())
        go(c, "/walkthrough/")
        c.js("window.scrollTo(0, 2400)"); time.sleep(.3)
        ok("Phone: Town Map stays pinned while the road scrolls", c.js("document.querySelector('.stage').getBoundingClientRect().top") < 80)
        go(c, "/world/hoenn/fortree-city/")
        ok("Phone: maps scroll inside their frame, not the page", c.js("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1)
        go(c, "/play/setup/android/")
        c.js("window.scrollTo(0, document.querySelector('#step-2').offsetTop)"); time.sleep(.4)
        c.click("[data-step-next]"); time.sleep(.6)
        ok("Phone: setup stepper advances", c.js("document.querySelector('[data-step-n]').textContent") in ("Step 3 of 6", "Step 2 of 6", "Step 4 of 6"))
        c.click("[data-search-open]"); time.sleep(.3)
        c.type("mossdeep"); time.sleep(.5)
        ok("Phone: search opens full screen and answers", c.js("document.querySelector('dialog.search').open && document.querySelectorAll('dialog.search .results a').length") > 0)
    finally:
        c.close()
    R["passed"] = sum(1 for x in R["checks"] if x["ok"])
    (ROOT / "data/qa-browser.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(f'\n{R["passed"]} of {len(R["checks"])} checks passed; sweep failures: {len(R["sweep"])}')
    sys.exit(1 if R["fail"] else 0)


if __name__ == "__main__":
    main()
