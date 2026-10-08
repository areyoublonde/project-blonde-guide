#!/usr/bin/env python3
"""Browser test of the Pokédex index: search, filters and availability, measured by what is actually visible.

    python3 tools/qa_pokedex.py [base-url]       default http://localhost:8765 ; e.g. https://areyoublonde.github.io/project-blonde-guide
    -> qa-evidence/pokedex-audit/<label>.json + screenshots ; exit 1 on any failure

A row counts as shown only if its computed display is not `none`. (The first version of the site set the `hidden`
attribute correctly but a stylesheet rule kept the rows on screen; checking the attribute alone missed that.)
"""
import json, sys, time
from pathlib import Path
from cdp import Chrome

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765").rstrip("/")
LABEL = "live" if "github.io" in BASE else "local"
OUT = ROOT / "qa-evidence" / "pokedex-audit"
AV = json.loads((ROOT / "data/availability.json").read_text())["species"]
DEX = json.loads((ROOT / "data/dex.json").read_text())
PUBLIC = sorted(DEX[k]["slug"] for k, v in AV.items() if v["status"] == "obtainable")
EXCLUDED = sorted(DEX[k]["slug"] for k, v in AV.items() if v["status"] != "obtainable")
VIS = "[...document.querySelectorAll('#dex > li')].filter(l => getComputedStyle(l).display !== 'none')"
res = []


def ok(name, cond, detail=""):
    res.append({"name": name, "ok": bool(cond), "detail": str(detail)[:240]})
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)


def run(c, mobile):
    tag = "phone" if mobile else "desktop"
    c.viewport(390 if mobile else 1440, 844 if mobile else 900, 1, mobile)
    c.events.clear()
    c.nav(BASE + "/pokemon/"); c.wait("document.readyState==='complete'", 20); time.sleep(.8)
    ids = c.js("[...document.querySelectorAll('#dex > li')].map(l => l.id)")
    ok(f"[{tag}] index lists exactly the {len(PUBLIC)} obtainable entries", sorted(ids) == PUBLIC, f"{len(ids)} rows; extra {sorted(set(ids) - set(PUBLIC))[:4]}; missing {sorted(set(PUBLIC) - set(ids))[:4]}")
    ok(f"[{tag}] no excluded species is in the index", not (set(ids) & set(EXCLUDED)), sorted(set(ids) & set(EXCLUDED))[:5])
    ok(f"[{tag}] every row is visible before any search", c.js(VIS + ".length") == len(ids))

    def search(q):
        c.js("(()=>{const i=document.querySelector('[data-filter-list]');i.focus();i.select();})()")
        if c.js("document.querySelector('[data-filter-list]').value"):
            c.key("Backspace", "Backspace", 8); time.sleep(.15)
        if q:
            c.type(q)
        time.sleep(.35)
        return c.js(f"({{shown: {VIS}.map(l => l.id), count: document.querySelector('[data-filter-count]').textContent, empty: getComputedStyle(document.querySelector('[data-filter-empty]')).display !== 'none', value: document.querySelector('[data-filter-list]').value}})")

    for q, must, n in (("pikachu", ["pikachu"], 1), ("Pikachu", ["pikachu"], 1), ("PIKA", ["pikachu"], None), ("eevee", ["eevee"], 1), ("ninetales", ["ninetales", "ninetales-alola"], 2),
                       ("alolan", ["vulpix-alola", "raichu-alola", "marowak-alola"], 18), ("vulpix alola", ["vulpix-alola"], 1), ("galarian", ["meowth-galar", "ponyta-galar"], 15), ("hisui", ["growlithe-hisui"], 7),
                       ("char", ["charmander", "charmeleon", "charizard"], None), ("mr. mime", ["mr-mime"], None), ("farfetch'd", ["farfetch-d"], 2), ("ho-oh", ["ho-oh"], 1), ("Ho Oh", ["ho-oh"], 1), ("nidoran", ["nidoran-f", "nidoran-m"], 2), ("porygon", ["porygon", "porygon2", "porygon-z"], 3), ("unown", ["unown"], 1)):
        r = search(q)
        good = all(m in r["shown"] for m in must) and (n is None or len(r["shown"]) == n) and 0 < len(r["shown"]) < len(ids) and r["value"] == q
        ok(f"[{tag}] typing “{q}” filters at once to {len(r['shown'])} row(s) incl. {must[0]}", good, r["shown"][:6])
        ok(f"[{tag}] “{q}”: result count reads {len(r['shown'])} of {len(ids)}", r["count"] == f"{len(r['shown'])} of {len(ids)}", r["count"])
        if q == "pikachu":
            c.shot(str(OUT / f"02-{LABEL}-{tag}-search-pikachu.png"))
    r = search("zzzzqq")
    ok(f"[{tag}] no match: zero rows and the empty state is shown", len(r["shown"]) == 0 and r["empty"], r)
    c.shot(str(OUT / f"03-{LABEL}-{tag}-no-results.png"))
    r = search("")
    ok(f"[{tag}] clearing the search restores all {len(ids)} entries", len(r["shown"]) == len(ids) and not r["empty"], len(r["shown"]))
    for q in ("greninja", "garchomp", "lucario"):
        r = search(q)
        ok(f"[{tag}] unobtainable “{q}” is not listed", not any(x.replace("-", "") == q.replace("-", "") for x in r["shown"]), r["shown"][:4])
    search("")
    # type / region filters, alone and combined with search
    c.js("document.querySelector('[data-region-filter=hoenn]').scrollIntoView({block:'center'})"); c.click("[data-region-filter=hoenn]"); time.sleep(.3)
    hoenn = c.js(VIS + ".map(l => l.dataset.r)")
    ok(f"[{tag}] region filter Hoenn shows only Hoenn entries ({len(hoenn)})", 0 < len(hoenn) < len(ids) and all("hoenn" in x.split() for x in hoenn))
    r = search("water")
    both = c.js(VIS + ".map(l => [l.dataset.r, l.dataset.f])")
    ok(f"[{tag}] search + region filter combine ({len(both)} Water in Hoenn)", 0 < len(both) < len(hoenn) and all("hoenn" in a.split() and "water" in b for a, b in both))
    r = search("")
    c.click("[data-region-filter=nowild]"); time.sleep(.3)
    nw = c.js(VIS + ".length")
    ok(f"[{tag}] method filter ‘Evolution or egg only’ works ({nw})", 0 < nw < len(ids))
    c.click("[data-region-filter='']"); time.sleep(.3)
    ok(f"[{tag}] All restores the full list", c.js(VIS + ".length") == len(ids))
    r = search("ghost")
    ok(f"[{tag}] type search “ghost” narrows the list", 0 < len(r["shown"]) < 40 and "gengar" in r["shown"], len(r["shown"]))
    search("")
    over = c.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    ok(f"[{tag}] no sideways scroll on the index", over <= 1, over)
    errs = [e for e in c.events if e.get("method") in ("Runtime.exceptionThrown",)]
    ok(f"[{tag}] no JavaScript error on the index", not errs, json.dumps(errs[:1])[:200])
    # detail pages, evolution links, wording
    for slug_, want in (("pikachu", "Wild encounter"), ("gengar", "Evolve"), ("meowth-galar", "Bill"), ("porygon", "Game Corner"), ("porygon2", "Use Upgrade"), ("porygon-z", "Use Dubious Disc"), ("cleffa", "Day Care"), ("milotic", "Beauty"), ("unown", "Ruins")):
        c.events.clear()
        c.nav(BASE + f"/pokemon/{slug_}/"); c.wait("document.readyState==='complete'", 20); time.sleep(.4)
        t = c.js("document.querySelector('.entry-where').textContent")
        h1 = c.js("[...document.querySelectorAll('h1')].filter(e=>e.offsetParent!==null).length")
        bad = "Not available" in t or "no source" in t.lower() or "cannot say it is obtainable" in t
        errs = [e for e in c.events if e.get("method") == "Runtime.exceptionThrown"]
        ok(f"[{tag}] /pokemon/{slug_}/ loads and explains how to obtain it ({want})", h1 == 1 and want in t and not bad and not errs, t[:120])
    c.nav(BASE + "/pokemon/haunter/"); c.wait("document.readyState==='complete'", 20); time.sleep(.4)
    hrefs = c.js("[...document.querySelectorAll('.evo a')].map(a => a.getAttribute('href'))")
    ok(f"[{tag}] evolution family links are present (Gastly, Haunter, Gengar)", len(hrefs) == 3 and all("/pokemon/" in h for h in hrefs), hrefs)
    c.js("[...document.querySelectorAll('.evo a')].pop().scrollIntoView({block:'center'})"); time.sleep(.2); c.click(".evo a", 2); time.sleep(.9)
    ok(f"[{tag}] an evolution link opens that Pokémon", c.js("location.pathname").endswith("/pokemon/gengar/"))
    c.nav(BASE + "/pokemon/porygon/"); c.wait("document.readyState==='complete'", 20); time.sleep(.4)
    # Porygon2 and Porygon-Z are obtainable (Up-Grade: Silph Co gift, Mahogany shop); until 2026-10-09 the audit wrongly left them out
    ok(f"[{tag}] Porygon's family links Porygon2 and Porygon-Z, none marked not obtainable", c.js("[...document.querySelectorAll('.evo a')].map(a => a.getAttribute('href').split('/').filter(Boolean).pop())") == ["porygon", "porygon2", "porygon-z"] and not c.js("document.querySelector('.evo').textContent.includes('not obtainable')"))
    for slug_ in ("turtwig", "greninja", "lucario"):
        code = c.js(f"fetch('{BASE}/pokemon/{slug_}/').then(r => r.status)")
        ok(f"[{tag}] no public page exists for unobtainable {slug_}", code == 404, code)
    # global search still works and only knows public Pokémon
    c.nav(BASE + "/"); c.wait("document.readyState==='complete'", 20); time.sleep(.5)
    c.click("[data-search-open]"); time.sleep(.4); c.type("pikachu"); time.sleep(1.0)
    hs = c.js("[...document.querySelectorAll('dialog.search .results a')].map(a => a.getAttribute('href'))") or []
    ok(f"[{tag}] global search finds Pikachu", any(h.endswith("/pokemon/pikachu/") for h in hs), hs[:3])
    c.js("(()=>{const i=document.querySelector('dialog.search input');i.value='';i.dispatchEvent(new Event('input'))})()"); c.type("greninja"); time.sleep(1.0)
    hs = c.js("[...document.querySelectorAll('dialog.search .results a')].map(a => a.getAttribute('href'))") or []
    ok(f"[{tag}] global search does not offer a page for unobtainable Greninja", not any("/pokemon/greninja" in h for h in hs), hs[:3])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = Chrome()
    try:
        run(c, False)
        run(c, True)
        # the other filtered lists share the same code and had the same defect
        c.viewport(1440, 900)
        for path, sel, q in (("/items/", "#items > li", "surf"), ("/trainers/", ".people > li", "wallace"), ("/world/", "[data-atlas-panel=jk] .places > li", "ecruteak"), ("/items/mega-stones/", "#megas > li", "charizard")):
            c.nav(BASE + path); c.wait("document.readyState==='complete'", 20); time.sleep(.5)
            total = c.js(f"document.querySelectorAll('{sel}').length")
            c.click("[data-filter-list]"); c.type(q); time.sleep(.4)
            shown = c.js(f"[...document.querySelectorAll('{sel}')].filter(l => getComputedStyle(l).display !== 'none').length")
            ok(f"[desktop] {path} filter “{q}” visibly narrows {total} rows to {shown}", 0 < shown < total)
    finally:
        c.close()
    p = sum(r["ok"] for r in res)
    (OUT / f"browser-{LABEL}.json").write_text(json.dumps({"base": BASE, "browser": "Chrome (headless)", "date": time.strftime("%Y-%m-%d"), "passed": p, "total": len(res), "checks": res}, indent=1, ensure_ascii=False))
    print(f"{p} of {len(res)} passed against {BASE}")
    sys.exit(0 if p == len(res) else 1)


if __name__ == "__main__":
    main()
