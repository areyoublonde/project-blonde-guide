# Pokédex accuracy audit and website numbering

Audited 2026-10-31 on the latest approved build, **r09 / public v1.4.1**, ROM SHA-256 `115a3204c1b2ff8bff6b39fb89418fd80b7674172b5c97974f7b7da8fd806d58`. The ROM, saves and in-game Pokédex were not changed.

## Result

| | |
|---|---|
| National slots in the ROM | 1,080 (1,025 species + 55 separate regional-form records) |
| Species rows with a name and a Pokédex record | 1,481 (those 1,080, plus 401 Mega, Primal and other forms that share a number) |
| **Entries in the in-game Pokédex** | **482** (440 species + 42 regional forms), `sObtainableToNationalOrder` |
| Rows the National-mode list draws | 440, numbered #001 to #482, with the 42 regional forms inside their base species' rows |
| Johto mode | 282 entries, #001 Chikorita to #282 Celebi |
| Engine slots not in the Pokédex | 598 (585 species + 13 regional forms); the list never draws them |
| Missing, duplicated or wrongly numbered Pokédex entries | **none** |

## Which number the game shows

The compiled Pokédex is `pokedex_plus_hgss.c`, not `pokedex.c`. Three numberings exist and they are not interchangeable.

- **Species id:** the index of `gSpeciesInfo`. Never shown.
- **National number (`natDexNum`):** the key of the seen and caught bits. Never shown in this Pokédex.
- **In-game number:** position in the game's own list, drawn by `CreateMonDexNum` and `PrintMonInfo`. This is the number the site prints.

The game's list is grouped by family, so it departs from the official National Dex from Pichu on: Pichu is #025 (National 172) and Pikachu #026 (National 25). 416 of the 440 species have a number different from their National number.

Numbers are three digits on the list and INFO screens. The STATS page prints the same value with four digits (`No0037`). The site uses three.

## Regional and other forms

- A regional form shows **its base species' number** on the list, INFO and STATS screens. Alolan Vulpix is #039, like Vulpix. The site does the same, because that is the game's behaviour.
- The 42 list positions held by regional forms are never drawn in the Pokédex, so the list skips: 419 → 439 → 446 → 449 → 454 → 457 → 464 → 466 → 469. Numbers run without gaps from #469 to #482.
- Regional evolutions (Perrserker, Sirfetch'd, Mr. Rime, Cursola, Obstagoon, Overqwil, Sneasler, Clodsire) are separate species with their own numbers.
- Mega, Primal and other forms share the base species' number and have no row of their own. That includes the Megas added beyond the mainline set (Mega Meganium, Mega Victreebel, Mega Absol Z). No custom species has its own Pokédex slot.

## Findings from this audit and where they stand (updated 2026-11-01)

The public game is still r09. The three game fixes below exist only in an isolated experimental ROM (`output/v1.4-exp-roster-dex-20261101`, SHA-256 `66f4596e…`), not released. This guide describes the public game, so it does not change for them until a release does.

1. **Summary screen and Hall of Fame differ from the Pokédex for regional forms on r09.** Both print the form's raw list position: Alolan Vulpix is No039 in the Pokédex, No425 on its Summary screen and No.0425 in the Hall of Fame. All 42 forms confirmed on r09. Fixed in the experimental ROM only. The site follows the Pokédex.
2. **Six species fought on r09 but absent from the Pokédex:** Rotom (3 slots), Bronzong, Klinklang, Reuniclus, Eelektross and Beheeyem, on Silph Co scientists 1497, 1500, 1504, 1511, 1514 and 1527. Replaced in the experimental ROM only. A full roster scan found no other species outside the Pokédex.
3. **Johto-mode header shows National totals on r09** once the National Dex is on (`pokedex_plus_hgss.c:2071`, drawn at `:3261`). Fixed in the experimental ROM only.
4. **Paldean Tauros, website fixed.** The Pokédex slot points at the Aqua Breed row, and the running game's Pokédex shows Aqua Breed art, Fighting / Water typing and the Aqua text. The page now shows that and lists all three breeds. Jessica's trade gives the breed by starter: Chikorita Aqua, Cyndaquil Blaze, Totodile Combat (`paldean-tauros-r09.json`, ROM script and table checked). The comment above her script states a different mapping; the code is what the game does, and that mismatch is reported to the owner.
5. **Primal Kyogre and Primal Groudon, website fixed.** The rows (species 954 and 955) were added to `data/dex.json` by re-running `tools/dex.py`, which changed nothing else in that file; both pages now list them under the same number as their base species, with the Orb, ability and stats.
6. **Website data, not shown publicly:** `data/dex.json` has wrong names on two form records of Pokémon that are not in the Pokédex (`SPECIES_FLABEBE_ORANGE`, `SPECIES_FLOETTE_ETERNAL`), a source-parser error in `tools/dex.py`. No page renders them.

## Website audit (live site, before this update)

Compared the live `/pokemon/` list and data with the ROM: 482 rows, 0 missing, 0 extra, 0 duplicate rows, 0 name differences, every regional label correct. It showed no numbers. Its order was National order, which would have put 39 rows out of number order once numbers appeared, so the list now follows the game's order, with each regional form after its base species. Rows are otherwise unchanged. The Pokémon page URLs are unchanged.

## How the numbers reach the site

`tools/dex_numbers.py` reads the ROM tables and writes `data/pokedex-numbers.json`. That file is the only source: `tools/model.py` attaches the number and `dex_no()` prints it. `tools/qa_dex_numbers.py` checks every list row and every Pokémon page against it, in CI and against the live URL. Re-run `dex_numbers.py` for a new approved ROM.

## Evidence (`qa-evidence/pokedex-numbers/`)

- **ROM tables:** every National slot, list and Johto entry was checked against its species row; there are no duplicates, blanks or dangling entries, and no evolution or wild encounter leads outside the list.
- **Running ROM, what is drawn on screen:** all bits forced on in emulator RAM on a private save copy, in National and Johto modes. Each of the 440 and 282 rows was captured from the screen. Digit shapes map one-to-one to the expected digits, and name pixels match the ROM names on every row (`rom-national-rows.json`, `rom-johto-rows.json`).
- **All 42 regional forms:** list, INFO and STATS screens, with the base species' bits cleared so the form is the row's representative (`rom-regional-forms.json`).
- **Summary screen:** tested on Vulpix and Alolan Vulpix only, by writing the species into a party slot in RAM. The other 40 pairs are computed from the same function.

## Limits

- Obtainability was not re-derived. The list of 482 and the availability audit agree, but that audit stands on the r04 extraction, which `content/releases.json` records as the guide's data source (`guide_data_from`). Availability was not replayed in play on r09.
- Forms screens other than these were sampled, not swept. Other sort orders and search results were not swept: the number comes from the same function.
- The bits were forced in RAM, not earned by play.
- Real Safari and iPhone were not tested; browser tests ran in headless Chrome with phone emulation.
