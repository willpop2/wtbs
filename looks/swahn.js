/* Swahn look: solid geometric forms filled with a tight dot halftone. Injects a
   hero (behind the masthead), a Farbteiler-style divider band, and a small
   composition swatch on every index row. All tagged .look-injected so the
   switcher can tear them down. */
window.__heroRender = window.__heroRender || {};
window.__heroRender['swahn'] = function () {
  var PAL = ['#d83a2b', '#f2b02e', '#3f9c48', '#2f6fb0', '#1f93a6', '#d24b86', '#e2661f'], PAPER = '#efe6d1';
  var DPR = Math.min(2, window.devicePixelRatio || 1), c, STEP = 3.6;
  function mb(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function shade(hex, dd) { var n = parseInt(hex.slice(1), 16), R = Math.max(0, Math.min(255, (n >> 16) + dd)), G = Math.max(0, Math.min(255, (n >> 8 & 255) + dd)), B = Math.max(0, Math.min(255, (n & 255) + dd)); return '#' + (1 << 24 | R << 16 | G << 8 | B).toString(16).slice(1); }
  function half(bx, by, bw, bh, col, rnd) { var st = STEP, rr = st * 0.66; for (var y = by - st; y < by + bh + st; y += st) { var row = Math.round((y - by) / st), ox = (row & 1) ? st * 0.5 : 0; for (var x = bx - st; x < bx + bw + st; x += st) { c.fillStyle = col; c.beginPath(); c.arc(x + ox + (rnd() - 0.5) * st * 0.2, y + (rnd() - 0.5) * st * 0.2, rr * (0.9 + rnd() * 0.2), 0, 7); c.fill(); } } }
  function clip(path, bx, by, bw, bh, col, rnd) { c.save(); c.beginPath(); path(); c.clip(); half(bx, by, bw, bh, col, rnd); c.restore(); }
  function disc(x, y, r0, col, rnd) { clip(function () { c.arc(x, y, r0, 0, 7); }, x - r0, y - r0, 2 * r0, 2 * r0, col, rnd); }
  function bar(x, y, w, h, ang, col, rnd) { c.save(); c.translate(x, y); c.rotate(ang); clip(function () { c.rect(-w / 2, -h / 2, w, h); }, -w / 2, -h / 2, w, h, col, rnd); c.restore(); }
  function iso(x, y, s, base, rnd) { var h = s * (0.9 + rnd() * 0.7);
    clip(function () { c.moveTo(x, y - s); c.lineTo(x + s, y - s * 0.5); c.lineTo(x, y); c.lineTo(x - s, y - s * 0.5); c.closePath(); }, x - s, y - s, 2 * s, s, shade(base, 28), rnd);
    clip(function () { c.moveTo(x, y); c.lineTo(x - s, y - s * 0.5); c.lineTo(x - s, y - s * 0.5 + h); c.lineTo(x, y + h); c.closePath(); }, x - s, y - s * 0.5, s, h + s, shade(base, -26), rnd);
    clip(function () { c.moveTo(x, y); c.lineTo(x + s, y - s * 0.5); c.lineTo(x + s, y - s * 0.5 + h); c.lineTo(x, y + h); c.closePath(); }, x, y - s * 0.5, s, h + s, base, rnd); }
  function ctx(cv, cssW, cssH) { cv.width = Math.max(1, cssW * DPR); cv.height = Math.max(1, cssH * DPR); c = cv.getContext('2d'); c.setTransform(DPR, 0, 0, DPR, 0, 0); c.fillStyle = PAPER; c.fillRect(0, 0, cssW, cssH); }
  function pick(rnd) { return PAL[Math.floor(rnd() * 7)]; }

  // hero behind the masthead
  var hero = document.querySelector('.hero');
  if (hero) {
    var cv = document.createElement('canvas'); cv.id = 'look-hero'; cv.className = 'look-injected';
    hero.insertBefore(cv, hero.firstChild);
    var r = hero.getBoundingClientRect(); ctx(cv, r.width, r.height); STEP = 3.6;
    var rnd = mb(Math.floor(Math.random() * 1e5)), count = Math.round(r.width * r.height / 9000);
    for (var i = 0; i < count; i++) { var t = rnd(), x = rnd() * r.width, y = rnd() * r.height, col = pick(rnd);
      if (t < 0.42) iso(x, y, (22 + rnd() * 30) * 1.4, col, rnd);
      else if (t < 0.76) disc(x, y, (16 + rnd() * 30) * 1.4, col, rnd);
      else bar(x, y, (50 + rnd() * 90) * 1.4, (14 + rnd() * 16) * 1.4, (rnd() - 0.5) * 1.6, col, rnd); }
  }

  var rows = document.querySelectorAll('.rows .r');

  // Farbteiler divider band, on the index only (below the hero)
  if (hero && rows.length) {
    var band = document.createElement('div'); band.className = 'look-divider look-injected';
    var bcv = document.createElement('canvas'); band.appendChild(bcv);
    hero.parentNode.insertBefore(band, hero.nextSibling);
    var W = band.getBoundingClientRect().width || 1000, Hb = 26; bcv.style.width = W + 'px'; bcv.style.height = Hb + 'px';
    ctx(bcv, W, Hb); STEP = 2.4; var rb = mb(7);
    for (var x2 = 0; x2 < W;) { var w = Hb * (0.7 + rb() * 1.3); bar(x2 + w / 2, Hb * 0.5, w, Hb * 0.72, 0, pick(rb), rb); x2 += w + Hb * 0.12; }
  }

  // a small composition swatch on each index row
  for (var k = 0; k < rows.length; k++) {
    var sc = document.createElement('canvas'); sc.className = 'look-swatch look-injected';
    rows[k].insertBefore(sc, rows[k].firstChild);
    ctx(sc, 38, 34); STEP = 2.0; var rs = mb(k * 97 + 11);
    bar(19, 15 + rs() * 5, 36, 15, (rs() - 0.5) * 0.4, pick(rs), rs);
    iso(13, 26, 11, pick(rs), rs);
    disc(24, 12, 10, pick(rs), rs);
  }
  window.__heroStop = function () {};
};
