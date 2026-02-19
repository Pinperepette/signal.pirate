/* ============================================
   SIGNAL PIRATE — Stable Diffusion Charts
   Noise schedule, compression comparison
   ============================================ */

(function() {
  var style = getComputedStyle(document.documentElement);
  var textColor = style.getPropertyValue('--chart-text').trim() || '#8888aa';
  var gridColor = style.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';

  /* ---- 1. Noise Schedule Chart ---- */
  var noiseCtx = document.getElementById('noise-schedule-chart');
  if (noiseCtx) {
    // Generate alpha_bar values for linear schedule
    var T = 1000;
    var betaMin = 0.00085;
    var betaMax = 0.012;
    var alphaBar = [];
    var cumProd = 1.0;
    for (var t = 0; t < T; t++) {
      var beta = betaMin + (t / (T - 1)) * (betaMax - betaMin);
      cumProd *= (1 - beta);
      alphaBar.push(cumProd);
    }

    // Sample every 10 steps for the chart
    var labels = [];
    var data = [];
    for (var i = 0; i < T; i += 10) {
      labels.push(i);
      data.push(alphaBar[i]);
    }

    new Chart(noiseCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'ᾱ (segnale rimanente)',
          data: data,
          borderColor: '#00ff88',
          backgroundColor: 'rgba(0,255,136,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
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
              display: true,
              text: 'Timestep t',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: { color: textColor, maxTicksLimit: 10 },
            grid: { color: gridColor }
          },
          y: {
            title: {
              display: true,
              text: 'ᾱt (quanto segnale resta)',
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

  /* ---- 2. Compression Chart ---- */
  var compCtx = document.getElementById('compression-chart');
  if (compCtx) {
    new Chart(compCtx, {
      type: 'bar',
      data: {
        labels: ['Pixel Space\n512×512×3', 'Latent Space\n64×64×4'],
        datasets: [{
          label: 'Numero di valori',
          data: [786432, 16384],
          backgroundColor: ['rgba(255,107,107,0.6)', 'rgba(0,255,136,0.6)'],
          borderColor: ['#ff6b6b', '#00ff88'],
          borderWidth: 2,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                return ctx.parsed.x.toLocaleString() + ' valori';
              }
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Valori numerici',
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            ticks: {
              color: textColor,
              callback: function(v) { return (v / 1000) + 'K'; }
            },
            grid: { color: gridColor }
          },
          y: {
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            },
            grid: { display: false }
          }
        }
      }
    });
  }
})();
