/* Jeres "Coronado": soft luminous translucent diagonal color-planes with a
   light gaussian haze, plus a few crisp vertical color bars. Injects a hero, a
   gradient divider band, and a mini composition swatch per index row. Static. */
window.__heroRender = window.__heroRender || {};
window.__heroRender['jeres'] = function () {
  var PAL = ['#e5389a', '#c13bd6', '#7b5cff', '#2f9fd6', '#22c0c0', '#ff7a3c', '#ff4d6d', '#9d4edd', '#3fd0a0'];
  var DPR = Math.min(2, window.devicePixelRatio || 1), c;
  function mb(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function hexA(hex, a) { var n = parseInt(hex.slice(1), 16); return 'rgba(' + (n >> 16) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')'; }
  function pick(rnd) { return PAL[Math.floor(rnd() * PAL.length)]; }
  function ctx(cv, W, H) { cv.width = Math.max(1, W * DPR); cv.height = Math.max(1, H * DPR); c = cv.getContext('2d'); c.setTransform(DPR, 0, 0, DPR, 0, 0); var g = c.createLinearGradient(0, 0, W, H); g.addColorStop(0, '#efe7f6'); g.addColorStop(0.5, '#f3e6ef'); g.addColorStop(1, '#e9e6f5'); c.fillStyle = g; c.fillRect(0, 0, W, H); }
  function plane(W, H, rnd, alpha) {
    var ang = rnd() < 0.75 ? (Math.PI * 0.22 + (rnd() - 0.5) * 0.6) : (rnd() * Math.PI);
    var cx = rnd() * W, cy = rnd() * H, len = (0.7 + rnd() * 0.9) * Math.max(W, H), wid = (0.06 + rnd() * 0.3) * Math.min(W, H);
    var a = pick(rnd), b = pick(rnd);
    c.save(); c.translate(cx, cy); c.rotate(ang);
    var g = c.createLinearGradient(0, -wid / 2, 0, wid / 2);
    g.addColorStop(0, hexA(a, 0)); g.addColorStop(0.5, hexA(a, alpha)); g.addColorStop(1, hexA(b, 0));
    c.fillStyle = g; c.fillRect(-len / 2, -wid / 2, len, wid); c.restore();
  }
  function bar(W, H, rnd) {
    var x = rnd() * W, w = (0.02 + rnd() * 0.055) * W, y = H * (0.35 + rnd() * 0.3), a = pick(rnd);
    var g = c.createLinearGradient(0, y, 0, H); g.addColorStop(0, hexA(a, 0)); g.addColorStop(0.3, hexA(a, 0.55)); g.addColorStop(1, hexA(a, 0.72));
    c.fillStyle = g; c.fillRect(x, y, w, H - y);
  }
  function compose(W, H, seed, planeN, alpha, blur, barN) {
    var rnd = mb(seed);
    if (c.filter !== undefined) c.filter = 'blur(' + blur + 'px)';
    for (var i = 0; i < planeN; i++) plane(W, H, rnd, alpha);
    if (c.filter !== undefined) c.filter = 'none';
    for (var j = 0; j < barN; j++) bar(W, H, rnd);
  }

  // hero
  var hero = document.querySelector('.hero');
  if (hero) {
    var cv = document.createElement('canvas'); cv.id = 'look-hero'; cv.className = 'look-injected';
    hero.insertBefore(cv, hero.firstChild);
    var r = hero.getBoundingClientRect(); ctx(cv, r.width, r.height);
    compose(r.width, r.height, Math.floor(Math.random() * 1e5), 16, 0.4, 8, 5);
  }

  // Coronado divider band on the index
  if (hero && document.querySelector('.rows')) {
    var band = document.createElement('div'); band.className = 'look-divider look-injected';
    var bcv = document.createElement('canvas'); band.appendChild(bcv);
    hero.parentNode.insertBefore(band, hero.nextSibling);
    var bw = band.getBoundingClientRect().width || 1000, bh = 26; bcv.style.width = bw + 'px'; bcv.style.height = bh + 'px';
    ctx(bcv, bw, bh); var rb = mb(9), gg = c.createLinearGradient(0, 0, bw, 0);
    for (var s = 0; s <= 6; s++) gg.addColorStop(s / 6, hexA(pick(rb), 0.72));
    c.fillStyle = gg; c.fillRect(0, 0, bw, bh);
    if (c.filter !== undefined) c.filter = 'blur(3px)';
    for (var k = 0; k < 6; k++) plane(bw, bh, rb, 0.5);
    if (c.filter !== undefined) c.filter = 'none';
  }

  // per-row swatch
  var rows = document.querySelectorAll('.rows .r');
  for (var m = 0; m < rows.length; m++) {
    var sc = document.createElement('canvas'); sc.className = 'look-swatch look-injected';
    rows[m].insertBefore(sc, rows[m].firstChild);
    ctx(sc, 38, 34); compose(38, 34, m * 131 + 7, 5, 0.5, 2, 1);
  }
  window.__heroStop = function () {};
};
