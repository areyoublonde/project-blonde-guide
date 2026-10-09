/* Make your game: builds Project Blonde on the visitor's own device from a file they choose.
   The chosen file is only read, never changed and never sent anywhere; the only download is the patch.
   A file is identified by its SHA-256 against the registry embedded in the page (content/patcher.json), never by its name. */
(() => {
  const root = document.querySelector("[data-patcher]"); if (!root) return;
  const REG = JSON.parse(document.getElementById("patcher-registry").textContent), T = REG.target;
  const $ = s => root.querySelector(s), $$ = s => [...root.querySelectorAll(s)];
  const hex = b => { let s = ""; for (const x of b) s += x.toString(16).padStart(2, "0"); return s; };
  const IOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  let cur = null, outUrl = null;

  // ---------- SHA-256: the browser's own where it exists, otherwise plain JS (http:// pages on a home network have no crypto.subtle)
  const K = new Uint32Array(64); { let n = 0, p = 2; while (n < 64) { let q = true; for (let i = 2; i * i <= p; i++) if (p % i === 0) { q = false; break; } if (q) { const c = Math.cbrt(p); K[n++] = ((c - Math.floor(c)) * 4294967296) >>> 0; } p++; } }
  function sha256js(d) {
    const H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]), w = new Uint32Array(64);
    const n = d.length, total = ((n + 9 + 63) >> 6) << 6, tail = new Uint8Array(total - (n & ~63)); tail.set(d.subarray(n & ~63)); tail[n & 63] = 0x80;
    const dv = new DataView(tail.buffer); dv.setUint32(tail.length - 8, Math.floor(n / 536870912)); dv.setUint32(tail.length - 4, (n << 3) >>> 0);
    const block = (b, o) => {
      for (let i = 0; i < 16; i++) w[i] = (b[o] << 24 | b[o + 1] << 16 | b[o + 2] << 8 | b[o + 3]) >>> 0, o += 4;
      for (let i = 16; i < 64; i++) { const x = w[i - 15], y = w[i - 2]; w[i] = (w[i - 16] + ((x >>> 7 | x << 25) ^ (x >>> 18 | x << 14) ^ (x >>> 3)) + w[i - 7] + ((y >>> 17 | y << 15) ^ (y >>> 19 | y << 13) ^ (y >>> 10))) >>> 0; }
      let a = H[0], b2 = H[1], c = H[2], e2 = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (let i = 0; i < 64; i++) {
        const t1 = (h + ((e >>> 6 | e << 26) ^ (e >>> 11 | e << 21) ^ (e >>> 25 | e << 7)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0;
        const t2 = (((a >>> 2 | a << 30) ^ (a >>> 13 | a << 19) ^ (a >>> 22 | a << 10)) + ((a & b2) ^ (a & c) ^ (b2 & c))) >>> 0;
        h = g; g = f; f = e; e = (e2 + t1) >>> 0; e2 = c; c = b2; b2 = a; a = (t1 + t2) >>> 0;
      }
      H[0] += a; H[1] += b2; H[2] += c; H[3] += e2; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    };
    for (let o = 0; o + 64 <= (n & ~63); o += 64) block(d, o);
    for (let o = 0; o < tail.length; o += 64) block(tail, o);
    const out = new Uint8Array(32), ov = new DataView(out.buffer); H.forEach((x, i) => ov.setUint32(i * 4, x)); return out;
  }
  const sha256 = async d => hex(root.dataset.forceJsHash === undefined && window.crypto && crypto.subtle ? new Uint8Array(await crypto.subtle.digest("SHA-256", d)) : sha256js(d));

  // ---------- BPS
  function applyBps(src, p) {
    if (p.length < 20 || p[0] !== 66 || p[1] !== 80 || p[2] !== 83 || p[3] !== 49) throw Error("patch");
    let i = 4; const dec = () => { let d = 0, sh = 1; for (;;) { const x = p[i++]; d += (x & 0x7f) * sh; if (x & 0x80) return d; sh *= 128; d += sh; } };
    const ss = dec(), ts = dec(), ms = dec(); i += ms; if (ss !== src.length) throw Error("base");
    const o = new Uint8Array(ts), end = p.length - 12; let n = 0, sr = 0, tr = 0;
    while (i < end) {
      const v = dec(), t = v & 3, len = Math.floor(v / 4) + 1;
      if (t === 0) { o.set(src.subarray(n, n + len), n); n += len; }
      else if (t === 1) { o.set(p.subarray(i, i + len), n); i += len; n += len; }
      else { const w = dec(), d = (w & 1 ? -1 : 1) * Math.floor(w / 2);
        if (t === 2) { sr += d; o.set(src.subarray(sr, sr + len), n); sr += len; n += len; }
        else { tr += d; for (let k = 0; k < len; k++) o[n++] = o[tr++]; } }
    }
    if (n !== ts) throw Error("size"); return o;
  }

  // ---------- what a refused file probably is. Hints only: nothing here decides whether a file is accepted.
  const ascii = (b, a, n) => String.fromCharCode(...b.subarray(a, a + n)).replace(/\0+$/, "");
  function describe(b) {
    if (b.length >= 4 && b[0] === 0x50 && b[1] === 0x4b && b[2] === 3 && b[3] === 4) return "zip";
    if (b.length === 131072 || b.length === 131088) return "save";
    if (b.length < 0xc0) return "other";
    const title = ascii(b, 0xa0, 12), code = ascii(b, 0xac, 4);
    if (title.startsWith("POKEMON HNS")) return "blonde";
    if (title.startsWith("POKEMON EMER")) return code !== "BPEE" ? "emerald-lang" : (b.length !== 16777216 ? "emerald-size" : "emerald-mod");
    return b[0xb2] === 0x96 ? "gba" : "other";
  }
  const WHY = {
    zip: "That is a zip file. Unpack it first, then choose the .gba file inside it.",
    save: "That looks like a save file, not the game. Choose the game file, the one ending in .gba. Keep the save safe; you will want it later.",
    "emerald-lang": "That is Pokémon Emerald in another language. Project Blonde needs the English version, the one sold in the USA and Europe.",
    "emerald-size": "That is Pokémon Emerald, but the file is not the right size. It may be cut short or padded. Project Blonde needs a complete, unchanged copy.",
    "emerald-mod": "That is Pokémon Emerald, but not an unchanged copy. It may be a hack, a randomised or already patched game, or a damaged file. Project Blonde needs the original game exactly as it is on the cartridge.",
    gba: "That is a Game Boy Advance game, but not the one this page needs.", other: "That is not a Game Boy Advance game file."
  };
  function refuse(kind, hit) {
    if (hit) return `This is ${hit.label}. This page cannot update that build. Your file has not been changed. Keep your save file safe and make Project Blonde ${T.public_version} from your own Pokémon Emerald file instead. Ask on Discord before relying on a save from that build.`;
    if (kind === "blonde") return "This looks like Project Blonde or Heart & Soul, but it is not a version this page knows. It may be an unreleased build, or a file changed by cheats or another patch. Your file has not been changed. Keep your save file safe and choose your own Pokémon Emerald file instead.";
    return (WHY[kind] || WHY.other) + (kind === "gba" || kind === "other" ? " Choose your own Pokémon Emerald (USA, Europe) file, or the Project Blonde .gba you already play." : "");
  }

  // ---------- interface
  const state = s => { root.dataset.state = s; };
  const say = (t, bad) => { const m = $("[data-mk-msg]"); m.textContent = t; m.classList.toggle("bad", !!bad); };
  const adv = rows => { $("[data-mk-adv]").innerHTML = rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join(""); };
  const show = (sel, on) => $$(sel).forEach(e => { e.hidden = !on; });
  const only = kind => $$("[data-mk-only]").forEach(e => { e.hidden = e.dataset.mkOnly !== kind; });
  const memory = err => err instanceof RangeError || /memory|allocation/i.test(err && err.message || "");
  const MEM = "This device ran out of memory, so nothing was built and your file has not been changed. Close other tabs and apps and try again, or do this step on a computer and send the finished game to this device.";
  function reset() {
    cur = null; if (outUrl) { URL.revokeObjectURL(outUrl); outUrl = null; }
    show("[data-mk-found],[data-mk-ready],[data-mk-current]", false); show("[data-mk-pickrow]", true); say(""); adv([["Status", "No file chosen yet."]]);
    delete root.dataset.outSha256; delete root.dataset.input; delete root.dataset.detected; delete root.dataset.error;
    $("[data-mk-backup]").checked = false; $("[data-mk-file]").value = ""; state("ask");
  }
  const sync = () => { $("[data-mk-go]").disabled = !cur || (cur.hit.kind === "release" && !$("[data-mk-backup]").checked); };
  $("[data-mk-backup]").addEventListener("change", sync);

  $("[data-mk-file]").addEventListener("change", async e => {
    const file = e.target.files[0]; if (!file) return;
    cur = null; show("[data-mk-found],[data-mk-ready],[data-mk-current]", false); sync(); state("checking"); say("Checking your file…");
    try {
      const bytes = new Uint8Array(await file.arrayBuffer()), sum = await sha256(bytes);
      root.dataset.input = sum;
      const hit = sum === T.sha256 && bytes.length === T.size ? "target" : REG.inputs.find(x => x.sha256 === sum && x.size === bytes.length);
      const rows = [["Your file", `${bytes.length.toLocaleString("en")} bytes<br><code>${sum}</code>`], ["Recognised as", hit === "target" ? `Project Blonde ${T.public_version} (build ${T.internal_build})` : hit ? hit.label : "Not in the list of known files"]];
      root.dataset.detected = hit === "target" ? "current" : hit ? hit.id : "unknown";
      if (hit === "target") { adv(rows.concat([["Check", "Matches the approved release exactly."]])); say(""); show("[data-mk-current]", true); state("current"); return; }
      if (!hit || hit.status !== "supported") { adv(rows); state("rejected"); say(refuse(describe(bytes), hit), true); return; }
      cur = { bytes, hit }; only(hit.kind);
      $("[data-mk-from]").textContent = hit.label; $("[data-mk-to]").textContent = `Project Blonde ${T.public_version}`;
      $("[data-mk-savenote]").textContent = hit.save ? hit.save.note : "";
      $("[data-mk-go] span").textContent = hit.kind === "base" ? "Make my game" : "Update my game";
      adv(rows.concat([["Will become", `Project Blonde ${T.public_version} (build ${T.internal_build})<br><code>${T.sha256}</code>`], ["Using", `${hit.patch.file}<br><code>${hit.patch.sha256}</code>`]]));
      show("[data-mk-found]", true); say(""); sync(); state("found");
    } catch (err) { state("error"); root.dataset.error = memory(err) ? "memory" : "read"; say(memory(err) ? MEM : "That file could not be read. Please try again.", true); }
  });

  $("[data-mk-go]").addEventListener("click", async () => {
    if (!cur) return; const { bytes, hit } = cur; $("[data-mk-go]").disabled = true; state("working");
    try {
      say(hit.patch.size > 1e6 ? `Getting Project Blonde (${Math.round((window.DecompressionStream ? hit.patch.size_gz : hit.patch.size) / 1048576)} MB)…` : "Getting the update…");
      const gz = !!window.DecompressionStream, r = await fetch(root.dataset.patches + hit.patch.file + (gz ? ".gz" : ""), { cache: "no-cache" });
      if (!r.ok) throw Error("download");
      const p = new Uint8Array(await (gz ? new Response(r.body.pipeThrough(new DecompressionStream("gzip"))) : r).arrayBuffer());
      if (await sha256(p) !== hit.patch.sha256) throw Error("damaged");
      say("Building your game…"); await new Promise(f => setTimeout(f, 40));
      const out = applyBps(bytes, p), sum = await sha256(out);
      root.dataset.outSha256 = sum;
      if (sum !== T.sha256 || out.length !== T.size) throw Error("result");
      const f = new File([out], T.file_name, { type: "application/octet-stream" });
      outUrl = URL.createObjectURL(f);
      const a = $("[data-mk-save]"); a.href = outUrl; a.download = T.file_name; a.querySelector("span").textContent = IOS ? "Save to Files" : "Save game file";
      const sh = $("[data-mk-share]"), can = IOS && navigator.canShare && navigator.canShare({ files: [f] });
      sh.hidden = !can; sh.onclick = () => navigator.share({ files: [f] }).catch(() => {});
      $$("[data-mk-ios]").forEach(x => { x.hidden = !IOS; }); $$("[data-mk-notios]").forEach(x => { x.hidden = IOS; });
      adv([["Started from", `${hit.label}<br><code>${hit.sha256}</code>`], ["Result", `Project Blonde ${T.public_version} (build ${T.internal_build}), ${out.length.toLocaleString("en")} bytes<br><code>${sum}</code>`], ["Check", "Matches the approved release exactly."], ["Privacy", "Built on this device. Your file was not changed and nothing was uploaded."]]);
      only(hit.kind); cur = null; show("[data-mk-found],[data-mk-pickrow]", false); show("[data-mk-ready]", true); say(""); state("ready");
      $("[data-mk-ready]").focus();
    } catch (err) {
      state("error"); $("[data-mk-go]").disabled = false; root.dataset.error = memory(err) ? "memory" : err.message;
      say(memory(err) ? MEM : err.message === "download" ? "The download did not finish. Check your connection and try again."
        : err.message === "damaged" ? "The download arrived damaged, so nothing was built. Please try again in a moment."
        : "Something went wrong while building the game, so nothing was saved. Please try again; if it keeps happening, tell us on Discord.", true);
    }
  });
  $$("[data-mk-reset]").forEach(b => b.addEventListener("click", reset));
  reset();
})();
