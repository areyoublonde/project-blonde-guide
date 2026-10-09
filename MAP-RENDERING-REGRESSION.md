# Map and Pokémon regression checks

Added 2026-10-09 with the Faraway Island and “Side Hazard Sharp Steel” fixes. Two of these run on every deploy.

## What runs where

| Check | Command | Needs the game folder | Runs on deploy |
|---|---|---|---|
| Map audit from the ROM | `python3 tools/qa_maps.py --audit` | yes | no |
| Map images against the audit | `python3 tools/qa_maps.py` | no | **yes** |
| Map inventory report | `python3 tools/qa_maps.py --report` | no | no |
| Contact sheets | `python3 tools/map_sheets.py` | no | no |
| Pokémon audit from the ROM | `python3 tools/qa_pokemon_data.py --audit` | yes | no |
| Pokémon types and fields on the built pages | `python3 tools/qa_pokemon_data.py` | no | **yes** |
| Map viewer and type labels in a browser | `python3 tools/qa_mapview.py [base-url] [--port N]` | no | no |

## After re-rendering maps or moving to a new build

1. `python3 tools/romx.py` then `python3 tools/dex.py --no-sprites`
2. `python3 tools/qa_maps.py --audit` and `python3 tools/qa_pokemon_data.py --audit`. Both must report no problems, or the problem must be recorded with a reason in `content/map-review.json`.
3. `python3 tools/build.py`, then the two plain checks.
4. `python3 tools/map_sheets.py` and look at the sheets. `python3 tools/qa_maps.py --report`.

## What the map checks prove

**Audit (structural, from the ROM).** For each of the 908 maps: the layout decodes; both tilesets resolve; tile art was found, and art read from a tileset sheet is proven identical to the ROM's compressed block; every metatile id is inside its tileset; under 2% of blocks point at a tile outside the art; the layout size equals the metadata; the PNG has exactly that size; the image is not one flat colour.

**Plain check (on deploy).** Every map has its PNG; the PNG's size matches the metadata; its hash is the audited one, so any unreviewed change to a map image stops the deploy; no two maps share an image name; no orphan image; every map image and every `#m-` anchor on the built pages belongs to a real map; the 16 once-broken maps are still drawn.

**What they do not prove.** That a map looks right. That is the contact sheets and, for the maps listed under `runtime` in `content/map-review.json`, a pixel match with an mGBA screenshot. Image stability is by hash, not by comparison with a trusted reference picture: no independent reference set exists for this build.

## What the Pokémon checks prove

Every record's types are one or two distinct names from the 18 real types. The 482 public entries' types equal the audited ROM values, regional forms included. The public Pokédex is 440 + 42. No duplicate ids, pages or display names. Every type label on every built page is a real type. Every trainer team row and every Pokémon page shows that Pokémon's audited types. No ability field holds a type name.

Run against the pages as they were before the fix, the check reports 488 problems, starting with `type label 'Side Hazard Sharp Steel' is not a Pokémon type`.

## Results on the integrated build (this branch + Download & Play, 2026-10-09)

| Suite | Result |
|---|---|
| Website build | 1,312 pages, 1,613 search entries, 60 chapters |
| `qa_maps.py --audit` | 908 maps, 3 recorded notes, 0 failures |
| `qa_maps.py` | 908 images, 462 shown, 0 problems |
| `qa_pokemon_data.py --audit` | 482 entries, 0 differences |
| `qa_pokemon_data.py` | 482 pages, 3,446 type labels, 0 problems |
| `qa_static.py` (links and assets) | 82,534 links, 32,879 assets, 0 failures |
| `qa_availability.py` | 36 of 36 |
| `qa_story.py` | 0 failures (2 known gaps, unchanged) |
| `qa_mapview.py` (map viewer, type labels; desktop + phone) | 159 of 159 |
| `qa_pokedex.py` (list, search, filters) | 136 of 136 |
| `qa_legendaries.py` | 144 of 144 |
| `qa_play.py` (Download & Play) | 134 of 134 |
| `qa_browser.py` (site-wide sweep, search, mobile) | 107 of 107 checks; 185 pages × 2 viewports swept, 0 failures |

Browser tests ran on their own server port (8791) and Chrome ports and profile (`pb-mapui-`), apart from other sessions.
