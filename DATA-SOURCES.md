# Data sources

Where every kind of fact comes from. Game root: `../blonde` (read-only; the guide never writes there).

## 1. Order of authority

1. **The completed natural playthrough** — `blonde/qa/natural-run-v100`, `-v101`, `-v102` (blank save to Hoenn credits, postgame and link smoke). Authority for progression order, gates, NPC steps, puzzles and common mistakes.
2. **The v105 ROM** (`d76ce7db…513a`, public version v1.0 release candidate, not yet owner-verified) — authority for every number and list: teams, encounters, items, shops, maps, species data.
3. **The source tree and build layers** — used where the ROM's strings and art were built from them (names, Pokédex text, sprites, event scripts).
4. **The project's audits** — only for content the run did not play, and labelled as such on the page.

v103 and v104 differ from v102 (the build the run finished on) by 1,861 bytes of script and text: Space Center stair guard, Oak's call typo, Dowsing Machine wording, seven Hoenn badge speeches. Every extracted table is the same data as on v102 (checked by re-running the extractor on both). v105 adds 473 bytes to v104 in three places (Wattson's speech at `0x090AB550`, the title sheet pointer at `0x09F6A144`, a new title sheet at `0x09F8CCA8`); none is in a table the extractors read, so `data/rom/` is the v104 extraction with the v105 identity recorded in `data/rom/manifest.json` (`extracted_from`).

## 2. Source-of-truth map

| Fact | Tool → file | Read from | Trace field |
|---|---|---|---|
| Maps, connections, warps, NPC / trainer objects, hidden items | `romx.py` → `data/rom/world.json` | ROM `gMapGroups` → map headers and events (908 maps) | `src` = table index, header symbol, address |
| Area map images | `romrender.py` (called by `romx.py`) → `site/assets/game/maps/` | ROM block data, metatiles, palettes; Hoenn tiles from the ROM (LZ77, `HMC1` packed records); Johto / Kanto tile art from the source tilesets (ROM copy is smol-compressed) | — |
| Trainer teams, levels, items, abilities, moves, format, prize rate | `romx.py` → `data/rom/trainers.json` | ROM `gTrainers[NORMAL]` (ids 1–633), `HoCampaignTrainers` (634–837), `HoExtTrainerRecords` (1152+) | `src` |
| Which trainers stand on which map | `romx.py` | `trainerbattle` commands reachable from each map's object scripts | `world[map].trainers` |
| Wild encounters, four times of day | `romx.py` → `data/rom/encounters.json` | ROM `gWildMonHeaders` (276 headers); slot weights are the engine's | `src` |
| Item balls, gift scripts | `romx.py` → `data/rom/gives.json` | ROM script bytes (`finditem` / `giveitem`), attributed to a map by script symbol | `addr`, `sym` |
| Shop stock | `romx.py` → `data/rom/marts.json` | ROM `pokemart` lists reached by an object on a shipped map | `sym`, `list_sym` |
| Place names, Town Map positions | `romx.py` → `data/rom/sections.json`; `worldmap.py` | ROM `gRegionMapEntries`; region-map layouts | — |
| Species stats, types, abilities, Pokédex number, evolutions with conditions, level-up moves | `dex.py` → `data/dex.json` | ROM `gSpeciesInfo` (268-byte rows) | `src` |
| Species names, Pokédex text, form flags, sprites | `dex.py` | `src/data/pokemon/species_info/*.h`, `graphics/pokemon/` | `src` |
| **Which Pokémon are obtainable** (the public Pokédex) | `availability.py` → `data/availability.json`, `AVAILABILITY-AUDIT.md` | ROM wild tables on reachable maps (map graph from warps, connections and script warps), event scripts (gifts, eggs, static and boss battles that allow capture, trades, roamers, the form converter), then evolution and Day Care closure from the ROM's evolution tables and egg groups; rules and hand-verified sources in `content/availability-rules.json` | `methods[].evidence` per entry; `reason` per excluded entry |
| Mega forms and their stones | `dex.py` → `data/megas.json` | `src/data/pokemon/form_change_tables.h` | `src` |
| Obtainable Mega Stones + completeness check | `megastones.py` → `data/megastones.json` | `data/scripts/hns_mega_stone_menus.inc`, cross-checked against the ROM bytes beside the aide's menus and against every item ball, hidden item, gift and shop | `check` block |
| Fixed encounters and gift Pokémon | `statics.py` → `data/statics.json` | `data/maps/*_hns/scripts.inc`, Hoenn overlay `qa/gym-rematch-yes-no-v84/map_events_overlay.s` | `src` |
| Item descriptions and pockets | `extract.py` → `data/items.json` | `src/data/items.h` | `src` |
| Credits | `credits.py` → `data/credits.json` | `qa/hgss-credits-build-v85/data/credits_text.txt` (the owner-edited credits) | section ids |
| Walkthrough steps, gates, puzzles | `content/walkthrough/*.json` | the natural run's trace and website notes | `ev` on every chapter (trace rows) and `basis` |
| Feature guides | `content/features.json` | run notes, game text, option strings in `src/challenge_menu.c` | `ev`, `basis` |
| Emulator setup | `content/play.json` | each emulator's own site, listed per device in `sources` | `sources`, `checked` |

## 2a. Permanent rule

**The Project Blonde public Pokédex must represent Pokémon legitimately obtainable in the current approved game build, not every species defined by the underlying ROM engine.** Every future release must revalidate Pokémon availability before the website is redeployed.

## 3. How to correct a wrong fact

- A number or list is wrong → it came from an extractor. Find the record's `src` in `data/`, fix the decoder (never the JSON) and re-run it.
- A walkthrough instruction is wrong → edit the chapter in `content/walkthrough/`; its `ev` names the trace rows it was written from.
- The build refuses → the message names the chapter and the map, place, trainer or item that does not exist in the game data.

## 4. Stated limits

See "Known gaps" in `CONTENT-COVERAGE.md`. In short: nothing about routes or unlock conditions is published for content the natural run did not play; shared Johto / Kanto Mart stock and prices are not extracted; fixed encounters come from scripts and three retired ones are labelled.
