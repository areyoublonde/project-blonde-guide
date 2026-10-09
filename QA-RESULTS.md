# QA results

_Last run on 2026-10-09 against the local production build for v1.0 release candidate (build v105), after the About page and release metadata changes. The all-routes sweep was run on the previous day's build (v104 data; same pages, same data tables). Regenerate the numbers with the commands in `README.md`; the raw results are in `data/qa-*.json`._

## Summary

| Test | Scope | Result |
|---|---|---|
| Build validation | every map, place, trainer, item and Mega Stone named in content must exist in the game data | **pass** (the build stops otherwise) |
| Static links and assets (`qa_static.py`) | all 1,883 pages: 97,060 internal links and anchors, 35,983 images / scripts / styles, one `<h1>`, `alt` on every image | **0 failures** |
| Same, under a GitHub Pages sub-path | built with `--base /project-blonde-guide` | **0 failures** |
| Browser page sweep, Chrome (`qa_browser.py`) | 181 pages × desktop 1440 px and phone 390 px: every hub, every chapter, every feature and setup page, a spread of Pokémon / Trainer / place / item pages | **0 failures** |
| Browser all-routes sweep, Chrome (`qa_browser.py --all`) | all 1,883 routes at 390 px: visible `<h1>`, no script error, no broken image, no sideways scroll, tap targets | **0 failures** after one fix (see below) |
| Interaction checks, Chrome | 107 scripted clicks, key presses, filters and state checks | **107 of 107 passed** |
| WebKit (Safari) | `qa_webkit.py`, 22 checks prepared | **not run** — Safari's “Allow remote automation” is off on this machine and turning it on needs the owner |
| Firefox | — | **not run** — not installed on this machine |

## Pokédex availability correction and search fix (2026-10-09, commit `b1a5a88`)

| Test | Result |
|---|---|
| Build validation, 19 availability checks (`AVAILABILITY-AUDIT.md`) | 0 failures |
| Static links and assets, root and `/project-blonde-guide/` sub-path | 1,296 pages, 77,856 links, 32,032 assets, 0 failures |
| Chrome, general suite (`qa_browser.py`), now measuring computed visibility | 182 pages × 2 viewports clean; 107 of 107 |
| Chrome, every route at phone width (`qa_browser.py --all`) | 1,296 pages, 0 failures |
| Chrome, Pokédex test (`qa_pokedex.py`), local | 136 of 136 |
| Chrome, Pokédex test, **live site** | 136 of 136; all 1,296 live routes return 200; 49 sampled removed Pokémon pages return 404 |
| Availability regressions (`qa_availability.py`): item aliases, NPC gifts, branch-opened shops; 2026-10-09 after the Porygon2 / Porygon-Z correction | 36 of 36 local (data, site, ROM); 31 of 31 in the Pages workflow (no ROM there) |
| Chrome, Pokédex test after that correction (482 entries) | 136 of 136 local; 136 of 136 **live** |
| Legendary guide completeness (`tools/legendaries.py`): ROM flags vs availability dataset vs guide, species and level verified in the ROM per entry | 360 of 360; 97 audited, 32 obtainable, 32 entries |
| Static links and assets with the Legendary guide, root and `/project-blonde-guide/` sub-path | 1,305 pages, 81,218 links, 32,166 assets, 0 failures |
| Chrome, Legendary guide (`qa_legendaries.py`), desktop and phone | 144 of 144 local; 144 of 144 **live** |
| Chrome, general suite and Pokédex test on the same build | 183 pages × 2 viewports clean, 107 of 107; Pokédex 136 of 136 |
| Safari / WebKit | **not run**: `safaridriver` could not create a session on this machine (first "Allow remote automation" disabled, later a session timeout) |
| Firefox | not run: not installed |

The Pokédex test types each query with real key events and counts rows whose computed `display` is not `none`: `pikachu`, `Pikachu`, `PIKA`, `eevee`, `ninetales`, `alolan`, `vulpix alola`, `galarian`, `hisui`, `char`, `mr. mime`, `farfetch'd`, `ho-oh`, `Ho Oh`, `nidoran`, `porygon`, `unown`, a no-match string, clearing, region and method filters alone and combined with search, detail pages, evolution links, global search, on desktop and phone. Evidence: `qa-evidence/pokedex-audit/`.

## Final pre-publication pass (v105, 2026-10-09)

- Root build: static check 0 failures; Chrome sweep of 181 pages × 2 viewports clean; 107 of 107 interaction checks.
- Sub-path build at `/project-blonde-guide/`: static check 0 failures; browser smoke test 14 of 14 (`data/qa-subpath.json`): 23 pages × 2 viewports, the Mega Stones section (51 stones, completeness match, filter, links stay in the sub-path), search index, saved position, disabled download, version wording, About page (project credits present, personal sections absent, non-affiliation notice).
- v105 against v104: 473 bytes in three places, none in an extracted table; extractors not re-run.

## Defects found by testing and fixed

- 131 broken in-page anchors: Pokémon and item pages linked to interior maps that had no section on their place page. Every map now has an anchor.
- Phone: mode, time-of-day and tab switches and the map expand button were 36 px; now 44 px. List rows (Pokédex, places, Trainers, items) are tappable across the whole row.
- Phone: sideways scroll of 3–27 px on chapters with long move lists or long map titles, 9 px on Home (the road line with 58 chapters), 6 px on Sinjoh Ruins (a long encounter row). All fixed; re-swept.
- Search results are now HTML-escaped before display.
- The chapter page picked a small interior as its main map; it now uses the chapter's own outdoor map.
- The map-group walk in the extractor stopped at empty slots and missed 126 Hoenn maps (dungeons, Safari Zone, the truck, the S.S. Tidal). Fixed: 908 maps.
- A stale headless Chrome from an aborted run made later runs hang. Not a site defect; noted in the harness instructions.

## Interaction checks by area

### Desktop sweep

- ✅ Desktop sweep: 181 pages clean

### Phone sweep

- ✅ Phone sweep: 181 pages clean

### Home

- ✅ Home (new player): headline is Play Project Blonde
- ✅ Home: one primary button above the fold
- ✅ Home: route into the walkthrough and into Play
- ✅ Home: section links cover all eight areas
- ✅ Home: Get started opens Play
- ✅ Home (returning): You are here with place, chapter and Continue
- ✅ Home (returning): Badge progress and next Badge

### Road

- ✅ Road: 58 stops, every one a link
- ✅ Road: four regions in order
- ✅ Road: first stop opens Chapter 1

### Chapter

- ✅ Chapter: opening it saves the position
- ✅ Chapter: title, objective, quick route in first screen
- ✅ Chapter: shows what it is based on
- ✅ Chapter: Quick mode hides the full walkthrough
- ✅ Chapter: Full mode restores it
- ✅ Chapter: rival battle has a team per starter
- ✅ Chapter: starter tab switches the team
- ✅ Chapter: time-of-day switch changes the tables
- ✅ Chapter: a sticking-point answer opens
- ✅ Chapter: Next goes to the following chapter
- ✅ Chapter: journey bar Previous goes back

### Map

- ✅ Map: zoom in enlarges
- ✅ Map: selecting a marker shows its detail
- ✅ Map: layer toggle hides its markers
- ✅ Map: expand fills the screen
- ✅ Map: Esc leaves full screen

### Gym map

- ✅ Gym map: pitfall layer exists and reveals

### Spoilers

- ✅ Spoilers: Hoenn crossing text is blurred by default
- ✅ Spoilers: selecting it reveals it
- ✅ Spoilers: global switch turns them on

### Search

- ✅ Search: / opens the palette
- ✅ Search: empty palette offers Continue first
- ✅ Search: a misspelling finds Misdreavus
- ✅ Search: a Leader's name finds their page
- ✅ Search: Mega Stones finds its section
- ✅ Search: a question finds its Stuck? answer
- ✅ Search: a place finds its page
- ✅ Search: an HM finds its item page
- ✅ Search: results are grouped by kind
- ✅ Search: arrow keys move the selection
- ✅ Search: Enter opens the selected result

### Search page

- ✅ Search page: ?q= runs the query

### Pokédex

- ✅ Pokédex: over a thousand entries listed
- ✅ Pokédex: typing a type filters the list
- ✅ Pokédex: region filter narrows it
- ✅ Pokédex: count readout matches

### Pokémon

- ✅ Pokémon: regional form is a separate, linked entry
- ✅ Pokémon: locations table and Town Map dots
- ✅ Pokémon: Alolan form has its own locations (Alola isle)
- ✅ Pokémon: Mega forms link to their Mega Stones
- ✅ Pokémon: trade evolution shows its level alternative

### Trainers

- ✅ Trainers: region filter

### Trainer page

- ✅ Trainer page: team with levels, items and moves

### Items

- ✅ Items: filter finds HM03 Surf

### Mega Stones

- ✅ Mega Stones: 51 obtainable stones listed
- ✅ Mega Stones: searchable
- ✅ Mega Stones: completeness check reports a match

### Mega Evolution guide links to the Mega Stones section

- ✅ Mega Evolution guide links to the Mega Stones section

### Item page

- ✅ Item page: Mega Stone links to its Pokémon and the section

### World

- ✅ World: hovering a place lights its dot
- ✅ World: Hoenn tab swaps the map and list
- ✅ World: filter leaves matching places

### Place

- ✅ Place: area map, encounter tables with four times of day
- ✅ Place: links back to its chapter

### Stuck?

- ✅ Stuck?: choosing where you are gives a next step
- ✅ Stuck?: it sets the last Badge and shows the road ahead
- ✅ Stuck?: answers for that stretch come first
- ✅ Stuck?: no answer from a later region is promoted
- ✅ Stuck?: a plain-language question narrows to the answer

### Progress

- ✅ Progress: setting the current chapter moves You are here
- ✅ Progress: Badges, milestones and chapters tick and count
- ✅ Progress: postgame objectives are tracked
- ✅ Progress: survives a reload
- ✅ Progress: Export produces a progress file
- ✅ Progress: cleared state is empty
- ✅ Progress: Import restores Badges, chapters and position
- ✅ Progress: a wrong file is refused with a message
- ✅ Progress: says plainly that nothing is synced

### Header

- ✅ Header: Continue chip returns to the chapter

### Play

- ✅ Play: download is present but disabled
- ✅ Play: no game file link anywhere on the page
- ✅ Play: four devices offered
- ✅ Play: saving, backup, update, restore, link and troubleshooting are all there
- ✅ Play: link section names the compatibility id and the unsupported modes

### Setup

- ✅ Setup · iphone: full path with Delta, six steps, sources
- ✅ Setup · android: full path with RetroArch, six steps, sources
- ✅ Setup · windows: full path with mGBA, six steps, sources
- ✅ Setup · mac: full path with mGBA, six steps, sources
- ✅ Setup: device chooser switches path
- ✅ Setup: step list jumps to a step

### Nav

- ✅ Nav: More opens and lists Mega Stones

### Keyboard

- ✅ Keyboard: first Tab lands on Skip to content
- ✅ Keyboard: focus is visible
- ✅ Keyboard: every control is reachable (no positive tabindex, no div buttons)

### Reduced motion

- ✅ Reduced motion: animations and transitions are switched off

### 404

- ✅ 404: unknown path is not a blank page

### Phone

- ✅ Phone: Menu opens the full list
- ✅ Phone: Menu links navigate
- ✅ Phone: chapter dock has Journey, Route, Map, Contents
- ✅ Phone: Journey sheet opens with previous / next
- ✅ Phone: Next in the sheet opens the next chapter
- ✅ Phone: Town Map stays pinned while the road scrolls
- ✅ Phone: maps scroll inside their frame, not the page
- ✅ Phone: setup stepper advances
- ✅ Phone: search opens full screen and answers

## Data completeness

- See `CONTENT-COVERAGE.md` (generated with every build): expected and generated page counts match for every page type.
- Extracted data on v104 is identical to v102 for trainers, maps, encounters and item scripts (compared record by record), which is what the release notes of v103 and v104 predict.
- Mega Stones: 92 defined, 51 offered by Elm's aide, 51 of 51 item ids found in the ROM beside the aide's menus, 0 other sources; the page documents 51.
- Spot checks of extracted data against the playthrough's own observations: Falkner's Noctowl Lv. 11 with Sitrus Berry; Roxanne's Mega Aerodactyl Lv. 87 and rematch Lv. 98; Wallace's Wailord Lv. 100; Ash's six with Charizardite Y; Red's Pikachu Lv. 93; Route 101 wild Lv. 70–73; Machoke → Machamp at Level 38; Will's prize ¥5,000 and Roxanne's rematch ¥10,000 from the prize formula.

## Not covered

- Safari / WebKit and Firefox (above). The site uses no framework and only long-established browser features (`<dialog>`, `IntersectionObserver`, `:has()` in two cosmetic rules), but that is an expectation, not a test result.
- Real phones: touch is emulated. Pinch-zoom and momentum scrolling were not exercised.
- Screen-reader output and a measured contrast audit. Structure is in place (landmarks, one heading per page, labels, focus ring, `prefers-reduced-motion`), but no assistive technology was run.
- The hosted site: nothing is deployed, so no test has run against a public URL.
- The game itself: this QA is of the website. Walkthrough accuracy rests on the natural playthrough; chapters not played are labelled.
