# Page-type architecture

Each page type exists to answer one question. The first screen answers it; everything else is depth.
Builders are one function each in `tools/build.py`; shared pieces are in `tools/site_core.py`.

## Navigation

```
Project Blonde   Walkthrough · World · Pokémon · Trainers · More ▾        ● Ecruteak City   Search /   Stuck?   Play
                                                         └ Items · Features · My progress · About
```

- Four primary destinations; four more under **More**. The header never grows past this.
- **● place** is your position; it appears once you have one and returns you to that chapter from anywhere.
- **Search**, **Stuck?** and **Play** are utilities on the right. Play is the only outlined item.
- Phones: wordmark, search icon, Menu. Everything else is in the Menu sheet and the dock (MOBILE-UX.md).

## The nineteen

| # | Page | URL | Question | First screen | Then |
|---|---|---|---|---|---|
| 1 | Home — new | `/` | How do I play this? | *Play Project Blonde*, one action, over New Bark Town | The road as one line · search · three quiet links |
| 2 | Home — returning | `/` | Where was I? | *You are here*: place, chapter N of 57, objective, Badges and next Badge, Continue, previous / next — over that place's plate (or the Town Map with your marker if no plate exists yet) | Same line and search |
| 3 | Walkthrough | `/walkthrough/` | What's the order, and where am I in it? | Town Map pinned left with your marker; *You are here* and the start of the road right | 57 stops, Badge counts per region, crossings |
| 4 | Chapter | `/walkthrough/{region}/{slug}/` | Where am I, what do I do, where next? | Journey bar; left: place, objective with ticks, four facts; right: the quick route ending in *Then → next place* | Area map · full walkthrough with pinned contents · reference (wild, items, optional) · unlocks · next destination and pager |
| 5 | Pokémon index | `/pokemon/` | Where do I find X? | Filter field, region switch, rows: icon · name · type · best places | 325 rows; the row itself answers the question |
| 6 | Pokémon entry | `/pokemon/{slug}/` | Where exactly, and what does it become? | Sprite, name, type, Pokédex line; *Best chance* line | Location table beside the Town Map with its places lit · family · base stats · where it turns up on the road |
| 7 | Trainers index | `/trainers/` | Who's next, and how strong? | Leaders in road order with portrait, town, Badge, team size and levels, chapter | Other major battles |
| 8 | Trainer entry | `/trainers/{region}/{slug}/` | Who, where, when, what do I face, what do I get? | Portrait over his city; Where / When / Format / Specialty / Reward / Then | Team and what to know · Gym trainers and the missable note · the Gym puzzle link · rematch (spoiler) · previous / next Leader |
| 9 | World | `/world/` | What is here? | Town Map pinned left with every place; filterable list right, by kind | Hover links list and map both ways; Hoenn sheet |
| 10 | Location | `/world/{region}/{slug}/` | What's in this place? | Plate; name; Gym, services, exits by direction; Town Map position | Chapters that visit it · working map · buildings · items · wild Pokémon · Trainers |
| 11 | Items index | `/items/` | Where do I get it? | Filter, pocket switch, rows: item · pocket · places · count | Open a row for its description and every pick-up |
| 12 | Item entry | `/items/{slug}/` | Where, how, do I need it, can I miss it? | Six answers: What it is / Where / How / Needs / Missable / Region | Using it · what it opens |
| 13 | Features hub | `/features/` | What's different in this game? | One row per system with its status | — |
| 14 | Feature guide | `/features/{slug}/` | How do I use it? | What it is in one sentence | 01 How · 02 When it unlocks · 03 Limits |
| 15 | Stuck? | `/stuck/` | I don't know what to do. | A question field; beside it *What was your last Badge?* pre-set from your position | The stretch of road you are on · answers for that stretch first |
| 16 | Progress | `/progress/` | What have I done, what's left? | *You are here*, set-position control | Per region: ticks, eight Badges, milestones · export / import / clear |
| 17 | Play | `/play/` | How do I get this running? | Three stages: 01 device · 02 get the game · 03 start | In-game save vs save state · backup, updating, Link Play, troubleshooting · changelog |
| 18 | Device setup | `/play/setup/{device}/` | What do I do on *my* device? | Device switch; pinned quick start and step list | Four words you'll see · numbered steps · first-launch problems · start the journey |
| 19 | Search | everywhere (`/`, ⌘K) and `/search/` | Take me to X. | Palette; empty state offers Continue, Walkthrough, Stuck?, Play | Grouped results, best group first, keyboard driven |

Also built: `/about/` — *What is Project Blonde?*

## What each page is made from

| Page | Data (generated) | Editorial |
|---|---|---|
| Road, Home, Progress, Stuck? stretch | `content/chapters.json` + Town Map coordinates | chapter titles and goals |
| Chapter | trainers, encounters, maps, markers validated against map events | prose, quick route, strategy |
| Pokémon index / entry | encounter tables, species data, sprites, place coordinates | none |
| Trainers | trainer parties, portraits | Morty's intro line |
| World / location | map sections, areas, connections, items, encounter tables | place intro line |
| Items | item balls and hidden items from 560 maps, item descriptions | gifts come from written chapters; HM Surf answers |
| Features | — | one guide |
| Play | `content/releases.json`, `content/play.json` | Mac path |

The build still stops if editorial content refers to something the game data does not contain.

## What was replaced, and what survived

**Replaced outright:** the old shell and both older stylesheets; Home (hero + buttons + cards); walkthrough landing (region cards); chapter page (article with rails); Pokémon index (card grid) and entry; Morty; World, Items and Features placeholder pages; Stuck? (FAQ accordion); Progress (four checklist cards); the tab bar; the hamburger drawer.

**Survived, restyled, because they earn their place:**

| Component | Why it stays |
|---|---|
| Working map viewer | The single most useful object on a chapter; now also on the location page |
| Battle block | A boss needs its team, format and advice together; one of only two panels |
| Trainer rows, encounter rows, item rows | Already rows, not cards |
| Margin notes (item, missable, optional, tip, unlocked) | Compact and scannable beside prose |
| Spoiler block and blurred lines | Needed; unchanged in behaviour |
| Quick / Full reading mode | Core to using it mid-game |
| Search palette | Kept and made the one global entry point |
| Build-time validation | Keeps facts honest |

## Now complete (2026-10-08, game v104)

Every page type is generated for the whole game: 58 chapters, 1,067 Pokémon entries, 85 Trainer pages, 199 places with 908 area maps, 442 item pages, 15 feature guides, four device paths, plus a twentieth page type, **Mega Stones** (`/items/mega-stones/`: three steps, a searchable list, differences from the official games and a completeness check). Stuck? gained a place chooser that gives the next step. See `CONTENT-COVERAGE.md` for counts and known gaps.

Changed from the prototype: the chapter page uses one compact content schema for all chapters (objective, what you need, quick route, steps, battles, sticking points) with wild Pokémon, items, Trainers and places filled in from data; navigation gained Mega Stones under More; the day theme was not built (dark only, by decision).
