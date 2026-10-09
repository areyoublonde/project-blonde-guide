"""Render any map straight from the ROM, composing it the way the engine does:
block -> metatile -> 8 tile entries -> palette. Tilesets, palettes and block data are read from the
shipped ROM, so Hoenn (which is not in the source tree) renders exactly like Johto and Kanto."""
import struct
from PIL import Image

B = 0x08000000


def lz77(b, off):
    assert b[off] == 0x10, hex(b[off])
    size = b[off + 1] | b[off + 2] << 8 | b[off + 3] << 16
    out = bytearray()
    p = off + 4
    while len(out) < size:
        flags = b[p]; p += 1
        for i in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> i):
                v = b[p] << 8 | b[p + 1]; p += 2
                n, d = (v >> 12) + 3, (v & 0xFFF) + 1
                for _ in range(n):
                    out.append(out[-d])
            else:
                out.append(b[p]); p += 1
    return bytes(out)


def packed(R, ptr, size=None):
    """Bytes behind a data pointer. Hoenn terrain is stored as 'HMC1' records (pointer | 1): magic, length, then LZ77 chunks."""
    if ptr & 1:
        a = ptr - 1 - B
        assert R.b[a:a + 4] == b"HMC1", hex(ptr)
        n = struct.unpack_from("<I", R.b, a + 4)[0]
        out, i = b"", 0
        while len(out) < n:
            out += lz77(R.b, struct.unpack_from("<I", R.b, a + 8 + 4 * i)[0] - B)
            i += 1
        return out[:n]
    return R.b[ptr - B: ptr - B + (size or 0x4000)]


class Renderer:
    def __init__(self, rom, game=None):
        self.R = rom
        self.game = game
        self.dirs = {}
        if game:
            import re
            for f in ("src/data/tilesets/graphics.h", "src/graphics.c"):                # the General primary tileset is declared in graphics.c
                for m in re.finditer(r'gTilesetTiles_(\w+)\[\] = INCBIN_U32\("([^"]+)/tiles\.', (game / f).read_text(errors="replace")):
                    self.dirs.setdefault("gTilesetTiles_" + m.group(1), game / m.group(2))
        self.ts = {}      # tileset addr -> (tile bytes 4bpp, palettes, metatile u16s)
        self.mt = {}      # (primary, secondary, split) -> {metatile id: Image}

    def tileset(self, a):
        if a not in self.ts:
            R = self.R
            comp, tiles, pals, metas = R.u8(a) & 1, R.u32(a + 4), R.u32(a + 8), R.u32(a + 12)
            if not comp or (R.b[tiles - B] == 0x10 and R.rev.get(tiles, "") not in self.dirs):
                d = lz77(R.b, tiles - B) if comp else R.b[tiles - B: tiles - B + 0x4000]   # a tileset stored uncompressed is plain 4bpp, 512 tiles at most
                raw = bytes(x for byte in d for x in (byte & 15, byte >> 4))          # one palette index per pixel, 64 per tile
            else:                                                                     # H&S tiles are smol-compressed in the ROM: read the same art from the source tileset
                src = self.dirs.get(R.rev.get(tiles, ""))
                raw = b""
                if src and (src / "tiles.png").exists():
                    im = Image.open(src / "tiles.png")
                    if im.mode != "P":
                        im = im.convert("P")
                    tw, th, px = im.width // 8, im.height // 8, im.tobytes()
                    buf = bytearray(tw * th * 64)
                    for t in range(tw * th):
                        tx, ty = (t % tw) * 8, (t // tw) * 8
                        for y in range(8):
                            o = (ty + y) * im.width + tx
                            buf[t * 64 + y * 8: t * 64 + y * 8 + 8] = bytes(v & 15 for v in px[o:o + 8])
                    raw = bytes(buf)
                else:
                    self.missing = getattr(self, "missing", set()) | {R.rev.get(tiles, hex(tiles))}
            pal = [[self.rgb(R.u16(pals + 2 * (16 * p + c))) for c in range(16)] for p in range(13)]
            self.ts[a] = (raw, pal, packed(R, metas, 0x8000))
        return self.ts[a]

    @staticmethod
    def rgb(v):
        return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)

    def render(self, lay):
        R = self.R
        w, h, blocks, pri, sec, ver = R.s32(lay), R.s32(lay + 4), R.u32(lay + 12), R.u32(lay + 16), R.u32(lay + 20), R.u8(lay + 24)
        if not (R.ok(blocks & ~1) and R.ok(pri) and R.ok(sec)) or w <= 0 or h <= 0 or w * h > 40000:
            return None
        P, S = self.tileset(pri), self.tileset(sec)
        npri, npal = self.split(ver)
        pals = P[1][:npal] + S[1][npal:13]
        backdrop = pals[0][0]
        cache = self.mt.setdefault((pri, sec, npri), {})
        img = Image.new("RGB", (w * 16, h * 16), backdrop)
        data = struct.unpack_from(f"<{w * h}H", packed(R, blocks, w * h * 2))
        for i, v in enumerate(data):
            mid = v & 0x3FF
            im = cache.get(mid)
            if im is None:
                im = cache[mid] = self.metatile(mid, P, S, pals, npri, backdrop)
            img.paste(im, ((i % w) * 16, (i // w) * 16))
        return img

    def split(self, ver):
        """(tiles/metatiles in primary, palettes in primary) for a layout version. H&S layouts: 640 / 7; Emerald-format imports: 512 / 6."""
        return (512, 6) if ver == self.emerald_version else (640, 7)

    emerald_version = 0

    def metatile(self, mid, P, S, pals, npri, backdrop):
        R = self.R
        meta, base = (P[2], mid * 16) if mid < npri else (S[2], (mid - npri) * 16)
        im = Image.new("RGB", (16, 16), backdrop)
        if base + 16 > len(meta):
            return im
        px = im.load()
        for k in range(8):
            e = meta[base + 2 * k] | meta[base + 2 * k + 1] << 8
            t, hf, vf, pal = e & 0x3FF, e & 0x400, e & 0x800, e >> 12
            raw = P[0] if t < npri else S[0]
            ti = t if t < npri else t - npri
            o = ti * 64
            if o + 64 > len(raw) or pal >= len(pals):
                continue
            col = pals[pal]
            ox, oy = (k % 2) * 8, ((k % 4) // 2) * 8
            for y in range(8):
                row = o + (7 - y if vf else y) * 8
                for x in range(8):
                    c = raw[row + (7 - x if hf else x)]
                    if c or k < 4:
                        px[ox + x, oy + y] = col[c] if c else backdrop
        return im
