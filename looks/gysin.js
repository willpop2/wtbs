/* Gysin hero: an animated ASCII character field rendered behind the masthead.
   Calm/dim palette so the wordmark stays legible over it. */
window.__heroRender = window.__heroRender || {};
window.__heroRender['gysin'] = function () {
  var hero = document.querySelector('.hero'); if (!hero) return;
  var cv = document.createElement('canvas'); cv.id = 'look-hero'; hero.insertBefore(cv, hero.firstChild);
  var RAMP = " .`':,-~+=*ilcvxznut1jfry523460%#&8B@WM";
  var DIM = '#3b3e44', FG = '#7f847a', CY = '#49cbd6', RD = '#ff5b52', BG = '#0b0c0f';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var c, W, H, cw, ch = 16, raf;
  function fit() {
    var r = hero.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.max(1, r.width * d); cv.height = Math.max(1, r.height * d);
    c = cv.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0); W = r.width; H = r.height;
    c.font = '14px ' + '"Space Mono",monospace'; c.textBaseline = 'top'; cw = c.measureText('M').width || 8.4;
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
  window.__heroStop = function () { if (raf) cancelAnimationFrame(raf); window.removeEventListener('resize', onR); };
};
