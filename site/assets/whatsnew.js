/* What's new: the facing switch of the overworld gallery. Without it the gallery shows the front view. */
(() => {
  const seg = document.querySelector("[data-wn-seg]"), grid = document.querySelector("[data-wn-ow]");
  if (!seg || !grid) return;
  seg.addEventListener("click", e => {
    const b = e.target.closest("[data-wn-face]");
    if (!b) return;
    grid.style.setProperty("--f", b.dataset.wnFace);
    seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
  });
})();
