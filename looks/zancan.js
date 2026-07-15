/* Zancan hero: generative ink vines + woody branches with leaves, grown over a
   fine grid, behind the masthead. Grown synchronously (static). */
window.__heroRender = window.__heroRender || {};
window.__heroRender['zancan'] = function () {
  var hero = document.querySelector('.hero'); if (!hero) return;
  var cv = document.createElement('canvas'); cv.id = 'look-hero'; cv.className = 'look-injected'; hero.insertBefore(cv, hero.firstChild);
  var PAPER = '#f2efe4', INK = '#22241c', GRID = '#d9dbcc', MOSS = '#4b6043', PINK = '#dd7a9e', YELLOW = '#e8bf3e';
  var d = Math.min(2, window.devicePixelRatio || 1), r = hero.getBoundingClientRect();
  cv.width = Math.max(1, r.width * d); cv.height = Math.max(1, r.height * d);
  var c = cv.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0); var W = r.width, H = r.height;
  function mb(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  var rnd = mb(Math.floor(Math.random() * 1e5));
  function leaf(x, y, ang, size) { c.save(); c.translate(x, y); c.rotate(ang); c.beginPath(); c.moveTo(0, 0); c.quadraticCurveTo(size * 0.55, -size * 0.42, size, 0); c.quadraticCurveTo(size * 0.55, size * 0.42, 0, 0); c.closePath(); var f = rnd(); c.fillStyle = f < 0.16 ? MOSS : (f < 0.4 ? 'rgba(34,36,28,0.5)' : PAPER); c.fill(); c.strokeStyle = INK; c.lineWidth = 0.9; c.stroke(); c.beginPath(); c.moveTo(0, 0); c.lineTo(size * 0.9, 0); c.stroke(); c.restore(); }
  function twig(x, y, ang, len) { var ex = x + Math.cos(ang) * len, ey = y + Math.sin(ang) * len; c.strokeStyle = INK; c.lineWidth = 0.9; c.beginPath(); c.moveTo(x, y); c.lineTo(ex, ey); c.stroke(); if (rnd() < 0.5) { c.beginPath(); c.arc(ex, ey, 1.4, 0, 7); c.fillStyle = rnd() < 0.5 ? PINK : YELLOW; c.fill(); c.strokeStyle = INK; c.lineWidth = 0.6; c.stroke(); } }
  function bloom(x, y, col) { for (var i = 0; i < 5; i++) { var a = i / 5 * 6.283; c.beginPath(); c.ellipse(x + Math.cos(a) * 2.6, y + Math.sin(a) * 2.6, 2.4, 1.4, a, 0, 7); c.fillStyle = col; c.fill(); c.strokeStyle = INK; c.lineWidth = 0.5; c.stroke(); } c.beginPath(); c.arc(x, y, 1.5, 0, 7); c.fillStyle = INK; c.fill(); }
  c.fillStyle = PAPER; c.fillRect(0, 0, W, H);
  c.strokeStyle = GRID; c.lineWidth = 1; var g = 22, gx, gy;
  for (gx = 0; gx < W; gx += g) { c.beginPath(); c.moveTo(gx, 0); c.lineTo(gx, H); c.stroke(); }
  for (gy = 0; gy < H; gy += g) { c.beginPath(); c.moveTo(0, gy); c.lineTo(W, gy); c.stroke(); }
  var tips = [], cap = Math.round(W * H / 135), drawn = 0, nb = Math.round(W / 78) + 3;
  function spawn(x, y, a, type) { var life = type === 'branch' ? (120 + rnd() * 130) : (85 + rnd() * 105); tips.push({ x: x, y: y, a: a, life: life, life0: life, gen: 0, type: type, w: type === 'branch' ? (2.8 + rnd() * 2) : 1.6 }); }
  for (var i = 0; i < nb; i++) spawn(rnd() * W, H + 4, -Math.PI / 2 + (rnd() - 0.5) * 0.5, rnd() < 0.42 ? 'branch' : 'vine');
  for (var j = 0; j < Math.max(3, nb - 3); j++) spawn(rnd() * W, -4, Math.PI / 2 + (rnd() - 0.5) * 0.6, rnd() < 0.28 ? 'branch' : 'vine');
  function step() {
    var alive = false;
    for (var k = 0; k < tips.length; k++) { var t = tips[k]; if (t.life <= 0) continue; alive = true;
      var br = t.type === 'branch', seg = br ? 4.6 : 3.2, nx = t.x + Math.cos(t.a) * seg, ny = t.y + Math.sin(t.a) * seg;
      c.strokeStyle = INK; c.lineWidth = br ? Math.max(0.8, t.w * (t.life / t.life0)) : Math.max(0.7, 1.5 - t.gen * 0.28);
      c.beginPath(); c.moveTo(t.x, t.y); c.lineTo(nx, ny); c.stroke();
      t.x = nx; t.y = ny; t.a += (rnd() - 0.5) * (br ? 0.2 : 0.5); t.a += (t.y > H * 0.5 ? -0.02 : 0.006); t.life--; drawn++;
      if (br) { if (rnd() < 0.07) leaf(nx, ny, t.a + (rnd() < 0.5 ? 1.3 : -1.3), 3.5 + rnd() * 4); if (rnd() < 0.05) twig(nx, ny, t.a + (rnd() < 0.5 ? 1 : -1), 5 + rnd() * 8); if (t.life < t.life0 * 0.45 && rnd() < 0.03) bloom(nx, ny, rnd() < 0.5 ? PINK : YELLOW); if (rnd() < 0.075 && t.gen < 4 && drawn < cap) tips.push({ x: nx, y: ny, a: t.a + (rnd() < 0.5 ? 0.6 : -0.6) + (rnd() - 0.5) * 0.3, life: t.life * 0.72, life0: t.life0, gen: t.gen + 1, type: 'branch', w: t.w * 0.6 }); }
      else { if (rnd() < 0.22) leaf(nx, ny, t.a + (rnd() < 0.5 ? 1.25 : -1.25), 4 + rnd() * 5.5); else if (rnd() < 0.035) bloom(nx, ny, rnd() < 0.5 ? PINK : YELLOW); if (rnd() < 0.085 && t.gen < 4 && drawn < cap) tips.push({ x: nx, y: ny, a: t.a + (rnd() < 0.5 ? 0.75 : -0.75), life: t.life * 0.62, life0: t.life0, gen: t.gen + 1, type: 'vine', w: 1.6 }); }
      if (t.x < -10 || t.x > W + 10 || t.y < -10 || t.y > H + 10 || drawn > cap) t.life = 0;
    }
    return alive && drawn < cap;
  }
  var guard = 0; while (step() && guard++ < 4000) {}

  // vine divider band on the index
  if (document.querySelector('.rows')) {
    var band = document.createElement('div'); band.className = 'look-divider look-injected';
    var bcv = document.createElement('canvas'); band.appendChild(bcv);
    hero.parentNode.insertBefore(band, hero.nextSibling);
    var bw = band.getBoundingClientRect().width || 1000, bh = 24; bcv.style.width = bw + 'px'; bcv.style.height = bh + 'px';
    bcv.width = bw * d; bcv.height = bh * d; c = bcv.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0);
    c.fillStyle = PAPER; c.fillRect(0, 0, bw, bh);
    var y0 = bh * 0.5, x; c.strokeStyle = INK; c.lineWidth = 1.2; c.beginPath(); c.moveTo(0, y0);
    for (x = 0; x < bw; x += 6) c.lineTo(x, y0 + Math.sin(x * 0.06) * bh * 0.22); c.stroke();
    for (x = 4; x < bw; x += 8) { var yy = y0 + Math.sin(x * 0.06) * bh * 0.22; if (rnd() < 0.4) leaf(x, yy, (rnd() < 0.5 ? 1 : -1) * 1.3, 4 + rnd() * 3); if (rnd() < 0.09) bloom(x, yy, rnd() < 0.5 ? PINK : YELLOW); }
  }
  window.__heroStop = function () {};
};
