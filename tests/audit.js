(() => {
  const px = v => parseFloat(v) || 0;
  const parse = c => {
    const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(",").map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const bgOf = el => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.6) return c;
      n = n.parentElement;
    }
    return parse(getComputedStyle(document.body).backgroundColor) || { r: 0, g: 0, b: 0, a: 1 };
  };
  const contrast = (fg, bg) => {
    const L1 = lum(fg), L2 = lum(bg);
    return +(((Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)).toFixed(2));
  };
  const visible = el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && r.bottom > 0 && r.top < innerHeight * 3;
  };

  const smallTargets = [], tinyText = [], lowContrast = [];
  const radii = new Set(), borders = new Set(), shadows = new Set(), fonts = new Set();

  document.querySelectorAll("button, a, input, textarea, [role=button]").forEach(el => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (Math.min(r.width, r.height) < 44)
      smallTargets.push({ tag: el.tagName, id: el.id || "", txt: (el.textContent || "").trim().slice(0, 10),
        w: Math.round(r.width), h: Math.round(r.height) });
  });

  document.querySelectorAll("body *").forEach(el => {
    if (!visible(el)) return;
    const s = getComputedStyle(el);
    radii.add(s.borderRadius); borders.add(s.borderTopWidth); shadows.add(s.boxShadow.slice(0, 44));
    if (el.children.length === 0 && (el.textContent || "").trim()) {
      const fs = px(s.fontSize);
      fonts.add(Math.round(fs));
      if (fs < 12) tinyText.push({ tag: el.tagName, id: el.id || "", txt: el.textContent.trim().slice(0, 14), size: Math.round(fs) });
      const fg = parse(s.color), bg = bgOf(el);
      if (fg && bg) {
        const c = contrast(fg, bg);
        if (c < 4.5) lowContrast.push({ id: el.id || "", txt: el.textContent.trim().slice(0, 16), ratio: c, size: Math.round(fs) });
      }
    }
  });

  return JSON.stringify({
    view: document.body.dataset.view,
    smallTargets, tinyText, lowContrast: lowContrast.slice(0, 14),
    radii: [...radii].slice(0, 10), borders: [...borders], shadows: [...shadows].filter(Boolean).slice(0, 8),
    fontSizes: [...fonts].sort((a, b) => a - b)
  });
})()
