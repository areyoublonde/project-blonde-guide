# Project Blonde Guide

Player-facing walkthrough and reference site for Pokémon Project Blonde. Static, generated from the game's own data.

**Status:** complete and tested locally; **not deployed** (see `DEPLOYMENT-STATUS.md`). Game baseline: **v1.0 release candidate (build v105)**, not yet owner-verified. No game file is distributed; the download is disabled.

## Permanent rule: the Pokédex is an availability list

**The Project Blonde public Pokédex must represent Pokémon legitimately obtainable in the current approved game build, not every species defined by the underlying ROM engine.**

Every future release must revalidate Pokémon availability before the website is redeployed: change `BUILD` in `tools/romx.py`, then run `romx.py`, `dex.py` and **`availability.py`**, read `AVAILABILITY-AUDIT.md`, and only then build. The build refuses to run if `data/availability.json` was computed for a different ROM hash, and it stops on any disagreement between the audit and the pages (19 checks, listed at the end of the audit). Hand-checked sources, retired sources and special-area links live in `content/availability-rules.json`, each with its evidence; nothing is made obtainable by typing it there without a script that gives it.

## Run it

Python 3.9+ and Pillow. No Node, no install step.

```sh
cd blonde-guide
python3 tools/build.py                 # data/ + content/ -> dist/   (about 3 s, 1,296 pages)
python3 -m http.server 8765 -d dist    # http://localhost:8765/
python3 tools/qa_static.py             # every link, anchor and asset on every page
python3 tools/qa_browser.py            # Chrome, desktop + phone: page sweep and 107 interaction checks
python3 tools/qa_browser.py --all      # every route at phone width
python3 tools/qa_pokedex.py [url]      # Pokédex search, filters and availability, measured by what is visible; pass the live URL to test production
```

Re-extract from the game (reads `../blonde`, never writes there):

```sh
python3 tools/worldmap.py && python3 tools/romx.py && python3 tools/dex.py && python3 tools/availability.py && python3 tools/statics.py \
  && python3 tools/megastones.py && python3 tools/credits.py && python3 tools/pics.py && python3 tools/plates.py
```

To move to a newer game build, change the four lines of `BUILD` at the top of `tools/romx.py`; the extractor refuses to run if the ROM hash differs.

## Read first

- `IMPLEMENTATION-STATUS.md` — what is done, how to resume
- `AVAILABILITY-AUDIT.md` — generated: which Pokémon are obtainable, how, and why the rest are left out
- `CONTENT-COVERAGE.md` — generated: expected vs generated pages, known gaps
- `QA-RESULTS.md` — what was tested and what was not
- `DEPLOYMENT-STATUS.md` — hosting, and what needs the owner
- `DATA-SOURCES.md` — where every kind of fact comes from
- `REDESIGN-SYSTEM.md`, `PAGE-TYPE-ARCHITECTURE.md`, `MOBILE-UX.md` — the design ("The Road")

## Layout

```
content/chapters.json            order of the road and the crossings between regions
content/walkthrough/*.json       58 chapters (johto, kanto, hoenn, postgame), each with its evidence
content/features.json            15 feature guides
content/mega-stones.json         editorial layer for the Mega Stones section (the stone list itself is extracted)
content/play.json, releases.json device setup, saves, release facts (download disabled)
content/site.json, about.json    navigation, checklist, general Stuck? answers, About
data/rom/                        decoded from the ROM by tools/romx.py — do not edit
data/dex.json, megas.json, megastones.json, statics.json, credits.json   other generated data — do not edit
site/assets/app.css, app.js      the whole front end
site/assets/game/                maps, sprites, Town Maps, trainer pictures (generated)
tools/romx.py, romrender.py      ROM extractor and map renderer
tools/dex.py, statics.py, megastones.py, credits.py, pics.py, worldmap.py, plates.py
tools/model.py, site_core.py, build.py    the game model, shared fragments, one builder per page type
tools/cdp.py, qa_static.py, qa_browser.py, qa_webkit.py
```

The build stops if content names a map, place, trainer or item that the game data does not contain.
