#!/usr/bin/env python3
"""Browser test of Download & Play and the Discord entry points, measured by what a visitor actually sees.

    python3 tools/qa_play.py [base-url]     default http://localhost:8765 ; e.g. https://areyoublonde.github.io/project-blonde-guide
    PB_CDP_PORT=9717 ...                    DevTools port (default: a free one; never an already-used port)
    -> qa-evidence/download-play/<label>.json + screenshots ; exit 1 on any failure

Expected values come from content/releases.json, content/site.json and content/play.json; actual values are read from the
rendered page. The invite itself is checked against Discord's public invite API (server name, no expiry).
"""
import json, os, socket, sys, time, urllib.request
from pathlib import Path
from cdp import Chrome

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765").rstrip("/")
LABEL = "live" if "github.io" in BASE else "local"
OUT = ROOT / "qa-evidence" / "download-play"
J = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
REL_ALL, SITE, PLAY = J("content/releases.json"), J("content/site.json"), J("content/play.json")
REL = next(r for r in REL_ALL["releases"] if r["version"] == REL_ALL["current"])
DC = SITE["community"]["discord"]
PUBLIC = REL["status"] == "released"
res = []
GAMEFILE = "[...document.querySelectorAll('a')].filter(a=>/\\.(gba|zip|bps|ips|ups|xdelta|7z|rar)(\\?|#|$)/i.test(a.href)).map(a=>a.href)"
SHOWN = "(s=>{const e=document.querySelector(s);if(!e)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'})"


def ok(name, cond, detail=""):
    res.append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)


def free_port():
    if os.environ.get("PB_CDP_PORT"):
        return int(os.environ["PB_CDP_PORT"])
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def go(c, path):
    c.nav(BASE + path); c.wait("document.readyState==='complete'", 20); time.sleep(.4)


def invite():
    code = DC["url"].rsplit("/", 1)[1]
    req = urllib.request.Request(f"https://discord.com/api/v10/invites/{code}?with_expiration=true", headers={"User-Agent": "pb-guide-qa"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    ok("Discord: the configured invite resolves to the official server and never expires", d["guild"]["name"] == DC["server"] and d.get("expires_at") is None, (d["guild"]["name"], d.get("expires_at")))


def run(c, mobile):
    tag = "phone" if mobile else "desktop"
    c.viewport(390 if mobile else 1440, 844 if mobile else 900, 1, mobile)
    go(c, "/play/"); c.js("localStorage.clear()"); go(c, "/play/")
    txt = lambda sel: c.js(f"(document.querySelector({json.dumps(sel)})||{{}}).textContent||''")

    # ---- release record on the page
    ok(f"[{tag}] page is Download & Play for Pokémon Project Blonde", txt("h1") == "Pokémon Project Blonde" and "Download & Play" in c.js("document.title"))
    ok(f"[{tag}] title-screen artwork is loaded and shown crisp", c.js("(i=>i.complete&&i.naturalWidth===240&&getComputedStyle(i).imageRendering==='pixelated')(document.querySelector('.titleart img'))"))
    kv = c.js("Object.fromEntries([...document.querySelectorAll('#release dl > div')].map(d=>[d.querySelector('dt').textContent,d.querySelector('dd').textContent]))")
    ok(f"[{tag}] version and build come from the release record", REL["public_version"] in kv["Version"] and REL["internal_build"] in kv["Version"] and txt(".relline b") == REL["public_version"], kv["Version"])
    ok(f"[{tag}] status shown is the recorded one", REL["status_short"] in kv["Status"] and REL["status_short"] in txt(".relline"), kv["Status"])
    ok(f"[{tag}] file format, size, save compatibility and link version shown", REL["file"]["size"] in kv["File"] and REL["save_compatibility_short"] in kv["Saves"] and REL["link_protocol"] in kv["Link version"])
    ok(f"[{tag}] every release highlight is listed", all(h in txt("#release") for h in REL["highlights"]))
    state = c.js("document.querySelector('.wrap.play').dataset.releaseState")
    if not PUBLIC:
        ok(f"[{tag}] pre-release: state, 'not released' wording, no date and no checksum invented", state == "prerelease" and "Not released yet" in txt(".relline") and kv["Released"] == "Not announced" and kv["SHA-256"] == "Published with the release", (state, kv["Released"], kv["SHA-256"]))
        ok(f"[{tag}] pre-release: no download control of any kind, enabled or disabled", c.js("document.querySelectorAll('[data-download],[aria-disabled],button[disabled]').length") == 0)
        ok(f"[{tag}] pre-release: no link to a game or patch file anywhere on the page", c.js(GAMEFILE) == [], c.js(GAMEFILE))
        ok(f"[{tag}] pre-release: the primary action is the Discord invite", c.js("(a=>a&&a.matches('a.btn[data-discord]')&&a.href)(document.querySelector('.relhero .actions > :first-child'))") == DC["url"])
        ok(f"[{tag}] pre-release: Get the game says plainly that nothing is released", "is not released yet" in txt("#get"))
    elif state == "patcher":
        ok(f"[{tag}] released: status, date and the finished game's checksum come from the release record", "Released" in txt(".relline") and REL["date"] in kv["Released"] and REL["sha256"] in kv["SHA-256"] and "Emerald" in kv["You need"], (kv["Released"], kv["Status"]))
        ok(f"[{tag}] released: the primary action leads to the in-page patcher, with one file selector", c.js("document.querySelector('.relhero .actions > :first-child').getAttribute('href')") == "#get" and c.js("document.querySelectorAll('#get [data-patcher] [data-mk-file]').length") == 1)
        ok(f"[{tag}] released: no link to a complete game file anywhere on the page", c.js("[...document.querySelectorAll('a')].filter(a=>/\\.(gba|zip|7z|rar)(\\?|#|$)/i.test(a.href)).length") == 0)
    else:
        ok(f"[{tag}] released: one primary download pointing at the approved URL, with date and checksum", c.js("document.querySelector('.relhero a.btn[data-download]').href") == REL["download"]["url"] and REL["sha256"] in kv["SHA-256"] and REL["date"] in kv["Released"])

    # ---- device setup
    devs = c.js("[...document.querySelectorAll('.devices a')].map(a=>[a.querySelector('b').textContent,a.querySelector('span').textContent,a.getAttribute('href')])")
    ok(f"[{tag}] four devices with their emulators", [(d[0], d[1]) for d in devs] == [(d["name"], d["emulator"]) for d in PLAY["devices"]], devs)
    c.js("document.querySelector('.relhero .actions a.link').click()"); time.sleep(.6)
    ok(f"[{tag}] 'Set up your device' jumps to the device list", c.js("location.hash") == "#devices")
    c.js("document.querySelector('.devices a').click()"); c.wait("location.pathname.includes('/play/setup/iphone/')", 6)
    ok(f"[{tag}] a device opens its setup guide", "/play/setup/iphone/" in c.url())
    for d in PLAY["devices"]:
        go(c, f"/play/setup/{d['id']}/")
        ok(f"[{tag}] setup · {d['id']}: {len(d['steps'])} steps, update link and Discord help", c.js("document.querySelectorAll('.steps > li').length") == len(d["steps"])
           and c.js(f"!!document.querySelector('a[href$=\"/play/#update-{d['id']}\"]')") and c.js("(a=>a&&a.href)(document.querySelector('.helpline a[data-discord]'))") == DC["url"])

    # ---- update guide
    go(c, "/play/")
    up = PLAY["update"]
    ok(f"[{tag}] update section has the exact title", txt("#update h2") == up["title"])
    ok(f"[{tag}] update: all devices collapsed at first, each with its own steps", c.js("[...document.querySelectorAll('#update details.upd')].map(d=>[d.id,d.open,d.querySelectorAll('ol li').length])") == [[f"update-{d['id']}", False, len(d["steps"])] for d in up["devices"]])
    c.js("document.querySelector('#update-windows summary').click()"); time.sleep(.3)
    c.js("document.querySelector('#update-iphone summary').click()"); time.sleep(.3)
    ok(f"[{tag}] update: choosing a device shows its steps and closes the other", c.js("[...document.querySelectorAll('#update details.upd')].filter(d=>d.open).map(d=>d.id)") == ["update-iphone"] and c.js(SHOWN + "('#update-iphone ol li')"))
    go(c, "/play/#update-android")
    ok(f"[{tag}] update: a direct link opens that device's steps", c.js("document.getElementById('update-android').open") and "Close Content" in txt("#update-android"))
    t = txt("#update")
    ok(f"[{tag}] update: covers in-game save vs save state, backup, restore, checking and rollback", all(x in t for x in ("save state", "Back up", "Restore", "Continue", up["check_title"], up["rollback_title"], "Do not save")))
    ok(f"[{tag}] update: does not promise future save compatibility", "not a promise for every future version" in t)
    ok(f"[{tag}] old #update / #backup / #restore / #move / #link / #save / #trouble / #changelog anchors all exist", c.js("['update','backup','restore','move','link','save','trouble','changelog','rollback','release','get','devices'].filter(i=>!document.getElementById(i))") == [])

    # ---- troubleshooting
    qs = c.js("[...document.querySelectorAll('#trouble details.qa summary b')].map(b=>b.textContent)")
    ok(f"[{tag}] troubleshooting lists every written problem", qs == [a for a, _ in PLAY["trouble"]], len(qs))
    c.js("document.querySelector('#trouble details.qa summary').click()"); time.sleep(.2)
    ok(f"[{tag}] troubleshooting: an answer opens", c.js("document.querySelector('#trouble details.qa').open") and c.js(SHOWN + "('#trouble details.qa > div p')"))
    ok(f"[{tag}] troubleshooting ends with Discord support", c.js("(a=>a&&a.href)(document.querySelector('#trouble .support a[data-discord]'))") == DC["url"])

    # ---- Discord everywhere it should be, and only the configured URL
    for path in ("/", "/play/", "/stuck/", "/walkthrough/johto/new-bark-town/", "/pokemon/", "/postgame/legendaries/"):
        go(c, path)
        links = c.js("[...document.querySelectorAll('a[href*=\"discord\"]')].map(a=>[a.href,a.target,a.rel,!!a.querySelector('svg.dci'),a.textContent.trim(),a.hasAttribute('data-discord')])")
        ok(f"[{tag}] {path}: every Discord link is the configured invite, opens in a new tab, has the icon and a name", links and all(l[0] == DC["url"] and l[1] == "_blank" and "noopener" in l[2] and l[3] and l[4] and l[5] for l in links), links[:2])
        ok(f"[{tag}] {path}: Discord in the footer", c.js(SHOWN + "('.foot a[data-discord]')") and txt(".foot a[data-discord]") == DC["label"])
        if mobile:
            c.js("document.querySelector('[data-menu]').click()"); time.sleep(.3)
            ok(f"[{tag}] {path}: menu offers Download & Play and Discord", c.js(SHOWN + "('.menu-sheet a[data-discord]')") and c.js("!!document.querySelector('.menu-sheet a[href$=\"/play/\"]')"))
        else:
            ok(f"[{tag}] {path}: header has the Discord icon and Play", c.js(SHOWN + "('.util a[data-discord]')") and c.js(SHOWN + "('.util a.play')"))
        ok(f"[{tag}] {path}: footer links to Download & Play", c.js("(a=>a&&a.textContent)(document.querySelector('.foot a[href$=\"/play/\"]'))") == "Download & Play")
        ok(f"[{tag}] {path}: no sideways scroll", c.js("document.documentElement.scrollWidth <= window.innerWidth"), c.js("document.documentElement.scrollWidth"))
    go(c, "/stuck/")
    ok(f"[{tag}] Stuck?: points to Download & Play troubleshooting and Discord", c.js("!!document.querySelector('.stuck .helpline a[href$=\"/play/#trouble\"]') && !!document.querySelector('.stuck .helpline a[data-discord]')"))
    go(c, "/")
    ok(f"[{tag}] Home: Get started leads to Download & Play", c.js("!!document.querySelector('.hero a.btn[href$=\"/play/\"]')"))

    # ---- keyboard
    if not mobile:
        go(c, "/play/")
        seen = []
        for _ in range(14):
            c.key("Tab"); time.sleep(.05)
            seen.append(c.js("(e=>e?(e.dataset.discord!==undefined?'discord:':'')+(e.className||e.tagName):'')(document.activeElement)"))
        ok("[desktop] keyboard: Tab reaches the header Discord link and the primary action", any(s.startswith("discord:dc") for s in seen) and any("dcbtn" in s or s.strip() == "btn" for s in seen), seen)
        c.js("document.querySelector('#update-mac summary').focus()"); c.key(" ", "Space", 32); time.sleep(.3)
        ok("[desktop] keyboard: Space on a device opens its update steps", c.js("document.getElementById('update-mac').open"))
        c.js("document.querySelector('.relhero .actions .btn').focus()")
        ok("[desktop] keyboard: focus ring is visible on the primary action", c.js("getComputedStyle(document.activeElement).outlineStyle") != "none" or c.js("getComputedStyle(document.activeElement).boxShadow") != "none")

    # ---- regressions: search, progress, Pokédex, Legendary guide
    go(c, "/play/")
    c.js("document.querySelector('[data-search-open]').click()"); time.sleep(.4)
    c.js("(i=>{i.value='update save';i.dispatchEvent(new Event('input',{bubbles:true}))})(document.querySelector('dialog.search input'))"); time.sleep(.8)
    ok(f"[{tag}] search finds the update guide", "How to update without losing your save" in txt("dialog.search .results"), txt("dialog.search .results")[:120])
    c.js("(i=>{i.value='Lugia';i.dispatchEvent(new Event('input',{bubbles:true}))})(document.querySelector('dialog.search input'))"); time.sleep(.8)
    ok(f"[{tag}] search still finds a Pokémon", "Lugia" in txt("dialog.search .results"))
    go(c, "/walkthrough/johto/new-bark-town/"); time.sleep(.5); go(c, "/")
    ok(f"[{tag}] progress tracking still remembers the chapter opened", c.js("document.documentElement.dataset.pos") == "known" and c.js("!!JSON.parse(localStorage.getItem('pb-guide:v1')||'{}').pos"))
    go(c, "/pokemon/")
    ok(f"[{tag}] Pokédex still lists 482 entries", c.js("document.querySelectorAll('#dex li').length") == 482, c.js("document.querySelectorAll('#dex li').length"))
    go(c, "/postgame/legendaries/"); c.wait("document.querySelector('[data-lg-count]') && document.querySelector('[data-lg-count]').textContent", 10)
    ok(f"[{tag}] Legendary guide still lists 32 of 32", txt("[data-lg-count]") == "32 of 32", txt("[data-lg-count]"))
    c.js("localStorage.clear()")
    go(c, "/play/"); c.shot(str(OUT / f"{LABEL}-{tag}-play.png"), full=True)
    c.js("document.getElementById('update-iphone').open=true;document.getElementById('update').scrollIntoView()"); time.sleep(.3); c.shot(str(OUT / f"{LABEL}-{tag}-update.png"))
    c.js("window.scrollTo(0,0)"); time.sleep(.2); c.shot(str(OUT / f"{LABEL}-{tag}-top.png"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    invite()
    c = Chrome(free_port())
    try:
        run(c, False); run(c, True)
    finally:
        c.close()
    bad = [r for r in res if not r["ok"]]
    (OUT / f"{LABEL}.json").write_text(json.dumps({"base": BASE, "checked": time.strftime("%Y-%m-%d %H:%M"), "passed": len(res) - len(bad), "failed": len(bad), "results": res}, indent=1, ensure_ascii=False))
    print(f"{len(res) - len(bad)} of {len(res)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
