/* =========================================================
   shazam-charts.js
   Chart.js + Canvas 2D per "L'Impronta nel Rumore"
   Dati generati inline, lazy loading via IntersectionObserver
   ========================================================= */

/* --- COLORI --- */
const SC = {
  green: '#00ff88', red: '#ff6b6b', cyan: '#4ecdc4',
  orange: '#ff8800', purple: '#7c4dff', yellow: '#ffd93d',
  pink: '#ff6eb4', bg: '#0a0a0f', card: '#12121a',
  text: '#e0e0e0', muted: '#8888aa'
};

/* --- DATI GENERATI --- */
const SHAZAM_DATA = {};

/* Genera segnale audio simulato (mix di sinusoidi) */
(function generateSignals() {
  const N = 512;
  const fs = 44100;
  const freqs = [440, 554, 659, 880, 1320, 1760, 2093];
  const amps  = [1.0, 0.7, 0.5, 0.8, 0.3,  0.4,  0.2];
  const t = Array.from({length: N}, (_, i) => i / fs);
  const clean = new Array(N).fill(0);
  const noisy = new Array(N).fill(0);

  // Seeded PRNG
  let seed = 42;
  function rng() { seed = (seed * 16807 + 0) % 2147483647; return seed / 2147483647 - 0.5; }

  for (let n = 0; n < N; n++) {
    for (let f = 0; f < freqs.length; f++) {
      clean[n] += amps[f] * Math.sin(2 * Math.PI * freqs[f] * t[n]);
    }
    noisy[n] = clean[n] + rng() * 3.5;
  }

  // Normalizza
  const maxC = Math.max(...clean.map(Math.abs));
  const maxN = Math.max(...noisy.map(Math.abs));
  SHAZAM_DATA.waveform = {
    time: t.map(v => (v * 1000).toFixed(2)),
    clean: clean.map(v => v / maxC),
    noisy: noisy.map(v => v / maxN)
  };

  // FFT (semplice DFT magnitudine, solo prima metà)
  const halfN = N / 2;
  const mag = new Array(halfN).fill(0);
  for (let k = 0; k < halfN; k++) {
    let re = 0, im = 0;
    for (let n = 0; n < N; n++) {
      const angle = -2 * Math.PI * k * n / N;
      re += clean[n] * Math.cos(angle);
      im += clean[n] * Math.sin(angle);
    }
    mag[k] = Math.sqrt(re * re + im * im) / N;
  }
  const freqAxis = Array.from({length: halfN}, (_, k) => Math.round(k * fs / N));
  SHAZAM_DATA.fft = { freq: freqAxis, mag: mag };
  SHAZAM_DATA.sourceFreqs = freqs;
})();

/* Genera spettrogramma simulato */
(function generateSpectrogram() {
  const frames = 60;
  const bins = 40;
  const maxFreq = 5000;

  let seed = 77;
  function rng() { seed = (seed * 16807 + 0) % 2147483647; return seed / 2147483647; }

  // Melodia simulata: frequenze che cambiano nel tempo
  const melody = [
    {f: 440, t0: 0, t1: 15, amp: 0.9},
    {f: 880, t0: 0, t1: 15, amp: 0.6},
    {f: 1320, t0: 0, t1: 15, amp: 0.35},
    {f: 554, t0: 10, t1: 30, amp: 0.8},
    {f: 1108, t0: 10, t1: 30, amp: 0.5},
    {f: 659, t0: 25, t1: 45, amp: 0.85},
    {f: 1318, t0: 25, t1: 45, amp: 0.45},
    {f: 784, t0: 40, t1: 60, amp: 0.75},
    {f: 1568, t0: 40, t1: 60, amp: 0.4},
    {f: 440, t0: 50, t1: 60, amp: 0.7},
    // Percussioni (banda larga, brevi)
    {f: 200, t0: 5, t1: 7, amp: 0.6, wide: true},
    {f: 200, t0: 20, t1: 22, amp: 0.6, wide: true},
    {f: 200, t0: 35, t1: 37, amp: 0.6, wide: true},
    {f: 200, t0: 50, t1: 52, amp: 0.6, wide: true},
  ];

  const grid = [];
  for (let m = 0; m < frames; m++) {
    const row = [];
    for (let b = 0; b < bins; b++) {
      const freq = (b / bins) * maxFreq;
      let val = rng() * 0.12; // noise floor
      for (const note of melody) {
        if (m >= note.t0 && m <= note.t1) {
          if (note.wide) {
            // Wideband percussion
            const dist = Math.abs(freq - note.f);
            val += note.amp * Math.exp(-dist * dist / (800 * 800));
          } else {
            // Narrowband note
            const dist = Math.abs(freq - note.f);
            val += note.amp * Math.exp(-dist * dist / (80 * 80));
          }
        }
      }
      row.push(Math.min(val, 1));
    }
    grid.push(row);
  }

  SHAZAM_DATA.spectrogram = { grid, frames, bins, maxFreq };

  // Estrai picchi (massimi locali) per constellation map
  const peaks = [];
  for (let m = 1; m < frames - 1; m++) {
    for (let b = 1; b < bins - 1; b++) {
      const v = grid[m][b];
      if (v > 0.35 &&
          v > grid[m-1][b] && v > grid[m+1][b] &&
          v > grid[m][b-1] && v > grid[m][b+1]) {
        peaks.push({ time: m, freq: (b / bins) * maxFreq, amp: v });
      }
    }
  }
  SHAZAM_DATA.peaks = peaks;

  // Genera coppie hash (anchor → target)
  const pairs = [];
  for (let i = 0; i < peaks.length && pairs.length < 25; i++) {
    for (let j = i + 1; j < peaks.length && j < i + 6; j++) {
      const dt = peaks[j].time - peaks[i].time;
      if (dt > 0 && dt < 15) {
        pairs.push({ anchor: peaks[i], target: peaks[j] });
        if (pairs.length >= 25) break;
      }
    }
  }
  SHAZAM_DATA.hashPairs = pairs;
})();

/* Genera dati offset histogram */
(function generateOffsetHistogram() {
  let seed = 123;
  function rng() { seed = (seed * 16807 + 0) % 2147483647; return seed / 2147483647; }

  const bins = 60;
  const data = new Array(bins).fill(0);

  // Rumore di fondo: offset casuali
  for (let i = 0; i < bins; i++) {
    data[i] = Math.floor(rng() * 4) + 1;
  }

  // Spike al match corretto (offset ~95 secondi = bin 32)
  const matchBin = 32;
  data[matchBin] = 28;
  data[matchBin - 1] = 8;
  data[matchBin + 1] = 6;

  SHAZAM_DATA.offsetHistogram = {
    bins: Array.from({length: bins}, (_, i) => (85 + i * 1).toFixed(0)),
    counts: data,
    matchBin
  };
})();

/* Genera curva robustezza al rumore */
(function generateNoiseRobustness() {
  const snr = Array.from({length: 30}, (_, i) => -10 + i);
  // Sigmoide che sale da ~10% a ~98%
  const hashSurvival = snr.map(s => {
    const x = (s + 3) * 0.3;
    return 10 + 88 / (1 + Math.exp(-x));
  });
  const matchRate = snr.map(s => {
    const x = (s + 5) * 0.5;
    return 5 + 93 / (1 + Math.exp(-x));
  });

  SHAZAM_DATA.noiseRobustness = { snr, hashSurvival, matchRate };
})();

/* Genera dati energia per banda */
(function generateEnergyBands() {
  SHAZAM_DATA.energyBands = {
    labels: ['Sub Bass\n20-60', 'Bass\n60-250', 'Low Mid\n250-500', 'Mid\n500-2k', 'High Mid\n2k-4k', 'Presence\n4k-6k', 'Brilliance\n6k-20k'],
    music: [0.15, 0.35, 0.55, 0.80, 0.65, 0.40, 0.20],
    noise: [0.20, 0.30, 0.35, 0.40, 0.30, 0.15, 0.08],
    colors: [SC.purple, SC.purple, SC.cyan, SC.green, SC.green, SC.yellow, SC.orange]
  };
})();


/* ========================================================= */
/* SETUP DEFAULTS                                            */
/* ========================================================= */
function setupShazamChartDefaults() {
  const d = Chart.defaults;
  d.font.family = "'JetBrains Mono', monospace";
  d.font.size = 11;
  d.color = SC.muted;

  d.scale = d.scale || {};
  d.scale.grid = d.scale.grid || {};
  d.scale.grid.color = 'rgba(255,255,255,0.06)';
  d.scale.ticks = d.scale.ticks || {};
  d.scale.ticks.color = SC.muted;

  d.plugins = d.plugins || {};
  d.plugins.legend = d.plugins.legend || {};
  d.plugins.legend.labels = d.plugins.legend.labels || {};
  d.plugins.legend.labels.color = SC.text;
  d.plugins.legend.labels.usePointStyle = true;
  d.plugins.legend.labels.padding = 14;
  d.plugins.legend.labels.font = { family: "'JetBrains Mono', monospace", size: 11 };

  d.plugins.tooltip = d.plugins.tooltip || {};
  d.plugins.tooltip.backgroundColor = 'rgba(18,18,26,0.95)';
  d.plugins.tooltip.titleColor = SC.green;
  d.plugins.tooltip.bodyColor = SC.text;
  d.plugins.tooltip.borderColor = 'rgba(0,255,136,0.3)';
  d.plugins.tooltip.borderWidth = 1;
  d.plugins.tooltip.padding = 12;
  d.plugins.tooltip.cornerRadius = 8;
  d.plugins.tooltip.titleFont = { family: "'JetBrains Mono', monospace", size: 12, weight: 'bold' };
  d.plugins.tooltip.bodyFont = { family: "'JetBrains Mono', monospace", size: 11 };
}


/* =========================================================
   #1  Waveform: segnale pulito vs rumoroso
   ========================================================= */
function createWaveformChart() {
  const ctx = document.getElementById('waveform-chart');
  if (!ctx) return;
  const d = SHAZAM_DATA.waveform;

  // Decimazione per performance (mostra ogni 2 campioni)
  const step = 2;
  const labels = d.time.filter((_, i) => i % step === 0);
  const cleanD = d.clean.filter((_, i) => i % step === 0);
  const noisyD = d.noisy.filter((_, i) => i % step === 0);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Segnale pulito',
          data: cleanD,
          borderColor: SC.green,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
          fill: false
        },
        {
          label: '+ rumore ristorante',
          data: noisyD,
          borderColor: SC.red + '88',
          borderWidth: 1,
          pointRadius: 0,
          tension: 0.1,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Tempo (ms)', color: SC.muted },
          ticks: { callback: (v, i) => i % 25 === 0 ? labels[i] : '', color: SC.muted, maxRotation: 0 },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          min: -1.2, max: 1.2,
          title: { display: true, text: 'Ampiezza', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { position: 'top' } }
    }
  });
}


/* =========================================================
   #2  FFT Spectrum
   ========================================================= */
function createFFTSpectrumChart() {
  const ctx = document.getElementById('fft-spectrum-chart');
  if (!ctx) return;
  const d = SHAZAM_DATA.fft;

  // Solo 0-5000 Hz
  const maxIdx = d.freq.findIndex(f => f > 5000) || d.freq.length;
  const step = 2;
  const labels = d.freq.slice(0, maxIdx).filter((_, i) => i % step === 0);
  const values = d.mag.slice(0, maxIdx).filter((_, i) => i % step === 0);

  // Evidenzia picchi
  const threshold = 0.08;
  const bgColors = values.map(v => v > threshold ? SC.green + 'cc' : SC.purple + '44');
  const bdColors = values.map(v => v > threshold ? SC.green : SC.purple + '88');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels.map(f => f > 0 ? f : ''),
      datasets: [{
        label: 'Magnitudine FFT',
        data: values,
        backgroundColor: bgColors,
        borderColor: bdColors,
        borderWidth: 1,
        barPercentage: 1.0,
        categoryPercentage: 1.0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Frequenza (Hz)', color: SC.muted },
          ticks: { callback: (v, i) => i % 12 === 0 ? labels[i] : '', color: SC.muted, maxRotation: 0 },
          grid: { display: false }
        },
        y: {
          title: { display: true, text: '|X[k]|', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { display: false } }
    },
    plugins: [{
      id: 'freqLabels',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        c.font = 'bold 9px JetBrains Mono';
        c.textAlign = 'center';
        SHAZAM_DATA.sourceFreqs.forEach(f => {
          if (f > 5000) return;
          const idx = Math.round(f / labels[1]);
          if (idx >= 0 && idx < labels.length) {
            const x = scales.x.getPixelForValue(idx);
            c.fillStyle = SC.green;
            c.fillText(f + ' Hz', x, scales.y.top + 12);
          }
        });
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #3  Energia per banda di frequenza
   ========================================================= */
function createEnergyBandsChart() {
  const ctx = document.getElementById('energy-bands-chart');
  if (!ctx) return;
  const d = SHAZAM_DATA.energyBands;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'Musica',
          data: d.music,
          backgroundColor: SC.green + 'aa',
          borderColor: SC.green,
          borderWidth: 2,
          borderRadius: 4,
          barPercentage: 0.45
        },
        {
          label: 'Rumore ristorante',
          data: d.noise,
          backgroundColor: SC.red + '66',
          borderColor: SC.red,
          borderWidth: 2,
          borderRadius: 4,
          barPercentage: 0.45
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: { grid: { display: false }, ticks: { color: SC.text, font: { size: 9 }, maxRotation: 0 } },
        y: {
          min: 0, max: 1,
          title: { display: true, text: 'Energia relativa', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { position: 'top' } }
    }
  });
}


/* =========================================================
   #4  Spettrogramma (Canvas 2D)
   ========================================================= */
function createSpectrogramChart() {
  const canvas = document.getElementById('spectrogram-chart');
  if (!canvas) return;
  const d = SHAZAM_DATA.spectrogram;

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.parentElement.clientWidth;
    const ch = Math.min(cw * 0.5, 350);
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const margin = { top: 25, right: 55, bottom: 40, left: 55 };
    const gw = cw - margin.left - margin.right;
    const gh = ch - margin.top - margin.bottom;
    const cellW = gw / d.frames;
    const cellH = gh / d.bins;

    ctx.fillStyle = SC.bg;
    ctx.fillRect(0, 0, cw, ch);

    // Disegna spettrogramma
    for (let m = 0; m < d.frames; m++) {
      for (let b = 0; b < d.bins; b++) {
        const val = d.grid[m][b];
        const t = Math.min(val / 0.8, 1);

        // Color scale: nero → viola → ciano → verde → giallo
        let r, g, bl;
        if (t < 0.25) {
          const s = t / 0.25;
          r = Math.round(s * 60); g = 0; bl = Math.round(s * 120);
        } else if (t < 0.5) {
          const s = (t - 0.25) / 0.25;
          r = Math.round(60 - s * 60); g = Math.round(s * 200); bl = Math.round(120 + s * 76);
        } else if (t < 0.75) {
          const s = (t - 0.5) / 0.25;
          r = 0; g = Math.round(200 + s * 55); bl = Math.round(196 - s * 60);
        } else {
          const s = (t - 0.75) / 0.25;
          r = Math.round(s * 255); g = 255; bl = Math.round(136 - s * 136);
        }

        const x = margin.left + m * cellW;
        const y = margin.top + (d.bins - 1 - b) * cellH;
        ctx.fillStyle = `rgb(${r},${g},${bl})`;
        ctx.fillRect(x, y, cellW + 0.5, cellH + 0.5);
      }
    }

    // Sovrapponi picchi della constellation map
    SHAZAM_DATA.peaks.forEach(p => {
      const x = margin.left + (p.time / d.frames) * gw + cellW / 2;
      const b = (p.freq / d.maxFreq) * d.bins;
      const y = margin.top + (d.bins - b) / d.bins * gh;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = SC.green + 'dd';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // Assi
    ctx.fillStyle = SC.muted;
    ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('Tempo (frame) →', margin.left + gw / 2, ch - 5);
    ctx.save();
    ctx.translate(12, margin.top + gh / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Frequenza (Hz) →', 0, 0);
    ctx.restore();

    // Tick labels
    ctx.font = '9px JetBrains Mono';
    for (let i = 0; i <= 5; i++) {
      const f = Math.round((i / 5) * d.maxFreq);
      const y = margin.top + (1 - i / 5) * gh;
      ctx.textAlign = 'right';
      ctx.fillText(f, margin.left - 5, y + 3);
    }
    for (let i = 0; i <= 4; i++) {
      const m = Math.round((i / 4) * d.frames);
      const x = margin.left + (i / 4) * gw;
      ctx.textAlign = 'center';
      ctx.fillText(m, x, margin.top + gh + 16);
    }

    // Color bar
    const barX = cw - margin.right + 12;
    const barY = margin.top;
    const barW = 12;
    const barH = gh;
    for (let y = 0; y < barH; y++) {
      const t = 1 - y / barH;
      let r, g, bl;
      if (t < 0.25) {
        const s = t / 0.25;
        r = Math.round(s * 60); g = 0; bl = Math.round(s * 120);
      } else if (t < 0.5) {
        const s = (t - 0.25) / 0.25;
        r = Math.round(60 - s * 60); g = Math.round(s * 200); bl = Math.round(120 + s * 76);
      } else if (t < 0.75) {
        const s = (t - 0.5) / 0.25;
        r = 0; g = Math.round(200 + s * 55); bl = Math.round(196 - s * 60);
      } else {
        const s = (t - 0.75) / 0.25;
        r = Math.round(s * 255); g = 255; bl = Math.round(136 - s * 136);
      }
      ctx.fillStyle = `rgb(${r},${g},${bl})`;
      ctx.fillRect(barX, barY + y, barW, 1);
    }
    ctx.strokeStyle = SC.muted + '44';
    ctx.lineWidth = 1;
    ctx.strokeRect(barX, barY, barW, barH);
    ctx.font = '9px JetBrains Mono';
    ctx.fillStyle = SC.muted;
    ctx.textAlign = 'left';
    ctx.fillText('High', barX + barW + 3, barY + 8);
    ctx.fillText('Low', barX + barW + 3, barY + barH);

    // Legend for peaks
    ctx.beginPath();
    ctx.arc(margin.left + 10, margin.top + 10, 4, 0, Math.PI * 2);
    ctx.fillStyle = SC.green + 'dd';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.font = '9px JetBrains Mono';
    ctx.fillStyle = SC.green;
    ctx.textAlign = 'left';
    ctx.fillText('Picchi (constellation)', margin.left + 18, margin.top + 13);
  }

  draw();
  let rt;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 150); });
}


/* =========================================================
   #5  Constellation Map (Scatter)
   ========================================================= */
function createConstellationChart() {
  const ctx = document.getElementById('constellation-chart');
  if (!ctx) return;
  const peaks = SHAZAM_DATA.peaks;

  new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Landmark (picchi spettrali)',
        data: peaks.map(p => ({ x: p.time, y: p.freq })),
        backgroundColor: peaks.map(p => {
          if (p.amp > 0.7) return SC.green + 'ee';
          if (p.amp > 0.5) return SC.cyan + 'cc';
          return SC.purple + 'aa';
        }),
        borderColor: peaks.map(p => p.amp > 0.7 ? SC.green : p.amp > 0.5 ? SC.cyan : SC.purple),
        borderWidth: 1.5,
        pointRadius: peaks.map(p => 4 + p.amp * 6),
        pointHoverRadius: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Tempo (frame)', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          title: { display: true, text: 'Frequenza (Hz)', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => `t=${c.raw.x} f=${Math.round(c.raw.y)} Hz`
          }
        }
      }
    },
    plugins: [{
      id: 'starGlow',
      afterDraw(chart) {
        const { ctx: c } = chart;
        c.save();
        peaks.filter(p => p.amp > 0.7).forEach(p => {
          const meta = chart.getDatasetMeta(0);
          const el = meta.data[peaks.indexOf(p)];
          if (!el) return;
          const glow = c.createRadialGradient(el.x, el.y, 0, el.x, el.y, 20);
          glow.addColorStop(0, SC.green + '33');
          glow.addColorStop(1, SC.green + '00');
          c.fillStyle = glow;
          c.fillRect(el.x - 20, el.y - 20, 40, 40);
        });
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #6  Hash Pairs (Canvas 2D)
   ========================================================= */
function createHashPairsChart() {
  const canvas = document.getElementById('hash-pairs-chart');
  if (!canvas) return;
  const pairs = SHAZAM_DATA.hashPairs;
  const d = SHAZAM_DATA.spectrogram;

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.parentElement.clientWidth;
    const ch = Math.min(cw * 0.55, 380);
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const margin = { top: 30, right: 20, bottom: 40, left: 55 };
    const gw = cw - margin.left - margin.right;
    const gh = ch - margin.top - margin.bottom;

    ctx.fillStyle = SC.bg;
    ctx.fillRect(0, 0, cw, ch);

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 8; i++) {
      const x = margin.left + (i / 8) * gw;
      ctx.beginPath(); ctx.moveTo(x, margin.top); ctx.lineTo(x, margin.top + gh); ctx.stroke();
      const y = margin.top + (i / 8) * gh;
      ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(margin.left + gw, y); ctx.stroke();
    }

    function toX(t) { return margin.left + (t / d.frames) * gw; }
    function toY(f) { return margin.top + (1 - f / d.maxFreq) * gh; }

    // Disegna linee hash (anchor → target)
    pairs.forEach((p, i) => {
      const x1 = toX(p.anchor.time);
      const y1 = toY(p.anchor.freq);
      const x2 = toX(p.target.time);
      const y2 = toY(p.target.freq);

      // Colore basato su distanza
      const hue = (i / pairs.length);
      const color = hue < 0.33 ? SC.green : hue < 0.66 ? SC.cyan : SC.purple;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = color + '66';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrowhead
      const angle = Math.atan2(y2 - y1, x2 - x1);
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - 6 * Math.cos(angle - 0.4), y2 - 6 * Math.sin(angle - 0.4));
      ctx.lineTo(x2 - 6 * Math.cos(angle + 0.4), y2 - 6 * Math.sin(angle + 0.4));
      ctx.closePath();
      ctx.fillStyle = color + 'aa';
      ctx.fill();
    });

    // Disegna punti (anchor = quadrato, target = cerchio)
    const drawn = new Set();
    pairs.forEach(p => {
      // Anchor
      const aKey = p.anchor.time + ',' + p.anchor.freq;
      if (!drawn.has(aKey)) {
        drawn.add(aKey);
        const x = toX(p.anchor.time);
        const y = toY(p.anchor.freq);
        ctx.fillStyle = SC.green;
        ctx.fillRect(x - 4, y - 4, 8, 8);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.strokeRect(x - 4, y - 4, 8, 8);
      }
      // Target
      const tKey = p.target.time + ',' + p.target.freq;
      if (!drawn.has(tKey)) {
        drawn.add(tKey);
        const x = toX(p.target.time);
        const y = toY(p.target.freq);
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = SC.cyan;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    });

    // Legenda
    ctx.fillStyle = SC.green;
    ctx.fillRect(margin.left + 5, margin.top + 5, 8, 8);
    ctx.font = '9px JetBrains Mono';
    ctx.fillStyle = SC.text;
    ctx.textAlign = 'left';
    ctx.fillText('Anchor', margin.left + 18, margin.top + 13);

    ctx.beginPath();
    ctx.arc(margin.left + 9, margin.top + 28, 5, 0, Math.PI * 2);
    ctx.fillStyle = SC.cyan;
    ctx.fill();
    ctx.fillStyle = SC.text;
    ctx.fillText('Target', margin.left + 18, margin.top + 31);

    // Assi
    ctx.fillStyle = SC.muted;
    ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('Tempo (frame)', margin.left + gw / 2, ch - 5);
    ctx.save();
    ctx.translate(12, margin.top + gh / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Frequenza (Hz)', 0, 0);
    ctx.restore();

    // Tick labels
    ctx.font = '9px JetBrains Mono';
    for (let i = 0; i <= 5; i++) {
      const f = Math.round((i / 5) * d.maxFreq);
      const y = toY(f);
      ctx.textAlign = 'right';
      ctx.fillText(f, margin.left - 5, y + 3);
    }

    // Hash formula callout
    ctx.font = 'bold 10px JetBrains Mono';
    ctx.fillStyle = SC.orange;
    ctx.textAlign = 'right';
    ctx.fillText('hash = H(f₁, f₂, Δt)', cw - margin.right - 5, margin.top + 15);
  }

  draw();
  let rt;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 150); });
}


/* =========================================================
   #7  Offset Histogram
   ========================================================= */
function createOffsetHistogramChart() {
  const ctx = document.getElementById('offset-histogram-chart');
  if (!ctx) return;
  const d = SHAZAM_DATA.offsetHistogram;

  const bgColors = d.counts.map((v, i) => {
    if (i === d.matchBin) return SC.green + 'ee';
    if (Math.abs(i - d.matchBin) <= 1 && v > 5) return SC.green + '88';
    return SC.purple + '44';
  });

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.bins,
      datasets: [{
        label: 'Hash allineati per offset',
        data: d.counts,
        backgroundColor: bgColors,
        borderColor: d.counts.map((v, i) => i === d.matchBin ? SC.green : SC.purple + '66'),
        borderWidth: 1,
        borderRadius: 2,
        barPercentage: 1.0,
        categoryPercentage: 0.95
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Offset temporale (secondi nel brano)', color: SC.muted },
          ticks: { callback: (v, i) => i % 10 === 0 ? d.bins[i] : '', color: SC.muted, maxRotation: 0 },
          grid: { display: false }
        },
        y: {
          title: { display: true, text: 'Conteggio hash', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { display: false } }
    },
    plugins: [{
      id: 'matchAnnotation',
      afterDraw(chart) {
        const { ctx: c, scales, chartArea } = chart;
        c.save();

        const x = scales.x.getPixelForValue(d.matchBin);
        const y = scales.y.getPixelForValue(d.counts[d.matchBin]);

        // Arrow
        c.strokeStyle = SC.green;
        c.lineWidth = 2;
        c.setLineDash([]);
        c.beginPath();
        c.moveTo(x, y - 30);
        c.lineTo(x, y - 10);
        c.stroke();
        c.beginPath();
        c.moveTo(x, y - 10);
        c.lineTo(x - 4, y - 16);
        c.lineTo(x + 4, y - 16);
        c.closePath();
        c.fillStyle = SC.green;
        c.fill();

        // Label
        c.font = 'bold 10px JetBrains Mono';
        c.fillStyle = SC.green;
        c.textAlign = 'center';
        c.fillText('MATCH!', x, y - 36);
        c.font = '9px JetBrains Mono';
        c.fillStyle = SC.muted;
        c.fillText('offset ≈ 95s', x, y - 48);

        // Noise label
        c.font = '9px JetBrains Mono';
        c.fillStyle = SC.purple + 'aa';
        c.textAlign = 'left';
        c.fillText('rumore (collisioni casuali)', chartArea.left + 8, chartArea.bottom - 8);

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #8  Noise Robustness
   ========================================================= */
function createNoiseRobustnessChart() {
  const ctx = document.getElementById('noise-robustness-chart');
  if (!ctx) return;
  const d = SHAZAM_DATA.noiseRobustness;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.snr.map(s => s + ' dB'),
      datasets: [
        {
          label: 'Hash sopravvissuti (%)',
          data: d.hashSurvival,
          borderColor: SC.cyan,
          backgroundColor: SC.cyan + '15',
          borderWidth: 2.5,
          fill: true,
          pointRadius: 0,
          tension: 0.4
        },
        {
          label: 'Tasso di riconoscimento (%)',
          data: d.matchRate,
          borderColor: SC.green,
          backgroundColor: SC.green + '15',
          borderWidth: 3,
          fill: true,
          pointRadius: 0,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'SNR (dB)', color: SC.muted },
          ticks: { callback: (v, i) => i % 5 === 0 ? d.snr[i] + ' dB' : '', color: SC.muted, maxRotation: 0 },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          min: 0, max: 100,
          title: { display: true, text: '%', color: SC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: v => v + '%' }
        }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'restaurantZone',
      beforeDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();

        // Restaurant SNR zone (-5 to +5 dB)
        const xLeft = scales.x.getPixelForValue(5);  // index 5 = -5 dB
        const xRight = scales.x.getPixelForValue(15); // index 15 = +5 dB

        c.fillStyle = SC.orange + '12';
        c.fillRect(xLeft, chartArea.top, xRight - xLeft, chartArea.bottom - chartArea.top);

        c.strokeStyle = SC.orange + '44';
        c.lineWidth = 1;
        c.setLineDash([4, 3]);
        c.beginPath(); c.moveTo(xLeft, chartArea.top); c.lineTo(xLeft, chartArea.bottom); c.stroke();
        c.beginPath(); c.moveTo(xRight, chartArea.top); c.lineTo(xRight, chartArea.bottom); c.stroke();

        c.setLineDash([]);
        c.font = 'bold 9px JetBrains Mono';
        c.fillStyle = SC.orange;
        c.textAlign = 'center';
        c.fillText('RISTORANTE', (xLeft + xRight) / 2, chartArea.top + 14);

        c.restore();
      }
    }]
  });
}


/* =========================================================
   INIT — Lazy loading con IntersectionObserver
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  setupShazamChartDefaults();

  const charts = {
    'waveform-chart':         createWaveformChart,
    'fft-spectrum-chart':     createFFTSpectrumChart,
    'energy-bands-chart':     createEnergyBandsChart,
    'spectrogram-chart':      createSpectrogramChart,
    'constellation-chart':    createConstellationChart,
    'hash-pairs-chart':       createHashPairsChart,
    'offset-histogram-chart': createOffsetHistogramChart,
    'noise-robustness-chart': createNoiseRobustnessChart
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && charts[entry.target.id]) {
        try {
          charts[entry.target.id]();
        } catch (e) {
          console.error(`Chart error [${entry.target.id}]:`, e);
        }
        delete charts[entry.target.id];
      }
    });
  }, { threshold: 0.1, rootMargin: '50px' });

  Object.keys(charts).forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
    else console.warn(`Canvas not found: #${id}`);
  });
});
