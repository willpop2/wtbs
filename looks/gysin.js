/* Gysin hero: an animated ASCII character field behind the masthead, plus a
   box-drawing/ASCII divider band on the index. All tagged .look-injected. */
window.__heroRender = window.__heroRender || {};
window.__heroRender['gysin'] = function () {
  var hero = document.querySelector('.hero'); if (!hero) return;
  var DPR = Math.min(2, window.devicePixelRatio || 1);
  var RAMP = " .`':,-~+=*ilcvxznut1jfry523460%#&8B@WM";
  var DIM = '#3b3e44', FG = '#7f847a', CY = '#49cbd6', RD = '#ff5b52', BG = '#0b0c0f';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function mb(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  // animated ASCII field
  var cv = document.createElement('canvas'); cv.id = 'look-hero'; cv.className = 'look-injected';
  hero.insertBefore(cv, hero.firstChild);
  var c, W, H, cw, ch = 16, raf;
  function fit() {
    var r = hero.getBoundingClientRect();
    cv.width = Math.max(1, r.width * DPR); cv.height = Math.max(1, r.height * DPR);
    c = cv.getContext('2d'); c.setTransform(DPR, 0, 0, DPR, 0, 0); W = r.width; H = r.height;
    c.font = '14px "Space Mono",monospace'; c.textBaseline = 'top'; cw = c.measureText('M').width || 8.4;
  }
  fit();
  function frame(t) {
    var tt = t * 0.0009, cols = Math.ceil(W / cw), rows = Math.ceil(H / ch);
    c.fillStyle = BG; c.fillRect(0, 0, W, H);
    for (var y = 0; y < rows; y++) for (var x = 0; x < cols; x++) {
      var v = (Math.sin(x * 0.28 + tt) + Math.sin(y * 0.42 - tt * 0.7) + Math.sin((x + y) * 0.19 + tt * 0.5)) / 3;
      var n = (v + 1) / 2, chn = RAMP[Math.floor(n * (RAMP.length - 1))];
      if (chn === ' ') continue;
      c.fillStyle = n > 0.85 ? CY : (n > 0.8 ? FG : (n < 0.12 ? RD : DIM));
      c.fillText(chn, x * cw, y * ch);
    }
  }
  function loop(t) { frame(t); raf = requestAnimationFrame(loop); }
  if (reduce) frame(0); else raf = requestAnimationFrame(loop);
  var onR = function () { fit(); if (reduce) frame(0); };
  window.addEventListener('resize', onR);

  // box-drawing / ASCII divider band on the index
  if (document.querySelector('.rows')) {
    var band = document.createElement('div'); band.className = 'look-divider look-injected';
    var bcv = document.createElement('canvas'); band.appendChild(bcv);
    hero.parentNode.insertBefore(band, hero.nextSibling);
    var bw = band.getBoundingClientRect().width || 1000, bh = 22; bcv.style.width = bw + 'px'; bcv.style.height = bh + 'px';
    bcv.width = bw * DPR; bcv.height = bh * DPR; var bc = bcv.getContext('2d'); bc.setTransform(DPR, 0, 0, DPR, 0, 0);
    bc.fillStyle = BG; bc.fillRect(0, 0, bw, bh); bc.font = '14px "Space Mono",monospace'; bc.textBaseline = 'middle';
    var CH = "─│┌┐└┘├┤┬┴┼═║╬▓▒░+*=.-", rb = mb(3), bcw = bc.measureText('M').width || 8.4;
    for (var bx = 0; bx < bw; bx += bcw) { bc.fillStyle = rb() < 0.12 ? CY : (rb() < 0.2 ? RD : DIM); bc.fillText(CH[Math.floor(rb() * CH.length)], bx, bh / 2); }
  }

  window.__heroStop = function () { if (raf) cancelAnimationFrame(raf); window.removeEventListener('resize', onR); };
};
