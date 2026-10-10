#!/usr/bin/env python3
"""Browser test of the in-browser patcher (private prototype), with the real ROM files named in private/roms.json.

    python3 tools/build.py --prototype && python3 -m http.server 8951 -d dist &
    python3 tools/qa_patcher.py [base-url]        default http://localhost:8951
    -> qa-evidence/patcher/local.json + screenshots ; exit 1 on any failure

Expected values come from content/patcher.json (written by tools/patches.py from the files themselves); actual values are what the page
shows and the bytes it offers for saving. Variant files (damaged, renamed, cut short) are made in a temp folder; no source file is written to.
"""
import hashlib, json, os, socket, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
import cdp

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8951").rstrip("/")
OUT = ROOT / "qa-evidence" / "patcher"
LABEL = "live" if "github.io" in BASE else "local"
REG = json.loads((ROOT / "content/patcher.json").read_text(encoding="utf-8")); T = REG["target"]
_REL = json.loads((ROOT / "content/releases.json").read_text(encoding="utf-8"))
PAGE = next(("/play/" if r["version"] == _REL["current"] else r["page"]) for r in _REL["releases"] if r["version"] == json.loads((ROOT / "content/patcher.json").read_text(encoding="utf-8"))["release"])   # the page that carries the patcher
ROMS = json.loads((ROOT / "private/roms.json").read_text(encoding="utf-8"))["roms"]
BY = {x["id"]: x for x in REG["inputs"]}
res, perf = [], {}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ok(name, cond, detail=""):
    res.append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("  ok   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)


def variants(tmp):
    em = Path(ROMS["emerald-usa"]).read_bytes(); v = {}
    def w(name, data): p = Path(tmp) / name; p.write_bytes(data); v[name] = str(p); return str(p)
    b = bytearray(em); b[0x400000] ^= 1; w("corrupt-one-byte.gba", bytes(b))
    b = bytearray(em); b[0xAC:0xB0] = b"BPEJ"; w("other-language.gba", bytes(b))
    w("cut-short.gba", em[:8 << 20]); w("save-sized.sav", bytes(131072)); w("not-a-game.gba", b"hello" * 5000)
    with zipfile.ZipFile(Path(tmp) / "zipped.zip", "w", zipfile.ZIP_STORED) as z: z.writestr("game.gba", em[:4096])
    v["zipped.zip"] = str(Path(tmp) / "zipped.zip")
    w("Pokemon Project Blonde v1.0.gba", Path(ROMS["v100"]).read_bytes())      # an unsupported build wearing the current release's name
    w("holiday-photos.bin", em)                                                 # the right game under a meaningless name
    return v


def rss(prefix):
    """Resident memory (MB) of every Chrome process of this test browser."""
    out = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout
    return round(sum(int(l.split(None, 1)[0]) for l in out.splitlines() if prefix in l) / 1024)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = {k: sha(p) for k, p in ROMS.items()}
    _m = tempfile.mkdtemp; tempfile.mkdtemp = lambda prefix="x", **k: _m(prefix="pbpatcher-qa-", **k)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    tmp = _m(prefix="pbpatcher-files-"); V = variants(tmp)
    c = cdp.Chrome(port)
    R = "document.querySelector('[data-patcher]')"
    st = lambda: c.js(R + ".dataset.state")
    msg = lambda: c.js("document.querySelector('[data-mk-msg]').textContent")
    vis = lambda sel: c.js(f"(e=>!!e&&!e.hidden&&e.getBoundingClientRect().height>0)(document.querySelector({json.dumps(sel)}))")

    def load(mobile=True):
        c.viewport(390 if mobile else 1440, 844 if mobile else 900, 1, mobile)
        c.nav(BASE + PAGE); c.wait("document.readyState==='complete' && " + R + ".dataset.state==='ask'", 20); c.events.clear()

    def choose(path):
        doc = c.send("DOM.getDocument"); node = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector="[data-mk-file]")
        c.send("DOM.setFileInputFiles", files=[path], nodeId=node["nodeId"])
        c.wait(R + ".dataset.state!=='ask' && " + R + ".dataset.state!=='checking'", 60); return st()

    def go(prefix=None):
        t, peak = time.time(), 0
        c.js("document.querySelector('[data-mk-go]').click()")
        while time.time() - t < 180:
            if prefix: peak = max(peak, rss(prefix))
            if st() in ("ready", "error"): break
            time.sleep(.05)
        return round(time.time() - t, 2), peak

    saved = lambda: c.js("(async()=>{const a=document.querySelector('[data-mk-save]');const b=await (await fetch(a.href)).arrayBuffer();const h=await crypto.subtle.digest('SHA-256',b);return [a.download,b.byteLength,[...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('')]})()")
    reqs = lambda: [(e["params"]["request"]["method"], e["params"]["request"]["url"].rsplit("/", 1)[-1], "postData" in e["params"]["request"] or e["params"]["request"].get("hasPostData", False)) for e in c.events if e.get("method") == "Network.requestWillBeSent" and not e["params"]["request"]["url"].startswith("blob:")]
    def snap(name):
        c.js("document.documentElement.style.scrollBehavior='auto';document.getElementById('get').scrollIntoView()"); time.sleep(.3); c.shot(str(OUT / f"{LABEL}-{name}"))

    try:
        c.send("Network.enable")
        # ---- first sight
        load()
        ok("one file selector, labelled 'Choose your game file', and no New / Updating choice", c.js("document.querySelector('.mk-pick span').textContent") == "Choose your game file" and c.js("document.querySelectorAll('[data-mk-file]').length") == 1 and c.js("document.querySelectorAll('[data-mk-path]').length") == 0)
        ok("nothing technical is visible before a file is chosen", not vis("[data-mk-found]") and not vis("[data-mk-ready]") and not c.js("document.querySelector('.mk-adv').open") and not c.js("document.querySelector('[data-mk-adv]').checkVisibility()"))
        if REG["enabled"]:
            if PAGE == "/play/":
                ok("released: no prototype notice, the page says Released and the primary action leads to the patcher", not vis(".mk-proto") and "Released" in c.js("document.querySelector('.relline').textContent") and c.js("document.querySelector('.wrap.play').dataset.releaseState") == "patcher" and c.js("document.querySelector('.relhero .actions a.btn').getAttribute('href')") == "#get")
            else:
                ok("previous release: no prototype notice, the page names its version as a previous release and points to the current one", not vis(".mk-proto") and c.js("document.querySelector('.wrap.play').dataset.releaseState") == "patcher" and c.js("document.querySelector('.wrap.play').dataset.release") == T["public_version"]
                   and "Previous release" in c.js("document.querySelector('#release').textContent") and c.js("document.querySelector('.phead .actions a.btn').getAttribute('href')").endswith("/play/#get"))
        else:
            ok("the prototype is labelled private and the page still says release candidate, not released", vis(".mk-proto") and "Not released yet" in c.js("document.querySelector('.relline').textContent") and c.js("document.querySelector('.wrap.play').dataset.releaseState") == "prerelease")
        ok("the file selector takes any file (no type filter that could grey out a .gba on iOS)", c.js("document.querySelector('[data-mk-file]').getAttribute('accept')") is None)
        ok("no sideways scroll at phone width", c.js("document.documentElement.scrollWidth <= window.innerWidth"))

        # ---- clean Emerald -> latest (phone size, CPU slowed 6x as a stand-in for a phone)
        c.send("Emulation.setCPUThrottlingRate", rate=6)
        r0 = rss("pbpatcher-qa-"); t = time.time(); s1 = choose(ROMS["emerald-usa"]); perf["emerald: recognise (s, CPU 6x slower)"] = round(time.time() - t, 2)
        ok("Emerald: recognised automatically as the clean base game", s1 == "found" and c.js(R + ".dataset.detected") == "emerald-usa" and c.js(R + ".dataset.input") == BY["emerald-usa"]["sha256"], (s1, msg()))
        ok("Emerald: shows what the file is and what it will become, before anything is made", c.js("document.querySelector('[data-mk-from]').textContent") == BY["emerald-usa"]["label"] and c.js("document.querySelector('[data-mk-to]').textContent") == f'Project Blonde {T["public_version"]}')
        ok("Emerald: no save-backup tick box for a new game, and the button is ready", not vis("[data-mk-backup]") and not vis(".mk-found .mk-warn") and c.js("!document.querySelector('[data-mk-go]').disabled") and c.js("document.querySelector('[data-mk-go] span').textContent") == "Make my game")
        dt, peak = go("pbpatcher-qa-"); perf["emerald: download + build + check (s, CPU 6x slower)"] = dt; perf["emerald: browser memory before / peak (MB, all Chrome processes)"] = [r0, peak]
        ok("Emerald: game built", st() == "ready", (st(), msg()))
        sv = saved()
        ok("Emerald: the file offered for saving is the approved release, byte for byte", sv == [T["file_name"], T["size"], T["sha256"]] and c.js(R + ".dataset.outSha256") == T["sha256"], sv)
        ok("Emerald: a clear save action, with setup pointer; no save-transfer wording for a new game", vis("[data-mk-save]") and c.js("document.querySelector('[data-mk-save] span').textContent") in ("Save game file", "Save to Files") and not vis(".mk-ready .mk-warn"))
        rq = reqs()
        ok("Emerald: the only network traffic is one download of the patch; nothing is sent", [x for x in rq] == [("GET", BY["emerald-usa"]["patch"]["file"] + ".gz", False)], rq)
        c.send("Emulation.setCPUThrottlingRate", rate=1)
        snap("phone-ready-new.png")

        # ---- the same game under a meaningless name; the JS hash and uncompressed-download fallbacks
        load(); c.js(R + ".dataset.forceJsHash='1'; delete window.DecompressionStream; 1")
        t = time.time(); s1 = choose(V["holiday-photos.bin"]); perf["emerald: recognise with the plain-JS hash (s)"] = round(time.time() - t, 2)
        ok("the right game under a meaningless file name is still recognised", s1 == "found" and c.js(R + ".dataset.detected") == "emerald-usa")
        dt, _ = go(); perf["emerald: build with plain-JS hash and uncompressed patch (s)"] = dt
        ok("fallbacks (no crypto.subtle, no DecompressionStream): same exact result from the uncompressed patch", st() == "ready" and saved()[2] == T["sha256"] and reqs()[-1][1] == BY["emerald-usa"]["patch"]["file"], (st(), reqs()[-1:]))

        # ---- supported earlier builds -> latest
        for vid in [x["id"] for x in REG["inputs"] if x["kind"] == "release" and x["status"] == "supported"]:
            load(); s1 = choose(ROMS[BY[vid]["rom"]])
            ok(f"{vid}: recognised automatically as an earlier Project Blonde build", s1 == "found" and c.js(R + ".dataset.detected") == vid and c.js("document.querySelector('[data-mk-from]').textContent") == BY[vid]["label"] and c.js("document.querySelector('[data-mk-to]').textContent") == f'Project Blonde {T["public_version"]}')
            ok(f"{vid}: save-backup reminder shown, with the link to the backup steps and no promise", vis(".mk-found .mk-warn") and "does not update or move your save" in c.js("document.querySelector('.mk-found .mk-warn').textContent") and c.js("!!document.querySelector('.mk-found .mk-warn a[href$=\"#update\"]')") and "does not prove that a save will carry over" in c.js("document.querySelector('.mk-save').textContent") and BY[vid]["save"]["note"] in c.js("document.querySelector('.mk-save').textContent"))
            ok(f"{vid}: cannot update until the backup box is ticked", c.js("document.querySelector('[data-mk-go]').disabled") and c.js("document.querySelector('[data-mk-go] span').textContent") == "Update my game")
            c.js("document.querySelector('[data-mk-go]').click()"); time.sleep(.3)
            ok(f"{vid}: clicking the disabled button does nothing", st() == "found")
            c.js("document.querySelector('[data-mk-backup]').click()")
            dt, _ = go(); perf[f"{vid}: update (s)"] = dt
            sv = saved() if st() == "ready" else None
            ok(f"{vid}: updated file is the approved release, byte for byte", sv == [T["file_name"], T["size"], T["sha256"]], (st(), sv, msg()))
            ok(f"{vid}: afterwards explains that the save must be restored separately", vis(".mk-ready .mk-warn") and "starts without one" in c.js("document.querySelector('.mk-ready .mk-warn').textContent") and c.js("!!document.querySelector('.mk-ready .mk-warn a[href$=\"#update\"]')"))
            ok(f"{vid}: only its own patch was downloaded", [x[:2] for x in reqs()] == [("GET", BY[vid]["patch"]["file"] + ".gz")], reqs())
        snap("phone-ready-update.png")
        load(); choose(ROMS["v104"]); snap("phone-found-update.png")

        # ---- already current
        load(); s1 = choose(ROMS[T["rom"]])
        ok("current release: says it is already up to date and offers no patching", s1 == "current" and vis("[data-mk-current]") and not vis("[data-mk-found]") and not vis("[data-mk-go]") and "already have Project Blonde " + T["public_version"] in c.js("document.querySelector('[data-mk-current]').textContent") and reqs() == [])
        snap("phone-current.png")

        # ---- refusals: nothing offered, nothing downloaded, a plain reason
        cases = [("recognised but unsupported build (v100)", ROMS["v100"], "v100", "cannot update that build"),
                 ("unsupported build renamed to the release's file name", V["Pokemon Project Blonde v1.0.gba"], "v100", "cannot update that build"),
                 ("unknown Project Blonde / Heart & Soul build (Heart & Soul 2.0)", "/Users/blonde/Desktop/VSC/Pokemon - Heart & Soul 2.0.gba", "unknown", "not a version this page knows"),
                 ("modified Emerald (Recharged Emerald 2.2.5)", "/Users/blonde/Downloads/recharged_em_version_2.2.5.gba", "unknown", "not an unchanged copy"),
                 ("Emerald with one byte changed", V["corrupt-one-byte.gba"], "unknown", "not an unchanged copy"),
                 ("Emerald with another language code (synthetic)", V["other-language.gba"], "unknown", "another language"),
                 ("Emerald cut short", V["cut-short.gba"], "unknown", "not the right size"),
                 ("zip file", V["zipped.zip"], "unknown", "zip file"), ("save-sized file", V["save-sized.sav"], "unknown", "save file"), ("not a game at all", V["not-a-game.gba"], "unknown", "not a Game Boy Advance game")]
        for name, path, det, phrase in cases:
            if not os.path.exists(path): ok(f"refused: {name}", False, "test file missing"); continue
            load(); s1 = choose(path)
            ok(f"refused: {name}", s1 == "rejected" and c.js(R + ".dataset.detected") == det and phrase in msg() and not vis("[data-mk-found]") and not vis("[data-mk-ready]") and not vis("[data-mk-save]") and reqs() == [], (s1, c.js(R + ".dataset.detected"), msg()[:90]))
        snap("phone-refused.png")
        ok("after a refusal the visitor can simply choose another file", choose(ROMS["emerald-usa"]) == "found")

        # ---- incorrect / damaged patch from the server
        for name, hook, err in [("the wrong patch is delivered", "u.replace('emerald-usa-to','v104-to')", "damaged"), ("the download is cut off", None, None)]:
            load()
            if hook: c.js(f"(f=>{{window.fetch=(u,o)=>f({hook},o)}})(window.fetch.bind(window));1")
            else: c.js("(f=>{window.fetch=async(u,o)=>{const r=await f(u,o);const b=await r.arrayBuffer();return new Response(b.slice(0,b.byteLength>>1))}})(window.fetch.bind(window));1")
            choose(ROMS["emerald-usa"]); go()
            ok(f"patch check: {name} -> nothing is built or offered, with a plain message", st() == "error" and (err is None or c.js(R + ".dataset.error") == err) and not vis("[data-mk-ready]") and not vis("[data-mk-save]") and c.js(R + ".dataset.outSha256") is None and "nothing was" in msg(), (st(), c.js(R + ".dataset.error"), msg()[:80]))
        # ---- out of memory
        load(); c.js("File.prototype.arrayBuffer=()=>Promise.reject(new RangeError('Array buffer allocation failed'));1"); s1 = choose(ROMS["emerald-usa"])
        ok("out of memory: a clear message, nothing offered", s1 == "error" and c.js(R + ".dataset.error") == "memory" and "ran out of memory" in msg() and "on a computer" in msg(), msg()[:80])

        # ---- advanced details, keyboard, desktop
        load(False); choose(ROMS["v104"])
        c.js("document.querySelector('.mk-adv summary').click()"); time.sleep(.2)
        ok("advanced details (opened on request) show the checksums and the patch used", (lambda t: BY["v104"]["sha256"] in t and T["sha256"] in t and BY["v104"]["patch"]["file"] in t)(c.js("document.querySelector('.mk-adv').textContent")))
        ok("checksums and patch names appear nowhere outside advanced details", c.js("(m=>{const k=m.cloneNode(true);k.querySelectorAll('.mk-adv,script,noscript').forEach(e=>e.remove());return !/[0-9a-f]{32}|\\.bps|SHA-256|checksum/i.test(k.textContent)})(document.querySelector('.mkgame'))"))
        c.js("document.querySelector('[data-mk-backup]').focus()"); c.key(" ", "Space", 32); time.sleep(.2)
        ok("keyboard: Space ticks the backup box and enables Update", c.js("document.querySelector('[data-mk-backup]').checked && !document.querySelector('[data-mk-go]').disabled"))
        c.js("document.querySelector('[data-mk-file]').focus()")
        ok("keyboard: the file selector takes focus and shows a focus ring", c.js("document.activeElement===document.querySelector('[data-mk-file]') && getComputedStyle(document.querySelector('.mk-pick')).outlineStyle!=='none'"))
        snap("desktop-found-update.png")
        c.nav(BASE + "/play/"); c.wait("document.readyState==='complete'", 20)
        ok("device guides and the update guide are still on Download & Play", c.js("document.querySelectorAll('.devices a').length") == 4 and c.js("document.querySelectorAll('#update details.upd').length") == 4)
        after = {k: sha(p) for k, p in ROMS.items()}
        ok("no source ROM file was changed by the test", after == before)
    finally:
        c.close()
    bad = [r for r in res if not r["ok"]]
    (OUT / f"{LABEL}.json").write_text(json.dumps({"base": BASE, "checked": time.strftime("%Y-%m-%d %H:%M"), "passed": len(res) - len(bad), "failed": len(bad), "performance": perf, "results": res}, indent=1, ensure_ascii=False))
    print(json.dumps(perf, indent=1)); print(f"{len(res) - len(bad)} of {len(res)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
