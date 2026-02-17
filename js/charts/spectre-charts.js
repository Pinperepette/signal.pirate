(function() {
  'use strict';

  var GREEN  = '#00ff88';
  var RED    = '#ff6b6b';
  var PURPLE = '#7c4dff';
  var CYAN   = '#4ecdc4';
  var ORANGE = '#ff8800';
  var YELLOW = '#f5c518';

  var style = getComputedStyle(document.documentElement);
  var TEXT_COLOR = style.getPropertyValue('--chart-text').trim() || 'rgba(255,255,255,0.6)';
  var GRID_COLOR = style.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';

  var FONT_MONO = "'JetBrains Mono', monospace";
  var FONT_SANS = "'Inter', sans-serif";

  var baseScales = {
    x: {
      ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
      grid: { color: GRID_COLOR }
    },
    y: {
      ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
      grid: { color: GRID_COLOR }
    }
  };

  var baseLegend = {
    labels: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } }
  };

  var baseTooltip = {
    titleFont: { family: FONT_MONO },
    bodyFont: { family: FONT_SANS }
  };

  /* ========================================================
   * Chart 1: Cache Timing Scatter (hit vs miss)
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('cache-timing-chart');
    if (!ctx) return;

    /* Simula 200 punti basati sui valori reali misurati */
    function gauss(mean, std) {
      var u = 0, v = 0;
      while (u === 0) u = Math.random();
      while (v === 0) v = Math.random();
      return mean + std * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }

    var hitData = [], missData = [];
    for (var i = 0; i < 200; i++) {
      hitData.push({ x: i, y: Math.max(10, Math.round(gauss(26, 6))) });
      missData.push({ x: i, y: Math.max(80, Math.round(gauss(290, 60))) });
    }

    new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Cache HIT',
            data: hitData,
            backgroundColor: GREEN + '80',
            borderColor: GREEN,
            pointRadius: 2.5,
            pointHoverRadius: 5
          },
          {
            label: 'Cache MISS',
            data: missData,
            backgroundColor: RED + '80',
            borderColor: RED,
            pointRadius: 2.5,
            pointHoverRadius: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: baseLegend,
          tooltip: baseTooltip,
          annotation: undefined
        },
        scales: {
          x: {
            title: { display: true, text: 'Round', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          },
          y: {
            title: { display: true, text: 'Cicli', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            min: 0,
            max: 500
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 2: Flush+Reload (byte extraction for 'A' = 0x41)
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('flush-reload-chart');
    if (!ctx) return;

    var SECRET_BYTE = 0x41; /* 'A' */
    var labels = [];
    var data = [];
    var colors = [];

    for (var i = 0; i < 256; i++) {
      if (i % 16 === 0) {
        labels.push('0x' + i.toString(16).toUpperCase().padStart(2, '0'));
      } else {
        labels.push('');
      }

      if (i === SECRET_BYTE) {
        data.push(500);
        colors.push(GREEN);
      } else {
        /* Minimo rumore casuale */
        data.push(Math.random() < 0.02 ? 1 : 0);
        colors.push(RED + '40');
      }
    }

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Hit count',
          data: data,
          backgroundColor: colors,
          borderColor: colors,
          borderWidth: 0,
          borderRadius: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            titleFont: { family: FONT_MONO },
            bodyFont: { family: FONT_SANS },
            callbacks: {
              title: function(items) {
                var idx = items[0].dataIndex;
                var hex = '0x' + idx.toString(16).toUpperCase().padStart(2, '0');
                var ch = (idx >= 32 && idx < 127) ? " '" + String.fromCharCode(idx) + "'" : '';
                return hex + ch;
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Byte value', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 9 }, maxRotation: 0 },
            grid: { display: false }
          },
          y: {
            title: { display: true, text: 'Hit (su 500)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            max: 550
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 3: Spectre v1 Extraction Results
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('spectre-results-chart');
    if (!ctx) return;

    var secret = 'Il processore mente.';
    var hits = [4997, 3970, 3448, 4807, 5000, 3436, 3778, 1268,
                5000, 5000, 1963, 5000, 2881, 4990, 4791, 4995,
                4501, 4999, 2377, 2416];

    var labels = [];
    var data = [];
    var bgColors = [];

    for (var i = 0; i < secret.length; i++) {
      var c = secret[i] === ' ' ? '␣' : secret[i];
      labels.push('[' + i + '] ' + c);
      data.push(hits[i]);

      /* Colore in base alla confidenza */
      var ratio = hits[i] / 5000;
      if (ratio > 0.8) bgColors.push(GREEN);
      else if (ratio > 0.5) bgColors.push(CYAN);
      else bgColors.push(YELLOW);
    }

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Hit / 5000',
          data: data,
          backgroundColor: bgColors,
          borderColor: bgColors,
          borderWidth: 0,
          borderRadius: 3
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            titleFont: { family: FONT_MONO },
            bodyFont: { family: FONT_SANS },
            callbacks: {
              label: function(item) {
                return item.raw + '/5000 hit (' + (item.raw / 50).toFixed(1) + '%)';
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Hit su 5000 tentativi', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            max: 5500,
            min: 0
          },
          y: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            grid: { display: false }
          }
        }
      }
    });

    /* Forza altezza per il bar chart orizzontale */
    ctx.parentElement.style.minHeight = '500px';
  })();

})();
