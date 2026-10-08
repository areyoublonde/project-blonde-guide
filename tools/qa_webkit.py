#!/usr/bin/env python3
"""WebKit pass through Safari's WebDriver (safaridriver). Needs Safari > Settings > Developer > "Allow remote automation".

    python3 tools/qa_webkit.py      -> data/qa-webkit.json ; exit 2 when Safari automation is not enabled (reported, not a failure of the site)
"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BASE, PORT = "http://localhost:8765", 4477


def call(method, path, body=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(body).encode() if body is not None else None, method=method, headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=40).read())["value"]
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read()).get("value", {})}


def main():
    proc = subprocess.Popen(["safaridriver", "-p", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    out = {"browser": "Safari (WebKit)", "checks": []}
    try:
        s = call("POST", "/session", {"capabilities": {"alwaysMatch": {"browserName": "safari"}}})
        if not isinstance(s, dict) or "sessionId" not in s:
            out["not_run"] = str(s)[:300]
            (ROOT / "data/qa-webkit.json").write_text(json.dumps(out, indent=1))
            print("WebKit not run:", out["not_run"]); sys.exit(2)
        sid = s["sessionId"]
        ex = lambda js: call("POST", f"/session/{sid}/execute/sync", {"script": js, "args": []})
        def go(p):
            call("POST", f"/session/{sid}/url", {"url": BASE + p}); time.sleep(0.7)
        def ok(name, cond):
            out["checks"].append({"name": name, "ok": bool(cond)}); print(("  ok   " if cond else "  FAIL ") + name)
        call("POST", f"/session/{sid}/window/rect", {"width": 1280, "height": 860})
        for p in ["/", "/walkthrough/", "/walkthrough/hoenn/fortree-city/", "/pokemon/", "/pokemon/eevee/", "/trainers/hoenn/wallace/", "/world/", "/world/hoenn/route-119/", "/items/", "/items/mega-stones/", "/features/link-play/", "/stuck/", "/progress/", "/play/", "/play/setup/iphone/", "/about/"]:
            go(p)
            r = ex("const de=document.documentElement;return {h1:[...document.querySelectorAll('h1')].filter(e=>e.offsetParent!==null).length,over:de.scrollWidth-de.clientWidth,bad:[...document.images].filter(i=>i.complete&&i.naturalWidth===0&&i.getAttribute('src')).length}")
            ok(f"{p} renders: one h1, no sideways scroll, no broken image", isinstance(r, dict) and r.get("h1") == 1 and r.get("over", 9) <= 1 and r.get("bad") == 0)
        go("/pokemon/")
        ok("Pokédex filter works", ex("const i=document.querySelector('[data-filter-list]');i.value='ghost';i.dispatchEvent(new Event('input'));const n=[...document.querySelectorAll('#dex li')].filter(l=>!l.hidden).length;return n>0&&n<200"))
        go("/walkthrough/johto/ecruteak-city/")
        ok("Opening a chapter saves the position", ex("return JSON.parse(localStorage.getItem('pb-guide:v1')).pos") == "johto/ecruteak-city")
        ok("Map viewer zooms", ex("const v=document.querySelector('.mapv');const z=v.pbZoom();v.querySelector('[data-zoom=in]').click();return v.pbZoom()>z"))
        go("/")
        ok("Home shows the returning state", ex("return [...document.querySelectorAll('h1')].find(e=>e.offsetParent).textContent") == "Ecruteak City")
        ok("Search palette opens and answers", ex("document.querySelector('[data-search-open]').click();const i=document.querySelector('dialog.search input');i.value='wallace';i.dispatchEvent(new Event('input'));return document.querySelector('dialog.search').open"))
        time.sleep(1.0)
        ok("Search returns results", ex("return document.querySelectorAll('dialog.search .results a').length") > 0)
        call("DELETE", f"/session/{sid}")
    finally:
        proc.terminate()
    out["passed"] = sum(1 for c in out["checks"] if c["ok"])
    (ROOT / "data/qa-webkit.json").write_text(json.dumps(out, indent=1))
    print(f'{out["passed"]} of {len(out["checks"])} WebKit checks passed')
    sys.exit(0 if out["passed"] == len(out["checks"]) else 1)


if __name__ == "__main__":
    main()
