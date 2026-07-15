/* Swahn hero: solid geometric forms (iso-blocks, discs, bars) filled with a tight
   dot halftone — reads solid at a distance, marks up close. Static composition. */
window.__heroRender = window.__heroRender || {};
window.__heroRender['swahn'] = function () {
  var hero = document.querySelector('.hero'); if (!hero) return;
  var cv = document.createElement('canvas'); cv.id = 'look-hero'; hero.insertBefore(cv, hero.firstChild);
  var PAL = ['#d83a2b', '#f2b02e', '#3f9c48', '#2f6fb0', '#1f93a6', '#d24b86', '#e2661f'], PAPER = '#efe6d1', STEP = 3.6;
  var d = Math.min(2, window.devicePixelRatio || 1), r = hero.getBoundingClientRect();
  cv.width = Math.max(1, r.width * d); cv.height = Math.max(1, r.height * d);
  var c = cv.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0); var W = r.width, H = r.height;
  function mb(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  var rnd = mb(Math.floor(Math.random() * 1e5));
  function shade(hex, dd) { var n = parseInt(hex.slice(1), 16), R = Math.max(0, Math.min(255, (n >> 16) + dd)), G = Math.max(0, Math.min(255, (n >> 8 & 255) + dd)), B = Math.max(0, Math.min(255, (n & 255) + dd)); return '#' + (1 << 24 | R << 16 | G << 8 | B).toString(16).slice(1); }
  function half(bx, by, bw, bh, col) { var st = STEP, rr = st * 0.66; for (var y = by - st; y < by + bh + st; y += st) { var row = Math.round((y - by) / st), ox = (row & 1) ? st * 0.5 : 0; for (var x = bx - st; x < bx + bw + st; x += st) { c.fillStyle = col; c.beginPath(); c.arc(x + ox + (rnd() - 0.5) * st * 0.2, y + (rnd() - 0.5) * st * 0.2, rr * (0.9 + rnd() * 0.2), 0, 7); c.fill(); } } }
  function clip(path, bx, by, bw, bh, col) { c.save(); c.beginPath(); path(); c.clip(); half(bx, by, bw, bh, col); c.restore(); }
  function disc(x, y, r0, col) { clip(function () { c.arc(x, y, r0, 0, 7); }, x - r0, y - r0, 2 * r0, 2 * r0, col); }
  function bar(x, y, w, h, ang, col) { c.save(); c.translate(x, y); c.rotate(ang); clip(function () { c.rect(-w / 2, -h / 2, w, h); }, -w / 2, -h / 2, w, h, col); c.restore(); }
  function iso(x, y, s, base) { var h = s * (0.9 + rnd() * 0.7);
    clip(function () { c.moveTo(x, y - s); c.lineTo(x + s, y - s * 0.5); c.lineTo(x, y); c.lineTo(x - s, y - s * 0.5); c.closePath(); }, x - s, y - s, 2 * s, s, shade(base, 28));
    clip(function () { c.moveTo(x, y); c.lineTo(x - s, y - s * 0.5); c.lineTo(x - s, y - s * 0.5 + h); c.lineTo(x, y + h); c.closePath(); }, x - s, y - s * 0.5, s, h + s, shade(base, -26));
    clip(function () { c.moveTo(x, y); c.lineTo(x + s, y - s * 0.5); c.lineTo(x + s, y - s * 0.5 + h); c.lineTo(x, y + h); c.closePath(); }, x, y - s * 0.5, s, h + s, base); }
  c.fillStyle = PAPER; c.fillRect(0, 0, W, H);
  var count = Math.round(W * H / 9000);
  for (var i = 0; i < count; i++) { var t = rnd(), x = rnd() * W, y = rnd() * H, col = PAL[Math.floor(rnd() * 7)];
    if (t < 0.42) iso(x, y, (22 + rnd() * 30) * 1.4, col);
    else if (t < 0.76) disc(x, y, (16 + rnd() * 30) * 1.4, col);
    else bar(x, y, (50 + rnd() * 90) * 1.4, (14 + rnd() * 16) * 1.4, (rnd() - 0.5) * 1.6, col); }
  window.__heroStop = function () {};
};
