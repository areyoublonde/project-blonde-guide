#!/usr/bin/env python3
"""Patch generator and verifier for the in-browser patcher. Registry: content/patcher.json.

    python3 tools/patches.py build      make one direct patch per registry input -> private/patches/<release>/, write hashes into the registry
    python3 tools/patches.py verify     re-check every registry hash, re-apply every patch with the independent decoder -> PATCHER-MATRIX.md ; exit 1 on any mismatch

Reads the ROM files named in private/roms.json (never writes to them). Patches are BPS: one per supported or recognised input,
always straight to the target. Nothing in private/ is committed or deployed; `tools/build.py --prototype` copies the patches into dist/
for a local test only.
"""
import gzip, hashlib, json, struct, sys, time, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG_PATH, ROMS_PATH = ROOT / "content/patcher.json", ROOT / "private/roms.json"
sha256 = lambda b: hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------- BPS encoder
def encode(src, tgt, index_step=0):
    """BPS patch turning src into tgt. index_step 0 = same-offset matching only (near-identical files);
    otherwise source blocks every index_step bytes are indexed so moved data is copied rather than stored."""
    K, idx = 16, {}
    if index_step:
        for p in range(((len(src) - K) // index_step) * index_step, -1, -index_step):
            idx[src[p:p + K]] = p
    out = bytearray(b"BPS1")

    def enc(n):
        while True:
            x = n & 0x7f; n >>= 7
            if n == 0:
                out.append(0x80 | x); return
            out.append(x); n -= 1

    def mlen(a, i, b, j):
        n, m = 0, min(len(a) - i, len(b) - j)
        while n < m:
            c = min(4096, m - n)
            if a[i + n:i + n + c] == b[j + n:j + n + c]:
                n += c; continue
            lo, hi = 0, c
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if a[i + n:i + n + mid] == b[j + n:j + n + mid]: lo = mid
                else: hi = mid - 1
            return n + lo
        return n

    rel = lambda d: enc((abs(d) << 1) | (d < 0))
    enc(len(src)); enc(len(tgt)); enc(0)
    srel = trel = t = 0
    lit, N = None, len(tgt)

    def flush(upto):
        nonlocal lit
        if lit is not None:
            enc((upto - lit - 1) << 2 | 1); out.extend(tgt[lit:upto]); lit = None

    while t < N:
        key = tgt[t:t + K]
        if t < len(src) and src[t:t + 4] == key[:4]:                       # same place in the source
            n = mlen(src, t, tgt, t); flush(t); enc((n - 1) << 2 | 0); t += n; continue
        if len(key) == K and key == key[:1] * K and t > 0 and tgt[t - 1] == key[0]:      # a run: overlapping target copy
            n = mlen(tgt, t - 1, tgt, t); flush(t); enc((n - 1) << 2 | 3); rel((t - 1) - trel); trel = t - 1 + n; t += n; continue
        s = idx.get(key) if index_step else None
        if s is not None:                                                     # moved data
            n, b = mlen(src, s, tgt, t), 0
            while lit is not None and t - b > lit and s - b > 0 and src[s - b - 1] == tgt[t - b - 1]: b += 1
            s -= b; t -= b; n += b
            if lit == t: lit = None
            flush(t); enc((n - 1) << 2 | 2); rel(s - srel); srel = s + n; t += n; continue
        if lit is None: lit = t
        t += 1
    flush(N)
    out += struct.pack("<II", zlib.crc32(src), zlib.crc32(tgt)); out += struct.pack("<I", zlib.crc32(bytes(out)))
    return bytes(out)


# ----------------------------------------------------------------------------- BPS decoder (independent of the encoder: written from the format)
def apply(src, p):
    assert p[:4] == b"BPS1" and zlib.crc32(p[:-4]) == struct.unpack("<I", p[-4:])[0], "patch is damaged"
    i = 4

    def dec():
        nonlocal i
        d, sh = 0, 1
        while True:
            x = p[i]; i += 1; d += (x & 0x7f) * sh
            if x & 0x80: return d
            sh <<= 7; d += sh

    ss, ts, ms = dec(), dec(), dec(); i += ms
    assert ss == len(src) and zlib.crc32(src) == struct.unpack("<I", p[-12:-8])[0], "patch does not belong to this file"
    o, sr, tr = bytearray(), 0, 0
    while i < len(p) - 12:
        v = dec(); typ, n = v & 3, (v >> 2) + 1
        if typ == 0: o += src[len(o):len(o) + n]
        elif typ == 1: o += p[i:i + n]; i += n
        else:
            v = dec(); d = (-1 if v & 1 else 1) * (v >> 1)
            if typ == 2:
                sr += d; o += src[sr:sr + n]; sr += n
            else:
                tr += d
                if tr + n <= len(o): o += o[tr:tr + n]; tr += n
                else:
                    for _ in range(n): o.append(o[tr]); tr += 1
    assert len(o) == ts and zlib.crc32(bytes(o)) == struct.unpack("<I", p[-8:-4])[0], "patched result is wrong"
    return bytes(o)


# ----------------------------------------------------------------------------- registry
def load():
    reg, roms = json.loads(REG_PATH.read_text(encoding="utf-8")), json.loads(ROMS_PATH.read_text(encoding="utf-8"))["roms"]
    return reg, {k: Path(v) for k, v in roms.items()}


def pdir(reg):
    return ROOT / "private/patches" / reg["target"]["public_version"]


def build():
    reg, roms = load()
    tgt = roms[reg["target"]["rom"]].read_bytes()
    reg["target"].update(sha256=sha256(tgt), size=len(tgt), crc32=zlib.crc32(tgt))
    out = pdir(reg); out.mkdir(parents=True, exist_ok=True)
    seen = {reg["target"]["sha256"]}
    for x in reg["inputs"]:
        src = roms[x["rom"]].read_bytes(); t0 = time.time()
        h = sha256(src); assert h not in seen, f'{x["id"]}: same file as another registry entry'; seen.add(h)
        p = encode(src, tgt)                                 # near-identical builds need nothing more
        if len(p) > 2_000_000: p = encode(src, tgt, 4)       # a different game underneath: index it
        assert sha256(apply(src, p)) == reg["target"]["sha256"], f'{x["id"]}: patch does not reproduce the target'
        name = f'{x["id"]}-to-{reg["target"]["internal_build"]}.bps'
        (out / name).write_bytes(p)
        with open(out / (name + ".gz"), "wb") as f:
            with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9, mtime=0, filename="") as g: g.write(p)
        x.update(sha256=h, size=len(src), patch={"file": name, "sha256": sha256(p), "size": len(p), "size_gz": (out / (name + ".gz")).stat().st_size})
        print(f'{x["id"]:12} -> {reg["target"]["internal_build"]}  patch {len(p):>10,} bytes  ({round(time.time() - t0, 1)} s)  reproduces target: yes')
    REG_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def verify():
    reg, roms = load(); bad, rows = [], []
    T = reg["target"]; tgt = roms[T["rom"]].read_bytes()
    if (sha256(tgt), len(tgt), zlib.crc32(tgt)) != (T["sha256"], T["size"], T["crc32"]): bad.append("target ROM does not match the registry")
    for x in reg["inputs"]:
        src = roms[x["rom"]].read_bytes(); p = (pdir(reg) / x["patch"]["file"]).read_bytes()
        gz = gzip.decompress((pdir(reg) / (x["patch"]["file"] + ".gz")).read_bytes())
        checks = {"input hash": sha256(src) == x["sha256"] and len(src) == x["size"], "patch hash": sha256(p) == x["patch"]["sha256"] and gz == p}
        try: checks["reproduces target"] = sha256(apply(src, p)) == T["sha256"]
        except AssertionError as e: checks["reproduces target"] = False
        others = [y for y in reg["inputs"] if y is not x]
        wrong = 0
        for y in others:                                       # this patch must refuse every other known file
            try: apply(roms[y["rom"]].read_bytes(), p); wrong += 1
            except AssertionError: pass
        checks["refuses other inputs"] = wrong == 0
        bad += [f'{x["id"]}: {k}' for k, v in checks.items() if not v]
        rows.append((x, checks))
    md = ["# Patcher: supported-version matrix", "", f'Generated by `tools/patches.py verify` from the real ROM files. Target: **Project Blonde {T["public_version"]}** (build {T["internal_build"]}), {T["size"]:,} bytes, SHA-256 `{T["sha256"]}`.',
          "", f'Registry `enabled`: **{str(reg["enabled"]).lower()}** (no patcher and no patch file in the public build while false).', "",
          "| Input | Recognised as | Offered to players | Input SHA-256 | Patch | Size (compressed) | Reproduces target exactly | Refuses every other input | Save status |", "|---|---|---|---|---|---|---|---|---|"]
    for x, c in rows:
        md.append(f'| {x["label"]} | {"clean base game: makes a new game" if x["kind"] == "base" else "earlier Project Blonde: updates it"} | {"yes" if x["status"] == "supported" else "no: recognised, refused"} | `{x["sha256"][:16]}…` | `{x["patch"]["file"]}` | {x["patch"]["size"]:,} ({x["patch"]["size_gz"]:,}) | {"yes" if c["reproduces target"] and c["input hash"] and c["patch hash"] else "NO"} | {"yes" if c["refuses other inputs"] else "NO"} | {x.get("save", {}).get("status", "new game")} |')
    md += ["", "Any file whose SHA-256 is not in this table is unknown and is refused.", ""]
    (ROOT / "PATCHER-MATRIX.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[6:])); print("FAILED: " + "; ".join(bad) if bad else "all patches verified")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    {"build": build, "verify": verify}[sys.argv[1] if len(sys.argv) > 1 else "verify"]()
