# Pokédex audit and search fix — evidence (2026-10-09)

Game: v1.0 release candidate (build v105), SHA-256 `d76ce7db778f09ad9085e6c11a535e6c7c8f4271de1def30d98af46698d5513a` (verified against the delivery folder's `SHA256.txt` and `blonde/release/public-version.json`).

## 1. Search defect

**Reproduced on the live site before any change** (`01-search-defect-reproduction.json`, `01-live-before-search-pikachu.png`): after typing `pikachu`

- the input held `pikachu`, the counter read `1 of 1067`, and 1,066 rows carried the `hidden` attribute, so the script was working;
- but 0 rows were actually invisible: the computed `display` of a hidden row was `grid`.

**Root cause.** `site/assets/app.css` styles list rows with `.dex li, .people li, .places li {display:grid}` (and similar rules for the item and Mega Stone lists). An author `display` declaration overrides the browser's built-in `[hidden] {display:none}`, which has the lowest priority. The stylesheet only restored `display:none` for three unrelated panel types. The same defect was present on Items, Trainers, World and Mega Stones (438, 85, 199 and 51 rows marked hidden, none hidden on screen).

It was not caught earlier because the tests asked whether rows had the `hidden` property, not whether they were visible.

**Fix.** One rule at the top of the stylesheet: `[hidden]{display:none!important}`. No script was replaced. Two small improvements were made while there: matching now prefers the whole phrase (so `ho-oh` finds Ho-Oh, not every row containing "ho" and "oh"), and rows carry searchable form words (`alolan`, `galarian`, `hisuian`, `paldean`).

**Tests** now measure computed visibility: `tools/qa_pokedex.py` (results in `browser-local.json`, `browser-live.json`) and the same change in `tools/qa_browser.py`.

## 2. Availability

See `/AVAILABILITY-AUDIT.md` (generated on every build) and `data/availability.json` (one record per species and regional form, with the evidence for every method). Rules: `content/availability-rules.json`.
