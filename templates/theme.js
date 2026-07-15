/* WTBS "Look" switcher. Runtime themes: each look is a stylesheet (looks/<id>.css,
   scoped under html[data-look=<id>]) plus an optional generative hero (looks/<id>.js).
   Brutalist is the default and needs no assets. Choice is saved per browser and
   applied before paint by the inline snippet in <head>. */
(function () {
  var LOOKS = [
    { id: 'brutalist', name: 'Brutalist' },
    { id: 'swahn',     name: 'Erik Swahn' },
    { id: 'gysin',     name: 'Andreas Gysin' },
    { id: 'zancan',    name: 'Zancan' },
    { id: 'jeres',     name: 'Jeres' }
  ];
  var ROOT = ((document.currentScript && document.currentScript.src) || '').replace(/theme\.js.*$/, '');
  function cur() { try { return localStorage.getItem('wtbs-look') || 'brutalist'; } catch (e) { return 'brutalist'; } }

  var loaded = {};
  function loadJS(id, cb) {
    if (loaded[id]) return cb();
    var s = document.createElement('script');
    s.src = ROOT + 'looks/' + id + '.js';
    s.onload = function () { loaded[id] = 1; cb(); };
    s.onerror = cb;
    document.head.appendChild(s);
  }
  function setCss(id) {
    var link = document.getElementById('look-css');
    if (id === 'brutalist') { if (link) link.remove(); return; }
    if (!link) { link = document.createElement('link'); link.rel = 'stylesheet'; link.id = 'look-css'; document.head.appendChild(link); }
    link.href = ROOT + 'looks/' + id + '.css';
  }
  function applyHero(id) {
    if (window.__heroStop) { try { window.__heroStop(); } catch (e) {} window.__heroStop = null; }
    var inj = document.querySelectorAll('.look-injected');   // heroes, dividers, swatches, ...
    for (var i = 0; i < inj.length; i++) inj[i].remove();
    if (id === 'brutalist') return;
    loadJS(id, function () { var r = window.__heroRender && window.__heroRender[id]; if (r) r(ROOT); });
  }
  function setLook(id) {
    try { localStorage.setItem('wtbs-look', id); } catch (e) {}
    var r = document.documentElement;
    if (id === 'brutalist') r.removeAttribute('data-look'); else r.setAttribute('data-look', id);
    setCss(id); applyHero(id); render();
  }

  var btn, menu;
  function render() {
    var c = cur();
    if (menu) Array.prototype.forEach.call(menu.children, function (li) {
      li.setAttribute('aria-current', li.dataset.id === c ? 'true' : 'false');
    });
  }
  function build() {
    var links = document.querySelector('.nav .links'); if (!links) return;
    var wrap = document.createElement('div'); wrap.className = 'lookswitch';
    btn = document.createElement('button'); btn.type = 'button'; btn.className = 'look-btn';
    btn.setAttribute('aria-haspopup', 'true'); btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Change the look');
    btn.appendChild(document.createTextNode('Look'));
    var car = document.createElement('span'); car.className = 'look-car'; car.textContent = '▾'; btn.appendChild(car);
    menu = document.createElement('ul'); menu.className = 'look-menu'; menu.hidden = true;
    LOOKS.forEach(function (l) {
      var li = document.createElement('li'); li.textContent = l.name; li.dataset.id = l.id; li.tabIndex = 0; li.setAttribute('role', 'button');
      li.addEventListener('click', function () { setLook(l.id); close(); });
      li.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setLook(l.id); close(); } });
      menu.appendChild(li);
    });
    function open() { menu.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
    function close() { menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
    btn.addEventListener('click', function (e) { e.stopPropagation(); menu.hidden ? open() : close(); });
    document.addEventListener('click', function (e) { if (!wrap.contains(e.target)) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    wrap.appendChild(btn); wrap.appendChild(menu);
    links.insertBefore(wrap, links.querySelector('#surprise') || null);
    render();
  }
  function init() { build(); applyHero(cur()); }
  if (document.readyState !== 'loading') init(); else document.addEventListener('DOMContentLoaded', init);
})();
