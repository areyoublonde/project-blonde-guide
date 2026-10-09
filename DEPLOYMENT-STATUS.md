# Deployment status

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
