/* ============================================
   SIGNAL PIRATE — Main JavaScript
   Scroll animations, typing effect, counters
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initTypingEffect();
  initScrollAnimations();
  initCounterAnimations();
});

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
