# Map rendering defects

Build: v105 (public v1.0 release candidate), ROM SHA-256 `d76ce7db…513a`, checked by `tools/romx.py` before any byte is read. Audit date 2026-10-09. The ROM and the game project were read only.

## Summary

| | |
|---|---|
| Maps audited | 908 (462 shown on the site, 446 not shown) |
| Defective images found | 16 |
| Defective images corrected | 16 |
| Page defects found | 1 (three maps with a fixed encounter had no map section) |
| Root causes | 3 |
| Left as recorded notes | 3 maps (game data, not the renderer) |

Before and after, all sixteen: `qa-evidence/map-rendering/before-after-all-16-maps.png`.

## D-1. The General primary tileset was never found (15 maps)

**Symptom.** Dark blue rectangle with a few stray tiles. Faraway Island Entrance was 99% one colour; Faraway Island Interior showed only its tall grass.

**Cause.** `tools/romrender.py` cannot decode this build's `smol`-compressed tile art from the ROM, so it reads the same art from the game project's tileset sheet. It found the sheets by scanning `src/data/tilesets/graphics.h`. One tileset, `gTilesetTiles_General`, is declared in `src/graphics.c` instead. The renderer got zero tiles for it, and every tile of the primary tileset was drawn as the backdrop colour. Only the secondary tileset's tiles appeared.

**Not the cause** (each checked): map dimensions, block data, metatile decoding, primary / secondary split, palettes, layer order, PNG colour reduction (the largest map has 105 colours, under the 255 limit), image paths, CSS, scaling, the viewer.

**Fix.** The renderer scans both files. The audit then proves, for every tileset read from a sheet, that the compressed file built from that sheet is byte-for-byte the block in the ROM (127 of 127 tilesets).

**Maps.** Faraway Island Interior and Entrance; Southern Island Exterior and Interior; Birth Island Exterior and Harbor; Battle Frontier Outside West, Outside East, Reception Gate, Battle Palace Corridor and Battle Room; Verdanturf Battle Tent Battle Room; Fuchsia City Safari Zone Beach, Brush and Mountain.

Six Contest Hall maps use the same tileset but only its blank tile, so their images did not change.

## D-2. Uncompressed tile art was skipped (1 map)

**Symptom.** Petalburg City Gym: a black strip, 99% one colour.

**Cause.** The Gym's secondary tileset is stored uncompressed in the ROM (`isCompressed = 0`). The renderer only handled LZ77 data.

**Fix.** Uncompressed tilesets are read as plain 4bpp. The Cable Club tileset (Trade Center, Colosseum; not shown on the site) is read the same way now.

**Runtime check.** Two mGBA screenshots of the Norman battle room match the new image block for block (36 and 42 visible blocks identical at one alignment).

## D-3. Faraway Island Interior had no map on its page

**Symptom.** `/world/kanto/faraway-island/#m-faraway-island-interior` scrolled to a line of text under “Also here”. The only map on the page was the blank Entrance image.

**Cause.** The game types Mew's clearing as an indoor map. `rich()` in `tools/build.py` gives an indoor map a full section only if it has wild Pokémon, trainers, items or pitfalls. A fixed encounter did not count.

**Fix.** A map with a fixed battle encounter gets its own section and map. This affects three maps: Faraway Island Interior, Saffron City Fighting Dojo and Sinjoh Ruins Registeel Room. No other page changed.

## Faraway Island acceptance

| Check | Result |
|---|---|
| Terrain, no missing tiles | 754 of 754 blocks resolve; 747 identical to an independent render of the Emerald layout kept in the game project (the other 7 are animated flower and water frames) |
| Palettes | Read from the ROM; unchanged |
| Dimensions | 29×26 tiles, 464×416 px, as the layout says |
| Layers | Bottom then top, as the engine draws them |
| Anchor | Lands on the map's own section (desktop and phone) |
| Zoom, pan, fit, markers, full screen | Pass on desktop and phone (`tools/qa_mapview.py`) |
| In-game capture | **Not done.** Reaching the island in the key-press-only harness needs a played route with the Old Sea Map. Marked “reference-render compared”, not “runtime verified”. |

The game has one state for this map. The picture shows the layout as stored: Mew, the moving grass and the player are not drawn.

## Recorded notes (not renderer defects)

1. **Faraway Island Entrance and both Southern Island maps use the Rustboro secondary tileset in the game data** (`data/layouts/layouts.json`), where Emerald uses other tilesets. Cliffs and trees look different from Emerald. The site shows what the ROM defines. Whether this looks right in play was not checked. This is a question about the game, not the site.
2. **Fuchsia Safari Zone Beach**: 54 blocks of the gate building point at tile slots the General tileset does not have. Drawn transparent.
3. **Melemele Isle** (and, less, Akala, Poni, Ula'ula): overlay entries on greenhouse roofs point past the Alola tile sheet. Drawn transparent. Nothing visibly missing.
4. **Union Room**: leftover layout with mismatched tilesets. Not reachable, not shown.

## Limits of every map picture

One still frame for animated tiles. No time-of-day tint, weather or underwater blending. No people or objects. No script-changed tiles. Battle Pyramid and Trainer Hill floors show only their stored template.
