# Pokémon data and display audit

Build: v105 (public v1.0 release candidate). Audit date 2026-10-09.

## The Probopass report

The site showed `PROBOPASS  ● ROCK  ● SIDE HAZARD SHARP STEEL`.

- **ROCK** was Probopass's first type, correct.
- **SIDE HAZARD SHARP STEEL** was its second type, **Steel**, under the wrong name. It was never strategy data. The site has no battle-role or strategy labels anywhere.
- The dot before each label is the type colour marker, which made one long label read like two fields.

**Cause.** `tools/dex.py` read the correct type byte from the ROM (9) and named it by looking for a symbol starting with `TYPE_` that has that value. `include/constants/battle.h` defines an alias for hazards, `TYPE_SIDE_HAZARD_SHARP_STEEL = TYPE_STEEL`, and it sorts first. So the data extraction was wrong, not the page. Rock has the same kind of alias (`TYPE_SIDE_HAZARD_POINTED_STONES`) but `TYPE_ROCK` happens to sort first.

**Extent.** 93 records carried the wrong label: every Steel-type, on every page that shows types (Pokémon pages, trainer teams, the legendary guide, the Mega Stone list, search text).

**Fix.** Type names now come from the game's own `enum Type` in `include/constants/pokemon.h`. The extractor stops if that list ever disagrees with the ROM symbols. `data/dex.json` changed in exactly 93 lines, all `"Side Hazard Sharp Steel"` → `"Steel"`.

## Audit of the 482 public entries

`python3 tools/qa_pokemon_data.py --audit` → `data/pokemon-audit.json`.

| Check | Result |
|---|---|
| Entries | 482 = 440 species + 42 regional forms (unchanged) |
| Types against the ROM's two type bytes | 482 of 482 agree |
| Types against the species source (`MON_TYPES(...)`) | 466 of 466 agree (16 entries use a macro the check does not read) |
| Abilities and hidden ability against the species source | No difference |
| Regional forms | Each read from its own ROM row, not from its base species |
| Duplicate ids, page names or display names | None |
| Other name tables with the same alias problem (abilities, trainer classes, map types) | None |

Shared with the extractor and not proven independently: the size of a species row (268 bytes) and the offsets of the type and ability fields.

No availability change. No species added or removed.

## Field separation

Types, abilities, held items, moves, evolution and encounters come from separate fields and are shown in separate elements. Only the type name table was wrong. There are no editorial strategy descriptors on the site, so nothing needed relabelling.

## Display change

One small CSS change in `site/assets/app.css`: a type label never breaks across lines, and a pair of labels wraps as whole labels on a narrow screen. No redesign.

## Components checked

All type labels are drawn by one helper (`types()` in `tools/site_core.py`). Checked in the built pages: Pokémon pages (482), trainer team rows, the legendary guide, the Mega Stone list, the Pokédex list search and the global search index. 3,446 labels, all one of the 18 types.

## Evidence

`qa-evidence/map-rendering/`: `before-live-*-pokemon-probopass.png`, `before-live-*-trainer-team-steel.png`, `local-*-pokemon-probopass.png` (dual type), `local-*-pokemon-pikachu.png` (single type), `local-*-pokemon-sandslash-alola.png` (regional form), `local-*-trainer-team-steel.png`.
