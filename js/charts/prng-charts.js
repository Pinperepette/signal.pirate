/* ============================================
   SIGNAL PIRATE — PRNG Charts
   Distribution, prediction vs reality, MT vs CSPRNG
   ============================================ */

(function() {
  var style = getComputedStyle(document.documentElement);
  var textColor = style.getPropertyValue('--chart-text').trim() || '#8888aa';
  var gridColor = style.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';

  /* ---- Mersenne Twister in JS (minimal, for chart data) ---- */
  function MT19937(seed) {
    this.mt = new Array(624);
    this.index = 624;
    this.mt[0] = seed >>> 0;
    for (var i = 1; i < 624; i++) {
      var s = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = (((((s & 0xffff0000) >>> 16) * 1812433253) << 16) +
                     (s & 0x0000ffff) * 1812433253 + i) >>> 0;
    }
  }

  MT19937.prototype.twist = function() {
    for (var i = 0; i < 624; i++) {
      var y = (this.mt[i] & 0x80000000) | (this.mt[(i + 1) % 624] & 0x7fffffff);
      this.mt[i] = this.mt[(i + 397) % 624] ^ (y >>> 1);
      if (y & 1) this.mt[i] ^= 0x9908b0df;
    }
    this.index = 0;
  };

  MT19937.prototype.next = function() {
    if (this.index >= 624) this.twist();
    var y = this.mt[this.index++];
    y ^= (y >>> 11);
    y ^= (y << 7) & 0x9d2c5680;
    y ^= (y << 15) & 0xefc60000;
    y ^= (y >>> 18);
    return y >>> 0;
  };

  MT19937.prototype.random = function() {
    return this.next() / 4294967296;
  };

  /* ---- Untemper ---- */
  function untemper(y) {
    y ^= (y >>> 18);
    y ^= (y << 15) & 0xefc60000;
    var tmp = y;
    for (var i = 0; i < 4; i++) tmp = y ^ ((tmp << 7) & 0x9d2c5680);
    y = tmp >>> 0;
    tmp = y;
    for (var i = 0; i < 2; i++) tmp = y ^ (tmp >>> 11);
    y = tmp >>> 0;
    return y;
  }


  /* ---- 1. Distribution Chart ---- */
  var distCtx = document.getElementById('distribution-chart');
  if (distCtx) {
    var mt = new MT19937(42);
    var bins = new Array(50).fill(0);
    var N = 100000;
    for (var i = 0; i < N; i++) {
      var v = mt.random();
      var bin = Math.min(Math.floor(v * 50), 49);
      bins[bin]++;
    }

    var labels = [];
    for (var i = 0; i < 50; i++) {
      labels.push((i / 50).toFixed(2));
    }

    new Chart(distCtx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Frequenza',
          data: bins,
          backgroundColor: 'rgba(0,255,136,0.5)',
          borderColor: '#00ff88',
          borderWidth: 1,
          borderRadius: 2
        }, {
          label: 'Atteso (uniforme)',
          data: new Array(50).fill(N / 50),
          type: 'line',
          borderColor: '#ff6b6b',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        },
        scales: {
          x: {
            title: {
              display: true, text: 'Valore',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: { color: textColor, maxTicksLimit: 10 },
            grid: { color: gridColor }
          },
          y: {
            title: {
              display: true, text: 'Frequenza',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: { color: textColor },
            grid: { color: gridColor }
          }
        }
      }
    });
  }


  /* ---- 2. Prediction vs Reality Chart ---- */
  var predCtx = document.getElementById('prediction-chart');
  if (predCtx) {
    // Victim MT
    var victim = new MT19937(12345);
    // Observe 624 outputs
    var observed = [];
    for (var i = 0; i < 624; i++) observed.push(victim.next());

    // Crack: untemper to recover state
    var cloned = new MT19937(0);
    for (var i = 0; i < 624; i++) cloned.mt[i] = untemper(observed[i]);
    cloned.index = 624; // trigger twist

    // Generate next 100 from both
    var victimData = [];
    var clonedData = [];
    var indices = [];
    for (var i = 0; i < 100; i++) {
      indices.push(i);
      victimData.push(victim.random());
      clonedData.push(cloned.random());
    }

    new Chart(predCtx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Vittima (reale)',
          data: indices.map(function(i) { return {x: i, y: victimData[i]}; }),
          backgroundColor: 'rgba(0,255,136,0.6)',
          borderColor: '#00ff88',
          pointRadius: 4,
          pointStyle: 'circle'
        }, {
          label: 'Clone (predetto)',
          data: indices.map(function(i) { return {x: i, y: clonedData[i]}; }),
          backgroundColor: 'rgba(255,107,107,0.6)',
          borderColor: '#ff6b6b',
          pointRadius: 2,
          pointStyle: 'cross'
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(6);
              }
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true, text: 'Output #',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: { color: textColor },
            grid: { color: gridColor }
          },
          y: {
            title: {
              display: true, text: 'Valore random()',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: { color: textColor },
            grid: { color: gridColor },
            min: 0,
            max: 1
          }
        }
      }
    });
  }


  /* ---- 3. MT vs CSPRNG Comparison Chart ---- */
  var compCtx = document.getElementById('comparison-chart');
  if (compCtx) {
    new Chart(compCtx, {
      type: 'bar',
      data: {
        labels: ['Velocita\'', 'Distribuzione', 'Sicurezza', 'Predicibilita\'', 'Stato (KB)'],
        datasets: [{
          label: 'Mersenne Twister',
          data: [95, 98, 5, 100, 2.5],
          backgroundColor: 'rgba(255,107,107,0.6)',
          borderColor: '#ff6b6b',
          borderWidth: 2,
          borderRadius: 4
        }, {
          label: 'CSPRNG (ChaCha20)',
          data: [85, 95, 98, 0, 0.032],
          backgroundColor: 'rgba(0,255,136,0.6)',
          borderColor: '#00ff88',
          borderWidth: 2,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
          },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                var label = ctx.dataset.label;
                var val = ctx.parsed.y;
                if (ctx.dataIndex === 4) return label + ': ' + val + ' KB';
                if (ctx.dataIndex === 3) return label + ': predicibile ' + val + '%';
                return label + ': ' + val + '/100';
              }
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 }
            },
            grid: { display: false }
          },
          y: {
            ticks: { color: textColor },
            grid: { color: gridColor },
            max: 100
          }
        }
      }
    });
  }
})();
