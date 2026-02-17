/**
 * Charts for "Come Pensa la Macchina"
 * LLM article — Signal Pirate
 */

(function() {
  'use strict';

  const _rs = getComputedStyle(document.documentElement);
  const GREEN = '#00ff88';
  const PURPLE = '#7c4dff';
  const CYAN = '#4ecdc4';
  const RED = '#ff6b6b';
  const ORANGE = '#ff8800';
  const YELLOW = '#f5c518';
  const GRID_COLOR = _rs.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';
  const TEXT_COLOR = _rs.getPropertyValue('--chart-text').trim() || 'rgba(255,255,255,0.6)';

  const baseOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { labels: { color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } } },
      tooltip: { titleFont: { family: "'JetBrains Mono', monospace" }, bodyFont: { family: "'Inter', sans-serif" } }
    },
    scales: {
      x: { ticks: { color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 10 } }, grid: { color: GRID_COLOR } },
      y: { ticks: { color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 10 } }, grid: { color: GRID_COLOR } }
    }
  };

  /* ============================================
   * 1. Token count: IT vs EN
   * ============================================ */
  (function() {
    const ctx = document.getElementById('token-count-chart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          'La regina delle\napi depone uova',
          'The queen bee\nlays eggs',
          'intelligenza\nartificiale',
          'artificial\nintelligence',
          'Ciao,\ncome stai?',
          'Hello,\nhow are you?'
        ],
        datasets: [{
          label: 'Token count',
          data: [9, 5, 7, 3, 7, 6],
          backgroundColor: [PURPLE, GREEN, PURPLE, GREEN, PURPLE, GREEN],
          borderColor: [PURPLE, GREEN, PURPLE, GREEN, PURPLE, GREEN],
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        ...baseOptions,
        indexAxis: 'y',
        plugins: {
          ...baseOptions.plugins,
          legend: { display: false }
        },
        scales: {
          x: {
            ...baseOptions.scales.x,
            title: { display: true, text: 'Numero di token', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          y: {
            ...baseOptions.scales.y,
            ticks: { color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 9 } }
          }
        }
      }
    });
  })();

  /* ============================================
   * 2. Embedding cosine similarity
   * ============================================ */
  (function() {
    const ctx = document.getElementById('embedding-similarity-chart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          'neurone ↔\nrete neurale',
          're ↔\nregina',
          'intelligenza ↔\nartificiale',
          'ape ↔\ncomputer',
          'ape ↔\nregina',
          'gatto ↔\ncane',
          'ape ↔\nmiele',
          'token ↔\nparola',
          're ↔\ntrono',
          'intelligenza ↔\npatata',
          'neurone ↔\ncervello',
          'gatto ↔\nalgebra'
        ],
        datasets: [{
          label: 'Cosine Similarity',
          data: [0.625, 0.503, 0.484, 0.485, 0.468, 0.432, 0.409, 0.405, 0.422, 0.355, 0.351, 0.353],
          backgroundColor: function(context) {
            const v = context.raw;
            if (v >= 0.5) return GREEN;
            if (v >= 0.4) return CYAN;
            return PURPLE;
          },
          borderRadius: 4,
          borderWidth: 0
        }]
      },
      options: {
        ...baseOptions,
        indexAxis: 'y',
        plugins: {
          ...baseOptions.plugins,
          legend: { display: false }
        },
        scales: {
          x: {
            ...baseOptions.scales.x,
            min: 0,
            max: 0.8,
            title: { display: true, text: 'Cosine Similarity', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          y: {
            ...baseOptions.scales.y,
            ticks: { color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 9 } }
          }
        }
      }
    });
  })();

  /* ============================================
   * 3. Attention weights simulation
   * ============================================ */
  (function() {
    const ctx = document.getElementById('attention-weights-chart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['La', 'regina', 'delle', 'api', 'dep', 'one'],
        datasets: [{
          label: 'Peso attention da "dep+one" (depone)',
          data: [0.02, 0.38, 0.05, 0.32, 0.15, 0.08],
          backgroundColor: [
            'rgba(124,77,255,0.3)',
            GREEN,
            'rgba(124,77,255,0.3)',
            CYAN,
            ORANGE,
            'rgba(124,77,255,0.3)'
          ],
          borderRadius: 4,
          borderWidth: 0
        }]
      },
      options: {
        ...baseOptions,
        plugins: {
          ...baseOptions.plugins,
          legend: { display: true },
          annotation: {}
        },
        scales: {
          x: {
            ...baseOptions.scales.x,
            title: { display: true, text: 'Token nella sequenza', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          y: {
            ...baseOptions.scales.y,
            min: 0,
            max: 0.5,
            title: { display: true, text: 'Peso attention', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  })();

  /* ============================================
   * 4. Temperature: cold (T=0.3)
   * ============================================ */
  (function() {
    const ctx = document.getElementById('temp-cold-chart');
    if (!ctx) return;

    // Simulate logits and apply temperature
    const tokens = ['uova', 'circa', 'le', 'fino', 'molte', 'in', 'più', 'ogni', 'durante', 'poche'];
    const logits = [4.2, 2.8, 2.1, 1.5, 1.2, 0.8, 0.5, 0.3, 0.1, -0.2];
    const T = 0.3;
    const scaled = logits.map(l => Math.exp(l / T));
    const sum = scaled.reduce((a, b) => a + b, 0);
    const probs = scaled.map(s => s / sum);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: tokens,
        datasets: [{
          label: 'P(token) @ T=0.3',
          data: probs.map(p => parseFloat(p.toFixed(4))),
          backgroundColor: GREEN,
          borderRadius: 3,
          borderWidth: 0
        }]
      },
      options: {
        ...baseOptions,
        plugins: { ...baseOptions.plugins, legend: { display: false } },
        scales: {
          x: { ...baseOptions.scales.x, ticks: { ...baseOptions.scales.x.ticks, maxRotation: 45, minRotation: 45 } },
          y: { ...baseOptions.scales.y, min: 0, title: { display: true, text: 'Probabilità', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 10 } } }
        }
      }
    });
  })();

  /* ============================================
   * 5. Temperature: hot (T=1.5)
   * ============================================ */
  (function() {
    const ctx = document.getElementById('temp-hot-chart');
    if (!ctx) return;

    const tokens = ['uova', 'circa', 'le', 'fino', 'molte', 'in', 'più', 'ogni', 'durante', 'poche'];
    const logits = [4.2, 2.8, 2.1, 1.5, 1.2, 0.8, 0.5, 0.3, 0.1, -0.2];
    const T = 1.5;
    const scaled = logits.map(l => Math.exp(l / T));
    const sum = scaled.reduce((a, b) => a + b, 0);
    const probs = scaled.map(s => s / sum);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: tokens,
        datasets: [{
          label: 'P(token) @ T=1.5',
          data: probs.map(p => parseFloat(p.toFixed(4))),
          backgroundColor: RED,
          borderRadius: 3,
          borderWidth: 0
        }]
      },
      options: {
        ...baseOptions,
        plugins: { ...baseOptions.plugins, legend: { display: false } },
        scales: {
          x: { ...baseOptions.scales.x, ticks: { ...baseOptions.scales.x.ticks, maxRotation: 45, minRotation: 45 } },
          y: { ...baseOptions.scales.y, min: 0, title: { display: true, text: 'Probabilità', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 10 } } }
        }
      }
    });
  })();

  /* ============================================
   * 6. Training loss curve
   * ============================================ */
  (function() {
    const ctx = document.getElementById('training-loss-chart');
    if (!ctx) return;

    const steps = [];
    const loss = [];
    for (let i = 0; i <= 100; i++) {
      steps.push(i * 1000);
      // Simulated training loss curve: rapid initial decrease, then slow convergence
      const l = 3.5 * Math.exp(-i / 15) + 1.8 * Math.exp(-i / 60) + 1.2 + (Math.random() - 0.5) * 0.15;
      loss.push(parseFloat(l.toFixed(3)));
    }

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: steps,
        datasets: [{
          label: 'Training Loss (cross-entropy)',
          data: loss,
          borderColor: CYAN,
          backgroundColor: 'rgba(78,205,196,0.1)',
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.3
        }]
      },
      options: {
        ...baseOptions,
        plugins: { ...baseOptions.plugins, legend: { display: true } },
        scales: {
          x: {
            ...baseOptions.scales.x,
            title: { display: true, text: 'Training steps (×1000)', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } },
            ticks: {
              ...baseOptions.scales.x.ticks,
              callback: function(val, idx) { return idx % 10 === 0 ? (val / 1000) + 'K' : ''; }
            }
          },
          y: {
            ...baseOptions.scales.y,
            title: { display: true, text: 'Loss', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  })();

  /* ============================================
   * 7. Confidence vs Accuracy
   * ============================================ */
  (function() {
    const ctx = document.getElementById('confidence-accuracy-chart');
    if (!ctx) return;

    // Generate scatter data showing that high confidence doesn't mean correctness
    const correct = [];
    const wrong = [];
    const rng = function(seed) {
      let s = seed;
      return function() { s = (s * 16807) % 2147483647; return s / 2147483647; };
    };
    const rand = rng(42);

    for (let i = 0; i < 40; i++) {
      correct.push({ x: 0.3 + rand() * 0.65, y: 0.5 + rand() * 0.5 });
    }
    for (let i = 0; i < 25; i++) {
      // Wrong answers can also have high confidence
      wrong.push({ x: 0.4 + rand() * 0.55, y: rand() * 0.4 });
    }

    new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Risposta corretta',
            data: correct,
            backgroundColor: 'rgba(0,255,136,0.5)',
            borderColor: GREEN,
            borderWidth: 1,
            pointRadius: 5
          },
          {
            label: 'Hallucination',
            data: wrong,
            backgroundColor: 'rgba(255,107,107,0.5)',
            borderColor: RED,
            borderWidth: 1,
            pointRadius: 5,
            pointStyle: 'triangle'
          }
        ]
      },
      options: {
        ...baseOptions,
        plugins: { ...baseOptions.plugins, legend: { display: true } },
        scales: {
          x: {
            ...baseOptions.scales.x,
            min: 0.2,
            max: 1.0,
            title: { display: true, text: 'Confidence del modello (P max token)', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          y: {
            ...baseOptions.scales.y,
            min: 0,
            max: 1.0,
            title: { display: true, text: 'Correttezza fattuale', color: TEXT_COLOR, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  })();

})();
