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
   * Chart 1: Security Radar  - Signal vs alternative
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('security-radar-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'radar',
      data: {
        labels: [
          'Forward Secrecy',
          'Break-in Recovery',
          'Deniability',
          'Metadata Protection',
          'Open Source',
          'Audit Indipendente',
          'Post-Quantum'
        ],
        datasets: [
          {
            label: 'Signal Protocol',
            data: [10, 10, 9, 7, 10, 10, 8],
            backgroundColor: GREEN + '20',
            borderColor: GREEN,
            borderWidth: 2,
            pointBackgroundColor: GREEN,
            pointRadius: 4
          },
          {
            label: 'WhatsApp (Signal Protocol)',
            data: [10, 10, 9, 4, 3, 6, 8],
            backgroundColor: CYAN + '20',
            borderColor: CYAN,
            borderWidth: 2,
            pointBackgroundColor: CYAN,
            pointRadius: 4
          },
          {
            label: 'Telegram (MTProto)',
            data: [3, 2, 5, 3, 7, 4, 0],
            backgroundColor: PURPLE + '20',
            borderColor: PURPLE,
            borderWidth: 2,
            pointBackgroundColor: PURPLE,
            pointRadius: 4
          },
          {
            label: 'iMessage',
            data: [6, 3, 2, 5, 0, 5, 7],
            backgroundColor: ORANGE + '20',
            borderColor: ORANGE,
            borderWidth: 2,
            pointBackgroundColor: ORANGE,
            pointRadius: 4
          }
        ]
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
          tooltip: baseTooltip
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 10,
            ticks: {
              stepSize: 2,
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 9 },
              backdropColor: 'transparent'
            },
            grid: { color: GRID_COLOR },
            angleLines: { color: GRID_COLOR },
            pointLabels: {
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 10 }
            }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 2: Attack Surface  - dove colpiscono
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('attack-surface-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          'Protocollo\ncrittografico',
          'Device-linking\n(QR phishing)',
          'AI Agent\n(endpoint)',
          'Legislazione\n(backdoor)',
          'Client-side\nscanning',
          'Social\nengineering'
        ],
        datasets: [
          {
            label: 'Attacchi documentati (2024-2026)',
            data: [0, 8, 5, 4, 2, 12],
            backgroundColor: [
              GREEN + '40',
              RED + 'cc',
              ORANGE + 'cc',
              PURPLE + 'cc',
              YELLOW + '99',
              RED
            ],
            borderColor: [
              GREEN,
              RED,
              ORANGE,
              PURPLE,
              YELLOW,
              RED
            ],
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
                var notes = [
                  'Zero attacchi riusciti al Signal Protocol stesso',
                  'UNC5792 (Russia): QR code malevoli contro militari ucraini',
                  'Clawdbot: credenziali Signal esposte su pannelli pubblici',
                  'Svezia, UK, EU, Australia: tentativi legislativi',
                  'EU CSAR propone scansione pre-crittografia',
                  'Phishing, pretexting, sim-swap per accesso account'
                ];
                return notes[item.dataIndex];
              }
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Numero di campagne/incidenti documentati',
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 11 }
            },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
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
   * Chart 3: Backdoor History  - anni di vita prima del breach
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('backdoor-history-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          'Clipper Chip\n(1993)',
          'Dual_EC_DRBG\n(2006)',
          'Juniper ScreenOS\n(2008)',
          'Crypto AG\n(1970)'
        ],
        datasets: [
          {
            label: 'Anni prima della compromissione',
            data: [1, 7, 7, 50],
            backgroundColor: [
              RED + 'cc',
              ORANGE + 'cc',
              PURPLE + 'cc',
              YELLOW + 'cc'
            ],
            borderColor: [RED, ORANGE, PURPLE, YELLOW],
            borderWidth: 1,
            borderRadius: 4
          }
        ]
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
              label: function(item) {
                var details = [
                  'Matt Blaze buco\' il LEAF a 16 bit in meno di 1 anno',
                  'Snowden confermo\' la backdoor NSA nel 2013. 7 anni nascosta',
                  'Backdoor NSA nel VPN Juniper sfruttata da attore cinese',
                  'CIA possedeva segretamente Crypto AG. 120 paesi spiati per 50 anni'
                ];
                return item.raw + ' anni  - ' + details[item.dataIndex];
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { display: false }
          },
          y: {
            title: {
              display: true,
              text: 'Anni attiva prima del breach',
              color: TEXT_COLOR,
              font: { family: FONT_MONO, size: 11 }
            },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          }
        }
      }
    });
  })();

})();
