#!/usr/bin/env python3
"""Static QA over dist/: every internal link, anchor, image and asset on every page must resolve.

    python3 tools/qa_static.py [--base /sub-path]      -> exit 1 on any failure; writes data/qa-static.json
"""
import argparse, json, re, sys
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links, self.srcs, self.ids, self.h1, self.title, self._t, self.imgs_noalt = [], [], set(), 0, "", False, 0
    def handle_starttag(self, tag, a):
        a = dict(a)
        if "id" in a: self.ids.add(a["id"])
        if tag == "a" and a.get("href") is not None: self.links.append(a["href"])
        if tag in ("img", "script") and a.get("src"): self.srcs.append(a["src"])
        if tag == "link" and a.get("href"): self.srcs.append(a["href"])
        if tag == "img" and "alt" not in a: self.imgs_noalt += 1
        if tag == "h1": self.h1 += 1
        if tag == "title": self._t = True
    def handle_data(self, d):
        if self._t: self.title += d
    def handle_endtag(self, tag):
        if tag == "title": self._t = False


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default="")
    base = ap.parse_args().base.rstrip("/")
    pages = {}
    for f in DIST.rglob("index.html"):
        rel = str(f.parent.relative_to(DIST))
        url = "/" + ("" if rel == "." else rel) + "/"       # only the root is "."; a folder may have a dot in its name (/play/v1.1/)
        url = url.replace("//", "/")
        p = P(); p.feed(f.read_text(encoding="utf-8")); pages[url] = p
    bad, n_links, n_src, titles = [], 0, 0, {}
    for url, p in pages.items():
        if p.h1 < 1 or p.h1 > 2: bad.append(f"{url}: {p.h1} <h1>")      # Home, Road and Progress carry two states (new / returning); only one is shown
        if p.imgs_noalt: bad.append(f"{url}: {p.imgs_noalt} <img> without alt")
        titles.setdefault(p.title, []).append(url)
        for href in p.links:
            if re.match(r"^(https?:|mailto:|#$)", href) or href == "#": continue
            n_links += 1
            path, _, frag = href.partition("#")
            if path and base and not path.startswith(base + "/"):
                bad.append(f"{url}: link outside base: {href}"); continue
            path = path[len(base):] if path else url
            path = path.split("?")[0]
            if path not in pages:
                bad.append(f"{url}: broken link {href}"); continue
            if frag and frag not in pages[path].ids:
                bad.append(f"{url}: missing anchor {href}")
        for src in p.srcs:
            if re.match(r"^(https?:|data:)", src): continue
            n_src += 1
            rel = src[len(base):] if base else src
            if not (DIST / rel.lstrip("/")).exists():
                bad.append(f"{url}: missing asset {src}")
    dup = {t: u for t, u in titles.items() if len(u) > 1}
    out = {"pages": len(pages), "links_checked": n_links, "assets_checked": n_src, "failures": bad[:400], "failure_count": len(bad), "duplicate_titles": {k: v[:4] for k, v in list(dup.items())[:20]}}
    (ROOT / "data/qa-static.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if k != "failures"}, ensure_ascii=False)[:900])
    for b in bad[:40]: print("  FAIL", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
