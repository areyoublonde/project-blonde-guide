#!/usr/bin/env python3
"""Browser test of the Legendary & Mythical field guide, measured by what a visitor actually sees.

    python3 tools/qa_legendaries.py [base-url]     default http://localhost:8765 ; e.g. https://areyoublonde.github.io/project-blonde-guide
    PB_CDP_PORT=9717 ...                           DevTools port (default: a free one; never an already-used port)
    -> qa-evidence/legendary-guide/<label>.json + screenshots ; exit 1 on any failure

Expected values come from content/legendaries.json, data/legendaries.json (the ROM-side audit) and data/availability.json;
actual values are read from the rendered page. A row counts as shown only if its computed display is not `none`.
"""
import json, os, re, socket, sys, time, urllib.request
from pathlib import Path
from cdp import Chrome

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765").rstrip("/")
LABEL = "live" if "github.io" in BASE else "local"
OUT = ROOT / "qa-evidence" / "legendary-guide"
URL = BASE + "/postgame/legendaries/"
GUIDE = json.loads((ROOT / "content/legendaries.json").read_text())
AUDIT = json.loads((ROOT / "data/legendaries.json").read_text())
AV = json.loads((ROOT / "data/availability.json").read_text())["species"]
DEX = json.loads((ROOT / "data/dex.json").read_text())
E = GUIDE["entries"]
IDS = [e["id"] for e in E]
VIS = "[...document.querySelectorAll('#legends > li')].filter(l => getComputedStyle(l).display !== 'none').map(l => l.id)"
res = []


def ok(name, cond, detail=""):
    res.append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)


def free_port():
    if os.environ.get("PB_CDP_PORT"):
        return int(os.environ["PB_CDP_PORT"])
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def load(c, url=URL):
    c.nav(url); c.wait("document.readyState==='complete'", 20); c.wait("document.querySelector('[data-lg-count]') && document.querySelector('[data-lg-count]').textContent", 10); time.sleep(.5)


def search(c, q):
    c.js(f"(()=>{{const i=document.querySelector('[data-lg-q]'); i.value={json.dumps(q)}; i.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
    time.sleep(.15)
    return c.js(VIS)


def press(c, key, v):
    c.js(f"document.querySelector('[data-lg-filter=\"{key}\"][data-v=\"{v}\"]').click()"); time.sleep(.15)
    return c.js(VIS)


def run(c, mobile):
    tag = "phone" if mobile else "desktop"
    c.viewport(390 if mobile else 1440, 844 if mobile else 900, 1, mobile)
    c.events.clear()
    load(c)
    c.js("localStorage.clear()"); load(c)

    # ---- coverage: A (ROM flags) / B (availability) / C (page)
    rows = c.js("[...document.querySelectorAll('#legends > li')].map(l => ({id:l.id, region:l.dataset.region, type:l.dataset.type, stage:l.dataset.stage, name:l.querySelector('.lg-n b').textContent}))")
    obtainable = sorted(k for k in AUDIT["entries"])
    ok(f"[{tag}] the ROM-side audit passed all its checks", AUDIT["counts"]["failed"] == 0 and AUDIT["counts"]["obtainable"] == len(E))
    ok(f"[{tag}] every obtainable Legendary / Mythical Pokémon in the availability dataset has a row", sorted(e["species"] for e in E) == obtainable and all(AV[k]["status"] == "obtainable" for k in obtainable), len(obtainable))
    ok(f"[{tag}] page lists exactly the {len(E)} guide entries, in order", [r["id"] for r in rows] == IDS, [r["id"] for r in rows][:5])
    ok(f"[{tag}] no unobtainable species has a guide row", not ({DEX[x["id"]]["slug"] for x in AUDIT["unobtainable"]} & {r["id"] for r in rows}))
    bad = [r["id"] for r, e in zip(rows, E) if (r["region"], r["type"], r["stage"]) != (e["region"], e["type"], e["stage"])]
    ok(f"[{tag}] every row carries its region, encounter type and availability", not bad, bad)
    ok(f"[{tag}] every row is visible before any search", c.js(VIS) == IDS)
    ok(f"[{tag}] counter reads {len(E)} of {len(E)}", c.js("document.querySelector('[data-lg-count]').textContent") == f"{len(E)} of {len(E)}")
    thin = c.js("""[...document.querySelectorAll('#legends > li')].filter(l => { const s=[...l.querySelectorAll('.lg-main section')]; const t=s.map(x=>x.querySelector('.label').textContent.trim());
      return t.join('|') !== 'Where to start|What you need|What to do|The encounter|Afterwards' || s.some(x => x.textContent.trim().length < 40) || l.querySelectorAll('.lg-steps li').length < 3 || l.querySelectorAll('.lg-side .kv div').length < 9; }).map(l => l.id)""")
    ok(f"[{tag}] every entry has all five sections with real content, 3+ steps and its fact sheet", not thin, thin)
    lv = c.js("Object.fromEntries([...document.querySelectorAll('#legends > li')].map(l => [l.id, l.querySelector('.lg-side .kv dd').textContent]))")
    bad = [e["id"] for e in E if any(str(x) not in lv[e["id"]] for x in AUDIT["entries"][e["species"]]["levels"])]
    ok(f"[{tag}] each entry shows every level the availability audit records for it", not bad, bad)

    # ---- search: by what is visible
    for q, want in [("suicune", ["suicune"]), ("ho-oh", ["ho-oh"]), ("hooh", ["ho-oh"]), ("Ho Oh", ["ho-oh"]), ("mew", ["mewtwo", "mew"]), ("regi", ["regirock", "regice", "registeel", "regieleki", "regidrago", "regigigas"]),
                    ("tapu", ["tapu-koko", "tapu-lele", "tapu-bulu", "tapu-fini"]), ("galarian", ["articuno-galar", "zapdos-galar", "moltres-galar"]), ("ARCEUS", ["arceus"]),
                    ("eon ticket", ["latias", "latios"]), ("roaming", ["raikou", "entei", "latias", "latios"])]:
        got = search(c, q)
        ok(f"[{tag}] search “{q}” shows {len(want)}", sorted(got) == sorted(want), got)
    for q in ("dialga", "cosmog", "zzzz"):
        got = search(c, q)
        ok(f"[{tag}] search “{q}” shows nothing and says so", got == [] and c.js("getComputedStyle(document.querySelector('[data-lg-empty]')).display !== 'none'"), got)
    c.js("document.querySelector('[data-lg-reset]').click()"); time.sleep(.2)
    ok(f"[{tag}] clearing restores all rows", c.js(VIS) == IDS and c.js("document.querySelector('[data-lg-q]').value") == "")

    # ---- filters
    if mobile:
        ok(f"[{tag}] filters start collapsed on a phone", not c.js("document.querySelector('.lg-filters').open"))
        c.js("document.querySelector('.lg-filters > summary').click()"); time.sleep(.2)
    else:
        ok(f"[{tag}] filters start open on a desktop", c.js("document.querySelector('.lg-filters').open"))
    for key, vals in (("region", sorted({e["region"] for e in E})), ("type", sorted({e["type"] for e in E})), ("stage", sorted({e["stage"] for e in E}))):
        for v in vals:
            got = press(c, key, v)
            want = [e["id"] for e in E if e[key] == v]
            ok(f"[{tag}] filter {key}={v} shows {len(want)}", got == want, got)
        press(c, key, "")
    got = (press(c, "region", "kanto"), press(c, "type", "roaming"))[1]
    ok(f"[{tag}] filters combine (Kanto + roaming = Latias, Latios)", got == ["latias", "latios"], got)
    ok(f"[{tag}] active filters are named in the panel", c.js("document.querySelector('[data-lg-active]').textContent") == "Kanto · Roaming")
    got = search(c, "latios")
    ok(f"[{tag}] search and filters combine", got == ["latios"], got)
    hid = c.js("[...document.querySelectorAll('#legends > li[hidden]')].filter(l => getComputedStyle(l).display !== 'none').length")
    ok(f"[{tag}] no hidden row is still on screen (CSS regression)", hid == 0, hid)
    c.js("document.querySelector('[data-lg-q]').value='zz'; document.querySelector('[data-lg-q]').dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('[data-lg-reset]').click()"); time.sleep(.2)
    ok(f"[{tag}] reset clears search and all three filters", c.js(VIS) == IDS and c.js("[...document.querySelectorAll('[data-lg-filter][aria-pressed=true]')].every(b => !b.dataset.v)"))

    # ---- spoilers
    blur = "getComputedStyle(document.querySelector('#suicune .lg-w')).filter"
    ok(f"[{tag}] locations are blurred by default", "blur" in c.js(blur))
    c.js("document.querySelector('.lg-spoil').click()"); time.sleep(.3)
    ok(f"[{tag}] the spoiler switch reveals every location", c.js("[...document.querySelectorAll('#legends .lg-w')].every(w => getComputedStyle(w).filter === 'none')") and c.js("document.querySelector('.lg-spoil').textContent") == "Spoilers: shown")
    load(c)
    ok(f"[{tag}] the choice is remembered on reload", c.js(blur) == "none")
    c.js("document.querySelector('.lg-spoil').click()"); time.sleep(.3)
    ok(f"[{tag}] switching back hides them again", "blur" in c.js(blur))
    c.js("document.querySelector('#arceus > details > summary').click()"); time.sleep(.3)
    ok(f"[{tag}] opening an entry shows its own location", c.js("getComputedStyle(document.querySelector('#arceus .lg-w')).filter") == "none" and "blur" in c.js(blur))
    n = c.js("document.querySelectorAll('#arceus .blur').length")
    ok(f"[{tag}] Arceus keeps its story details behind tap-to-reveal", n >= 2 and "blur" in c.js("getComputedStyle(document.querySelector('#arceus .blur')).filter"), n)
    c.js("document.querySelector('#arceus .blur').click()"); time.sleep(.2)
    ok(f"[{tag}] tapping a hidden detail reveals it", c.js("getComputedStyle(document.querySelector('#arceus .blur')).filter") == "none")

    # ---- Arceus: the two battles are told apart
    t = c.js("document.querySelector('#arceus').textContent")
    ok(f"[{tag}] Arceus: first battle is stated as not catchable, second as catchable", "You cannot throw a Ball and you cannot run" in t and "Only the second can end in a capture" in t and "100 (cannot be caught), then 80" in t)

    # ---- deep links, cross links, map
    load(c, URL + "#mew")
    ok(f"[{tag}] a link to #mew opens that entry", c.js("document.querySelector('#mew > details').open") and c.js("(r => r.top >= 0 && r.top < innerHeight)(document.querySelector('#mew').getBoundingClientRect())"))
    c.wait("(i => i && i.complete && i.naturalWidth > 0)(document.querySelector('#mew .mapv-stage img'))", 15)
    m = c.js("""(() => { const d=document.querySelector('#mew'), v=d.querySelector('.mapv-view'), k=d.querySelector('.mk'), i=d.querySelector('.mapv-stage img'); v.scrollIntoView({block:'center'});
      const a=v.getBoundingClientRect(), b=k.getBoundingClientRect(); return {img:i.naturalWidth, marks:d.querySelectorAll('.mk').length, inside: b.left>=a.left && b.right<=a.right && b.top>=a.top && b.bottom<=a.bottom, label:k.dataset.label}; })()""")
    ok(f"[{tag}] Mew’s map loads with the Old Sea Map marked and in view", m["img"] > 0 and m["marks"] == 1 and m["inside"] and m["label"] == "Old Sea Map", m)
    c.js("document.querySelector('#mew .mk').click()"); time.sleep(.2)
    ok(f"[{tag}] selecting the marker explains it", "Old Sea Map" in c.js("document.querySelector('#mew .mapv-tip').textContent"))
    z0 = c.js("getComputedStyle(document.querySelector('#mew .mapv-stage')).getPropertyValue('--z')")
    c.js("document.querySelector('#mew [data-zoom=in]').click()"); time.sleep(.2)
    ok(f"[{tag}] the map zooms", float(c.js("getComputedStyle(document.querySelector('#mew .mapv-stage')).getPropertyValue('--z')")) > float(z0))
    c.js("document.querySelector('#mew a[data-lg-open]').click()"); time.sleep(.4)
    ok(f"[{tag}] “How legendaries return” opens the shared section", c.js("document.querySelector('#league-reset').open") and c.url().endswith("#league-reset"))
    c.shot(str(OUT / f"{LABEL}-{tag}-entry.png"))
    load(c, URL + "#regirock"); c.js("document.querySelector('[data-lg-filter=region][data-v=hoenn]').click()"); time.sleep(.2)
    c.js("document.querySelector('#regigigas').hidden || 1; location.hash = '#regigigas'"); time.sleep(.5)
    ok(f"[{tag}] a link to an entry hidden by a filter clears the filter and opens it", c.js("document.querySelector('#regigigas > details').open && getComputedStyle(document.querySelector('#regigigas')).display !== 'none'"))

    # every link on the page resolves; same-page anchors exist
    hrefs = c.js("[...new Set([...document.querySelectorAll('main a[href]')].map(a => a.href))]")
    here = c.js("location.origin + location.pathname")
    ids = set(c.js("[...document.querySelectorAll('[id]')].map(e => e.id)"))
    broken = []
    for h in hrefs:
        page, _, frag = h.partition("#")
        if page == here:
            if frag and frag not in ids:
                broken.append(h)
            continue
        if not page.startswith(BASE):
            continue
        try:
            body = urllib.request.urlopen(urllib.request.Request(page, headers={"User-Agent": "pb-qa"}), timeout=20).read().decode("utf-8", "replace")
            if frag and not re.search(r'id="?%s["\s>]' % re.escape(frag), body):
                broken.append(h)
        except Exception as ex:
            broken.append(f"{h} ({ex})")
    kinds = {k: sum(1 for h in hrefs if f"/{k}/" in h) for k in ("pokemon", "world", "walkthrough", "items")}
    ok(f"[{tag}] all {len(hrefs)} links in the guide resolve, anchors included", not broken, broken[:4])
    ok(f"[{tag}] the guide links to Pokédex pages, atlas places, chapters and items", kinds["pokemon"] >= len(E) and kinds["world"] >= 20 and kinds["walkthrough"] >= 10 and kinds["items"] >= 10, kinds)

    # from the rest of the site, back to the guide
    load_plain = lambda url: (c.nav(url), c.wait("document.readyState==='complete'", 20), time.sleep(.6))
    load_plain(BASE + "/pokemon/arceus/")
    href = c.js("(a => a && a.getAttribute('href'))([...document.querySelectorAll('a')].find(a => /How to get Arceus/.test(a.textContent)))")
    ok(f"[{tag}] Arceus’s Pokédex page links to its guide entry", bool(href) and href.endswith("/postgame/legendaries/#arceus"), href)
    load_plain(BASE + "/pokemon/pikachu/")
    ok(f"[{tag}] an ordinary Pokémon’s page has no legendary link", not c.js("[...document.querySelectorAll('a')].some(a => /legendaries\\/#/.test(a.href))"))
    load_plain(BASE + "/world/far/sinjoh-ruins/")
    ok(f"[{tag}] the Sinjoh Ruins atlas page links back to the guide", c.js("[...document.querySelectorAll('main a')].some(a => /\\/postgame\\/legendaries\\/$/.test(a.pathname))"))
    load_plain(BASE + "/pokemon/")
    ok(f"[{tag}] the Pokédex index links to the guide", c.js("[...document.querySelectorAll('main a')].some(a => /\\/postgame\\/legendaries\\/$/.test(a.pathname))"))
    n_dex = c.js("document.querySelectorAll('#dex > li').length")
    c.js("(()=>{const i=document.querySelector('[data-filter-list]'); i.value='mewtwo'; i.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(.3)
    shown = c.js("[...document.querySelectorAll('#dex > li')].filter(l => getComputedStyle(l).display !== 'none').map(l => l.id)")
    ok(f"[{tag}] Pokédex index unchanged: {n_dex} obtainable entries, and its search still hides rows", n_dex == sum(1 for v in AV.values() if v["status"] == "obtainable") and shown == ["mewtwo"], f"{n_dex} {shown}")
    ok(f"[{tag}] the menu offers the guide", c.js("[...document.querySelectorAll('header.top a, #menu a')].some(a => /\\/postgame\\/legendaries\\/$/.test(a.pathname))"))

    # global search
    load(c)
    c.js("document.querySelector('[data-search-open]').click()"); time.sleep(.3)
    for q, frag in (("how to get suicune", "#suicune"), ("arceus", "#arceus"), ("legendary", "")):
        c.js(f"(()=>{{const i=document.querySelector('dialog.search input'); i.value={json.dumps(q)}; i.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
        c.wait("document.querySelectorAll('dialog.search .results a').length > 0", 8); time.sleep(.3)
        hits = c.js("[...document.querySelectorAll('dialog.search .results a')].filter(a => a.offsetParent !== null).map(a => a.getAttribute('href'))")
        ok(f"[{tag}] global search “{q}” offers the guide" + (f" at {frag}" if frag else ""), any(h.endswith("/postgame/legendaries/" + frag) for h in hits), hits[:4])
    c.js("document.querySelector('dialog.search').close()")

    # ---- layout
    load(c)
    over = c.js("document.documentElement.scrollWidth - innerWidth")
    ok(f"[{tag}] no horizontal overflow, entries closed", over <= 0, over)
    c.js("document.querySelectorAll('details.lg').forEach(d => d.open = true)"); time.sleep(.8)
    over = c.js("document.documentElement.scrollWidth - innerWidth")
    wide = c.js("[...document.querySelectorAll('.lg-body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && !e.closest('.mapv-view')).length")
    ok(f"[{tag}] no horizontal overflow with every entry open", over <= 0 and wide == 0, f"{over}px, {wide} elements")
    if mobile:
        ok(f"[{tag}] the dock is on screen with its four controls", c.js("(d => d && getComputedStyle(d).display !== 'none' && d.children.length === 4 && d.getBoundingClientRect().right <= innerWidth)(document.querySelector('.dock'))"))
        small = c.js("[...document.querySelectorAll('.lg > summary, [data-lg-filter], .lg-spoil')].filter(e => e.offsetParent && e.getBoundingClientRect().height < 44).length")
        ok(f"[{tag}] every control is at least 44px tall", small == 0, small)
    c.js("document.querySelectorAll('details.lg').forEach(d => d.open = false); document.querySelector('#find').scrollIntoView()"); time.sleep(.4)
    c.shot(str(OUT / f"{LABEL}-{tag}-index.png"))

    errs = [e for e in c.events if e.get("method") in ("Runtime.exceptionThrown",) or (e.get("method") == "Runtime.consoleAPICalled" and e["params"].get("type") == "error")]
    ok(f"[{tag}] no JavaScript errors", not errs, json.dumps(errs)[:280])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = Chrome(port=free_port())
    try:
        run(c, False)
        run(c, True)
    finally:
        c.close()
    fails = [r for r in res if not r["ok"]]
    (OUT / f"{LABEL}.json").write_text(json.dumps({"base": BASE, "checks": len(res), "failed": len(fails), "results": res}, indent=1, ensure_ascii=False))
    print(f"{len(res)} checks, {len(fails)} failed -> {OUT / (LABEL + '.json')}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
