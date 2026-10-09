/* DexNav manual: whole-number scaling for the screenshots, and the enlarged view. No dependencies. */
(() => {
  const W = 240, H = 160, shots = [...document.querySelectorAll(".dn-shot")];
  if (!shots.length) return;
  const dpr = () => window.devicePixelRatio || 1;
  // Largest width that maps every game pixel to a whole number of device pixels.
  const snap = avail => { const k = Math.floor(avail * dpr() / W); return k >= 1 ? k * W / dpr() : avail; };
  const fit = () => shots.forEach(b => {
    b.style.width = "";
    const max = parseFloat(getComputedStyle(b).width);
    if (max > 0) b.style.width = snap(max) + "px";
  });
  fit(); addEventListener("resize", fit);

  const dlg = document.querySelector("dialog.dn-zoom");
  if (!dlg || !dlg.showModal) return;
  const img = dlg.querySelector("img"), cap = dlg.querySelector("figcaption"), count = dlg.querySelector(".dn-zcount");
  let at = 0;
  const size = () => {
    const w = snap(Math.min(innerWidth - 24, (innerHeight - 170) * W / H));
    img.style.width = Math.max(w, W / dpr()) + "px"; img.style.height = "auto";
  };
  const show = i => {
    at = (i + shots.length) % shots.length;
    const src = shots[at].querySelector("img"), fc = shots[at].parentElement.querySelector("figcaption");
    img.src = src.currentSrc || src.src; img.alt = src.alt;
    cap.textContent = fc && fc.textContent.trim() ? fc.textContent : src.alt;
    count.textContent = (at + 1) + " / " + shots.length;
    size();
  };
  shots.forEach((b, i) => b.addEventListener("click", () => { show(i); dlg.showModal(); }));
  dlg.querySelector("[data-zclose]").addEventListener("click", () => dlg.close());
  dlg.querySelector("[data-zprev]").addEventListener("click", () => show(at - 1));
  dlg.querySelector("[data-znext]").addEventListener("click", () => show(at + 1));
  dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener("keydown", e => { if (e.key === "ArrowLeft") show(at - 1); else if (e.key === "ArrowRight") show(at + 1); });
  dlg.addEventListener("close", () => shots[at].focus());
  addEventListener("resize", () => { if (dlg.open) size(); });
})();
