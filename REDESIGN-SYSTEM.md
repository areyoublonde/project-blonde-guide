# Redesign system

One shell, one stylesheet (`site/assets/app.css`), one script (`site/assets/app.js`) for every page.
Earlier systems are in `design-archive/` for reference only; nothing in the build uses them.

## Principles

1. **World first.** Colour and character come from the game: graded town plates, the Town Map, working area maps, sprites. The interface adds none of its own.
2. **Journey aware.** The guide knows one thing about you — where you are on the road — and every page uses it: Home, the header, Stuck?, Progress, the phone dock.
3. **Quiet interface.** Type, space and hairlines. A panel appears only when the content is an object (a map, a battle).
4. **Useful, not promotional.** Every page opens with the answer to the question that brought you there.
5. **Game references as details.** Menu icons in tables, Badge diamonds, tile coordinates, chapter numerals. Never the frame.

## Typography

| Role | Face | Use |
|---|---|---|
| Text and headings | Instrument Sans 400 / 500 / 600 | Everything you read |
| Factual layer | Geist Mono 400 | Labels, numerals, levels, chances, captions |

| Size | Where |
|---|---|
| 35–54 px, weight 500, −0.03em | Page title — always a place, a person or a question |
| 28 px | Section title |
| 20–24 px | Sub-headings, device names, next-destination |
| 16.5 px / 1.65 | Body, max 64 characters |
| 14–15 px | Secondary lines, navigation |
| 11 px mono, uppercase, +0.09em | Labels (`.label`) |

No serif, no pixel font, no weight above 600.

## Spacing

`4 · 8 · 12 · 16 · 24 · 40 · 72 · 120` (`--s1` … `--s8`). Sections are separated by 72; a page's first content sits 40 below the header; lists use 44–64 px rows. Gutter 24 (20 on phones); content width 1240.

## Colour

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0e0d0c` | Ground |
| `--surface` / `--surface-2` | `#161413` / `#1e1b19` | The two panels (map, battle); hover |
| `--ink` / `--ink-2` / `--ink-3` | `#ebe5da` / `#a69e93` / `#6e675f` | Text, secondary, labels |
| `--hair` / `--hair-2` | 10 % / 20 % cream | Dividers; section rules |
| `--accent` | `#c9764f` rust | *You are here*, the current step, active marker. A few dozen pixels per screen. |
| `--ok` / `--danger` | muted green / muted red | Ticked, missable |

Region dots (Johto rust, Kanto blue, Hoenn teal, Postgame sand) appear only as 6 px marks beside region names. Only the dark ground is designed.

## Surfaces

- **None by default.** Lists are rows with hairlines. Notes are margin notes with a 1 px rule in the note's tone.
- **Panel:** the working map and a battle. 8–10 px radius, 1 px hairline ring.
- **Floating:** search palette, phone dock and sheets, map zoom control. Blurred dark glass, 12–14 px radius.

## Actions

| Level | Look | Rule |
|---|---|---|
| Primary | Cream pill, dark text, 44 px | At most one per screen |
| Secondary | Hairline pill (`.btn.ghost`) | Utilities (export, clear) |
| Text link | Label with arrow (`.link`) | Everything else |
| Switch | Underlined text pair (`.seg`, `.tabs`) | Modes, day/night, device, region |

Focus is a 1.5 px cream outline, 4 px offset, on every interactive element.

## Map language

Three kinds of map, each with one job:

| Map | Source | Job | Where |
|---|---|---|---|
| **Plate** | `tools/plates.py` — a graded crop of a town | Atmosphere and location | Home, chapter head, Morty, location page, crossings |
| **Town Map** | `tools/worldmap.py` — the game's own map, dimmed | Geography and position | The Road, World, Pokémon locations, location page, Home fallback |
| **Working map** | `tools/extract.py` — full-brightness area map | Finding things | Chapter, location, Gym puzzle |

Town Map marks: hollow dot = a place; filled = behind you; rust ring with pulse = you; rust dot = highlighted. The game's own roads are the route lines; nothing is drawn over them.
Working map: numbered discs by layer (objective, item, service, optional, exit), layer switches, pan, zoom, full screen, text legend.

## Game-detail language

Menu icons (32 px) in Pokémon and encounter rows · front sprites (56–192 px) on entries and teams · Leader portraits · Badge diamonds (outline until ticked) · two-digit chapter and step numerals in mono · tile coordinates in captions · type as a coloured dot and a word.

## Motion

150 ms colour and underline transitions; 250 ms row nudges; Town Map cross-fade 600 ms; mist drift on plates; the position pulse. Nothing on scroll. All off under reduced-motion.

## Shared patterns

| Pattern | What it is | Used by |
|---|---|---|
| **You are here** | Label, place, chapter N of 57, objective, Continue, previous / next | Home, Road, Progress, header chip, phone dock, Stuck? default |
| **Road row** | Dot · number · title · tag, on a line that is solid behind you | Road, Stuck? stretch, chapter pager |
| **Ticks** | The road compressed to marks | Home, chapter journey bar, Progress |
| **Row list** | Hairline rows, filter on top, count beside | Pokémon, Items, World, Trainers, Features |
| **Key–value block** | Mono label, plain answer | Chapter facts, Morty, item, location, release |
| **Entry** | Crumb · label · title · one sentence · then the answer | Pokémon, Trainer, place, item, feature |
| **Numbered answers** | 01 / 02 / 03 with a mono numeral | Quick route, setup steps, feature guide, Play stages |
| **Dock** | One bottom bar on phones; its contents depend on the page | see MOBILE-UX.md |

Consistency comes from these and the type system, not from repeating one card.
