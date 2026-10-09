#!/usr/bin/env python3
"""Browser test of the map viewer and of Pokémon type labels, measured by what is on screen.

    python3 tools/qa_mapview.py [base-url] [--port 9412]     default http://localhost:8791
    -> qa-evidence/map-rendering/<label>.json + screenshots ; exit 1 on any failure

A map counts as drawn only if the browser decoded it at the size the layout needs and it has more than a handful of
colours on a canvas: an <img> that merely exists, or a file that merely returns 200, proves nothing (Faraway Island's
first image was a valid PNG of one flat colour). Uses its own Chrome profile prefix and port so it never attaches to,
or is killed by, another session's browser."""
import json, sys, tempfile, time
from pathlib import Path
import cdp

ROOT = Path(__file__).resolve().parent.parent
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 9412
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--port"]
BASE = (args[0] if args else "http://localhost:8791").rstrip("/")
LABEL = "live" if "github.io" in BASE else "local"
OUT = ROOT / "qa-evidence" / "map-rendering"
TYPES = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"]
WORLD = json.loads((ROOT / "data/rom/world.json").read_text())
res = []
# one page per repaired map, and one untouched map per region as a control
PAGES = [("/world/kanto/faraway-island/", "FarawayIsland_Interior_hns"), ("/world/kanto/faraway-island/", "FarawayIsland_Entrance_hns"), ("/world/kanto/southern-island/", "SouthernIsland_Interior_hns"),
         ("/world/kanto/birth-island/", "BirthIsland_Exterior_hns"), ("/world/kanto/battle-frontier/", "BattleFrontier_OutsideEast_hns"), ("/world/kanto/fuchsia-city/", "FuchsiaCity_SafariZoneBrush_hns"),
         ("/world/hoenn/petalburg-city/", "PetalburgCity_Gym"), ("/world/johto/new-bark-town/", "NewBarkTown_hns"), ("/world/hoenn/littleroot-town/", "LittlerootTown"), ("/world/far/melemele-isle/", "MelemeleIsle_hns")]
MONS = [("probopass", ["Rock", "Steel"]), ("pikachu", ["Electric"]), ("sandslash-alola", ["Ice", "Steel"]), ("meowth-galar", ["Steel"]), ("steelix", ["Steel", "Ground"])]


def ok(name, cond, detail=""):
    res.append({"name": name, "ok": bool(cond), "detail": str(detail)[:240]})
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)


def figure(c, slug):
    """Measurements of one map section, taken in the page."""
    return c.js(f"""(() => {{ const s = document.getElementById('m-{slug}'); if (!s) return null; const v = s.querySelector('.mapv'); if (!v) return {{tag: s.tagName, viewer: false}};
      const img = v.querySelector('img'), view = v.querySelector('.mapv-view'), stg = v.querySelector('.mapv-stage'); const r = img.getBoundingClientRect(), vr = view.getBoundingClientRect();
      let colours = -1; try {{ const cv = document.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight; const x = cv.getContext('2d'); x.drawImage(img, 0, 0);
        const d = x.getImageData(0, 0, cv.width, cv.height).data, set = new Set(); for (let i = 0; i < d.length; i += 4 * 7) set.add(d[i] << 16 | d[i + 1] << 8 | d[i + 2]); colours = set.size; }} catch (e) {{}}
      const mk = [...v.querySelectorAll('.mk')].map(m => m.getBoundingClientRect()).filter(b => b.width);
      return {{tag: s.tagName, viewer: true, top: s.getBoundingClientRect().top, complete: img.complete, nw: img.naturalWidth, nh: img.naturalHeight, w: r.width, h: r.height, colours,
        px: getComputedStyle(img).imageRendering, z: +getComputedStyle(stg).getPropertyValue('--z'), sw: view.scrollWidth, cw: view.clientWidth, sl: view.scrollLeft, st: view.scrollTop,
        inside: vr.left >= -1 && vr.right <= innerWidth + 1, markers: mk.length, mkIn: mk.every(b => b.left >= r.left - 12 && b.right <= r.right + 12 && b.top >= r.top - 12 && b.bottom <= r.bottom + 12),
        pageOverflow: document.documentElement.scrollWidth - innerWidth, full: v.hasAttribute('data-full'), tip: (v.querySelector('.mapv-tip') || {{}}).textContent || ''}}; }})()""")


def load(c, path, slug):
    c.nav(BASE + path + "#m-" + slug); c.wait("document.readyState==='complete'", 20)
    c.js(f"(() => {{ const i = document.querySelector('#m-{slug} .mapv img'); if (i) i.loading = 'eager'; document.getElementById('m-{slug}')?.scrollIntoView(); }})()")
    c.wait(f"(() => {{ const i = document.querySelector('#m-{slug} .mapv img'); return !i || (i.complete && i.naturalWidth > 0); }})()", 15); time.sleep(.5)


def maps(c, tag):
    for path, key in PAGES:
        m = WORLD[key]; slug = m["slug"]
        load(c, path, slug)
        f = figure(c, slug)
        if not f or not f.get("viewer"):
            ok(f"[{tag}] {m['name']}: the anchor opens a section with a map", False, f)
            continue
        ok(f"[{tag}] {m['name']}: anchor #m-{slug} lands on its own section", f["tag"] == "SECTION" and -40 <= f["top"] <= 260, f["top"])
        ok(f"[{tag}] {m['name']}: image decoded at {m['w'] * 16}×{m['h'] * 16}", f["complete"] and (f["nw"], f["nh"]) == (m["w"] * 16, m["h"] * 16), (f["nw"], f["nh"]))
        ok(f"[{tag}] {m['name']}: picture has real content ({f['colours']} colours sampled)", f["colours"] >= 12, f["colours"])
        ok(f"[{tag}] {m['name']}: drawn with hard pixels, in proportion, inside the page", f["px"] == "pixelated" and abs(f["w"] / f["h"] - m["w"] / m["h"]) < .01 and f["inside"] and f["pageOverflow"] <= 1,
           (f["px"], f["w"], f["h"], f["pageOverflow"]))
        ok(f"[{tag}] {m['name']}: {f['markers']} markers sit on the map", f["mkIn"])
    # the reported page, in full: zoom, fit, pan, markers, layers, full screen
    m = WORLD["FarawayIsland_Interior_hns"]; slug = m["slug"]; sel = f"#m-{slug} .mapv"
    load(c, "/world/kanto/faraway-island/", slug)
    c.shot(str(OUT / f"{LABEL}-{tag}-faraway-island-interior.png"))
    a = figure(c, slug)
    c.js(f"document.querySelector('{sel} [data-zoom=in]').click()"); c.js(f"document.querySelector('{sel} [data-zoom=in]').click()"); time.sleep(.3)
    b = figure(c, slug)
    ok(f"[{tag}] zoom in enlarges the map ({a['z']:.2f} → {b['z']:.2f})", b["z"] > a["z"] and b["w"] > a["w"] * 1.2, (a["w"], b["w"]))
    if b["sw"] > b["cw"] + 4:
        p = c.js(f"(() => {{ const r = document.querySelector('{sel} .mapv-view').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }})()")
        if tag == "desktop":
            c.send("Input.dispatchMouseEvent", type="mousePressed", x=p[0], y=p[1], button="left", clickCount=1)
            c.send("Input.dispatchMouseEvent", type="mouseMoved", x=p[0] - 90, y=p[1] - 40, button="left", buttons=1)
            c.send("Input.dispatchMouseEvent", type="mouseReleased", x=p[0] - 90, y=p[1] - 40, button="left", clickCount=1)
        else:
            c.js(f"document.querySelector('{sel} .mapv-view').scrollBy(90, 40)")
        time.sleep(.3)
        d = figure(c, slug)
        ok(f"[{tag}] the zoomed map pans ({'drag' if tag == 'desktop' else 'scroll'})", d["sl"] != b["sl"] or d["st"] != b["st"], (b["sl"], d["sl"], b["st"], d["st"]))
    else:
        ok(f"[{tag}] the zoomed map pans", True, "fits the frame at this zoom")
    c.js(f"document.querySelector('{sel} [data-zoom=out]').click()"); time.sleep(.2)
    ok(f"[{tag}] zoom out reduces the map", figure(c, slug)["z"] < b["z"])
    c.js(f"document.querySelector('{sel} [data-zoom=fit]').click()"); time.sleep(.3)
    e = figure(c, slug)
    ok(f"[{tag}] fit shows the whole width in the frame", e["sw"] <= e["cw"] + 1 and e["w"] <= e["cw"] + 1, (e["sw"], e["cw"], e["w"]))
    n = c.js(f"document.querySelectorAll('{sel} .mk').length")
    if n:
        c.js(f"document.querySelector('{sel} .mk').click()"); time.sleep(.2)
        t = figure(c, slug)["tip"]
        ok(f"[{tag}] selecting a marker names it", t and t != "Select a marker.", t)
        c.js(f"document.querySelector('{sel} [data-filter]').click()"); time.sleep(.2)
        hid = c.js(f"[...document.querySelectorAll('{sel} .mk')].filter(m => getComputedStyle(m).display === 'none').length")
        ok(f"[{tag}] a layer button hides its markers", hid > 0, hid)
        c.js(f"document.querySelector('{sel} [data-filter]').click()")
    c.js(f"document.querySelector('{sel} [data-expand]').click()"); time.sleep(.4)
    g = figure(c, slug)
    ok(f"[{tag}] expand opens the map full screen", g["full"] and g["cw"] >= c.w - 40, (g["full"], g["cw"]))
    c.shot(str(OUT / f"{LABEL}-{tag}-faraway-island-interior-expanded.png"))
    c.key("Escape", "Escape", 27); time.sleep(.3)
    ok(f"[{tag}] Escape closes it again", not figure(c, slug)["full"])
    for path, key in PAGES[1:7]:
        load(c, path, WORLD[key]["slug"])
        c.shot(str(OUT / f"{LABEL}-{tag}-{WORLD[key]['slug']}.png"))


def types(c, tag):
    q = """(sel) => [...document.querySelectorAll(sel)].map(t => { const r = t.getBoundingClientRect(), lh = parseFloat(getComputedStyle(t).lineHeight) || 16;
            return {t: t.textContent, shown: getComputedStyle(t).textTransform === 'uppercase' ? t.textContent.toUpperCase() : t.textContent, top: Math.round(r.top), h: r.height, lh, l: r.left, r: r.right}; })"""
    for slug, want in MONS:
        c.nav(BASE + f"/pokemon/{slug}/"); c.wait("document.readyState==='complete'", 20); time.sleep(.4)
        t = c.js(f"({q})('.typeline .type')")
        ok(f"[{tag}] {slug}: the page shows {' / '.join(want).upper()}", [x["t"] for x in t] == want, [x["shown"] for x in t])
        ok(f"[{tag}] {slug}: type labels on one line, unbroken, on screen", len({x["top"] for x in t}) == 1 and all(x["h"] <= x["lh"] * 1.5 and x["l"] >= 0 and x["r"] <= c.w for x in t), t)
        ok(f"[{tag}] {slug}: no page overflow", c.js("document.documentElement.scrollWidth - innerWidth") <= 1)
        if slug in ("probopass", "pikachu", "sandslash-alola"):
            c.shot(str(OUT / f"{LABEL}-{tag}-pokemon-{slug}.png"))
    for path in ("/postgame/gym-rematches/", "/postgame/legendaries/"):
        c.nav(BASE + path); c.wait("document.readyState==='complete'", 20); time.sleep(.5)
        t = c.js(f"({q})('.type')")
        bad = sorted({x["t"] for x in t if x["t"] not in TYPES})
        ok(f"[{tag}] {path}: all {len(t)} type labels are Pokémon types", t and not bad, bad)
        ok(f"[{tag}] {path}: no type label wraps or leaves the screen", all(x["h"] <= x["lh"] * 1.5 for x in t if x["h"]) and c.js("document.documentElement.scrollWidth - innerWidth") <= 1,
           [x["t"] for x in t if x["h"] > x["lh"] * 1.5][:4])
        if "gym" in path:
            c.js("""(() => { const a = [...document.querySelectorAll('.mon a')].find(a => a.getAttribute('href').endsWith('/pokemon/probopass/') || a.getAttribute('href').endsWith('/pokemon/steelix/')); a && a.scrollIntoView({block: 'center'}); })()""")
            time.sleep(1)
            c.js("""(() => { const a = [...document.querySelectorAll('.mon a')].find(a => a.getAttribute('href').endsWith('/pokemon/steelix/')); a && a.scrollIntoView({block: 'center'}); })()""")
            time.sleep(.5); c.shot(str(OUT / f"{LABEL}-{tag}-trainer-team-steel.png"))
    # the Pokédex list search still finds Steel-types by type, and nothing by the old wrong label
    c.nav(BASE + "/pokemon/"); c.wait("document.readyState==='complete'", 20); time.sleep(.6)
    vis = "[...document.querySelectorAll('#dex > li')].filter(l => getComputedStyle(l).display !== 'none').map(l => l.id)"
    for term, check in (("steel", lambda s: "probopass" in s and "steelix" in s and "pikachu" not in s), ("hazard", lambda s: not s)):
        c.js("(()=>{const i=document.querySelector('[data-filter-list]');i.focus();i.select();})()")
        if c.js("document.querySelector('[data-filter-list]').value"):
            c.key("Backspace", "Backspace", 8); time.sleep(.15)
        c.type(term); time.sleep(.4)
        s = c.js(vis)
        ok(f"[{tag}] Pokédex search “{term}” → {len(s)} entries", check(s), s[:5])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mk = tempfile.mkdtemp
    cdp.tempfile.mkdtemp = lambda prefix="", **k: mk(prefix="pb-mapui-", **k)      # not the shared pb-review- prefix
    c = cdp.Chrome(PORT)
    try:
        for mobile in (False, True):
            tag = "phone" if mobile else "desktop"
            c.viewport(390 if mobile else 1440, 844 if mobile else 900, 1, mobile)
            maps(c, tag)
            types(c, tag)
        # the frame follows a resize: phone → desktop on the same page
        m = WORLD["FarawayIsland_Interior_hns"]
        c.viewport(390, 844, 1, True); load(c, "/world/kanto/faraway-island/", m["slug"]); a = figure(c, m["slug"])
        c.viewport(1440, 900, 1, False); time.sleep(.5); b = figure(c, m["slug"])
        ok("resizing the window keeps the map inside its frame", b["inside"] and b["pageOverflow"] <= 1 and b["cw"] > a["cw"], (a["cw"], b["cw"]))
    finally:
        c.close()
    bad = [r for r in res if not r["ok"]]
    (OUT / f"{LABEL}.json").write_text(json.dumps({"base": BASE, "checks": len(res), "failed": len(bad), "results": res}, indent=1, ensure_ascii=False))
    print(f"{len(res)} checks, {len(bad)} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
