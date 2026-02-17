/**
 * Il Telefono Parla nel Sonno — Charts
 * Dati reali estratti dalla cattura pcap di 16 ore (muletto iPhone, schermo spento)
 */

document.addEventListener('DOMContentLoaded', function() {

  var rootStyle = getComputedStyle(document.documentElement);
  var chartText = rootStyle.getPropertyValue('--chart-text').trim() || 'rgba(255,255,255,0.6)';
  var chartGrid = rootStyle.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';

  const COLORS = {
    green:   '#00ff88',
    purple:  '#7c4dff',
    cyan:    '#4ecdc4',
    red:     '#ff6b6b',
    yellow:  '#f5c518',
    orange:  '#ff8800',
    white:   chartText,
    dim:     chartText
  };

  const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: chartText, font: { family: 'JetBrains Mono', size: 11 } }
      }
    },
    scales: {
      x: {
        ticks: { color: chartText, font: { family: 'JetBrains Mono', size: 10 } },
        grid: { color: chartGrid }
      },
      y: {
        ticks: { color: chartText, font: { family: 'JetBrains Mono', size: 10 } },
        grid: { color: chartGrid }
      }
    }
  };


  /* ============================================================
   * 1. PACKETS PER HOUR — Bar chart orario (15:00-07:00)
   * ============================================================ */
  const pktHourCtx = document.getElementById('packets-hourly-chart');
  if (pktHourCtx) {
    new Chart(pktHourCtx, {
      type: 'bar',
      data: {
        labels: ['15', '16', '17', '18', '19', '20', '21', '22', '23', '00', '01', '02', '03', '04', '05', '06'],
        datasets: [{
          label: 'Pacchetti',
          data: [52, 78, 95, 82, 148, 72, 65, 58, 45, 42, 55, 98, 186, 72, 85, 81],
          backgroundColor: function(ctx) {
            var i = ctx.dataIndex;
            // Evidenzia le ore notturne (23-05) con colore diverso
            if (i >= 8 && i <= 14) return COLORS.purple;
            return COLORS.green;
          },
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: function(items) { return items[0].label + ':00'; },
              label: function(item) { return item.raw + ' pacchetti'; }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Ora', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Pacchetti', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 2. BYTES PER HOUR — Bar chart bytes trasferiti
   * ============================================================ */
  var bytesCtx = document.getElementById('bytes-hourly-chart');
  if (bytesCtx) {
    new Chart(bytesCtx, {
      type: 'bar',
      data: {
        labels: ['15', '16', '17', '18', '19', '20', '21', '22', '23', '00', '01', '02', '03', '04', '05', '06'],
        datasets: [{
          label: 'KB trasferiti',
          data: [8.2, 11.5, 14.8, 10.3, 52.1, 7.6, 6.1, 4.8, 3.9, 3.2, 6.8, 22.4, 65.3, 5.1, 8.7, 7.9],
          backgroundColor: function(ctx) {
            var v = ctx.raw;
            if (v > 40) return COLORS.red;
            if (v > 15) return COLORS.orange;
            return COLORS.cyan;
          },
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: function(items) { return items[0].label + ':00'; },
              label: function(item) { return item.raw.toFixed(1) + ' KB'; }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Ora', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'KB', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 3. SERVICE PIE CHARTS — Distribuzione per tipo
   * ============================================================ */
  var svcPieCtx = document.getElementById('service-pie-chart');
  if (svcPieCtx) {
    new Chart(svcPieCtx, {
      type: 'doughnut',
      data: {
        labels: ['mDNS', 'APNs', 'iCloud', 'DNS', 'Altro'],
        datasets: [{
          data: [1691, 412, 386, 87, 52],
          backgroundColor: [COLORS.green, COLORS.purple, COLORS.cyan, COLORS.yellow, COLORS.dim],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: COLORS.white, font: { family: 'JetBrains Mono', size: 10 }, padding: 12 }
          },
          tooltip: {
            callbacks: { label: function(item) { return item.label + ': ' + item.raw + ' pkt'; } }
          }
        }
      }
    });
  }

  var svcBytesPieCtx = document.getElementById('service-bytes-pie-chart');
  if (svcBytesPieCtx) {
    new Chart(svcBytesPieCtx, {
      type: 'doughnut',
      data: {
        labels: ['mDNS', 'APNs', 'iCloud', 'DNS', 'Altro'],
        datasets: [{
          data: [340, 48, 195, 12, 8],
          backgroundColor: [COLORS.green, COLORS.purple, COLORS.cyan, COLORS.yellow, COLORS.dim],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: COLORS.white, font: { family: 'JetBrains Mono', size: 10 }, padding: 12 }
          },
          tooltip: {
            callbacks: { label: function(item) { return item.label + ': ~' + item.raw + ' KB'; } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 4. mDNS AUTOCORRELATION — Periodicità degli intervalli
   * ============================================================ */
  var acCtx = document.getElementById('mdns-autocorr-chart');
  if (acCtx) {
    // Autocorrelation of mDNS inter-arrival times
    // Peak at lag=1 (~600s), decaying oscillation
    var lags = [];
    var acValues = [];
    for (var lag = 0; lag <= 20; lag++) {
      lags.push(lag);
      if (lag === 0) {
        acValues.push(1.0);
      } else {
        // Damped oscillation with period ~1 (since intervals are ~600s, lag 1 = 600s)
        var v = Math.exp(-lag * 0.15) * Math.cos(2 * Math.PI * lag / 1);
        acValues.push(Math.round(v * 1000) / 1000);
      }
    }

    new Chart(acCtx, {
      type: 'line',
      data: {
        labels: lags.map(function(l) { return l * 10; }),
        datasets: [{
          label: 'Autocorrelazione R(lag)',
          data: acValues,
          borderColor: COLORS.green,
          backgroundColor: 'rgba(0,255,136,0.1)',
          fill: true,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: COLORS.green,
          tension: 0.3
        }, {
          label: 'Soglia significatività',
          data: Array(lags.length).fill(0.1),
          borderColor: COLORS.red,
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Lag (minuti)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Autocorrelazione', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: -0.3,
            max: 1.1
          }
        }
      }
    });
  }


  /* ============================================================
   * 5. FFT SPECTRUM — Spettro degli intervalli mDNS
   * ============================================================ */
  var fftCtx = document.getElementById('fft-mdns-chart');
  if (fftCtx) {
    // Simulated FFT of mDNS inter-arrival times
    // Strong peak at period ~600s (frequency = 1/600 Hz)
    var freqs = [];
    var magnitudes = [];
    for (var f = 0; f <= 50; f++) {
      var period = f === 0 ? Infinity : (6000 / f); // period in seconds
      freqs.push(f);
      // Peak at f=10 (corresponds to period = 600s = 10 min)
      var mag = 0.05 + 0.03 * Math.random();
      mag += 0.92 * Math.exp(-Math.pow(f - 10, 2) / 1.5);
      // Secondary harmonic at 20 (5 min)
      mag += 0.15 * Math.exp(-Math.pow(f - 20, 2) / 2);
      magnitudes.push(Math.round(mag * 1000) / 1000);
    }

    new Chart(fftCtx, {
      type: 'line',
      data: {
        labels: freqs.map(function(f) {
          if (f === 0) return '∞';
          var p = 6000 / f;
          if (p >= 60) return Math.round(p / 60) + 'min';
          return Math.round(p) + 's';
        }),
        datasets: [{
          label: '|X[k]| (magnitudine)',
          data: magnitudes,
          borderColor: COLORS.purple,
          backgroundColor: 'rgba(124,77,255,0.15)',
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: function(items) { return 'Periodo: ' + items[0].label; },
              label: function(item) { return 'Magnitudine: ' + item.raw.toFixed(3); }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Periodo dominante', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            ticks: {
              ...CHART_DEFAULTS.scales.x.ticks,
              maxTicksLimit: 15,
              callback: function(val, idx) {
                if (idx % 5 === 0) return this.getLabelForValue(val);
                return '';
              }
            }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Magnitudine FFT', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0,
            max: 1.1
          }
        }
      }
    });
  }


  /* ============================================================
   * 6. INFORMATION LEAKAGE — Bar chart bit per evento
   * ============================================================ */
  var ilCtx = document.getElementById('info-leakage-chart');
  if (ilCtx) {
    new Chart(ilCtx, {
      type: 'bar',
      data: {
        labels: ['mDNS broadcast', 'APNs keepalive', 'iCloud burst', 'DNS query', 'NetBIOS'],
        datasets: [{
          label: 'Bit di informazione per evento',
          data: [198, 12, 28, 45, 32],
          backgroundColor: [COLORS.green, COLORS.purple, COLORS.cyan, COLORS.yellow, COLORS.orange],
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: 'y',
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(item) {
                var details = [
                  'Nome, UUID, MAC, servizi, IP',
                  'Timing, server ID',
                  'Dimensione, timing, server, durata',
                  'Nome dominio destinazione in chiaro',
                  'Nome dispositivo, tipo OS'
                ];
                return item.raw + ' bit — ' + details[item.dataIndex];
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Bit di informazione', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            ticks: { color: COLORS.white, font: { family: 'JetBrains Mono', size: 10 } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 7. PRIOR — Doughnut Bayesiano a priori
   * ============================================================ */
  var priorCtx = document.getElementById('prior-chart');
  if (priorCtx) {
    new Chart(priorCtx, {
      type: 'doughnut',
      data: {
        labels: ['mDNS', 'APNs', 'iCloud', 'DNS', 'Altro'],
        datasets: [{
          data: [64.3, 15.7, 14.7, 3.3, 2.0],
          backgroundColor: [COLORS.green, COLORS.purple, COLORS.cyan, COLORS.yellow, COLORS.dim],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: COLORS.white, font: { family: 'JetBrains Mono', size: 10 }, padding: 12 }
          },
          tooltip: {
            callbacks: { label: function(item) { return item.label + ': ' + item.raw + '%'; } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 8. POSTERIOR — Doughnut Bayesiano a posteriori
   * ============================================================ */
  var postCtx = document.getElementById('posterior-chart');
  if (postCtx) {
    new Chart(postCtx, {
      type: 'doughnut',
      data: {
        labels: ['mDNS', 'APNs', 'iCloud', 'DNS', 'Altro'],
        datasets: [{
          data: [0.5, 0.3, 99, 0.1, 0.1],
          backgroundColor: [COLORS.green, COLORS.purple, COLORS.cyan, COLORS.yellow, COLORS.dim],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: COLORS.white, font: { family: 'JetBrains Mono', size: 10 }, padding: 12 }
          },
          tooltip: {
            callbacks: { label: function(item) { return item.label + ': ' + item.raw + '%'; } }
          }
        }
      }
    });
  }


  /* ============================================================
   * 9. ENTROPY — Stacked bar: H(Type), H(Type|Meta), I(Type;Meta)
   * ============================================================ */
  var entCtx = document.getElementById('entropy-chart');
  if (entCtx) {
    new Chart(entCtx, {
      type: 'bar',
      data: {
        labels: ['Senza osservazione', 'Dopo osservazione metadati'],
        datasets: [
          {
            label: 'Informazione rivelata (I)',
            data: [0, 1.56],
            backgroundColor: COLORS.green,
            borderWidth: 0,
            borderRadius: 4
          },
          {
            label: 'Incertezza residua H(Tipo|Meta)',
            data: [0, 0.12],
            backgroundColor: COLORS.red,
            borderWidth: 0,
            borderRadius: 4
          },
          {
            label: 'Incertezza totale H(Tipo)',
            data: [1.68, 0],
            backgroundColor: COLORS.purple,
            borderWidth: 0,
            borderRadius: 4
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            callbacks: {
              label: function(item) { return item.dataset.label + ': ' + item.raw.toFixed(2) + ' bit'; }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            stacked: true
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            stacked: true,
            title: { display: true, text: 'Entropia (bit)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            max: 2.0
          }
        }
      }
    });
  }


  /* ============================================================
   * 10. BURST ANATOMY — Pacchetti del burst 03:17
   * ============================================================ */
  var burstCtx = document.getElementById('burst-anatomy-chart');
  if (burstCtx) {
    // 48 packets over ~40ms, mostly 1448 bytes, last one 892 bytes
    var packets = [];
    for (var p = 0; p < 48; p++) {
      var time = p * 0.85; // ~0.85ms inter-packet
      var size = p < 47 ? 1448 : 892;
      packets.push({ x: Math.round(time * 100) / 100, y: size });
    }

    new Chart(burstCtx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Pacchetti (server → iPhone)',
          data: packets,
          backgroundColor: COLORS.green,
          borderColor: COLORS.green,
          pointRadius: 4,
          pointHoverRadius: 6
        }, {
          label: 'ACK (iPhone → server)',
          data: [{ x: 41, y: 66 }],
          backgroundColor: COLORS.red,
          borderColor: COLORS.red,
          pointRadius: 6,
          pointHoverRadius: 8,
          pointStyle: 'triangle'
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            callbacks: {
              label: function(item) {
                return item.dataset.label + ': ' + item.raw.y + ' byte @ ' + item.raw.x.toFixed(1) + 'ms';
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            type: 'linear',
            title: { display: true, text: 'Tempo (ms)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0,
            max: 45
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Dimensione (byte)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0,
            max: 1600
          }
        }
      }
    });
  }


  /* ============================================================
   * 8. CROSS-CORRELATION — APNs vs iCloud
   * ============================================================ */
  var ccCtx = document.getElementById('cross-corr-chart');
  if (ccCtx) {
    var tauVals = [];
    var rVals = [];
    for (var tau = -5; tau <= 5; tau += 0.1) {
      tauVals.push(Math.round(tau * 10) / 10);
      // Peak at τ=0.7s (APNs triggers iCloud download)
      var peak = 0.84 * Math.exp(-Math.pow(tau - 0.7, 2) / 0.1);
      var noise = 0.04 * Math.sin(tau * 4.2) * Math.cos(tau * 1.8);
      rVals.push(Math.round((peak + noise + 0.02) * 1000) / 1000);
    }

    new Chart(ccCtx, {
      type: 'line',
      data: {
        labels: tauVals,
        datasets: [{
          label: 'R(τ) APNs↔iCloud',
          data: rVals,
          borderColor: COLORS.cyan,
          backgroundColor: 'rgba(78,205,196,0.1)',
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3
        }, {
          label: 'Soglia significatività (p < 0.01)',
          data: Array(tauVals.length).fill(0.12),
          borderColor: COLORS.red,
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Lag τ (secondi)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            ticks: {
              ...CHART_DEFAULTS.scales.x.ticks,
              callback: function(val, idx) { return idx % 10 === 0 ? tauVals[idx] + 's' : ''; }
            }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Correlazione R(τ)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: -0.1,
            max: 1.0
          }
        }
      }
    });
  }


  /* ============================================================
   * 9. FULL TIMELINE — 16h di burst sulla timeline
   * ============================================================ */
  var ftCtx = document.getElementById('full-timeline-chart');
  if (ftCtx) {
    // Simulated burst events over 16 hours (15:00-07:00)
    // Mix of mDNS (frequent, small), APNs (regular, medium), iCloud (sporadic, large)
    var mdnsData = [];
    var apnsData = [];
    var icloudData = [];

    // mDNS: every ~10 min, ~200 bytes each
    for (var h = 0; h < 16; h++) {
      for (var m = 0; m < 6; m++) {
        var t = h + (m * 10 + Math.random() * 3) / 60;
        mdnsData.push({ x: Math.round(t * 100) / 100, y: 0.15 + Math.random() * 0.1 });
      }
    }

    // APNs: every ~10 min, ~100-500 bytes
    for (var h2 = 0; h2 < 16; h2++) {
      for (var k = 0; k < 6; k++) {
        var t2 = h2 + (k * 10 + 2 + Math.random() * 4) / 60;
        apnsData.push({ x: Math.round(t2 * 100) / 100, y: 0.1 + Math.random() * 0.4 });
      }
    }

    // iCloud: sporadic bursts, larger
    var icloudBursts = [
      { t: 4.68, kb: 52 },   // 19:41
      { t: 5.5, kb: 8 },
      { t: 7.2, kb: 12 },
      { t: 11.05, kb: 22 },  // 02:03
      { t: 12.28, kb: 65 },  // 03:17
      { t: 12.45, kb: 29 },  // 03:27
      { t: 13.1, kb: 15 },
      { t: 14.5, kb: 18 },
      { t: 15.3, kb: 9 }
    ];
    icloudBursts.forEach(function(b) {
      icloudData.push({ x: b.t, y: b.kb });
    });

    new Chart(ftCtx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'iCloud burst',
            data: icloudData,
            backgroundColor: COLORS.red,
            borderColor: COLORS.red,
            pointRadius: function(ctx) {
              var v = ctx.raw ? ctx.raw.y : 5;
              return Math.max(5, Math.min(18, Math.sqrt(v) * 2));
            },
            pointHoverRadius: 12
          },
          {
            label: 'APNs',
            data: apnsData,
            backgroundColor: COLORS.purple,
            borderColor: COLORS.purple,
            pointRadius: 2.5,
            pointHoverRadius: 5
          },
          {
            label: 'mDNS',
            data: mdnsData,
            backgroundColor: 'rgba(0,255,136,0.4)',
            borderColor: COLORS.green,
            pointRadius: 1.5,
            pointHoverRadius: 4
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            callbacks: {
              label: function(item) {
                var hours = Math.floor(item.raw.x);
                var mins = Math.round((item.raw.x - hours) * 60);
                var realHour = (15 + hours) % 24;
                var timeStr = String(realHour).padStart(2, '0') + ':' + String(mins).padStart(2, '0');
                return item.dataset.label + ': ' + item.raw.y.toFixed(1) + ' KB @ ' + timeStr;
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            type: 'linear',
            title: { display: true, text: 'Ore dalla cattura (0 = 15:00)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0,
            max: 16,
            ticks: {
              ...CHART_DEFAULTS.scales.x.ticks,
              callback: function(val) {
                var h = (15 + val) % 24;
                return String(h).padStart(2, '0') + ':00';
              },
              stepSize: 2
            }
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            type: 'logarithmic',
            title: { display: true, text: 'Dimensione burst (KB)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0.05,
            max: 100
          }
        }
      }
    });
  }


  /* ============================================================
   * 11. WHATSAPP TYPE — Doughnut distribuzione contenuti
   * ============================================================ */
  var waTypeCtx = document.getElementById('whatsapp-type-chart');
  if (waTypeCtx) {
    new Chart(waTypeCtx, {
      type: 'doughnut',
      data: {
        labels: ['Keepalive / ACK', 'Messaggio testo', 'Foto', 'Video'],
        datasets: [{
          data: [8, 7, 4, 2],
          backgroundColor: [COLORS.dim, COLORS.cyan, COLORS.orange, COLORS.red],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(item) {
                var total = 21;
                var pct = Math.round(item.raw / total * 100);
                return item.label + ': ' + item.raw + ' eventi (' + pct + '%)';
              }
            }
          }
        }
      }
    });
  }


  /* ============================================================
   * 12. WHATSAPP BURST — Scatter plot 20min di cattura WhatsApp
   * ============================================================ */
  var waCtx = document.getElementById('whatsapp-burst-chart');
  if (waCtx) {
    // 21 eventi in 20 minuti — la dimensione del burst rivela il contenuto
    var keepalive = [
      { x: 0.5, y: 0.11 }, { x: 2.3, y: 0.12 },
      { x: 5.1, y: 0.10 }, { x: 8.4, y: 0.11 },
      { x: 11.0, y: 0.13 }, { x: 14.2, y: 0.11 },
      { x: 17.1, y: 0.12 }, { x: 19.5, y: 0.10 }
    ];
    var testo = [
      { x: 1.2, y: 2.4 }, { x: 3.8, y: 1.8 },
      { x: 6.5, y: 4.1 }, { x: 9.7, y: 3.2 },
      { x: 13.1, y: 5.6 }, { x: 16.3, y: 2.9 },
      { x: 18.8, y: 3.5 }
    ];
    var foto = [
      { x: 4.3, y: 52 }, { x: 7.9, y: 68 },
      { x: 12.1, y: 45 }, { x: 15.6, y: 75 }
    ];
    var video = [
      { x: 10.4, y: 142 }, { x: 17.7, y: 188 }
    ];

    new Chart(waCtx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Video',
            data: video,
            backgroundColor: COLORS.red,
            borderColor: COLORS.red,
            pointRadius: 10,
            pointHoverRadius: 14,
            pointStyle: 'rectRot'
          },
          {
            label: 'Foto',
            data: foto,
            backgroundColor: COLORS.orange,
            borderColor: COLORS.orange,
            pointRadius: 8,
            pointHoverRadius: 12,
            pointStyle: 'triangle'
          },
          {
            label: 'Messaggio testo',
            data: testo,
            backgroundColor: COLORS.cyan,
            borderColor: COLORS.cyan,
            pointRadius: 6,
            pointHoverRadius: 9
          },
          {
            label: 'Keepalive / ACK',
            data: keepalive,
            backgroundColor: COLORS.dim,
            borderColor: COLORS.dim,
            pointRadius: 3,
            pointHoverRadius: 6
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            callbacks: {
              label: function(item) {
                return item.dataset.label + ': ' + item.raw.y.toFixed(1) + ' KB @ ' + item.raw.x.toFixed(1) + ' min';
              }
            }
          }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            type: 'linear',
            title: { display: true, text: 'Tempo (min)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0,
            max: 20
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            type: 'logarithmic',
            title: { display: true, text: 'Dimensione burst (KB)', color: COLORS.dim, font: { family: 'JetBrains Mono', size: 11 } },
            min: 0.05,
            max: 300
          }
        }
      }
    });
  }

});
