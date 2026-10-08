# Mobile UX

Designed for one situation: the game is running, the phone is in one hand, and you have half a minute.

## Structure

- **Top bar (56 px):** wordmark · search · Menu. Nothing else.
- **Menu:** a full-screen sheet with every destination in large type. Opens and closes from the same corner.
- **The dock:** one floating bar at the bottom, in thumb reach. It is the only persistent control, and what it holds depends on the page.

## The dock

| Page | Dock | Why |
|---|---|---|
| The Road | **Continue · place** │ **Jump** | The two things you do there: resume, or move along the road. Jump opens a sheet: Where I am, Johto, Kanto, Hoenn, Postgame. |
| Chapter | **Journey** │ **Route** │ **Map** │ **Contents** | Journey opens previous / next / see it on the road. Route and Map jump to those sections. Contents opens the section list. |
| Device setup | **‹** Step N of 6 · title **›** | A stepper: one thumb moves through the steps while the other hand is on the computer. |
| Any reference page, once you have a position | **Continue · place** | One tap back to where you were reading. |
| Home, Play, Progress | none | The page itself is the action. |

Sheets rise from the dock, close when you choose something or tap elsewhere, and never cover the top bar.

## Per page

| Page | What changes from desktop |
|---|---|
| Home | Plate fills the top half and fades down; the position block (or Play) sits directly beneath; the road line below. |
| The Road | Town Map is a pinned band under the top bar and stays there while the road scrolls beneath it; your marker and the highlighted leg update as you go. Badge names drop off the rows; the diamonds remain. |
| Chapter | Order is: place → objective and its ticks → facts → quick route → *Then* → map → walkthrough. No side column; Contents lives in the dock. |
| Working map | Starts zoomed to a readable scale centred on the objectives rather than shrunk to fit. Layer switches scroll sideways inside the frame. Expand makes it the whole screen. |
| Pokémon index | Two-line rows: name and type, then places. Filter field takes the full width. |
| Pokémon / Trainer / item entry | Single column; tables become label-and-value pairs; six stats in two rows. |
| World | Map on top, list beneath; the Hoenn switch sits beside the filter. |
| Stuck? | Question field first, then the Badge picker, then answers. |
| Progress | Position and the set-position control first; Badges as large rows with a diamond to tap. |
| Play | The three stages stack; device names are 56 px-tall rows. |
| Search | Full screen, keyboard up, results as large rows. |

## Rules

- Tap targets are at least 44 px; list rows 44–64 px.
- Nothing scrolls sideways except content inside its own frame (maps, the device switch, map layers). Checked at 390 px on 18 pages.
- Body text 16.5 px. Labels never below 11 px.
- The dock leaves 84 px of clear space at the end of every page that has one.
- No hover-only information: the Home road line names a chapter on focus as well as hover, and its marks are links.

## Considered and left out

- A global five-item tab bar: it competed with the page docks and repeated the Menu.
- Swipe between chapters: conflicts with panning the map and with browser back-swipe; previous / next are in the Journey sheet and at the foot of the chapter.
- A sticky objective strip: the dock's Journey and Contents sheets reach the objective in one tap without spending permanent height.
