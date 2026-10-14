(function () {
  // Mobile menu
  var toggle = document.querySelector('.nav__toggle');
  var links = document.getElementById('nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Column headers for the source map when it collapses to one column
  var heads = Array.prototype.map.call(document.querySelectorAll('.ecomap__colhead'), function (h) { return h.textContent; });
  document.querySelectorAll('.ecomap__row:not(.ecomap__row--head)').forEach(function (row) {
    row.querySelectorAll('.ecomap__cell').forEach(function (cell, i) { cell.setAttribute('data-col', heads[i] || ''); });
  });

  // "Table" link under a chart opens its table view
  document.querySelectorAll('.js-open-table').forEach(function (a) {
    a.addEventListener('click', function () {
      var d = document.querySelector(a.getAttribute('href'));
      if (d) { d.open = true; }
    });
  });

  // Charts fill their card: resize once fonts and layout settle
  function resizeAll() {
    if (!window.Plotly) { return; }
    document.querySelectorAll('.chart__plot .plotly-graph-div').forEach(function (g) { window.Plotly.Plots.resize(g); });
  }
  window.addEventListener('load', resizeAll);
  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(resizeAll); }

  // Presenter keys: N = next chart or section, P = previous. Each stop is aligned to the top of the screen.
  function stops() {
    return Array.prototype.slice.call(document.querySelectorAll('.chart, .profile, .section-head, .callouts, .prose'));
  }
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) { return; }
    var tag = (e.target && e.target.tagName) || '';
    if (/INPUT|TEXTAREA|SELECT/.test(tag)) { return; }
    var key = e.key.toLowerCase();
    if (key !== 'n' && key !== 'p') { return; }
    var list = stops();
    var target = null;
    if (key === 'n') {
      target = list.find(function (el) { return el.getBoundingClientRect().top > 24; });
    } else {
      for (var i = list.length - 1; i >= 0; i--) {
        if (list[i].getBoundingClientRect().top < -24) { target = list[i]; break; }
      }
    }
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
})();
