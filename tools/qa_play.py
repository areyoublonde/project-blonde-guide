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
    elif state == "discord":
        post = c.js("[...document.querySelectorAll('a[data-release-post]')].map(a=>[a.href,a.target,a.rel])")
        ok(f"[{tag}] released: the primary action is the official release post (permanent link, new tab), in the hero and in Get the game",
           c.js("document.querySelector('.relhero .actions > :first-child').href") == REL["download"]["url"] and c.js("document.querySelector('#get .actions a.btn[data-release-post]').href") == REL["download"]["url"]
           and all(x[0] == REL["download"]["url"] and x[1] == "_blank" and "noopener" in x[2] for x in post), post[:2])
        ok(f"[{tag}] released: date, game checksum and ZIP checksum come from the release record", "Released" in txt(".relline") and REL["date"] in kv["Released"] and REL["sha256"] in kv["SHA-256"] and REL["archive"]["sha256"] in kv["SHA-256"]
           and REL["file"]["name"] in kv["SHA-256"] and REL["archive"]["name"] in kv["SHA-256"], kv["SHA-256"])
        ok(f"[{tag}] released: no link to a game file and no expiring attachment link anywhere on the page", c.js(GAMEFILE) == [] and c.js("[...document.querySelectorAll('a')].filter(a=>/cdn\\.discordapp|media\\.discordapp|[?&](ex|hm)=/.test(a.href)).length") == 0, c.js(GAMEFILE))
        ok(f"[{tag}] released: Get the game has five steps, starting with the server invite", c.js("document.querySelectorAll('#get ol.quick > li').length") == 5 and c.js("(a=>a&&a.href)(document.querySelector('#get ol.quick > li a[data-discord]'))") == DC["url"]
           and REL["archive"]["name"] in txt("#get") and REL["file"]["name"] in txt("#get"))
        cl = txt("#changelog")
        ok(f"[{tag}] changelog: every line of the release's changelog, word for word", all(x in cl for x in REL["changelog"]), [x for x in REL["changelog"] if x not in cl])
        ok(f"[{tag}] changelog: every known limitation, word for word, and a link to the gallery", all(x in cl for x in REL["known_limitations"]) and c.js("!!document.querySelector('#changelog a[href$=\"" + REL["page"] + "\"]')"))
        ok(f"[{tag}] changelog: says nothing about the ending, the credits or the habitat project", not any(w in (cl + txt("#release")).lower() for w in ("credits", "ending", "habitat")))
        hist = c.js("[...document.querySelectorAll('#history .history a')].map(a=>[a.querySelector('b').textContent,a.getAttribute('href'),a.textContent])")
        want = [r for r in REL_ALL["releases"] if r["status"] == "released"]
        ok(f"[{tag}] version history lists every public release, current first, each with its date and page", [h[0] for h in hist] == [r["public_version"] for r in want] and all(r["date"] in h[2] and h[1].endswith(r["page"]) for r, h in zip(want, hist))
           and "Current" in hist[0][2] and all("Previous" in h[2] for h in hist[1:]), hist)
        up = REL["upgrade"]
        ok(f"[{tag}] update: the release's own save compatibility, five instructions and both emulator guides", REL["save_compatibility"] in txt("#update .upgrade") and all(x in txt("#update .upgrade") for x in up["instructions"])
           and c.js("[...document.querySelectorAll('#update details.upg')].map(d=>[d.id,d.open,d.querySelectorAll('ol li').length])") == [[f"upgrade-{g['id']}", False, len(g["steps"])] for g in up["guides"]])
        c.js("document.querySelector('#upgrade-delta summary').click()"); time.sleep(.3)
        ok(f"[{tag}] update: the Delta guide opens and says what was not tested", c.js(SHOWN + "('#upgrade-delta ol li')") and "not tested on an iPhone or iPad" in txt("#upgrade-delta") and "Export Save File" in txt("#upgrade-delta"))
        c.js("document.querySelector('#upgrade-mgba summary').click()"); time.sleep(.3)
        ok(f"[{tag}] update: the mGBA guide opens and closes the other", c.js("[...document.querySelectorAll('#update details.upg')].filter(d=>d.open).map(d=>d.id)") == ["upgrade-mgba"] and "Pokemon - Project Blonde.sav" in txt("#upgrade-mgba"))
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
    ok(f"[{tag}] old #update / #backup / #restore / #move / #link / #save / #trouble / #changelog anchors all exist", c.js("['update','backup','restore','move','link','save','trouble','changelog','rollback','release','get','devices'" + (",'history'" if PUBLIC else "") + "].filter(i=>!document.getElementById(i))") == [])

    # ---- troubleshooting
    qs = c.js("[...document.querySelectorAll('#trouble details.qa summary b')].map(b=>b.textContent)")
    ok(f"[{tag}] troubleshooting lists every written problem", qs == [a for a, _ in PLAY["trouble"]], len(qs))
    c.js("document.querySelector('#trouble details.qa summary').click()"); time.sleep(.2)
    ok(f"[{tag}] troubleshooting: an answer opens", c.js("document.querySelector('#trouble details.qa').open") and c.js(SHOWN + "('#trouble details.qa > div p')"))
    ok(f"[{tag}] troubleshooting ends with Discord support", c.js("(a=>a&&a.href)(document.querySelector('#trouble .support a[data-discord]'))") == DC["url"])

    # ---- Discord everywhere it should be, and only the configured URL
    for path in ("/", "/play/", "/stuck/", "/walkthrough/johto/new-bark-town/", "/pokemon/", "/postgame/legendaries/"):
        go(c, path)
        links = c.js("[...document.querySelectorAll('a[href*=\"discord\"]:not([data-release-post])')].map(a=>[a.href,a.target,a.rel,!!a.querySelector('svg.dci'),a.textContent.trim(),a.hasAttribute('data-discord')])")
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

    if PUBLIC and REL.get("changelog"):
        whatsnew(c, tag)
    for r in REL_ALL["releases"]:
        if r is not REL and r["status"] == "released" and r.get("page"):
            go(c, r["page"])
            ok(f"[{tag}] {r['public_version']}: its own page, with version, date, checksum and a way to the current release", r["public_version"] in txt("h1") and r["sha256"] in txt("#release") and r["date"] in txt("#release")
               and c.js("document.querySelector('.phead .actions a.btn').getAttribute('href')").endswith("/play/#get") and REL["public_version"] in txt(".phead .actions a.btn"))
            ok(f"[{tag}] {r['public_version']}: its original download post and its notes are still there", c.js("(a=>a&&a.href)(document.querySelector('#release a[data-release-post]'))") == r.get("discord_post") and all(a in txt("#notes") for a, _ in REL_ALL["fixed"]))
            ok(f"[{tag}] {r['public_version']}: the in-browser patcher is still offered, for that version", r.get("method") != "patcher" or c.js("document.querySelectorAll('#get [data-patcher] [data-mk-file]').length") == 1 and r["public_version"] in txt("#get .lead"))
            if r.get("method") == "patcher":
                only, cur = r["public_version"] + " only", REL["public_version"]
                ok(f"[{tag}] {r['public_version']}: the patcher is labelled {only} in its heading, its notice and the release record, and says it does not make {cur}", only in txt("#get > .label") and txt("#get .notice.only b") == only + "." and f"does not make {cur}" in txt("#get .notice.only")
                   and only in txt("#release dl") and c.js("document.querySelector('#get .notice.only a').getAttribute('href')").endswith("/play/#get") and c.js(SHOWN + "('#get .notice.only')"))
                made = c.js("[...document.querySelectorAll('#get [data-patcher] h3, #get [data-patcher] .lead, #get h2')].map(e=>e.textContent).join(' | ')")
                ok(f"[{tag}] {r['public_version']}: nothing in the patcher says it makes {cur}", f"Blonde {cur}" not in made and f"Make {cur}" not in made and f"makes {cur}" not in made.replace("does not make", ""), made[:200])
                go(c, "/play/")
                ok(f"[{tag}] Download & Play: no patcher on the {cur} page, and the history row says the patcher is {only}", c.js("document.querySelectorAll('[data-patcher]').length") == 0 and only in c.js("[...document.querySelectorAll('#history .history a')].map(a=>a.textContent).join(' | ')"))
                go(c, r["page"])
            ok(f"[{tag}] {r['public_version']}: no sideways scroll", c.js("document.documentElement.scrollWidth <= window.innerWidth"))

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


def whatsnew(c, tag):
    """The release-notes page: changelog, title screen and the before / after gallery, measured as drawn."""
    G = J(f"data/whatsnew-{REL['public_version']}.json")
    txt = lambda sel: c.js(f"(document.querySelector({json.dumps(sel)})||{{}}).textContent||''")
    go(c, "/"); news = c.js("[...document.querySelectorAll('.relnews a')].map(a=>a.getAttribute('href'))")
    ok(f"[{tag}] Home: announces {REL['public_version']} with links to what's new and the download", REL["public_version"] + " is out" in txt(".relnews") and len(news) == 2 and news[0].endswith(REL["page"]) and news[1].endswith("/play/#get"), news)
    go(c, "/play/"); c.js("document.querySelector('#release a.link').click()"); c.wait("location.pathname.endsWith(" + json.dumps(REL["page"]) + ")", 6)
    ok(f"[{tag}] What's new: reached from Current release", c.url().endswith(REL["page"]) and txt("h1") == "What’s new in " + REL["public_version"], c.url())
    c.events.clear(); c.send("Runtime.enable"); c.send("Log.enable"); go(c, REL["page"])
    c.js("window.scrollTo(0,document.body.scrollHeight)"); time.sleep(.8)
    ok(f"[{tag}] What's new: title screen is the {REL['public_version']} screenshot at native size, drawn crisp, and not called new artwork", c.js("(i=>i.complete&&i.naturalWidth===240&&i.naturalHeight===160&&i.src.endsWith('title-" + REL["public_version"] + ".png')&&getComputedStyle(i).imageRendering==='pixelated')(document.querySelector('.titleart img'))")
       and "same as in " + G["before"]["public"] in txt(".titleart figcaption"))
    ok(f"[{tag}] What's new: the changelog, word for word", all(x in txt("#changes") for x in REL["changelog"]))
    n = c.js("[document.querySelectorAll('#overworld li').length,document.querySelectorAll('#portraits li').length,document.querySelectorAll('#battle li').length]")
    ok(f"[{tag}] gallery: {G['counts']['overworld']} overworld, {G['counts']['portrait']} portrait and {G['counts']['battle']} battle comparisons, each a before and an after", n == [G["counts"][k] for k in ("overworld", "portrait", "battle")]
       and c.js("[...document.querySelectorAll('.wn-grid li')].every(li=>li.querySelectorAll('.wn-s,.wn-f').length===2)"), n)
    N = G["counts"]
    ok(f"[{tag}] gallery: portraits are explained as {N['assignments']['portrait']} changed of {N['release_assignments']['portrait']} assignments, {N['identical']['portrait']['assignments']} pixel-identical", (lambda t: f"{N['release_assignments']['portrait']} portrait assignments" in t and f"{N['assignments']['portrait']} of them" in t
       and f"other {N['identical']['portrait']['assignments']}" in t and "pixel-identical" in t and all(x in t for x in N["identical"]["portrait"]["names"]))(txt("#portraits .wn-note")) and f"{N['assignments']['portrait']} of {N['release_assignments']['portrait']} assignments" in txt("#portraits .wn-head") and c.js(SHOWN + "('#portraits .wn-note')"), txt("#portraits .wn-note"))
    ok(f"[{tag}] gallery: titles and atlas cells match the generated data", c.js("[...document.querySelectorAll('.wn-grid li')].map(li=>li.querySelector('b').textContent)") == [x["title"] for k in ("overworld", "portrait", "battle") for x in G["comparisons"] if x["kind"] == k]
       and c.js("[...document.querySelectorAll('#overworld li')].map(li=>[...li.querySelectorAll('.wn-s')].map(e=>+e.style.getPropertyValue('--r')))") == [[x["before"], x["after"]] for x in G["comparisons"] if x["kind"] == "overworld"])
    atl = c.js("""Promise.all(['--ow','--fa'].map(v=>new Promise(r=>{const m=/url\\(['"]?(.*?)['"]?\\)/.exec(getComputedStyle(document.querySelector('.wn')).getPropertyValue(v));const i=new Image();i.onload=()=>r([i.naturalWidth,i.naturalHeight]);i.onerror=()=>r(null);i.src=m[1]})))""")
    ok(f"[{tag}] gallery: both atlases load at their recorded native size", atl == [[G["atlas"][k]["w"], G["atlas"][k]["h"]] for k in ("overworld", "faces")], atl)
    sharp = c.js("""[...document.querySelectorAll('.wn-s,.wn-f')].map(e=>{const s=getComputedStyle(e),c=e.matches('.wn-s')?32:64,w=parseFloat(s.width),bs=s.backgroundSize.split(' ').map(parseFloat),k=w/c;
      return s.imageRendering==='pixelated'&&Number.isInteger(k)&&k>=1&&parseFloat(s.height)===w&&bs[0]===(e.matches('.wn-s')?128:%d)*k&&bs[1]===(e.matches('.wn-s')?%d:%d)*k}).every(Boolean)""" % (G["atlas"]["faces"]["w"], G["atlas"]["overworld"]["h"], G["atlas"]["faces"]["h"]))
    ok(f"[{tag}] gallery: every sprite is a whole-number enlargement of the game's pixels with no smoothing", sharp, c.js("(e=>[getComputedStyle(e).width,getComputedStyle(e).backgroundSize])(document.querySelector('.wn-s'))"))
    ok(f"[{tag}] gallery: every sprite fits inside its card", c.js("[...document.querySelectorAll('.wn-grid li')].every(li=>{const a=li.getBoundingClientRect();return [...li.querySelectorAll('.wn-s,.wn-f')].every(e=>{const b=e.getBoundingClientRect();return b.left>=a.left&&b.right<=a.right+.5})})"))
    pos = lambda: c.js("getComputedStyle(document.querySelector('#overworld .wn-s')).backgroundPositionX")
    p0 = pos(); c.js("document.querySelector('[data-wn-face=\"3\"]').click()"); time.sleep(.2); p3 = pos()
    ok(f"[{tag}] gallery: the facing switch turns every overworld sprite", p0 != p3 and c.js("document.querySelector('[data-wn-face=\"3\"]').getAttribute('aria-pressed')") == "true" and c.js("document.querySelector('[data-wn-face=\"0\"]').getAttribute('aria-pressed')") == "false", (p0, p3))
    c.js("document.querySelector('[data-wn-face=\"0\"]').click()")
    ok(f"[{tag}] Alola: both palm screenshots load at native size and are drawn crisp", c.js("[...document.querySelectorAll('#alola img')].map(i=>i.complete&&i.naturalWidth===240&&i.naturalHeight===160&&getComputedStyle(i).imageRendering==='pixelated')") == [True, True])
    t = txt(".wn")
    ok(f"[{tag}] What's new: update steps for Delta and mGBA, known limitations and the release post", all(x in t for x in REL["known_limitations"]) and c.js("document.querySelectorAll('#update details.upg').length") == 2 and REL["save_compatibility"] in t
       and c.js("[...document.querySelectorAll('.wn a[data-release-post]')].every(a=>a.href===" + json.dumps(REL["download"]["url"]) + ")") and c.js("document.querySelectorAll('.wn a[data-release-post]').length") >= 1)
    ok(f"[{tag}] What's new: says nothing about the ending, the credits or the habitat project", not any(w in t.lower() for w in ("credits", "ending", "habitat")))
    ok(f"[{tag}] What's new: no sideways scroll, no broken image", c.js("document.documentElement.scrollWidth <= window.innerWidth") and c.js("[...document.images].filter(i=>!i.complete||!i.naturalWidth).length") == 0)
    errs = [e for e in c.events if e.get("method") in ("Runtime.exceptionThrown", "Network.loadingFailed") or e.get("method") == "Log.entryAdded" and e["params"]["entry"]["level"] == "error"
            or e.get("method") == "Runtime.consoleAPICalled" and e["params"]["type"] == "error"]
    ok(f"[{tag}] What's new: no script error and nothing logged to the console as an error", not errs, errs[:2])
    c.js("window.scrollTo(0,0)"); c.shot(str(OUT / f"{LABEL}-{tag}-whatsnew.png"), full=True)
    c.js("document.getElementById('gallery').scrollIntoView()"); time.sleep(.3); c.shot(str(OUT / f"{LABEL}-{tag}-gallery.png"))


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
