# Deployment status

**v1.3 website update, 2026-10-17 (owner approved publication and the website update in the release instruction).** Branch `release-v1.3` on `origin/main` `8bcaf46`
(with the v1.2 hotfix evidence commit). The game is public: v1.3 (build v116, game `e851f80d…87c3`, ZIP `5376be94…9405`) was published on Discord on 2026-10-17
(`https://discord.com/channels/1557763721051512932/1557776605844217866/1560852324795023480`); the v1.2 post stays up (owner: preserve v1.2), so `releases.json` gives v1.2
`discord_post` instead of `post_removed`. What changes: `releases.json` `current: "1.3"`; `/play/v1.3/` What's new with six real v1.3 screenshots (`tools/whatsnew_story.py`);
nine Silph Conspiracy chapters in the postgame (`postgame/silph-call` … `postgame/silph-league`) and an updated After the Credits; a Partner Battles feature page;
`romx.py` BUILD = v116 (group 18 moved past gMapGroups by the story layer is handled; the restored Silph floors have no symbol and are not map pages); two re-rendered,
re-audited maps (Seafoam Gym back entrance, Blaine's cave lab); a second in-browser patcher registry `content/patcher-v1.3.json` offered under the Discord download
(Emerald, v1.0, v1.1 and both v1.2 builds → v1.3; patches in `site/assets/patches/v1.3/`, `PATCHER-MATRIX-v1.3.md`); the v1.0 patcher stays on `/play/v1.0/`.
Local results: build 1,333 pages (69 chapters); `qa_static` 83,254 links / 39,342 assets, 0 failures; `qa_play` 256 of 256; `PB_PATCHER=v1.3 qa_patcher` 63 of 63;
`qa_maps` 0 problems (audit of v116); `qa_pokemon_data` 482 (440 + 42), 0 problems; `qa_story` 8 covered, 0 failures; `qa_field_encounters` pass; `qa_availability` 30 of 31 (the
game-folder check is skipped in a worktree). Not tested: a physical iPhone, Safari, Firefox, an Android device.

**v1.2 hotfix record, 2026-10-11.** The v1.2 download on Discord now carries the hotfix build (internal v115, game `b15f98da…22eb`, ZIP `c93d2d31…e7fd`): Ability Capsules and Ability Patches can no longer be sold. The ZIP was replaced on the same pinned post, so the download link did not change; the first v1.2 build (v113) is archived with the release records. This update changes the release record (`content/releases.json`: build, both checksums, ZIP size, one changelog line, two notes), the build record (`tools/romx.py`, `data/rom/manifest.json`, `data/availability.json`) and the gallery provenance (`tools/whatsnew_towns.py`, `data/whatsnew-v1.2.json`: screenshots taken on v113, whose maps and graphics are byte-identical in v115). No page design, guide, Pokédex, map or patcher change; the patcher stays v1.0 only. Local: build 1,315 pages, links 82,690 and assets 39,495 with 0 failures, `qa_play.py` 232 of 232.

**Latest deploy 2026-10-11 (v1.2 website update):** commit `848aa60` on `main`, workflow run 38111891002, success (build 1,315 pages and every CI check). Verified
live: `tools/qa_play.py https://areyoublonde.github.io/project-blonde-guide` 232 of 232, `tools/qa_patcher.py <live>` 49 of 49 on `/play/v1.0/`, a gallery screenshot
byte-identical to the committed file, and the only release-post link on `/play/` is the v1.2 post. Evidence: `qa-evidence/download-play/live.json`,
`qa-evidence/patcher/live.json`. This note and the live evidence are committed locally only (owner rule: no deployment solely for documentation); push them with
the next website update.

**v1.2 website update: PREPARED 2026-10-11, owner approved deployment once every check passes.** Branch `release-v1.2` on `origin/main` `c249cc0` (it also carries
the v1.1 deployment record). The game itself is already public: v1.2 (build v113) was published on Discord on 2026-10-11, and nothing in that release was touched here.
Local results: build 1,315 pages (also with `--base /project-blonde-guide`); links 82,690 and assets 39,495, 0 failures; `qa_play.py` 232 of 232; `qa_patcher.py`
49 of 49 (v1.0 patcher on `/play/v1.0/`); `qa_browser.py` 107 of 107, sweep failures 0; `qa_pokedex.py` 136 of 136; `qa_legendaries.py` 144 of 144; `qa_availability.py` 31 of 31; `qa_maps.py` 0 problems;
`qa_pokemon_data.py` 0 problems. Not tested: a physical iPhone, Safari, Firefox; the Discord post itself opens only for a signed-in member, so the link was checked
for form and against the release record, not by downloading through it.

**Latest deploy 2026-10-10 (v1.1 website update):** commit `c249cc0` on `main` (with `6b7cb55`), workflow run 38064635571, success (build 1,314 pages and every CI check). Verified live: `tools/qa_play.py https://areyoublonde.github.io/project-blonde-guide` 191 of 192 (the one failure, desktop "What's new: reached from Current release", was the test reading the heading before the slower live page had loaded; repeated by hand on desktop and phone, the link opens `/play/v1.1/` with the right heading), `tools/qa_patcher.py <live>` 49 of 49 on `/play/v1.0/`, both gallery atlases byte-identical to the committed files, both release-post links equal the release record. Evidence: `qa-evidence/download-play/live.json`, `qa-evidence/patcher/live.json`. This note and the live evidence are committed locally only (owner rule: no deployment solely for documentation); push them with the next website update.

**v1.1 website update: PREPARED, NOT DEPLOYED (2026-10-10).** Branch `release-v1.1` (two commits on `origin/main` `c7ca264`), built and tested locally; it waits for the owner's approval. The game itself is already public: v1.1 (build v111) was published on Discord on 2026-10-10, and nothing in that release was touched here. To deploy after approval: `git push origin release-v1.1:main`, watch the `Deploy guide to GitHub Pages` run, then `python3 tools/qa_play.py https://areyoublonde.github.io/project-blonde-guide`. Local results: build 1,314 pages (also with `--base /project-blonde-guide`); links 82,619 and assets 39,461, 0 failures; `qa_play.py` 192 of 192; `qa_patcher.py` 49 of 49 (v1.0 patcher on `/play/v1.0/`); `qa_browser.py` 107 of 107, sweep failures 0; `qa_pokedex.py` 136 of 136; `qa_legendaries.py` 144 of 144; `qa_availability.py` 31 of 31; `qa_maps.py` 0 problems against the v111 audit. Not tested: a physical iPhone, Safari, Firefox; the Discord post itself opens only for a signed-in member, so the link was checked for form and against the release record, not by downloading through it.

**Latest deploy 2026-10-09 (Legendary & Mythical field guide):** commit `e584044`, workflow run 37864751654 (build 1,305 pages; links 0 failures). Verified live in Chrome: `tools/qa_legendaries.py https://areyoublonde.github.io/project-blonde-guide` 144 of 144 on desktop and phone (coverage, classifications, search, filters, spoilers, links, map, layout, no script errors). Evidence: `qa-evidence/legendary-guide/live.json`. Audit: `LEGENDARY-MYTHICAL-COMPLETENESS-AUDIT.md`.

**Earlier deploy 2026-10-09 (Porygon2 / Porygon-Z correction):** commit `55dd5d4`, workflow run 37862342026 (build 1,305 pages; availability regressions 31 of 31; links 0 failures). Verified live in Chrome: `tools/qa_pokedex.py` 136 of 136, Pokédex index 482 rows, `/pokemon/porygon2/` and `/pokemon/porygon-z/` open with their evolution methods, `/items/upgrade/` lists the Silph Co gift and the Mahogany Town shop.

**Earlier deploy 2026-10-09:** commit `b1a5a88a38f8c081a0db42be19ef71dca714177a` (Pokédex availability correction and list-filter fix), workflow run 37819378668, verified live with `tools/qa_pokedex.py` (136 of 136).

**LIVE since 2026-10-09:** https://areyoublonde.github.io/project-blonde-guide/ — repository https://github.com/areyoublonde/project-blonde-guide, branch `main`, commit `4305a20ea29869118717e0b00fe355fac5d77056`, deployed by the `Deploy guide to GitHub Pages` workflow (run 37811686043, success). Live verification: all 1,883 routes return 200; 26 of 26 smoke checks (`data/qa-live.json`). To update the site: commit and push to `main`; the workflow rebuilds and redeploys. This note and `data/qa-live.json` were written after the deploy and are not yet pushed.

---

_Pre-deployment record:_

**Not deployed — ready, waiting for the owner's final approval (2026-10-09).** Repository `https://github.com/areyoublonde/project-blonde-guide` exists (public, empty, Pages not yet enabled); GitHub CLI is signed in as `areyoublonde` with `repo` and `workflow` scopes. Expected site: `https://areyoublonde.github.io/project-blonde-guide/`. Pre-publication audit of the 3,727 files to be committed (23 MB): no ROM, save, patch, archive, credential, token, local path or personal address; sub-path test 35 of 35 (`data/qa-subpath.json`).

**Earlier state, kept for the record:** Not deployed. The site is built and tested locally and is ready to publish. Publication is waiting on the owner (below). Nothing has been pushed anywhere.

## What exists

| | |
|---|---|
| Local repository | `blonde-guide/` — `git init` done on branch `main`, **no commit yet** (no git identity is configured on this machine) |
| Game baseline shown | v1.0 release candidate (build v105, `d76ce7db…513a`), not yet owner-verified |
| Remote | none |
| Build output | `dist/`, 1,883 pages, about 78 MB (maps, sprites and Town Maps are most of it) |
| Hosting target | GitHub Pages, deployed by GitHub Actions |
| Workflow | `.github/workflows/pages.yml` — checkout → `tools/build.py --base <pages base path>` → `tools/qa_static.py` → upload → deploy. It needs no game files: `data/` and `site/assets/game/` are committed |
| Sub-path | Verified locally: built with `--base /project-blonde-guide`, 97,060 links and 35,983 assets resolve under the prefix. A user site or custom domain uses an empty base; the workflow reads the right value from GitHub |
| Excluded from the repo | `dist/`, `screenshots/`, `design-archive/`, and by pattern any `.gba`, `.sav`, `.srm`, save state, `.zip`, `.bps`, `.ips` (`.gitignore`) |

## Checked on this machine (2026-10-08)

- `gh` CLI: not installed.
- SSH to github.com: no keys (`~/.ssh` is empty; host key not trusted).
- `git config user.name` / `user.email`: not set.
- So there are **no GitHub credentials here**. I did not create an account, a token or a repository, and did not guess a URL.

## Target

Repository **`project-blonde-guide`** (owner instruction, 2026-10-09). As a project site its address will be `https://<account>.github.io/project-blonde-guide/`; `<account>` is whichever GitHub account creates it. The sub-path build was smoke-tested locally at exactly `/project-blonde-guide/` (`data/qa-subpath.json`, 14 of 14).

**Nothing is published until the owner approves the final repository and URL.**

## Steps

Owner, in Terminal (each is interactive and stays on this Mac):

1. Install the GitHub CLI: `brew install gh` (Homebrew is already at `/opt/homebrew/bin/brew`).
2. Sign in: `gh auth login` → **GitHub.com** → **HTTPS** → *Authenticate Git with your GitHub credentials?* **Yes** → **Login with a web browser**. The terminal shows a one-time code; the browser asks for it and for your normal sign-in (and two-factor code). No password or token is typed into the terminal or given to me.
3. Check: `gh auth status` should print the account name. That account name is the first half of the public URL.
4. Tell me the account name, the commit name and email to use (a GitHub no-reply address `ID+username@users.noreply.github.com` keeps your address out of the public history; it is shown under GitHub → Settings → Emails), and confirm publication.

Then I run, from `blonde-guide/`, only after that confirmation:

```sh
git config user.name "<name>" && git config user.email "<no-reply address>"
git add -A && git commit -m "Project Blonde Guide"
gh repo create project-blonde-guide --public --source . --remote origin --push
gh api -X POST repos/{owner}/project-blonde-guide/pages -f build_type=workflow     # Pages source = GitHub Actions
gh run watch                                                                       # the build-and-deploy workflow
```

and verify the live site: the workflow's own link check, then the same smoke test as `data/qa-subpath.json` against the public URL.

To take the site down again: `gh repo edit --visibility private` (Pages stops serving on a free plan) or delete the repository.

## Content the owner should look at before it is public

- **No game download.** `content/releases.json` has `download.url: null` and distribution `undecided`; Download & Play shows a pre-release state with no download control (see below). Nothing in the repository or the build is a ROM, patch or save.
- **Version wording.** The site says "v1.0 release candidate (build v105)" and, on Play, "not yet owner-verified and not a public release". It never presents the game as released.
- **Credits.** The About page prints the project and source credits from the game's credits roll. The personal dedication and family acknowledgement sections are excluded at extraction (`PRIVATE` in `tools/credits.py`), so they are in neither `data/credits.json` nor the built site. The game keeps its full roll.
- **Game assets.** The site shows maps, sprites, Town Maps and trainer pictures rendered from the game. That is normal for a fan guide but is still Nintendo / GAME FREAK artwork; the footer and About page state the non-affiliation. The owner's call.
- **The two lab aides.** The guide documents the Mega Stone aide in full (approved feature). The other aide's free Ability Patch offer appears only as a data-derived source on the Ability Patch item page.

## Distribution of the game (separate decision)

Not approved, so nothing is offered. If the owner chooses a patch release: a patch must be made against a specific clean base ROM that the owner names and holds legitimately, and verified by applying it and matching the v105 hash. No base ROM was available or assumed here, so **no patch was created**. When a release artifact and destination exist, set `distribution.method`, `releases[0].download.url`, `sha256`, `date` and `file.name` in `content/releases.json` and rebuild; the Play page switches from the disabled state by itself.

## Download & Play and Discord (2026-10-09)

- **Discord.** The invite is written once, in `content/site.json` → `community.discord.url` (`https://discord.gg/vNRqevNHGd`, supplied by the owner; Discord's public invite API reports server POKÉMON: PROJECT BLONDE, no expiry). `discord_link()` in `tools/site_core.py` builds every link from it: header icon (desktop), menu (phone), footer, Download & Play (primary action while pre-release, Get the game, troubleshooting), each device setup page and Stuck?. Set the URL to `null` and all of them disappear.
- **Release record.** `content/releases.json` is the only place release facts are written. `release_state()` in `tools/build.py` refuses to build if a download URL is present while `status` is not `released`, or if a released version lacks date, URL, SHA-256, distribution method or (for a patch) any patch field.
- **To publish a release (owner approval required):** set `status` to `released`, `status_short`, `date`, `sha256`, `download.url`, `distribution.method` (`direct` or `patch`) and, for a patch, every field under `patch`; rebuild. The page then shows one primary download and, for a patch, the patching steps.
- **Current state:** v1.0 release candidate, build v105, not released, no download, distribution undecided.
- **Test:** `tools/qa_play.py [base-url]` → `qa-evidence/download-play/`.

## 2026-10-09 — Map rendering and Pokémon type fixes

- Commit `3b36fc6` on `main` (branch `fix/map-rendering-pokemon-ui`, merged over `68426d5`: Download & Play, permanent Discord invite, favicon). Fast-forward push, Pages run 37931625494 succeeded.
- Live checks, in a real browser: `qa_mapview.py` 159 of 159 (Faraway Island Interior anchor, image, zoom, pan, fit, markers, full screen; nine other maps; Probopass ROCK / STEEL; trainer teams), `qa_play.py` 134 of 134, `qa_pokedex.py` 136 of 136. The live `faraway-island-interior.png` has the audited hash `5c8284dd7f001f81`. Evidence: `qa-evidence/map-rendering/live*`.
- Reports: `MAP-RENDERING-AUDIT.md`, `MAP-RENDERING-DEFECTS.md`, `MAP-RENDERING-REGRESSION.md`, `POKEMON-DATA-UI-AUDIT.md`.

## v1.0 launch (2026-10-09)

Published on the owner's instruction: the in-browser patcher on Download & Play, the release record set to released, the enabled registry and three patches under `site/assets/patches/v1.0/`. No complete game file is in the repository or the site.

**Verified before publishing:** v105 ROM = manifest SHA-256 `d76ce7db…513a`, title label v1.0 (`version_label.py verify`); `tools/patches.py verify` (every patch reproduces v105 exactly and refuses every other input); `qa_patcher.py` 49 / 49; `qa_play.py` 130 / 130; `qa_browser.py` 107 / 107, sweep 0 failures; `qa_static.py` 0 failures; `qa_availability.py`, `qa_story.py` pass. Not tested: a physical iPhone, iOS Safari, Delta.

**Supported inputs:** Pokémon Emerald (USA, Europe); pre-release builds v103 and v104. v100 to v102 are recognised and refused: no direct save test into v105 exists.

**Live checks after a publish:** `tools/qa_patcher.py https://areyoublonde.github.io/project-blonde-guide` (needs `private/roms.json`), `tools/qa_play.py <same>`.

To withdraw: set `enabled` to false in `content/patcher.json`, `status` back to `candidate` and `distribution.method` to `undecided`, delete `site/assets/patches/`, push.
