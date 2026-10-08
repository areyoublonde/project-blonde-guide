/* Project Blonde Guide — behaviour for every page. Pages read without it; this adds position, search, maps and filters. */
(() => {
  const BASE = document.documentElement.dataset.base || "", KEY = "pb-guide:v1";
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const on = (el, ev, fn, o) => el && el.addEventListener(ev, fn, o);
  const J = JSON.parse(($("#journey") || { textContent: "[]" }).textContent);

  // ---------- local state: position (last chapter opened or set by hand), Badges and milestones ticked. Nothing else.
  const store = {
    read() { try { return Object.assign({ done: {}, chapters: {} }, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch { return { done: {}, chapters: {} }; } },
    write(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {} document.dispatchEvent(new CustomEvent("pb:change")); },
    patch(fn) { const s = this.read(); fn(s); this.write(s); },
  };
  window.pbStore = store;
  if (document.body.dataset.chapterKey) { const s = store.read(); if (s.pos !== document.body.dataset.chapterKey) { s.pos = document.body.dataset.chapterKey; try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {} } }
  const norm = s => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

  // ---------- place the reader on the road
  let cur = null;
  const badgeLine = (rid, d) => { const ids = J.filter(j => j.rid === rid && j.bid).map(j => j.bid); if (!ids.length) return ""; const n = ids.filter(i => d[i]).length; const nx = J.find(j => j.rid === rid && j.bid && !d[j.bid]); return `${n} of ${ids.length} Badges` + (nx ? ` · next: ${nx.b}` : ""); };
  const place = () => {
    const s = store.read(); cur = J.find(j => j.k === s.pos) || null;
    document.documentElement.dataset.pos = cur ? "known" : "none";
    document.body.dataset.spoilers = s.spoilers ? "on" : "off";
    const set = (n, fn) => $$(`[data-now="${n}"]`).forEach(fn);
    if (cur) {
      const prev = J[cur.n - 2], next = J[cur.n];
      set("title", e => e.textContent = cur.t); set("meta", e => e.textContent = `${cur.r} · Chapter ${cur.n} of ${J.length}`);
      set("goal", e => e.textContent = cur.g); set("href", e => e.href = cur.h); set("cta", e => e.textContent = cur.live ? "Continue" : "See it on the road");
      set("barlabel", e => e.textContent = "Continue"); set("bartitle", e => e.textContent = cur.t);
      set("here", e => e.href = `#ch-${cur.n}`); set("short", e => e.textContent = `Chapter ${cur.n}`);
      set("badges", e => { const b = badgeLine(cur.rid, s.done); e.textContent = b ? `${cur.r} · ${b}` : ""; });
      [["prev", prev], ["next", next]].forEach(([n, j]) => set(n, e => { e.style.visibility = j ? "" : "hidden"; if (j) { e.href = j.h; e.querySelector("b").textContent = j.t; } }));
    }
    $$("[data-ch]").forEach(e => { const j = J.find(x => x.k === e.dataset.ch); if (!j) return; e.classList.toggle("done", !!cur && j.n < cur.n); e.classList.toggle("here", !!cur && j.n === cur.n); });
    $$(".road .you-tag").forEach(e => e.remove());
    $$(".journey:not(.atlas) .road li.here").forEach(li => { const m = document.createElement("span"); m.className = "m you-tag"; m.textContent = "You are here"; const old = li.querySelector(".m"); old ? old.replaceWith(m) : li.appendChild(m); });
    $$("[data-seg]").forEach(i => i.classList.toggle("on", !!s.done[i.dataset.seg]));
    $$("[data-count]").forEach(e => { const ids = e.dataset.count.split(",").filter(Boolean); e.textContent = `${ids.filter(i => s.done[i]).length} of ${ids.length} Badges`; });
    $$("input[data-check]").forEach(i => i.checked = !!s.done[i.dataset.check]);
    $$("[data-chapcount]").forEach(e => { const js = J.filter(j => j.rid === e.dataset.chapcount); e.textContent = `${js.filter(j => s.chapters[j.k]).length} of ${js.length} chapters`; });
    $$("input[data-chapter]").forEach(i => i.checked = !!s.chapters[i.dataset.chapter]);
    $$("[data-mode-btn]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.modeBtn === (s.mode || "full"))));
    if (document.body.dataset.hasMode !== undefined) document.body.dataset.mode = s.mode || "full";
    $$("[data-spoiler-toggle]").forEach(b => b.textContent = s.spoilers ? "Spoilers: shown" : "Spoilers: hidden");
    if (s.spoilers) $$("details.spoiler").forEach(d => d.open = true);
    const sp = $("[data-set-pos]"); if (sp) sp.value = s.pos || "";
    home(); stageSync && stageSync();
  };
  // home: the world shows where you are — the chapter's own plate, or the Town Map when there is none yet
  const home = () => {
    const pp = $("[data-pos-plate]"), hm = $("[data-home-map]"); if (!pp) return;
    const img = pp.querySelector("img");
    if (cur && cur.plate) { img.src = img.dataset.plates + cur.plate + ".jpg"; pp.classList.add("has"); hm.hidden = true; }
    else { pp.classList.remove("has"); hm.hidden = !(cur && cur.map); if (cur && cur.map) { hm.dataset.view = cur.map; hm.querySelector(".you").style.cssText = `display:block;left:${cur.x}%;top:${cur.y}%`; } }
    const out = $("[data-readout]"); if (!out) return;
    const base = cur ? `Chapter ${cur.n} of ${J.length} · ${cur.t}` : out.dataset.default; out.textContent = base; out.dataset.base = base;
  };
  $$(".leg-s .ticks a").forEach(a => { const out = $("[data-readout]"); on(a, "mouseenter", () => out.textContent = a.dataset.tip); on(a, "mouseleave", () => out.textContent = out.dataset.base); on(a, "focus", () => out.textContent = a.dataset.tip); on(a, "blur", () => out.textContent = out.dataset.base); });

  // ---------- inputs that change state
  on(document, "change", e => {
    const i = e.target;
    if (i.matches("input[data-check]")) store.patch(s => i.checked ? s.done[i.dataset.check] = 1 : delete s.done[i.dataset.check]);
    else if (i.matches("input[data-chapter]")) store.patch(s => i.checked ? s.chapters[i.dataset.chapter] = 1 : delete s.chapters[i.dataset.chapter]);
    else if (i.matches("[data-set-pos]")) store.patch(s => i.value ? s.pos = i.value : delete s.pos);
  });
  on(document, "click", e => {
    const t = e.target.closest("[data-mode-btn],[data-spoiler-toggle],.blur,[data-tab],[data-tod]"); if (!t) return;
    if (t.matches("[data-mode-btn]")) store.patch(s => s.mode = t.dataset.modeBtn);
    else if (t.matches("[data-spoiler-toggle]")) store.patch(s => s.spoilers = !s.spoilers);
    else if (t.matches(".blur")) t.classList.add("shown");
    else if (t.matches("[data-tab]")) { const g = t.closest("[data-tabs]"); $$("[data-tab]", g).forEach(x => x.setAttribute("aria-selected", String(x === t))); $$("[data-panel]", g).forEach(p => p.hidden = p.dataset.panel !== t.dataset.tab); }
    else if (t.matches("[data-tod]")) { $$("[data-tod]").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.tod === t.dataset.tod))); $$("[data-tod-panel]").forEach(p => p.hidden = p.dataset.todPanel !== t.dataset.tod); }
  });
  on(document, "keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches(".blur")) { e.preventDefault(); e.target.classList.add("shown"); } });
  on(document, "pb:change", () => place());
  // export / import / clear
  on($("[data-export]"), "click", () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify({ app: "project-blonde-guide", version: 2, ...store.read() }, null, 2)], { type: "application/json" })); a.download = "project-blonde-progress.json"; a.click(); });
  on($("[data-import]"), "change", async e => { const msg = $("[data-io-msg]"); try { const d = JSON.parse(await e.target.files[0].text()); if (d.app !== "project-blonde-guide" || typeof d.done !== "object") throw 0; store.patch(s => { s.done = d.done; s.chapters = d.chapters || {}; if (d.pos) s.pos = d.pos; }); msg.textContent = "Progress imported."; } catch { msg.textContent = "That file isn't a Project Blonde progress export."; } e.target.value = ""; });
  on($("[data-clear]"), "click", () => { if (confirm("Clear your position and everything ticked on this device?")) store.write({ done: {}, chapters: {} }); });

  // ---------- header, menu, sheets
  const top = $(".top"), scrolled = () => top.classList.toggle("scrolled", scrollY > 12); on(window, "scroll", scrolled, { passive: true }); scrolled();
  const menuBtn = $("[data-menu]"), menu = $("#menu");
  const setMenu = open => { menu.hidden = !open; menuBtn.setAttribute("aria-expanded", String(open)); menuBtn.textContent = open ? "Close" : "Menu"; top.classList.toggle("solid", open); document.body.style.overflow = open ? "hidden" : ""; };
  on(menuBtn, "click", () => setMenu(menu.hidden));
  on(document, "click", e => {
    $$(".dock details[open], .more[open]").forEach(d => { if (!d.contains(e.target) || e.target.closest(".sheet a, .more a")) d.open = false; });
  });
  on(document, "keydown", e => { if (e.key === "Escape") { $$(".dock details[open], .more[open]").forEach(d => d.open = false); if (!menu.hidden) setMenu(false); } });

  // ---------- Town Map on the road: follow the part of the road on screen
  let stageSync = null;
  const stage = $(".journey:not(.atlas) .stage");
  if (stage) {
    const you = $(".you", stage), label = $("[data-stage-label]", stage);
    const NAMES = { jk: "Johto & Kanto · the game's Town Map", hoenn: "Hoenn · the game's Town Map", none: "Postgame · no fixed route" };
    let view = "jk", leg = "johto";
    stageSync = () => { stage.dataset.view = view; stage.dataset.leg = leg; label.textContent = NAMES[view];
      if (cur && cur.map === view && cur.x != null) you.style.cssText = `display:block;left:${cur.x}%;top:${cur.y}%`; else you.style.display = "none"; };
    const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { view = en.target.dataset.view; if (en.target.dataset.region) leg = en.target.dataset.region; stageSync(); } }), { rootMargin: "-45% 0px -50% 0px" });
    $$(".leg, .crossing").forEach(s => io.observe(s));
    const dot = k => $(`circle[data-ch="${k}"]`, stage);
    $$(".road li").forEach(li => { const f = v => { const c = dot(li.dataset.ch); c && c.classList.toggle("hot", v); }; on(li, "mouseenter", () => f(true)); on(li, "mouseleave", () => f(false)); });
    $$("circle[data-ch]", stage).forEach(c => { c.style.cursor = "pointer"; c.style.pointerEvents = "auto"; on(c, "click", () => { const li = $(`.road li[data-ch="${c.dataset.ch}"]`); if (li) { li.scrollIntoView({ block: "center" }); history.replaceState(null, "", "#" + li.id); } }); });
  }

  // ---------- World atlas
  const atlas = $(".atlas");
  if (atlas) {
    const st = $(".stage", atlas), out = $("[data-place-readout]", atlas), lab = $("[data-stage-label]", atlas), base = out.textContent;
    $$("[data-atlas]").forEach(b => on(b, "click", () => { $$("[data-atlas]").forEach(x => x.setAttribute("aria-pressed", String(x === b))); st.dataset.view = b.dataset.atlas; $$("[data-atlas-panel]").forEach(p => p.hidden = p.dataset.atlasPanel !== b.dataset.atlas); lab.textContent = b.dataset.atlas === "jk" ? "Johto & Kanto · the game's Town Map" : "Hoenn · the game's Town Map"; const fi = $("[data-filter-list]", atlas); fi && fi.dispatchEvent(new Event("input")); }));
    const row = s => $(`.places li[data-place="${s}"]`), dot = s => $(`circle[data-place="${s}"]`, st);
    $$(".places li").forEach(li => { on(li, "mouseenter", () => { const c = dot(li.dataset.place); c && c.classList.add("hot"); out.textContent = li.querySelector("b").textContent; }); on(li, "mouseleave", () => { const c = dot(li.dataset.place); c && c.classList.remove("hot"); out.textContent = base; }); });
    $$("circle[data-place]", st).forEach(c => { on(c, "mouseenter", () => { const li = row(c.dataset.place); li && li.classList.add("hot"); out.textContent = c.querySelector("title").textContent; }); on(c, "mouseleave", () => { const li = row(c.dataset.place); li && li.classList.remove("hot"); out.textContent = base; });
      on(c, "click", () => { const li = row(c.dataset.place); if (!li) return; const a = li.querySelector("a"); if (a) { location.href = a.href; return; } li.scrollIntoView({ block: "center" }); history.replaceState(null, "", "#" + li.id); $$(".places li.hot").forEach(x => x.classList.remove("hot")); li.classList.add("hot"); }); });
  }

  // ---------- list filtering (Pokémon, items, places)
  $$("[data-filter-list]").forEach(input => {
    const lists = $$(input.dataset.filterList), rows = lists.flatMap(l => $$(":scope > li", l)), scope = input.closest(".listpage, .roadcol") || document;
    const count = $("[data-filter-count]", scope), empty = $("[data-filter-empty]", scope); let region = "";
    const run = () => { const toks = norm(input.value).split(" ").filter(Boolean); let n = 0;
      rows.forEach(li => { const ok = toks.every(t => li.dataset.f.includes(t)) && (!region || (li.dataset.r || "").split(" ").includes(region) || li.dataset.r === region); li.hidden = !ok; n += ok; const c = li.dataset.place && $(`circle[data-place="${li.dataset.place}"]`); c && c.classList.toggle("dim", !ok); });
      if (count) count.textContent = `${n} of ${rows.length}`; if (empty) empty.hidden = n > 0; $$(".kind", scope).forEach(k => k.hidden = !$$("li:not([hidden])", k).length && !!$$("li", k).length); };
    on(input, "input", run);
    $$("[data-region-filter]", scope).forEach(b => on(b, "click", () => { region = b.dataset.regionFilter; $$("[data-region-filter]", scope).forEach(x => x.setAttribute("aria-pressed", String(x === b))); run(); }));
    run();
  });

  // ---------- working map: zoom, pan, layers, full screen
  $$(".mapv").forEach(v => {
    const view = $(".mapv-view", v), stg = $(".mapv-stage", v), tip = $(".mapv-tip", v), ex = $("[data-expand]", v), mw = +stg.dataset.w; let z = 1;
    const fit = () => Math.min(1, view.clientWidth / mw);
    const setZ = (nz, keep) => { const cx = (view.scrollLeft + view.clientWidth / 2) / (mw * z), cy = (view.scrollTop + view.clientHeight / 2) / (stg.offsetHeight || 1);
      z = Math.max(fit(), Math.min(3, nz)); stg.style.setProperty("--z", z); if (keep) { view.scrollLeft = cx * mw * z - view.clientWidth / 2; view.scrollTop = cy * stg.offsetHeight - view.clientHeight / 2; } };
    stg.style.setProperty("--mw", mw); setZ(v.dataset.zoom === "fill" ? Math.min(1.6, view.clientWidth / mw) : Math.max(fit(), 0.62)); v.pbZoom = () => z;
    $$("[data-zoom]", v).forEach(b => on(b, "click", () => setZ(b.dataset.zoom === "fit" ? fit() : z * (b.dataset.zoom === "in" ? 1.4 : 1 / 1.4), true)));
    $$("[data-filter]", v).forEach(b => on(b, "click", () => { const o = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", String(o)); $$(b.dataset.filter === "pit" ? ".pit" : `.mk[data-kind="${b.dataset.filter}"]`, v).forEach(m => m.hidden = !o); }));
    $$(".mk", v).forEach(m => on(m, "click", () => { $$(".mk", v).forEach(x => x.setAttribute("aria-expanded", String(x === m))); tip.innerHTML = `<b>${m.dataset.label}</b>${m.dataset.note ? " — " + m.dataset.note : ""}`; }));
    const full = o => { v.toggleAttribute("data-full", o); ex.setAttribute("aria-pressed", String(o)); ex.setAttribute("aria-label", o ? "Close full-screen map" : "Expand map"); document.body.style.overflow = o ? "hidden" : ""; setZ(o ? Math.max(z, Math.min(1.5, view.clientWidth / mw)) : z, true); };
    on(ex, "click", () => full(!v.hasAttribute("data-full"))); on(document, "keydown", e => { if (e.key === "Escape" && v.hasAttribute("data-full")) full(false); });
    let drag = null;
    on(view, "pointerdown", e => { if (e.pointerType === "mouse" && !e.target.closest(".mk")) { drag = [e.clientX, e.clientY, view.scrollLeft, view.scrollTop]; view.setPointerCapture(e.pointerId); } });
    on(view, "pointermove", e => { if (drag) { view.scrollLeft = drag[2] - (e.clientX - drag[0]); view.scrollTop = drag[3] - (e.clientY - drag[1]); } }); on(view, "pointerup", () => drag = null);
    if (v.dataset.focus) { const [fx, fy] = v.dataset.focus.split(",").map(Number); requestAnimationFrame(() => { view.scrollLeft = fx * mw * z - view.clientWidth / 2; view.scrollTop = fy * stg.offsetHeight - view.clientHeight / 2; }); }
  });

  // ---------- contents highlight; setup stepper
  const spy = (links, cls) => { if (!links.length) return; const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) links.forEach(a => a.classList.toggle(cls, a.hash === "#" + en.target.id)); }), { rootMargin: "-20% 0px -70% 0px" }); links.forEach(a => { const t = document.getElementById(a.hash.slice(1)); t && io.observe(t); }); };
  spy($$(".toc a"), "on"); spy($$(".stepnav a"), "on");
  const steps = $$(".steps > li[data-step]"), sd = $(".dock.stepper");
  if (steps.length && sd) { let i = 0; const n = $("[data-step-n]", sd), t = $("[data-step-t]", sd), pv = $("[data-step-prev]", sd), nx = $("[data-step-next]", sd);
    const show = k => { i = Math.max(0, Math.min(steps.length - 1, k)); n.textContent = `Step ${i + 1} of ${steps.length}`; t.textContent = steps[i].dataset.step; pv.disabled = i === 0; nx.disabled = i === steps.length - 1; };
    const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) show(steps.indexOf(en.target)); }), { rootMargin: "-30% 0px -60% 0px" }); steps.forEach(s => io.observe(s));
    on(pv, "click", () => steps[Math.max(0, i - 1)].scrollIntoView()); on(nx, "click", () => steps[Math.min(steps.length - 1, i + 1)].scrollIntoView()); show(0); }

  // ---------- search: one palette, grouped answers
  let index = null;
  const ORDER = ["Walkthrough", "Stuck?", "Pokémon", "Trainer", "World", "Item", "Feature", "Play", "Guide"];
  const safe = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const STOP = new Set("how do i the a to is where what of in my can get use and go after for are does s find on it an at".split(" "));
  const near = (a, b) => { if (Math.abs(a.length - b.length) > 1) return false; let i = 0, j = 0, d = 0; while (i < a.length && j < b.length) { if (a[i] === b[j]) { i++; j++; } else { if (++d > 1) return false; if (a.length > b.length) i++; else if (a.length < b.length) j++; else { i++; j++; } } } return d + (a.length - i) + (b.length - j) <= 1; };
  const load = async () => index || (index = (await (await fetch(BASE + "/assets/search-index.json")).json()).map(e => ({ ...e, T: norm(e.t), X: norm((e.x || "") + " " + (e.d || "")), W: norm(e.t + " " + (e.x || "")).split(" ") })));
  const find = q => { const raw = norm(q); let toks = raw.split(" ").filter(Boolean); const strong = toks.filter(t => !STOP.has(t)); if (strong.length) toks = strong; if (!toks.length) return [];
    return index.map(e => { let total = 0; for (const t of toks) { let b = 0; if (e.T.includes(t)) b = e.T.startsWith(t) || e.T.includes(" " + t) ? 10 : 6; else if (e.W.some(w => w.startsWith(t))) b = 4; else if (e.X.includes(t)) b = 3; else if (t.length >= 5 && e.W.some(w => near(w, t))) b = 2; if (!b) return [0, e]; total += b; } return [total + (e.T === raw ? 20 : 0) + (e.p || 0), e]; }).filter(x => x[0]).sort((a, b) => b[0] - a[0]).slice(0, 40).map(x => x[1]); };
  const row = e => `<a href="${BASE + e.u}" role="option"><b>${safe(e.t)}</b><span>${safe(e.d || "")}</span></a>`;
  const render = (box, q) => {
    if (!q.trim()) { const s = [];
      if (cur) s.push({ t: `Continue · ${cur.t}`, d: `${cur.r} · Chapter ${cur.n} of ${J.length}`, u: cur.h.replace(BASE, "") });
      s.push({ t: "The walkthrough", d: "The whole road, in order", u: "/walkthrough/" }, { t: "Stuck?", d: "Get unstuck from where you are", u: "/stuck/" }, { t: "Play Project Blonde", d: "Download, setup and saves", u: "/play/" });
      box.innerHTML = `<h5>Go to</h5>` + s.map(row).join(""); return; }
    const list = find(q); if (!list.length) { box.innerHTML = `<p class="empty muted">Nothing for “${q.replace(/[<>&]/g, "")}”. Try a place, a Pokémon, a Trainer or an item.</p>`; return; }
    const g = {}; list.forEach(e => (g[e.k] = g[e.k] || []).push(e));
    box.innerHTML = Object.keys(g).map(k => `<h5>${k}</h5>` + g[k].slice(0, 6).map(row).join("")).join("");   // groups appear in order of their best match
  };
  const wire = (input, box) => { let sel = -1; const run = async () => { await load(); render(box, input.value); sel = -1; if (input.value.trim()) { const as = $$("a", box); if (as.length) { sel = 0; as[0].classList.add("sel"); } } };
    on(input, "input", run);
    on(input, "keydown", e => { if (e.key === "Escape") { const d = input.closest("dialog"); if (d && d.open) { e.preventDefault(); d.close(); } return; }   // a search field's own Esc only clears the text
      const as = $$("a", box); if (!as.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + as.length) % as.length; as.forEach((a, i) => a.classList.toggle("sel", i === sel)); as[sel].scrollIntoView({ block: "nearest" }); }
      if (e.key === "Enter") { e.preventDefault(); as[Math.max(sel, 0)].click(); } });
    return run; };
  const dlg = $("dialog.search"), dInput = $("input", dlg), dRun = wire(dInput, $(".results", dlg));
  const openSearch = () => { if (dlg.open) return; if (!menu.hidden) setMenu(false); dlg.showModal(); dInput.value = ""; dRun(); dInput.focus(); };
  on(document, "click", e => { if (e.target.closest("[data-search-open]")) { e.preventDefault(); openSearch(); } else if (e.target.closest("[data-search-close]") || e.target === dlg) dlg.close(); else if (dlg.open && e.target.closest(".results a")) dlg.close(); });
  on(document, "keydown", e => { if ((e.key === "/" || (e.key === "k" && (e.metaKey || e.ctrlKey))) && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); openSearch(); } });
  const sp = $("[data-search-page]"); if (sp) { const i = $("input", sp); i.value = new URLSearchParams(location.search).get("q") || ""; wire(i, $(".results", sp))(); i.focus(); }

  // ---------- Stuck?: a question, or where you are
  const sq = $("[data-stuck-q]");
  if (sq) {
    const sel = $("[data-stuck-badge]"), qas = $$("[data-answers] .qa"), box = $("[data-answers]"), lab = $("[data-answers-label]"), empty = $("[data-stuck-empty]"), stretch = $("[data-stretch]"), list = $("[data-stretch-list]"), nextB = $("[data-stretch-next]");
    let range = null;
    const run = () => { const toks = norm(sq.value).split(" ").filter(t => t && !STOP.has(t)); let n = 0; const rel = [];
      qas.forEach(q => { const hit = toks.every(t => q.dataset.f.includes(t)); const inR = !!range && range.includes(q.dataset.ch); q.classList.toggle("rel", inR && !toks.length); q.hidden = !hit; n += hit; if (inR) rel.push(q); });
      if (!toks.length && rel.length) rel.reverse().forEach(q => box.prepend(q));
      lab.textContent = toks.length ? `${n} answer${n === 1 ? "" : "s"}` : (rel.length ? "Most likely for where you are" : "Common blockers"); empty.hidden = n > 0; };
    const locate = at => { const k = sel.value, from = typeof at === "number" ? at : (k ? J.find(j => j.k === k).n : 0); const after = J.filter(j => j.n > from); const stop = after.find(j => j.bid); const span = after.filter(j => !stop || j.n <= stop.n).slice(0, 8);
      range = span.map(j => j.k); stretch.hidden = false;
      list.innerHTML = span.map(j => `<li class="${j.bid ? "gym" : ""}"><span class="dot"></span><span class="n">${String(j.n).padStart(2, "0")}</span>${j.live ? `<a class="t" href="${j.h}">${j.t}</a>` : `<span class="t">${j.t}</span>`}${j.b ? `<span class="m">${j.b}</span>` : ""}</li>`).join("");
      nextB.textContent = stop ? `Next Badge: ${stop.b}, in Chapter ${stop.n}.` : "No more Badges on this stretch of the road."; run(); };
    const chap = $("[data-stuck-chapter]"), ns = $("[data-nextstep]"), NEEDS = JSON.parse(($("#needs") || { textContent: "{}" }).textContent);
    const step = () => { const j = J.find(x => x.k === chap.value); ns.hidden = !j; if (!j) return; const st = store.read(), done = !!st.chapters[j.k], t = done ? (J[j.n] || j) : j;
      $("[data-ns-title]", ns).textContent = t.t; $("[data-ns-goal]", ns).textContent = t.g || "A later part of the story. Open the chapter when you are ready for spoilers.";
      const need = NEEDS[t.k] || []; $("[data-ns-need]", ns).textContent = need.length ? "You need: " + need.join(" ") : ""; $("[data-ns-href]", ns).href = t.h;
      $("[data-ns-done]", ns).textContent = done ? `You marked ${j.t} complete, so this is the chapter after it.` : `Finished ${j.t} already? Mark it complete on its page and this moves on.`;
      const last = [...J].reverse().find(x => x.bid && x.n < t.n); sel.value = last ? last.k : ""; locate(t.n - 1);
      range = [t.k].concat(range || []); run(); };
    on(chap, "change", step);
    on(sq, "input", run); on(sel, "change", () => locate());
    const st = store.read(), me = J.find(j => j.k === st.pos);
    if (me) { chap.value = me.k; step(); } else run();
  }

  // ---------- anchors that point at a collapsed answer
  const openHash = () => { const d = location.hash && document.getElementById(location.hash.slice(1)); if (!d) return; const det = d.tagName === "DETAILS" ? d : d.querySelector(":scope > details"); if (det) det.open = true; };
  on(window, "hashchange", openHash); openHash();
  place();
})();
