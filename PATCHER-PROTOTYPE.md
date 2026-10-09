# In-browser patcher ("Make your game"): private prototype

Status: **prototype, not deployed, not enabled.** Project Blonde v1.0 (build v105) is a release candidate. `content/patcher.json` has `enabled: false`; a normal build contains no patcher, no registry and no patch file.

## What it does

One control, "Choose your game file". The page hashes the file (SHA-256) on the device, looks it up in the registry, and then:

- clean base game -> makes the latest Project Blonde;
- supported earlier Project Blonde build -> updates it (save-backup reminder and tick box first);
- the current release -> says so and does nothing;
- a recognised but unsupported build, or anything unknown -> explains and offers nothing.

The patch is downloaded, its checksum checked, applied in the browser, and the result must equal the target SHA-256 before it can be saved. The chosen file is only read. Nothing is uploaded.

## Files

- `content/patcher.json`: the registry (target, inputs, hashes, patch mapping, save status). Written by `tools/patches.py build`.
- `tools/patches.py`: `build` makes one direct patch per input into `private/patches/<version>/`; `verify` re-checks everything and writes `PATCHER-MATRIX.md`.
- `private/roms.json`, `private/patches/`: local only, git-ignored.
- `site/assets/patcher.js`, `patcher_html()` in `tools/build.py`: the page.
- `tools/qa_patcher.py`: browser test with the real ROM files -> `qa-evidence/patcher/`.

## Test it locally

```sh
python3 tools/patches.py verify
python3 tools/build.py --prototype          # LOCAL ONLY: never deploy this build
python3 -m http.server 8951 -d dist &
python3 tools/qa_patcher.py
```

On an iPhone on the same Wi-Fi: `python3 -m http.server 8951 -d dist --bind 0.0.0.0`, then open `http://<this Mac's address>:8951/play/#get` in Safari. Over plain http Safari has no Web Share, so only **Save to Files** appears; **Open in Delta** needs an https address.

## Adding a release

1. Add the new ROM to `private/roms.json`; set `target` in `content/patcher.json`; move the previous target into `inputs` as a `release` with its save status.
2. Decide, per earlier build, `supported` or `recognised`. Nothing is supported by default.
3. `python3 tools/patches.py build && python3 tools/patches.py verify`, then the browser test.
4. Only with the owner's approval: `enabled: true`, `distribution.method: "patcher"` and the release fields in `content/releases.json`. The build refuses an enabled registry for an unreleased version.
