> **Superseded for design and page structure** by `REDESIGN-SYSTEM.md`, `PAGE-TYPE-ARCHITECTURE.md` and `MOBILE-UX.md`. The stack, build pipeline and URL scheme below still apply.

# Site architecture

Project Blonde Guide — a static, data-driven companion site. Status: **prototype for owner review** (2026-10-07).

## 1. Two modes, one site

| Mode | Purpose | Shape |
|---|---|---|
| **Walkthrough** | "What do I do next?" | Chronological chapters, one permanent URL each |
| **Reference** | "Where is X?" | Pokémon, Trainers, World, Items, Features — generated from game data |

Stuck?, Search and My Progress cut across both.

## 2. Navigation (final proposal)

```
HOME
WALKTHROUGH      Johto · Kanto · Hoenn · Postgame
POKÉMON          Pokédex · Where to find · Special & legendary · Forms · Evolutions
TRAINERS         Gym Leaders · Elite Four & Champions · Rivals · Major battles · Rematches
WORLD            Johto · Kanto · Hoenn · Far-off places   (towns / routes / dungeons inside each)
ITEMS            Key Items · TMs & HMs · Evolution items · Important items
FEATURES         one short guide per verified system
STUCK?           (accented in the header)
— footer —       My Progress · Search · About & credits · theme / spoiler switches
```

Changes from the brief, based on the actual game:

- **Postgame sits beside the three regions** in the walkthrough and at `/postgame/`; it is a fourth "region" in the design system, not a separate site section.
- **"Special Areas" became "Far-off places"** — the source contains whole extra areas (four Alola isles, Sinjoh Ruins / New Sinjoh, Embedded Tower, Cerulean Cave, Southern / Birth / Faraway Island) that need a home outside the three regions.
- **Story Events (Lillie, Ash)** get their own postgame chapter; they are custom to this game and gate the road to Hoenn.
- **FAQ is merged into Stuck?** One question-led page instead of two overlapping ones.
- **Day & Night** and **Game Options** were added to Features: both change what a player sees on almost every page.
- Features not yet backed by an accepted build (Link Play) are listed as *awaiting confirmation*, never as supported.

## 3. URL scheme

```
/                                   home
/walkthrough/                       all four parts, every chapter
/walkthrough/{region}/              region landing
/walkthrough/{region}/{chapter}/    chapter            e.g. /walkthrough/johto/ecruteak-city/
/postgame/  /postgame/{chapter}/    postgame landing and chapters
/pokemon/  /pokemon/{species}/      e.g. /pokemon/misdreavus/
/trainers/  /trainers/{region}/{name}/   e.g. /trainers/johto/morty/
/world/{region}/{area}/             (planned)
/items/  /items/{item}/             (index built; item pages planned)
/features/#{id}                     short guides; promoted to /features/{id}/ when a guide outgrows a card
/stuck/#{question-id}
/progress/   /search/?q=   /about/
```

Slugs are permanent once published. Chapter numbers are display-only and may change. In-page anchors (`#theater`, `#gym`, `#morty`) are stable and are what Stuck? and Search link to.

## 4. Chapter template

A chapter is one JSON file in `content/walkthrough/{region}/`. Sections render only when present:

Where you are · **Current objective** (with progress ticks) · **Quick route** · Area map · Step-by-step (each step: prose, trainers, boss card, puzzle tip, items, spoiler block) · Wild Pokémon · Items · Optional · Missable · What unlocks · **Next destination**.

Quick / Full is a reading-mode switch stored per device: *Quick* keeps objective, quick route, map, unlocks and next destination and hides the rest.

## 5. Stack — and why

**Chosen: a dependency-free static generator in Python** (`tools/extract.py` → JSON → `tools/build.py` → `dist/`).

- The environment has **no Node.js** (no node / npm / bun); Python 3.9 + Pillow are present and are what the project's own tooling already uses.
- The hard part of this site is extraction (maps, trainers, encounters), which is Python either way. One language covers extract → build → screenshot.
- Output is plain HTML + one CSS file + one 13 KB script. Nothing to hydrate, nothing to upgrade, works from any static host or straight off disk via `python3 -m http.server`.
- Trade-off: no component ecosystem, templates are Python f-strings. Acceptable at ~10 page types.

**If Node is installed later, Astro is the recommended upgrade.** The JSON in `data/` and `content/` is already the contract; Astro content collections can read it unchanged and the CSS carries over as-is. I would only migrate if the template count or contributor count grows — not for its own sake.

## 6. Build pipeline

```
blonde/ (game source, read-only)
   │  tools/extract.py
   ▼
data/*.json + site/assets/game/{maps,pokemon,icons,trainers}     ← generated facts
content/**/*.json                                                 ← editorial prose + references to facts
   │  tools/build.py   (validates references, fails on any mismatch)
   ▼
dist/  static site  +  search-index.json  +  WALKTHROUGH-CHAPTER-MAP.md
```

The builder **refuses to build** when content points at something the game does not contain: an unknown trainer ID, a map marker with no matching warp/object at that tile, an item listed as a pickup that is not an item ball on that map, a chapter whose maps do not exist. (This caught a real mismatch during the prototype.)

## 7. Search

- Built at compile time into `assets/search-index.json` (32 KB, 160 entries now): questions, chapters, locations, trainers, items, Pokémon, features.
- Loaded **lazily** the first time the search box is focused. Opens with the header button, `/` or `⌘K`; also lives at `/search/?q=`.
- Matching is client-side: stop-words stripped from questions, whole-word > prefix > keyword > one-typo fuzzy match, results grouped by kind. Verified queries: "where do I get surf" → Stuck? answer + HM Surf; "misdrevus" (typo) → Misdreavus; "whitney" → the after-Whitney answer.
- At full size (est. 2–3k entries, ~400 KB raw / ~90 KB gzip) this approach still holds. Beyond that, split the index per kind.

## 8. Progress

- `localStorage` key `pb-guide:v1` → `{ done: {id:1}, chapters: {"johto/ecruteak-city":1}, last, theme, spoilers, mode }`. No account, nothing leaves the device.
- Checklist IDs are stable strings (`badge-fog`, `johto-league`). The same ID can appear on `/progress/`, on a chapter's objective card and on region badge rows; all stay in sync.
- Export downloads a JSON file; Import validates and merges; Clear asks first and keeps display preferences.
- "Continue" on the home page reads `last` (the most recent chapter opened).

## 9. Spoilers

Three levels, all defaulting to hidden: collapsible **spoiler blocks** inside chapters (the Burned Tower basement), **blurred lines** in lists (late chapter goals, late checklist entries — tap to reveal), and a **global switch** in the footer and on `/progress/`. Ordinary navigation, town names and Gym Leader names are never hidden.

## 10. Performance and accessibility (measured on the prototype)

- Ecruteak chapter: 61 KB HTML (12.5 KB gzip), CSS 35 KB (9 KB gzip), JS 13 KB (4.8 KB gzip), three fonts 100 KB total, city map 190 KB (lazy except in the viewer). No third-party requests.
- All content is in the HTML; JavaScript only adds search, maps zoom, tabs, progress and preferences.
- Semantic landmarks, skip link, one `h1` per page, labelled controls, visible focus ring, 44 px minimum targets, `prefers-reduced-motion` disables mist / flicker / transitions, day and night themes (system default + manual switch), print stylesheet.
- Tables collapse to label/value rows under 640 px; trainer teams are cards at every width; maps scroll and zoom inside their frame so the page never scrolls sideways.
- **Not yet done:** automated contrast audit, screen-reader pass with VoiceOver, keyboard pan for the map viewer (it is focusable and scrolls with arrow keys, but markers are reached by Tab only), Lighthouse run (no Node here).

## 11. What is real in the prototype

| Page | State |
|---|---|
| Home, Walkthrough landing, four region landings | Built |
| `/walkthrough/johto/ecruteak-city/` | Fully authored, art-directed |
| `/trainers/johto/morty/` | Built from data, incl. rematch team |
| `/pokemon/…` | 50 species pages generated (those met in the Ecruteak chapter and their families) |
| Stuck?, My Progress, Search | Working |
| Trainers / World / Items / Features / About | Index pages showing structure and what data is ready |

## 12. Recommended changes before full production

1. **Decide the Hoenn data route first** (see DATA-SOURCES.md §4). Hoenn is not in the source tree the way Johto and Kanto are; that extractor is the largest unknown in the schedule.
2. **Trace gates before writing prose.** For each chapter, list its flags/vars and what sets them (as done for Ecruteak) before any sentence is written. The chapter map marks which chapters are only structurally confirmed.
3. **Add prize money and a damage-relevant type chart** to the trainer extractor so boss cards can show payouts and weaknesses from data, not prose.
4. **Render every map once, then pick.** The renderer is general; a batch run over all 560 Johto/Kanto maps will show which need special handling (animated tiles, time-of-day palettes, multi-floor dungeons).
5. **Confirm naming with you:** "Tin Tower" (the game's own text) vs "Bell Tower"; "Rival" vs a default name; Badge display names.
6. **Choose hosting** when you are ready (nothing is deployed). The site works under a sub-path via `build.py --base`.

---

## Addendum (third structure pass) — superseded sections

The navigation, home, walkthrough-landing and progress sections above describe the first prototype. The current proposal is in **STRUCTURE-CONCEPTS.md** ("The Road") and changes:

- **Walkthrough** is one continuous road of 57 stops beside the game's Town Map, with crossings between regions — no region cards.
- **Home** is the reader's position (returning) or the way in to playing (new); it has one action.
- **Progress** is position (*Chapter N of 57*, the chapter last opened) plus Badges ticked. Nothing else is counted.
- **Play** is a first-class section: `/play/` (release, device chooser, saves) and `/play/setup/{iphone,android,mac,windows}/`. Release facts live in `content/releases.json`; device paths in `content/play.json`.
- New tools: `tools/worldmap.py` (Town Maps and place coordinates), `tools/plates.py` (graded town plates).
- Built for review only on: Home, Walkthrough, the Ecruteak chapter, Play and Setup. Other pages still use the earlier shell.
