(function () {
  var toggle = document.querySelector('.nav__toggle');
  var links = document.getElementById('nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  // Column headers for the ecosystem map on narrow screens (grid collapses to one column).
  var heads = Array.prototype.map.call(document.querySelectorAll('.ecomap__colhead'), function (h) { return h.textContent; });
  document.querySelectorAll('.ecomap__row:not(.ecomap__row--head)').forEach(function (row) {
    row.querySelectorAll('.ecomap__cell').forEach(function (cell, i) { cell.setAttribute('data-col', heads[i] || ''); });
  });
  // Re-layout Plotly charts after a table view opens (container width may change) and on nav toggle.
  document.querySelectorAll('details.chart__table').forEach(function (d) {
    d.addEventListener('toggle', function () {
      var plot = d.parentElement.querySelector('.plotly-graph-div');
      if (plot && window.Plotly) { window.Plotly.Plots.resize(plot); }
    });
  });
})();
