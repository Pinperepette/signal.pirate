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

  var baseLegend = {
    labels: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } }
  };

  var baseTooltip = {
    titleFont: { family: FONT_MONO },
    bodyFont: { family: FONT_SANS }
  };

  /* ========================================================
   * Chart 1: Trigger Strategies Comparison
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('trigger-strategies-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['entries() + mutation', 'for...of + mutation', 'rAF + layout recalc'],
        datasets: [
          {
            label: 'Iterazioni prima del crash',
            data: [3, 5, 10],
            backgroundColor: RED + 'cc',
            borderColor: RED,
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Inserimenti per rehash',
            data: [512, 512, 512],
            backgroundColor: ORANGE + '80',
            borderColor: ORANGE,
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Groom objects',
            data: [50, 50, 50],
            backgroundColor: PURPLE + '80',
            borderColor: PURPLE,
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: baseLegend,
          tooltip: baseTooltip
        },
        scales: {
          x: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { display: false }
          },
          y: {
            type: 'logarithmic',
            ticks: {
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 10 },
              callback: function(val) { return val; }
            },
            grid: { color: GRID_COLOR }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 2: Exploit Chain — Step difficulty / impact
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('exploit-chain-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          '1. UAF Trigger',
          '2. Heap Spray',
          '3. Type Confusion',
          '4. Code Exec (sandbox)',
          '5. Sandbox Escape',
          '6. Kernel Exploit'
        ],
        datasets: [
          {
            label: 'Difficolta\'',
            data: [2, 4, 7, 8, 9, 10],
            backgroundColor: [
              GREEN + 'cc',
              GREEN + '99',
              YELLOW + 'cc',
              ORANGE + 'cc',
              RED + 'cc',
              RED
            ],
            borderColor: [GREEN, GREEN, YELLOW, ORANGE, RED, RED],
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            titleFont: { family: FONT_MONO },
            bodyFont: { family: FONT_SANS },
            callbacks: {
              label: function(item) {
                var labels = [
                  'CSS + JS, poche righe, nessun permesso',
                  'Allocazione massiva, stessa dimensione del freed block',
                  'Interpretare dati controllati come oggetti interni',
                  'Redirect esecuzione dentro la sandbox del renderer',
                  'Serve un secondo bug (Mojo IPC, GPU process, ecc.)',
                  'Serve un terzo bug per uscire completamente'
                ];
                return 'Difficolta\' ' + item.raw + '/10 — ' + labels[item.dataIndex];
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Difficolta\' (1-10)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            max: 11,
            min: 0
          },
          y: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { display: false }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 3: Chrome zero-day vulnerability types (2021-2026)
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('vuln-types-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: [
          'Use-After-Free',
          'Type Confusion',
          'Heap Buffer Overflow',
          'Integer Overflow',
          'Out-of-Bounds Read/Write',
          'Altro'
        ],
        datasets: [{
          data: [42, 18, 14, 8, 12, 6],
          backgroundColor: [
            RED,
            ORANGE,
            PURPLE,
            YELLOW,
            CYAN,
            '#555577'
          ],
          borderColor: '#0a0a0f',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 10 },
              padding: 15
            }
          },
          tooltip: {
            titleFont: { family: FONT_MONO },
            bodyFont: { family: FONT_SANS },
            callbacks: {
              label: function(item) {
                return item.label + ': ' + item.raw + '% degli zero-day';
              }
            }
          }
        }
      }
    });
  })();

})();
