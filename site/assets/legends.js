/* Legendary & Mythical field guide: search, three filters, deep links into the expandable entries. */
(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = $("[data-legends]"); if (!root) return;
  const rows = $$(".lg-index > li", root), input = $("[data-lg-q]", root), count = $("[data-lg-count]", root), empty = $("[data-lg-empty]", root);
  const active = $("[data-lg-active]", root), panel = $(".lg-filters", root), buttons = $$("[data-lg-filter]", root);
  const state = { region: "", type: "", stage: "" };
  const norm = s => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[’']/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

  const run = () => {
    const q = norm(input.value), qc = q.replace(/ /g, ""), toks = q.split(" ").filter(Boolean);
    // A name is what people type first: if the whole phrase is part of a name, show those and nothing else.
    const byName = q ? rows.filter(li => li.dataset.n.includes(q) || li.dataset.nc.includes(qc)) : [];
    let n = 0;
    rows.forEach(li => {
      const text = !q || (byName.length ? byName.includes(li) : toks.every(t => li.dataset.f.includes(t)));
      const ok = text && Object.keys(state).every(k => !state[k] || li.dataset[k] === state[k]);
      li.hidden = !ok; n += ok;
    });
    count.textContent = `${n} of ${rows.length}`;
    empty.hidden = n > 0;
    active.textContent = buttons.filter(b => b.dataset.v && b.getAttribute("aria-pressed") === "true").map(b => b.textContent).join(" · ");
  };
  const press = (key, v) => { state[key] = v; buttons.filter(b => b.dataset.lgFilter === key).forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === v))); };
  const reset = () => { input.value = ""; Object.keys(state).forEach(k => press(k, "")); run(); };

  buttons.forEach(b => b.addEventListener("click", () => { press(b.dataset.lgFilter, b.dataset.v); run(); }));
  input.addEventListener("input", run);
  $("[data-lg-reset]", root).addEventListener("click", () => { reset(); input.focus(); });
  if (matchMedia("(min-width: 761px)").matches) panel.open = true;

  // Bring the marked spot into view when an entry's map first becomes visible.
  const centre = d => { const view = $(".mapv-view", d), stage = $(".mapv-stage", d), mk = $(".mk", d); if (!view || !mk || d.dataset.centred) return; d.dataset.centred = "1";
    requestAnimationFrame(() => { view.scrollLeft = parseFloat(mk.style.left) / 100 * stage.offsetWidth - view.clientWidth / 2; view.scrollTop = parseFloat(mk.style.top) / 100 * stage.offsetHeight - view.clientHeight / 2; }); };
  $$("details.lg", root).forEach(d => d.addEventListener("toggle", () => {
    if (!d.open) return;
    centre(d);
    const id = d.id || d.parentElement.id;
    if (id && location.hash.slice(1) !== id) history.replaceState(null, "", "#" + id);
  }));

  // #suicune, #sinjoh: open that entry, clearing filters that would hide it.
  const go = () => {
    const el = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (!el || !root.contains(el)) return;
    const d = el.matches("details.lg") ? el : $(":scope > details.lg", el); if (!d) return;
    if (el.hidden) reset();
    d.open = true; el.scrollIntoView();
  };
  root.addEventListener("click", e => { const a = e.target.closest("a[data-lg-open]"); if (!a) return; e.preventDefault(); history.pushState(null, "", a.getAttribute("href")); go(); });
  addEventListener("hashchange", go);
  run(); go();
})();
