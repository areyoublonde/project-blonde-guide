# Implementation status

Resume file for the full-site completion task (brief received 2026-10-08). Update after every milestone.

## Baseline decisions (audit, done)

- **Game baseline: v105 = public v1.0 RELEASE CANDIDATE, NOT USER VERIFIED** (`d76ce7db…513a`, owner instruction 2026-10-09). v105 = v104 + 473 bytes
  (Wattson line, title label); metadata only was updated, extractors not re-run. Before that: v104 (`2b254f96…7582`), declared frozen RC on 2026-10-08 (mid-session;
  work began on v102). v103 + v104 change 1,861 bytes of script and text only; extracted tables are identical to v102.
  The site says "frozen release candidate, not a public release" and never "1.0".
- **Evidence order:** natural run (`blonde/qa/natural-run-v100|v101|v102`) > ROM tables > source tree > older audits.
- **Hoenn lives only in the ROM / build layers.** `tools/romx.py` decodes the v102 ROM with the v84 symbol table
  (`qa/natural-run-v102/harness/sym-v84.json`): 782 maps (238 Hoenn), 1,171 trainers (H&S 1–633, legacy Hoenn 634–837
  `HoCampaignTrainers`, extended 1152+ `HoExtTrainerRecords`), 219 encounter headers with four times of day, map-section
  names, item balls, hidden items, gift scripts, Mart stock. Output: `data/rom/*.json`.
- **Mega Stones (owner addition):** dedicated searchable section. Elm's lab aide hands out 51 stones free once you hold the
  MEGA RING (`data/scripts/hns_mega*.inc`, called from `NewBarkTown_Lab_hns`) — an approved feature, not a debug leftover.
  MEGA RING: Radio Tower 5F after ARCHER (natural trace row 94). Completeness check compares ROM/source vs site.
- No git repo, no `gh`, no Node. Python 3.9 + Pillow only. Browsers: Chrome, Safari (no Firefox, no Playwright).

## Chapter order corrections found by the natural run

- Sprout Tower is mandatory (Route 32 gate checks tower scene, ZEPHYR BADGE, EGG).
- Goldenrod Gym needs the Radio Card quiz first; the badge comes after the Bridget scene.
- Ecruteak as played: Burned Tower → Gym → Theater (SURF).
- Olivine/Cianwood/Mahogany are free order and scale (_1 / _1_2 / _1_3); Radio Tower starts only after the 7th badge.
- Kanto as played: Vermilion → Saffron → Cerulean + Power Plant chain → Lavender radio → Snorlax → Diglett's Cave →
  Pewter → Celadon → Fuchsia → Viridian/Pallet → Cinnabar/Seafoam (Blaine) → Blue → Oak.
- Then: Kanto League rematch → Mt. Silver (RED) → Viridian Forest (ASH) → OAK call → BIRCH + truck in Pallet → Littleroot.
- Hoenn: see `natural-run-v102/NATURAL-PLAYTHROUGH-WEBSITE-NOTES.md` (15-step order); Champion is WALLACE; JUAN is the 8th Leader.

## Work plan and state

| # | Milestone | State |
|---|---|---|
| 1 | Audit of site, docs, natural run, versions | done |
| 2 | `tools/romx.py` ROM extractor: 908 maps (348 Hoenn), 1,171 trainers, 276 encounter headers, item balls, hidden items, gifts, marts, all maps rendered | done |
| 3 | `tools/dex.py` (1,241 species records from `gSpeciesInfo`, evolutions with conditions, sprites), `statics.py`, `megastones.py`, `credits.py`, `pics.py` | done |
| 4 | Content: 58 chapters in `content/walkthrough/{johto,kanto,hoenn,postgame}.json`, 15 feature guides, Mega Stones, Play (4 devices), About | done |
| 5 | `tools/model.py` + `site_core.py` + `build.py`: 1,883 pages, build stops on any content reference the ROM does not contain | done |
| 6 | `tools/qa_static.py`: 97,060 links and 35,983 assets, 0 failures | done |
| 7 | Browser QA (`tools/qa_browser.py`): 181-page sweep on desktop + phone, all 1,883 routes at phone width, 107 of 107 interaction checks; WebKit and Firefox NOT run (see `QA-RESULTS.md`) | done |
| 8 | `QA-RESULTS.md`, `DEPLOYMENT-STATUS.md`, README, DATA-SOURCES, PAGE-TYPE-ARCHITECTURE | done |
| 9 | Deployment prep: `git init`, `.github/workflows/pages.yml`, sub-path build verified | done |
| 10 | **Publish** — blocked on the owner: GitHub account / repository, credentials on this machine, approval of public content (`DEPLOYMENT-STATUS.md`) | waiting |

## If work continues

- After the owner's go-ahead: commit, push, enable Pages (Actions), then verify the live URL.
- Content worth adding when it has been played: Steven / Wally final battles, Johto Dojo rematches, post-League legendaries, far-off areas, battle facilities (all `basis: source` today).
- Not extracted: standard Johto / Kanto Mart stock and all prices; TM compatibility.
- Enable Safari remote automation and run `tools/qa_webkit.py`.

## Rebuild from scratch

```sh
cd blonde-guide
python3 tools/worldmap.py && python3 tools/romx.py && python3 tools/dex.py && python3 tools/statics.py \
  && python3 tools/megastones.py && python3 tools/credits.py && python3 tools/pics.py && python3 tools/plates.py
python3 tools/build.py            # add --base /repo-name for a GitHub Pages project site
python3 tools/qa_static.py
python3 -m http.server 8765 -d dist
```

`tools/extract.py` (old source-tree extractor) is still needed once for `data/items.json` (item descriptions) and the three plate source maps; its other outputs are superseded by `data/rom/`.

## Content facts still to double-check if the game changes

- Chapter text marked `basis: source|mixed` (postgame except the first three) describes data only.
- `content/releases.json`: download disabled, distribution method `undecided`. Owner decision.

## Publication (owner instruction 2026-10-09)

- Repository name: `project-blonde-guide` → `https://<account>.github.io/project-blonde-guide/`. Do not publish until the owner approves the final repository and URL.
- Personal dedication and family acknowledgement are excluded from the public credits (`PRIVATE` in `tools/credits.py`).
- Download stays disabled until the owner explicitly approves a release and supplies distribution details.
