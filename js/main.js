/* ============================================
   SIGNAL PIRATE — Main JavaScript
   Scroll animations, typing effect, counters
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initTypingEffect();
  initScrollAnimations();
  initCounterAnimations();
});

/* ---- Theme Toggle ---- */
function getTheme() {
  // 1) URL param (funziona sempre, anche file://)
  if (location.search.indexOf('t=l') > -1) return 'light';
  if (location.search.indexOf('t=d') > -1) return 'dark';
  // 2) localStorage (funziona su HTTP)
  try { var s = localStorage.getItem('theme'); if (s) return s; } catch(e) {}
  return 'dark';
}

function tagLinks(theme) {
  var code = theme === 'light' ? 'l' : 'd';
  document.querySelectorAll('a[href]').forEach(function(a) {
    var h = a.getAttribute('href');
    if (!h || h.charAt(0) === '#' || h.indexOf('://') > -1) return;
    // strip old param
    h = h.replace(/[?&]t=[ld]/g, '').replace(/\?$/, '');
    // split path and hash: ?t= must go before #
    var hash = '';
    var hi = h.indexOf('#');
    if (hi > -1) { hash = h.slice(hi); h = h.slice(0, hi); }
    var sep = h.indexOf('?') > -1 ? '&' : '?';
    a.setAttribute('href', h + sep + 't=' + code + hash);
  });
}

function initThemeToggle() {
  var theme = getTheme();
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem('theme', theme); } catch(e) {}
  tagLinks(theme);

  var btn = document.getElementById('theme-toggle');
  if (!btn) return;

  btn.addEventListener('click', function() {
    var next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch(e) {}
    tagLinks(next);
    updateChartColors();
  });
}

function updateChartColors() {
  if (typeof Chart === 'undefined') return;
  var style = getComputedStyle(document.documentElement);
  var textColor = style.getPropertyValue('--chart-text').trim();
  var gridColor = style.getPropertyValue('--chart-grid').trim();

  Object.values(Chart.instances).forEach(function(chart) {
    if (chart.options.scales) {
      Object.values(chart.options.scales).forEach(function(scale) {
        if (scale.ticks) scale.ticks.color = textColor;
        if (scale.grid) scale.grid.color = gridColor;
        if (scale.title) scale.title.color = textColor;
        if (scale.angleLines) scale.angleLines.color = gridColor;
        if (scale.pointLabels) scale.pointLabels.color = textColor;
      });
    }
    if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
      chart.options.plugins.legend.labels.color = textColor;
    }
    chart.update();
  });
}

/* ---- Typing Effect ---- */
function initTypingEffect() {
  const el = document.getElementById('typing-text');
  if (!el) return;

  const text = 'Laboratorio di un pirata.';
  let i = 0;

  function type() {
    if (i < text.length) {
      el.textContent += text.charAt(i);
      i++;
      setTimeout(type, 50 + Math.random() * 40);
    }
  }

  setTimeout(type, 800);
}

/* ---- Scroll Animations (Intersection Observer) ---- */
function initScrollAnimations() {
  const observerOptions = {
    root: null,
    rootMargin: '0px 0px -60px 0px',
    threshold: 0.1
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // Don't unobserve — keep class even if scrolling away
      }
    });
  }, observerOptions);

  // Observe article cards
  document.querySelectorAll('.article-card').forEach(card => {
    observer.observe(card);
  });

  // Observe generic fade-in elements
  document.querySelectorAll('.fade-in').forEach(el => {
    observer.observe(el);
  });

  // Observe stat cards
  document.querySelectorAll('.stat-card').forEach(el => {
    observer.observe(el);
  });

  // Observe formula
  document.querySelectorAll('.formula-text').forEach(el => {
    observer.observe(el);
  });
}

/* ---- Counter Animations ---- */
function initCounterAnimations() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target.dataset.counted) {
        entry.target.dataset.counted = 'true';
        animateCounter(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
}

function animateCounter(el) {
  const target = parseInt(el.dataset.count, 10);
  const suffix = el.dataset.suffix || '';
  const duration = 1500;
  const start = performance.now();

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(eased * target);
    el.textContent = current + suffix;

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}
