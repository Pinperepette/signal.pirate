/* =========================================================
   attention-hidden-charts.js
   16 grafici Chart.js per "L'Attenzione Invisibile"
   Dati inline + lazy loading via IntersectionObserver
   ========================================================= */

/* --- DATA INLINE (nessun fetch necessario) --- */
const HIDDEN_DATA = {
  signals: {
    names: ["dwellTimeMs","isDetailExpanded","isBookmarked","isProfileClicked","isVideoPlayback50","isPhotoExpanded","isOpenLinked"],
    labels: ["Dwell Time","Detail Expand","Bookmark","Profile Click","Video 50%","Photo Expand","Open Link"]
  },
  factorLoadings: {
    labels: ["dwellTimeMs","isDetailExpanded","isBookmarked","isProfileClicked","isVideoPlayback50","isPhotoExpanded","isOpenLinked"],
    loadings: [0.92, 0.78, 0.74, 0.68, 0.65, 0.55, 0.32],
    communality: [0.846, 0.608, 0.548, 0.462, 0.423, 0.303, 0.102],
    uniqueness: [0.154, 0.392, 0.452, 0.538, 0.577, 0.697, 0.898]
  },
  bayesian: {
    xAxis: Array.from({length:101}, (_,i) => i/100),
    prior: null,
    posterior: null,
    updateSteps: {
      labels: ["Prior β(2,2)","+ dwellTime\n(3.2s)","+ detailExpand","+ bookmark","+ profileClick","+ video50%"],
      means: [0.50, 0.58, 0.54, 0.57, 0.56, 0.55],
      ci_lower: [0.15, 0.38, 0.40, 0.44, 0.45, 0.46],
      ci_upper: [0.85, 0.78, 0.68, 0.70, 0.67, 0.64]
    }
  },
  informationTheory: {
    mutualInformation: {
      labels: ["dwellTimeMs","isDetailExpanded","isBookmarked","isProfileClicked","isVideoPlayback50","isPhotoExpanded","isOpenLinked"],
      values: [0.482, 0.187, 0.164, 0.138, 0.121, 0.089, 0.043]
    },
    conditionalMI: {
      labels: ["Dwell","Detail","Bookmark","Profile","Video50","Photo","Link"],
      matrix: [
        [0.482,0.091,0.078,0.065,0.058,0.041,0.019],
        [0.091,0.187,0.062,0.054,0.048,0.035,0.015],
        [0.078,0.062,0.164,0.047,0.042,0.031,0.013],
        [0.065,0.054,0.047,0.138,0.039,0.028,0.011],
        [0.058,0.048,0.042,0.039,0.121,0.025,0.010],
        [0.041,0.035,0.031,0.028,0.025,0.089,0.008],
        [0.019,0.015,0.013,0.011,0.010,0.008,0.043]
      ]
    },
    klDivergence: {
      labels: ["Power User","Casual","Bot-like","News","Creator"],
      platform_vs_user: [0.34,0.12,0.87,0.28,0.19],
      user_vs_platform: [0.41,0.15,1.12,0.33,0.22]
    }
  },
  fisher: {
    labels: ["dwellTimeMs","isDetailExpanded","isBookmarked","isProfileClicked","isVideoPlayback50","isPhotoExpanded","isOpenLinked"],
    fisherInfo: [3.42, 0.89, 0.72, 0.58, 0.48, 0.31, 0.12],
    fisherPercent: [52.1, 13.6, 11.0, 8.8, 7.3, 4.7, 1.8],
    cramerRao: {
      numSignals: [1,2,3,4,5,6,7],
      bound: [0.292,0.232,0.199,0.179,0.165,0.156,0.152],
      empiricalVar: [0.35,0.27,0.22,0.19,0.17,0.16,0.155]
    }
  },
  scoreFunction: {
    weights: {
      labels: ["dwellTimeMs","isBookmarked","isDetailExpanded","isVideoPlayback50","isProfileClicked","isPhotoExpanded","isOpenLinked"],
      values: [0.30,0.22,0.18,0.14,0.12,0.08,-0.04]
    },
    sensitivity: {
      labels: ["dwellTimeMs","isBookmarked","isDetailExpanded","isVideoPlayback50","isProfileClicked","isPhotoExpanded","isOpenLinked"],
      dS_dsignal: [0.075,0.055,0.045,0.035,0.030,0.020,-0.010]
    }
  },
  strategyRadar: {
    labels: ["Dwell Time","Segnali Binari","Timing","Visual Content","Thread","Curiosity Gap","CTA Implicita"],
    optimal: [95,80,85,75,70,90,65],
    average: [40,35,30,45,25,20,15],
    advanced: [90,75,90,80,85,85,70]
  }
};

/* --- Genera Beta PDF e Posterior analiticamente --- */
(function generateBayesianCurves() {
  function betaPDF(x, a, b) {
    if (x <= 0 || x >= 1) return 0;
    const logB = lgamma(a) + lgamma(b) - lgamma(a + b);
    return Math.exp((a - 1) * Math.log(x) + (b - 1) * Math.log(1 - x) - logB);
  }
  function lgamma(x) {
    const c = [76.18009172947146,-86.50532032941677,24.01409824083091,
      -1.231739572450155,0.1208650973866179e-2,-0.5395239384953e-5];
    let y = x, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    let ser = 1.000000000190015;
    for (let j = 0; j < 6; j++) ser += c[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }
  const xs = HIDDEN_DATA.bayesian.xAxis;
  HIDDEN_DATA.bayesian.prior = xs.map(x => betaPDF(x, 2, 2));
  HIDDEN_DATA.bayesian.posterior = xs.map(x => betaPDF(x, 8, 6));
})();

/* --- Genera traiettorie drift-diffusion con seed deterministico --- */
function generateDriftPaths() {
  function seededRandom(seed) {
    let s = seed;
    return function() {
      s = (s * 16807 + 0) % 2147483647;
      return s / 2147483647;
    };
  }
  function generatePath(mu, sigma, seed, steps, dt, upper, lower) {
    const rng = seededRandom(seed);
    const path = [0];
    for (let i = 1; i < steps; i++) {
      const u1 = rng(), u2 = rng();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      const prev = path[path.length - 1];
      const next = prev + mu * dt + sigma * Math.sqrt(dt) * z;
      if (next >= upper) { path.push(upper); break; }
      if (next <= lower) { path.push(lower); break; }
      path.push(next);
    }
    while (path.length < steps) path.push(null);
    return path;
  }
  const steps = 80;
  const dt = 0.1;
  return {
    timeAxis: Array.from({length: steps}, (_, i) => (i * dt).toFixed(1)),
    upperBarrier: 1.0,
    lowerBarrier: -1.0,
    paths: [
      { label: 'Alto drift (μ=0.35)', data: generatePath(0.35, 0.25, 42, steps, dt, 1.0, -1.0), color: 'green', width: 3 },
      { label: 'Medio drift (μ=0.15)', data: generatePath(0.15, 0.25, 77, steps, dt, 1.0, -1.0), color: 'cyan', width: 2.5 },
      { label: 'Basso drift (μ=0.03)', data: generatePath(0.03, 0.25, 123, steps, dt, 1.0, -1.0), color: 'orange', width: 2 },
      { label: 'Negativo (μ=-0.2)', data: generatePath(-0.2, 0.25, 55, steps, dt, 1.0, -1.0), color: 'red', width: 2 },
      { label: 'Alto drift #2', data: generatePath(0.30, 0.30, 999, steps, dt, 1.0, -1.0), color: 'green', width: 1.5, dash: [4,3] },
      { label: 'Negativo #2', data: generatePath(-0.15, 0.28, 200, steps, dt, 1.0, -1.0), color: 'red', width: 1.5, dash: [4,3] }
    ]
  };
}

/* --- Genera processo di Hawkes --- */
function generateHawkes() {
  const T = 30, dt = 0.2;
  const n = Math.ceil(T / dt);
  const t = Array.from({length: n}, (_, i) => +(i * dt).toFixed(1));
  const mu = 0.5;

  // Subcritical: alpha=0.4, beta=0.8 => n*=0.5
  const sub = new Array(n).fill(mu);
  const subEvents = [2.0, 7.0, 14.0, 20.0];
  subEvents.forEach(te => {
    for (let i = 0; i < n; i++) {
      if (t[i] > te) sub[i] += 0.4 * Math.exp(-0.8 * (t[i] - te));
    }
  });

  // Supercritical: alpha=1.2, beta=0.8 => n*=1.5
  const sup = new Array(n).fill(mu);
  const supEvents = [2.0, 3.5, 4.2, 5.0, 5.5, 6.2, 7.0, 7.5, 8.2, 9.0, 9.5, 10.5, 11.2, 12.0, 13.0, 14.0, 15.0, 16.5, 18.0];
  supEvents.forEach(te => {
    for (let i = 0; i < n; i++) {
      if (t[i] > te) sup[i] += 1.2 * Math.exp(-0.8 * (t[i] - te));
    }
  });

  return { timeAxis: t, baseline: new Array(n).fill(mu), subcritical: sub, supercritical: sup, subEvents, supEvents };
}

/* --- Genera prima-passage-time distributions --- */
function generateFirstPassage() {
  const t = Array.from({length:60}, (_,i) => (i * 0.2 + 0.2));
  function inversGaussian(x, mu_fp, lambda) {
    if (x <= 0) return 0;
    return Math.sqrt(lambda / (2 * Math.PI * x * x * x)) * Math.exp(-lambda * (x - mu_fp) * (x - mu_fp) / (2 * mu_fp * mu_fp * x));
  }
  return {
    timeAxis: t,
    high:   t.map(x => inversGaussian(x, 2.0, 8.0)),
    medium: t.map(x => inversGaussian(x, 4.0, 5.0)),
    low:    t.map(x => inversGaussian(x, 8.0, 3.0))
  };
}

/* --- Genera paesaggio score --- */
function generateScoreLandscape() {
  const points = [];
  for (let d = 0; d <= 1.0; d += 0.05) {
    for (let b = 0; b <= 1.0; b += 0.1) {
      const score = 0.30 * sigmoid(d * 5 - 1.5) + 0.22 * b * sigmoid(b * 3) + 0.18 * b * 0.7 + 0.14 * b * 0.5 + 0.12 * b * 0.4 + 0.08 * b * 0.3 - 0.04 * (1 - b) * 0.2;
      points.push({ dwell: d, binary: b, score: Math.min(score, 1) });
    }
  }
  return points;
}
function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }

/* --- Genera biforcazione --- */
function generateBifurcation() {
  const rate = Array.from({length: 60}, (_, i) => i * 0.01);
  const gamma_crit = 0.15;
  const sub = rate.map(r => {
    const x = 0.1 + r * 2;
    return x / (1 + Math.exp(5 * (r - gamma_crit))) + 0.1;
  });
  const sup = rate.map(r => {
    if (r < gamma_crit) return sub[rate.indexOf(r)];
    return 0.1 + r * 2 + Math.exp(3.5 * (r - gamma_crit)) * 0.8;
  });
  return { rate, sub, sup, critIdx: Math.round(gamma_crit / 0.01) };
}

/* --- Genera Hawkes Phase Diagram --- */
function generatePhasePoints() {
  const sub = [], crit = [], sup = [];
  for (let a = 0.1; a <= 2.0; a += 0.1) {
    for (let b = 0.2; b <= 2.5; b += 0.15) {
      const ns = a / b;
      const p = { x: a, y: b, ns: ns };
      if (ns < 0.9) sub.push(p);
      else if (ns <= 1.1) crit.push(p);
      else sup.push(p);
    }
  }
  return { sub, crit, sup };
}


/* ========================================================= */
/* COLORI E DEFAULTS                                         */
/* ========================================================= */
const HC = {
  green: '#00ff88', red: '#ff6b6b', cyan: '#4ecdc4',
  orange: '#ff8800', purple: '#7c4dff', yellow: '#ffd93d',
  pink: '#ff6eb4', bg: '#0a0a0f', card: '#12121a',
  text: '#e0e0e0', muted: '#8888aa'
};

function setupHiddenChartDefaults() {
  const d = Chart.defaults;
  d.font.family = "'JetBrains Mono', monospace";
  d.font.size = 11;
  d.color = HC.muted;

  d.scale = d.scale || {};
  d.scale.grid = d.scale.grid || {};
  d.scale.grid.color = 'rgba(255,255,255,0.06)';
  d.scale.ticks = d.scale.ticks || {};
  d.scale.ticks.color = HC.muted;

  d.plugins = d.plugins || {};
  d.plugins.legend = d.plugins.legend || {};
  d.plugins.legend.labels = d.plugins.legend.labels || {};
  d.plugins.legend.labels.color = HC.text;
  d.plugins.legend.labels.usePointStyle = true;
  d.plugins.legend.labels.padding = 14;
  d.plugins.legend.labels.font = { family: "'JetBrains Mono', monospace", size: 11 };

  d.plugins.tooltip = d.plugins.tooltip || {};
  d.plugins.tooltip.backgroundColor = 'rgba(18,18,26,0.95)';
  d.plugins.tooltip.titleColor = HC.green;
  d.plugins.tooltip.bodyColor = HC.text;
  d.plugins.tooltip.borderColor = 'rgba(0,255,136,0.3)';
  d.plugins.tooltip.borderWidth = 1;
  d.plugins.tooltip.padding = 12;
  d.plugins.tooltip.cornerRadius = 8;
  d.plugins.tooltip.titleFont = { family: "'JetBrains Mono', monospace", size: 12, weight: 'bold' };
  d.plugins.tooltip.bodyFont = { family: "'JetBrains Mono', monospace", size: 11 };
}

/* --- Utility: crea gradiente verticale --- */
function vGradient(ctx, chartArea, c1, c2) {
  const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  g.addColorStop(0, c1);
  g.addColorStop(1, c2);
  return g;
}

/* --- Utility: crea gradiente radiale per glow --- */
function glowGradient(ctx, x, y, r, color) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, color + 'aa');
  g.addColorStop(0.5, color + '33');
  g.addColorStop(1, color + '00');
  return g;
}


/* =========================================================
   #1  Factor Loadings (Bar orizzontale) — Sez. 02
   ========================================================= */
function createFactorLoadingsChart() {
  const ctx = document.getElementById('factor-loadings-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.factorLoadings;

  const barColors = d.loadings.map(v =>
    v >= 0.7 ? HC.green : v >= 0.5 ? HC.cyan : HC.orange
  );

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'Communality h²',
          data: d.communality,
          backgroundColor: barColors.map(c => c + '33'),
          borderColor: barColors.map(c => c + '66'),
          borderWidth: 1,
          borderRadius: 2,
          barPercentage: 0.85,
          categoryPercentage: 0.8
        },
        {
          label: 'Factor Loading λ',
          data: d.loadings,
          backgroundColor: barColors.map(c => c + 'cc'),
          borderColor: barColors,
          borderWidth: 2,
          borderRadius: 4,
          barPercentage: 0.6,
          categoryPercentage: 0.8
        }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1800, easing: 'easeOutQuart', delay: (ctx) => ctx.dataIndex * 100 },
      scales: {
        x: { min: 0, max: 1, title: { display: true, text: 'Valore', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { grid: { display: false }, ticks: { color: HC.text, font: { size: 11, weight: 'bold' } } }
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const i = ctx.dataIndex;
              return `Communality: ${d.communality[i].toFixed(3)}\nUniqueness: ${d.uniqueness[i].toFixed(3)}`;
            }
          }
        }
      }
    },
    plugins: [{
      id: 'loadingLabels',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();
        c.font = 'bold 10px JetBrains Mono';
        d.loadings.forEach((v, i) => {
          const x = scales.x.getPixelForValue(v) + 6;
          const y = scales.y.getPixelForValue(i);
          c.fillStyle = v >= 0.7 ? HC.green : v >= 0.5 ? HC.cyan : HC.orange;
          c.textAlign = 'left';
          c.textBaseline = 'middle';
          c.fillText(`λ=${v.toFixed(2)}`, x, y - 6);
        });
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #2  Bayesian Prior vs Posterior — Sez. 03
   ========================================================= */
function createBayesianPriorChart() {
  const ctx = document.getElementById('bayesian-prior-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.bayesian;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.xAxis,
      datasets: [
        {
          label: 'Prior Beta(2,2)',
          data: d.prior,
          borderColor: HC.muted,
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 0,
          tension: 0.4,
          fill: {
            target: 'origin',
            above: 'rgba(136,136,170,0.08)'
          }
        },
        {
          label: 'Posterior Beta(8,6)',
          data: d.posterior,
          borderColor: HC.green,
          borderWidth: 3,
          pointRadius: 0,
          tension: 0.4,
          fill: {
            target: 'origin',
            above: 'rgba(0,255,136,0.12)'
          }
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Attenzione (A)', color: HC.muted },
          ticks: { callback: (v, i) => i % 20 === 0 ? d.xAxis[i] : '', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          title: { display: true, text: 'Densità p(A)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'posteriorAnnotation',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        // MAP marker
        const mapIdx = d.posterior.indexOf(Math.max(...d.posterior));
        const mapX = scales.x.getPixelForValue(mapIdx);
        const mapY = scales.y.getPixelForValue(d.posterior[mapIdx]);
        // Vertical dashed line
        c.setLineDash([4, 3]);
        c.strokeStyle = HC.green + '88';
        c.lineWidth = 1;
        c.beginPath();
        c.moveTo(mapX, mapY);
        c.lineTo(mapX, scales.y.getPixelForValue(0));
        c.stroke();
        // Glow dot
        c.setLineDash([]);
        c.beginPath();
        c.arc(mapX, mapY, 6, 0, Math.PI * 2);
        c.fillStyle = HC.green;
        c.fill();
        c.beginPath();
        c.arc(mapX, mapY, 12, 0, Math.PI * 2);
        c.fillStyle = HC.green + '22';
        c.fill();
        // Label
        c.font = 'bold 11px JetBrains Mono';
        c.fillStyle = HC.green;
        c.textAlign = 'left';
        c.fillText(`MAP ≈ ${d.xAxis[mapIdx].toFixed(2)}`, mapX + 14, mapY - 4);
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #3  Bayesian Update (Line + CI band) — Sez. 03
   ========================================================= */
function createBayesianUpdateChart() {
  const ctx = document.getElementById('bayesian-update-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.bayesian.updateSteps;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'IC 90% superiore',
          data: d.ci_upper,
          borderColor: HC.cyan + '55',
          borderWidth: 1,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
          tension: 0.3
        },
        {
          label: 'E[A] (media post.)',
          data: d.means,
          borderColor: HC.green,
          borderWidth: 3,
          pointRadius: 7,
          pointBackgroundColor: d.means.map((_, i) => i === 0 ? HC.muted : HC.green),
          pointBorderColor: HC.bg,
          pointBorderWidth: 3,
          pointHoverRadius: 10,
          fill: false,
          tension: 0.3
        },
        {
          label: 'IC 90% inferiore',
          data: d.ci_lower,
          borderColor: HC.cyan + '55',
          borderWidth: 1,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: '-2',
          backgroundColor: HC.cyan + '12',
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: HC.muted, maxRotation: 25, font: { size: 9 } } },
        y: { min: 0, max: 1, title: { display: true, text: 'Stima di A', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'convergenceArrow',
      afterDraw(chart) {
        const { ctx: c, scales, chartArea } = chart;
        c.save();
        // Draw "convergenza" arrow
        const xStart = scales.x.getPixelForValue(2);
        const xEnd = scales.x.getPixelForValue(5);
        const yPos = scales.y.getPixelForValue(0.92);
        c.strokeStyle = HC.purple + 'aa';
        c.lineWidth = 1.5;
        c.setLineDash([]);
        c.beginPath();
        c.moveTo(xStart, yPos);
        c.lineTo(xEnd, yPos);
        c.stroke();
        // Arrowhead
        c.beginPath();
        c.moveTo(xEnd, yPos);
        c.lineTo(xEnd - 6, yPos - 4);
        c.lineTo(xEnd - 6, yPos + 4);
        c.closePath();
        c.fillStyle = HC.purple + 'aa';
        c.fill();
        // Label
        c.font = '10px JetBrains Mono';
        c.fillStyle = HC.purple;
        c.textAlign = 'center';
        c.fillText('convergenza →', (xStart + xEnd) / 2, yPos - 8);
        // Width annotation
        const w3 = scales.x.getPixelForValue(3);
        const yW = scales.y.getPixelForValue(d.ci_upper[3]);
        const yW2 = scales.y.getPixelForValue(d.ci_lower[3]);
        c.strokeStyle = HC.orange + '66';
        c.lineWidth = 1;
        c.setLineDash([2, 2]);
        c.beginPath();
        c.moveTo(w3 + 20, yW);
        c.lineTo(w3 + 20, yW2);
        c.stroke();
        c.setLineDash([]);
        c.font = '9px JetBrains Mono';
        c.fillStyle = HC.orange;
        c.textAlign = 'left';
        c.fillText('±' + ((d.ci_upper[3] - d.ci_lower[3]) / 2).toFixed(2), w3 + 24, (yW + yW2) / 2);
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #4  Mutual Information (Bar orizzontale) — Sez. 04
   ========================================================= */
function createMISignalsChart() {
  const ctx = document.getElementById('mi-signals-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.informationTheory.mutualInformation;
  const palette = [HC.green, HC.cyan, HC.purple, HC.orange, HC.yellow, HC.pink, HC.red];

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        label: 'I(Sᵢ ; A) [bit]',
        data: d.values,
        backgroundColor: palette.map(c => c + 'bb'),
        borderColor: palette,
        borderWidth: 2,
        borderRadius: 5,
        barPercentage: 0.7
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1600, easing: 'easeOutQuart', delay: ctx => ctx.dataIndex * 120 },
      scales: {
        x: { min: 0, max: 0.55, title: { display: true, text: 'Mutual Information [bit]', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { grid: { display: false }, ticks: { color: HC.text, font: { size: 10, weight: 'bold' } } }
      },
      plugins: { legend: { display: false } }
    },
    plugins: [{
      id: 'miLabels',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        d.values.forEach((v, i) => {
          const x = scales.x.getPixelForValue(v) + 6;
          const y = scales.y.getPixelForValue(i);
          c.font = 'bold 10px JetBrains Mono';
          c.fillStyle = palette[i];
          c.textAlign = 'left';
          c.textBaseline = 'middle';
          c.fillText(`${v.toFixed(3)} bit`, x, y);
          // Percentage of total
          const total = d.values.reduce((a, b) => a + b, 0);
          const pct = ((v / total) * 100).toFixed(0);
          c.font = '9px JetBrains Mono';
          c.fillStyle = HC.muted;
          c.fillText(`(${pct}%)`, x + 65, y);
        });
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #5  Conditional MI Heatmap (Canvas 2D) — Sez. 04
   ========================================================= */
function createConditionalMIChart() {
  const canvas = document.getElementById('conditional-mi-chart');
  if (!canvas) return;
  const d = HIDDEN_DATA.informationTheory.conditionalMI;
  const n = d.labels.length;

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.parentElement.clientWidth;
    const ch = Math.min(cw * 0.9, 440);
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const margin = { top: 55, right: 55, bottom: 15, left: 75 };
    const gw = cw - margin.left - margin.right;
    const gh = ch - margin.top - margin.bottom;
    const cellW = gw / n;
    const cellH = gh / n;

    ctx.fillStyle = HC.bg;
    ctx.fillRect(0, 0, cw, ch);

    const maxVal = 0.482;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const val = d.matrix[i][j];
        const t = val / maxVal;
        const cx = margin.left + j * cellW;
        const cy = margin.top + i * cellH;

        // Color interpolation: dark purple → green
        const r = Math.round(10 + t * 0);
        const g = Math.round(10 + t * 255);
        const b = Math.round(30 + t * 106);
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.2 + t * 0.8})`;

        // Rounded rect
        const pad = 1.5;
        const rr = 3;
        ctx.beginPath();
        ctx.roundRect(cx + pad, cy + pad, cellW - pad * 2, cellH - pad * 2, rr);
        ctx.fill();

        // Diagonal glow
        if (i === j) {
          ctx.strokeStyle = HC.green + '55';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.roundRect(cx + pad, cy + pad, cellW - pad * 2, cellH - pad * 2, rr);
          ctx.stroke();
        }

        // Value text
        ctx.fillStyle = t > 0.4 ? HC.bg : HC.text;
        ctx.font = 'bold 10px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(val.toFixed(2), cx + cellW / 2, cy + cellH / 2);
      }
    }

    // Column headers (top)
    ctx.fillStyle = HC.green;
    ctx.font = 'bold 10px JetBrains Mono';
    ctx.textAlign = 'center';
    for (let j = 0; j < n; j++) {
      ctx.save();
      ctx.translate(margin.left + j * cellW + cellW / 2, margin.top - 10);
      ctx.rotate(-0.5);
      ctx.fillText(d.labels[j], 0, 0);
      ctx.restore();
    }

    // Row headers (left)
    ctx.fillStyle = HC.text;
    ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < n; i++) {
      ctx.fillText(d.labels[i], margin.left - 8, margin.top + i * cellH + cellH / 2);
    }

    // Color bar legend
    const barX = cw - margin.right + 12;
    const barY = margin.top;
    const barW = 14;
    const barH = gh;
    for (let y = 0; y < barH; y++) {
      const t = 1 - y / barH;
      const r = Math.round(10 + t * 0);
      const g = Math.round(10 + t * 255);
      const b = Math.round(30 + t * 106);
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.2 + t * 0.8})`;
      ctx.fillRect(barX, barY + y, barW, 1);
    }
    ctx.strokeStyle = HC.muted + '44';
    ctx.lineWidth = 1;
    ctx.strokeRect(barX, barY, barW, barH);
    ctx.fillStyle = HC.muted;
    ctx.font = '9px JetBrains Mono';
    ctx.textAlign = 'left';
    ctx.fillText(maxVal.toFixed(2), barX + barW + 4, barY + 4);
    ctx.fillText('0', barX + barW + 4, barY + barH);
  }

  draw();
  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(draw, 150); });
}


/* =========================================================
   #6  KL Divergence (Grouped Bar) — Sez. 04
   ========================================================= */
function createKLDivergenceChart() {
  const ctx = document.getElementById('kl-divergence-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.informationTheory.klDivergence;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'D_KL(P‖Q) piattaforma→utente',
          data: d.platform_vs_user,
          backgroundColor: HC.green + 'aa',
          borderColor: HC.green,
          borderWidth: 2,
          borderRadius: 5,
          barPercentage: 0.45
        },
        {
          label: 'D_KL(Q‖P) utente→piattaforma',
          data: d.user_vs_platform,
          backgroundColor: HC.purple + 'aa',
          borderColor: HC.purple,
          borderWidth: 2,
          borderRadius: 5,
          barPercentage: 0.45
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: HC.text, font: { size: 10 } } },
        y: { title: { display: true, text: 'KL Divergence [nat]', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'botHighlight',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        // Highlight bot-like (index 2)
        const x = scales.x.getPixelForValue(2);
        const bw = (chartArea.right - chartArea.left) / d.labels.length;
        c.save();
        c.fillStyle = HC.red + '11';
        c.fillRect(x - bw / 2, chartArea.top, bw, chartArea.bottom - chartArea.top);
        c.font = '9px JetBrains Mono';
        c.fillStyle = HC.red;
        c.textAlign = 'center';
        c.fillText('⚠ anomaly', x, chartArea.top + 12);
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #7  Drift-Diffusion Paths — Sez. 05
   ========================================================= */
function createDriftPathsChart() {
  const ctx = document.getElementById('drift-paths-chart');
  if (!ctx) return;
  const dd = generateDriftPaths();

  const datasets = dd.paths.map(p => ({
    label: p.label,
    data: p.data,
    borderColor: HC[p.color],
    borderWidth: p.width,
    borderDash: p.dash || [],
    pointRadius: 0,
    tension: 0.2,
    spanGaps: false
  }));

  // Show only first 4 in legend
  datasets.forEach((ds, i) => { if (i >= 4) ds.label = undefined; });

  new Chart(ctx, {
    type: 'line',
    data: { labels: dd.timeAxis, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2500, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Tempo (s)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v, i) => i % 10 === 0 ? dd.timeAxis[i] : '', color: HC.muted }
        },
        y: {
          min: -1.3, max: 1.3,
          title: { display: true, text: 'Accumulatore A(t)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'barriers',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        const yUp = scales.y.getPixelForValue(1.0);
        const yLow = scales.y.getPixelForValue(-1.0);
        c.save();

        // Upper barrier zone
        const gUp = c.createLinearGradient(0, yUp - 20, 0, yUp + 10);
        gUp.addColorStop(0, HC.green + '00');
        gUp.addColorStop(1, HC.green + '15');
        c.fillStyle = gUp;
        c.fillRect(chartArea.left, yUp - 20, chartArea.right - chartArea.left, 30);

        // Lower barrier zone
        const gLow = c.createLinearGradient(0, yLow - 10, 0, yLow + 20);
        gLow.addColorStop(0, HC.red + '15');
        gLow.addColorStop(1, HC.red + '00');
        c.fillStyle = gLow;
        c.fillRect(chartArea.left, yLow - 10, chartArea.right - chartArea.left, 30);

        // Barrier lines
        c.setLineDash([10, 5]);
        c.lineWidth = 2;
        c.strokeStyle = HC.green + 'aa';
        c.beginPath(); c.moveTo(chartArea.left, yUp); c.lineTo(chartArea.right, yUp); c.stroke();
        c.strokeStyle = HC.red + 'aa';
        c.beginPath(); c.moveTo(chartArea.left, yLow); c.lineTo(chartArea.right, yLow); c.stroke();

        // Labels
        c.setLineDash([]);
        c.font = 'bold 11px JetBrains Mono';
        c.fillStyle = HC.green;
        c.textAlign = 'right';
        c.fillText('▲ ENGAGE', chartArea.right - 8, yUp - 8);
        c.fillStyle = HC.red;
        c.fillText('▼ SKIP', chartArea.right - 8, yLow + 16);

        // Zero line
        const y0 = scales.y.getPixelForValue(0);
        c.setLineDash([3, 5]);
        c.strokeStyle = HC.muted + '33';
        c.lineWidth = 1;
        c.beginPath(); c.moveTo(chartArea.left, y0); c.lineTo(chartArea.right, y0); c.stroke();

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #8  First Passage Time — Sez. 05
   ========================================================= */
function createFirstPassageChart() {
  const ctx = document.getElementById('first-passage-chart');
  if (!ctx) return;
  const fp = generateFirstPassage();

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: fp.timeAxis.map(t => t.toFixed(1)),
      datasets: [
        {
          label: 'Alto drift (μ=0.35)',
          data: fp.high,
          borderColor: HC.green,
          backgroundColor: HC.green + '18',
          borderWidth: 2.5,
          fill: true,
          pointRadius: 0,
          tension: 0.4
        },
        {
          label: 'Medio drift (μ=0.15)',
          data: fp.medium,
          borderColor: HC.cyan,
          backgroundColor: HC.cyan + '18',
          borderWidth: 2.5,
          fill: true,
          pointRadius: 0,
          tension: 0.4
        },
        {
          label: 'Basso drift (μ=0.03)',
          data: fp.low,
          borderColor: HC.orange,
          backgroundColor: HC.orange + '18',
          borderWidth: 2.5,
          fill: true,
          pointRadius: 0,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1800, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Tempo di decisione (s)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v, i) => i % 5 === 0 ? fp.timeAxis[i].toFixed(1) : '', color: HC.muted }
        },
        y: { title: { display: true, text: 'Densità f(T)', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'meanAnnotations',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        const means = [
          { t: 2.0, color: HC.green, label: 'E[T]=2.0s' },
          { t: 4.0, color: HC.cyan, label: 'E[T]=4.0s' },
          { t: 8.0, color: HC.orange, label: 'E[T]=8.0s' }
        ];
        means.forEach(m => {
          const idx = fp.timeAxis.findIndex(t => t >= m.t);
          if (idx < 0) return;
          const x = scales.x.getPixelForValue(idx);
          c.setLineDash([4, 3]);
          c.strokeStyle = m.color + '88';
          c.lineWidth = 1;
          c.beginPath();
          c.moveTo(x, scales.y.getPixelForValue(0));
          c.lineTo(x, scales.y.top);
          c.stroke();
          c.setLineDash([]);
          c.font = '9px JetBrains Mono';
          c.fillStyle = m.color;
          c.textAlign = 'center';
          c.fillText(m.label, x, scales.y.top + 12);
        });
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #9  Hawkes Intensity — Sez. 06
   ========================================================= */
function createHawkesIntensityChart() {
  const ctx = document.getElementById('hawkes-intensity-chart');
  if (!ctx) return;
  const hk = generateHawkes();

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: hk.timeAxis,
      datasets: [
        {
          label: 'Baseline μ₀',
          data: hk.baseline,
          borderColor: HC.muted,
          borderWidth: 1.5,
          borderDash: [8, 4],
          pointRadius: 0,
          tension: 0
        },
        {
          label: 'Subcritico (n*=0.5)',
          data: hk.subcritical,
          borderColor: HC.cyan,
          backgroundColor: HC.cyan + '12',
          borderWidth: 2.5,
          fill: true,
          pointRadius: 0,
          tension: 0.2
        },
        {
          label: 'Supercritico (n*=1.5)',
          data: hk.supercritical,
          borderColor: HC.red,
          backgroundColor: HC.red + '12',
          borderWidth: 3,
          fill: true,
          pointRadius: 0,
          tension: 0.2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2200, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Tempo (min)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v, i) => i % 5 === 0 ? hk.timeAxis[i] : '', color: HC.muted }
        },
        y: { title: { display: true, text: 'λ(t) Intensità eventi', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'hawkesEvents',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();

        // Event markers (subcritical)
        hk.subEvents.forEach(te => {
          const idx = hk.timeAxis.findIndex(t => t >= te);
          if (idx < 0) return;
          const x = scales.x.getPixelForValue(idx);
          // Triangle marker
          c.fillStyle = HC.cyan + 'cc';
          c.beginPath();
          c.moveTo(x, chartArea.bottom);
          c.lineTo(x - 4, chartArea.bottom + 8);
          c.lineTo(x + 4, chartArea.bottom + 8);
          c.closePath();
          c.fill();
        });

        // Event markers (supercritical) with glow
        hk.supEvents.slice(0, 6).forEach(te => {
          const idx = hk.timeAxis.findIndex(t => t >= te);
          if (idx < 0) return;
          const x = scales.x.getPixelForValue(idx);
          c.setLineDash([2, 3]);
          c.strokeStyle = HC.red + '44';
          c.lineWidth = 1;
          c.beginPath();
          c.moveTo(x, chartArea.top);
          c.lineTo(x, chartArea.bottom);
          c.stroke();
        });

        // "Esplosione virale" label
        c.setLineDash([]);
        c.font = 'bold 10px JetBrains Mono';
        c.fillStyle = HC.red;
        c.textAlign = 'center';
        const xMid = scales.x.getPixelForValue(Math.floor(hk.timeAxis.length * 0.6));
        const yMid = scales.y.getPixelForValue(Math.max(...hk.supercritical) * 0.85);
        c.fillText('↗ Cascata virale', xMid, yMid);

        // "Decadimento" label
        c.fillStyle = HC.cyan;
        const xSub = scales.x.getPixelForValue(Math.floor(hk.timeAxis.length * 0.55));
        const ySub = scales.y.getPixelForValue(1.2);
        c.fillText('↘ Decadimento', xSub, ySub);

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #10  Hawkes Phase Diagram (Scatter) — Sez. 06
   ========================================================= */
function createHawkesPhaseChart() {
  const ctx = document.getElementById('hawkes-phase-chart');
  if (!ctx) return;
  const ph = generatePhasePoints();

  new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Subcritico (n*<0.9)',
          data: ph.sub.map(p => ({ x: p.x, y: p.y })),
          backgroundColor: HC.cyan + '88',
          borderColor: HC.cyan,
          borderWidth: 1,
          pointRadius: 5,
          pointHoverRadius: 8
        },
        {
          label: 'Critico (0.9≤n*≤1.1)',
          data: ph.crit.map(p => ({ x: p.x, y: p.y })),
          backgroundColor: HC.orange + 'cc',
          borderColor: HC.orange,
          borderWidth: 2,
          pointRadius: 7,
          pointHoverRadius: 10,
          pointStyle: 'triangle'
        },
        {
          label: 'Supercritico (n*>1.1)',
          data: ph.sup.map(p => ({ x: p.x, y: p.y })),
          backgroundColor: HC.red + '88',
          borderColor: HC.red,
          borderWidth: 1,
          pointRadius: 5,
          pointHoverRadius: 8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1800, easing: 'easeOutQuart' },
      scales: {
        x: { title: { display: true, text: 'α (eccitazione)', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { title: { display: true, text: 'β (decadimento)', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: ctx => {
              const ns = ctx.raw.x / ctx.raw.y;
              return ` α=${ctx.raw.x.toFixed(2)}, β=${ctx.raw.y.toFixed(2)}, n*=${ns.toFixed(2)}`;
            }
          }
        }
      }
    },
    plugins: [{
      id: 'criticalRegion',
      beforeDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();
        // Draw n*=1 line (α=β)
        const x0 = scales.x.getPixelForValue(0);
        const y0 = scales.y.getPixelForValue(0);
        const xMax = scales.x.max || 2;
        const xEnd = scales.x.getPixelForValue(xMax);
        const yEnd = scales.y.getPixelForValue(xMax);
        c.setLineDash([8, 4]);
        c.strokeStyle = HC.orange + 'aa';
        c.lineWidth = 2;
        c.beginPath();
        c.moveTo(x0, y0);
        c.lineTo(xEnd, yEnd);
        c.stroke();

        // Shade supercritical region (above line = α>β)
        c.setLineDash([]);
        c.fillStyle = HC.red + '08';
        c.beginPath();
        c.moveTo(x0, y0);
        c.lineTo(xEnd, yEnd);
        c.lineTo(xEnd, chartArea.top);
        c.lineTo(x0, chartArea.top);
        c.closePath();
        c.fill();

        // Label
        c.font = 'bold 10px JetBrains Mono';
        c.fillStyle = HC.orange;
        c.textAlign = 'center';
        const midX = (x0 + xEnd) / 2;
        const midY = (y0 + yEnd) / 2;
        c.save();
        c.translate(midX, midY);
        c.rotate(Math.atan2(yEnd - y0, xEnd - x0));
        c.fillText('n*=1 (α=β)', 0, -10);
        c.restore();

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #11  Fisher Information (Bar orizzontale) — Sez. 07
   ========================================================= */
function createFisherInfoChart() {
  const ctx = document.getElementById('fisher-info-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.fisher;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        label: 'Fisher Information I(A)',
        data: d.fisherInfo,
        backgroundColor: (ctx) => {
          const chart = ctx.chart;
          const { chartArea } = chart;
          if (!chartArea) return HC.green + 'cc';
          const i = ctx.dataIndex;
          const c = chart.ctx;
          const g = c.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
          const color = i === 0 ? HC.green : i < 3 ? HC.cyan : HC.purple;
          g.addColorStop(0, color + '44');
          g.addColorStop(1, color + 'cc');
          return g;
        },
        borderColor: d.fisherInfo.map((_, i) => i === 0 ? HC.green : i < 3 ? HC.cyan : HC.purple),
        borderWidth: 2,
        borderRadius: 5,
        barPercentage: 0.7
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1600, easing: 'easeOutQuart', delay: ctx => ctx.dataIndex * 100 },
      scales: {
        x: { min: 0, title: { display: true, text: 'Fisher Information', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { grid: { display: false }, ticks: { color: HC.text, font: { size: 10, weight: 'bold' } } }
      },
      plugins: { legend: { display: false } }
    },
    plugins: [{
      id: 'fisherPctLabels',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        d.fisherInfo.forEach((v, i) => {
          const x = scales.x.getPixelForValue(v) + 6;
          const y = scales.y.getPixelForValue(i);
          const color = i === 0 ? HC.green : i < 3 ? HC.cyan : HC.purple;
          // Value
          c.font = 'bold 11px JetBrains Mono';
          c.fillStyle = color;
          c.textAlign = 'left';
          c.textBaseline = 'middle';
          c.fillText(v.toFixed(2), x, y - 1);
          // Percentage chip
          c.font = '9px JetBrains Mono';
          c.fillStyle = HC.muted;
          c.fillText(`(${d.fisherPercent[i]}%)`, x + 38, y - 1);
        });
        // dwellTime callout
        const x0 = scales.x.getPixelForValue(d.fisherInfo[0]);
        const y0 = scales.y.getPixelForValue(0);
        c.font = 'bold 9px JetBrains Mono';
        c.fillStyle = HC.green;
        c.textAlign = 'left';
        c.fillText('← 52% del totale!', x0 + 80, y0 - 1);
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #12  Cramér-Rao Bound — Sez. 07
   ========================================================= */
function createCramerRaoChart() {
  const ctx = document.getElementById('cramer-rao-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.fisher.cramerRao;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.numSignals.map(n => `${n} segnale${n > 1 ? 'i' : ''}`),
      datasets: [
        {
          label: 'Cramér-Rao Bound 1/I(A)',
          data: d.bound,
          borderColor: HC.green,
          borderWidth: 3,
          pointRadius: 7,
          pointBackgroundColor: HC.green,
          pointBorderColor: HC.bg,
          pointBorderWidth: 3,
          pointHoverRadius: 10,
          fill: {
            target: 'origin',
            above: 'rgba(0,255,136,0.10)'
          },
          tension: 0.3
        },
        {
          label: 'Varianza empirica osservata',
          data: d.empiricalVar,
          borderColor: HC.orange,
          borderWidth: 2.5,
          borderDash: [8, 4],
          pointRadius: 6,
          pointBackgroundColor: HC.orange,
          pointBorderColor: HC.bg,
          pointBorderWidth: 2,
          pointStyle: 'triangle',
          fill: false,
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1800, easing: 'easeOutQuart' },
      scales: {
        x: { title: { display: true, text: 'Segnali osservati', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { title: { display: true, text: 'Var(Â)', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'gapAnnotation',
      afterDraw(chart) {
        const { ctx: c, scales } = chart;
        c.save();
        // Show gap between bound and empirical at signal 3
        const idx = 2; // 3 segnali
        const xP = scales.x.getPixelForValue(idx);
        const yB = scales.y.getPixelForValue(d.bound[idx]);
        const yE = scales.y.getPixelForValue(d.empiricalVar[idx]);
        c.strokeStyle = HC.red + '66';
        c.lineWidth = 1;
        c.setLineDash([2, 2]);
        c.beginPath();
        c.moveTo(xP + 16, yB);
        c.lineTo(xP + 16, yE);
        c.stroke();
        c.setLineDash([]);
        c.font = '9px JetBrains Mono';
        c.fillStyle = HC.red;
        c.textAlign = 'left';
        c.fillText('gap', xP + 20, (yB + yE) / 2);
        // "Solo dwellTime" callout
        const x1 = scales.x.getPixelForValue(0);
        const y1 = scales.y.getPixelForValue(d.bound[0]);
        c.font = '9px JetBrains Mono';
        c.fillStyle = HC.muted;
        c.textAlign = 'center';
        c.fillText('solo dwell', x1, y1 - 14);
        c.restore();
      }
    }]
  });
}


/* =========================================================
   #13  Score Landscape (Scatter colorato) — Sez. 08
   ========================================================= */
function createScoreLandscapeChart() {
  const canvas = document.getElementById('score-landscape-chart');
  if (!canvas) return;
  const pts = generateScoreLandscape();

  // Use canvas 2D for proper color interpolation
  const c = canvas.getContext('2d');
  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.parentElement.clientWidth;
    const ch = Math.min(cw * 0.75, 450);
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    c.scale(dpr, dpr);

    const margin = { top: 30, right: 60, bottom: 45, left: 55 };
    const gw = cw - margin.left - margin.right;
    const gh = ch - margin.top - margin.bottom;

    c.fillStyle = HC.bg;
    c.fillRect(0, 0, cw, ch);

    // Grid
    c.strokeStyle = 'rgba(255,255,255,0.06)';
    c.lineWidth = 0.5;
    for (let i = 0; i <= 10; i++) {
      const x = margin.left + (i / 10) * gw;
      const y = margin.top + (i / 10) * gh;
      c.beginPath(); c.moveTo(x, margin.top); c.lineTo(x, margin.top + gh); c.stroke();
      c.beginPath(); c.moveTo(margin.left, y); c.lineTo(margin.left + gw, y); c.stroke();
    }

    // Plot points as soft glowing circles
    pts.forEach(p => {
      const x = margin.left + p.dwell * gw;
      const y = margin.top + (1 - p.binary) * gh;
      const r = 4 + p.score * 10;

      // Color based on score
      let col;
      if (p.score >= 0.7) col = HC.green;
      else if (p.score >= 0.4) col = HC.cyan;
      else if (p.score >= 0.2) col = HC.orange;
      else col = HC.red;

      // Glow
      const glow = c.createRadialGradient(x, y, 0, x, y, r * 2.5);
      glow.addColorStop(0, col + '44');
      glow.addColorStop(1, col + '00');
      c.fillStyle = glow;
      c.fillRect(x - r * 2.5, y - r * 2.5, r * 5, r * 5);

      // Point
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fillStyle = col + 'cc';
      c.fill();
      c.strokeStyle = col;
      c.lineWidth = 1;
      c.stroke();
    });

    // Axis labels
    c.font = '10px JetBrains Mono';
    c.fillStyle = HC.muted;
    c.textAlign = 'center';
    c.fillText('Dwell Time (normalizzato) →', margin.left + gw / 2, ch - 5);
    c.save();
    c.translate(12, margin.top + gh / 2);
    c.rotate(-Math.PI / 2);
    c.fillText('Segnali binari attivati →', 0, 0);
    c.restore();

    // Axis ticks
    c.font = '9px JetBrains Mono';
    c.fillStyle = HC.muted;
    for (let i = 0; i <= 10; i += 2) {
      const v = (i / 10).toFixed(1);
      c.textAlign = 'center';
      c.fillText(v, margin.left + (i / 10) * gw, margin.top + gh + 16);
      c.textAlign = 'right';
      c.fillText(v, margin.left - 6, margin.top + (1 - i / 10) * gh + 3);
    }

    // Score color bar
    const barX = cw - margin.right + 12;
    const barY = margin.top;
    const barW = 12;
    const barH = gh;
    for (let y = 0; y < barH; y++) {
      const t = 1 - y / barH;
      let col;
      if (t >= 0.7) col = HC.green;
      else if (t >= 0.4) col = HC.cyan;
      else if (t >= 0.2) col = HC.orange;
      else col = HC.red;
      c.fillStyle = col + 'cc';
      c.fillRect(barX, barY + y, barW, 1);
    }
    c.strokeStyle = HC.muted + '44';
    c.lineWidth = 1;
    c.strokeRect(barX, barY, barW, barH);
    c.font = '9px JetBrains Mono';
    c.fillStyle = HC.muted;
    c.textAlign = 'left';
    c.fillText('1.0', barX + barW + 3, barY + 4);
    c.fillText('0.5', barX + barW + 3, barY + barH / 2);
    c.fillText('0', barX + barW + 3, barY + barH);

    // Region labels
    c.font = 'bold 10px JetBrains Mono';
    c.globalAlpha = 0.5;
    c.fillStyle = HC.red;
    c.textAlign = 'left';
    c.fillText('SCROLL', margin.left + 10, margin.top + gh - 10);
    c.fillStyle = HC.green;
    c.textAlign = 'right';
    c.fillText('VIRALE', margin.left + gw - 10, margin.top + 18);
    c.globalAlpha = 1;
  }

  draw();
  let rt;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 150); });
}


/* =========================================================
   #14  Sensitivity ∂S/∂segnale (Bar) — Sez. 08
   ========================================================= */
function createSensitivityChart() {
  const ctx = document.getElementById('sensitivity-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.scoreFunction.sensitivity;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.labels,
      datasets: [{
        label: '∂S/∂segnale',
        data: d.dS_dsignal,
        backgroundColor: d.dS_dsignal.map(v => v >= 0 ? HC.green + 'bb' : HC.red + 'bb'),
        borderColor: d.dS_dsignal.map(v => v >= 0 ? HC.green : HC.red),
        borderWidth: 2,
        borderRadius: 5,
        barPercentage: 0.65
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 1500, easing: 'easeOutQuart' },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: HC.muted, maxRotation: 45, font: { size: 9 } } },
        y: { title: { display: true, text: '∂S/∂sᵢ (sensitività marginale)', color: HC.muted }, grid: { color: 'rgba(255,255,255,0.04)' } }
      },
      plugins: { legend: { display: false } }
    },
    plugins: [{
      id: 'sensitivityAnnotations',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();
        // Zero line
        const y0 = scales.y.getPixelForValue(0);
        c.strokeStyle = HC.muted + '55';
        c.lineWidth = 1.5;
        c.setLineDash([]);
        c.beginPath();
        c.moveTo(chartArea.left, y0);
        c.lineTo(chartArea.right, y0);
        c.stroke();

        // Negative zone shading
        c.fillStyle = HC.red + '08';
        c.fillRect(chartArea.left, y0, chartArea.right - chartArea.left, chartArea.bottom - y0);

        // Labels on bars
        d.dS_dsignal.forEach((v, i) => {
          const x = scales.x.getPixelForValue(i);
          const y = scales.y.getPixelForValue(v);
          c.font = 'bold 10px JetBrains Mono';
          c.fillStyle = v >= 0 ? HC.green : HC.red;
          c.textAlign = 'center';
          c.fillText((v > 0 ? '+' : '') + v.toFixed(3), x, y + (v >= 0 ? -8 : 14));
        });

        // Penalty zone label
        c.font = 'bold 9px JetBrains Mono';
        c.fillStyle = HC.red + 'aa';
        c.textAlign = 'right';
        c.fillText('⚠ PENALITÀ', chartArea.right - 5, chartArea.bottom - 5);

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #15  Bifurcation — Sez. 09
   ========================================================= */
function createBifurcationChart() {
  const ctx = document.getElementById('bifurcation-chart');
  if (!ctx) return;
  const bf = generateBifurcation();

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: bf.rate.map(r => r.toFixed(2)),
      datasets: [
        {
          label: 'Subcritico (tweet muore)',
          data: bf.sub,
          borderColor: HC.cyan,
          backgroundColor: HC.cyan + '10',
          borderWidth: 3,
          fill: true,
          pointRadius: 0,
          tension: 0.3
        },
        {
          label: 'Supercritico (amplificazione)',
          data: bf.sup,
          borderColor: HC.red,
          backgroundColor: HC.red + '10',
          borderWidth: 3,
          fill: true,
          pointRadius: 0,
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2200, easing: 'easeOutQuart' },
      scales: {
        x: {
          title: { display: true, text: 'Engagement rate iniziale', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v, i) => i % 10 === 0 ? bf.rate[i].toFixed(2) : '', color: HC.muted }
        },
        y: {
          type: 'logarithmic',
          title: { display: true, text: 'Reach (scala log)', color: HC.muted },
          grid: { color: 'rgba(255,255,255,0.04)' },
          min: 0.05
        }
      },
      plugins: { legend: { position: 'top' } }
    },
    plugins: [{
      id: 'bifurcationPoint',
      afterDraw(chart) {
        const { ctx: c, chartArea, scales } = chart;
        c.save();
        const critIdx = bf.critIdx;
        const critX = scales.x.getPixelForValue(critIdx);
        const critY = scales.y.getPixelForValue(bf.sub[critIdx]);

        // Vertical line at critical point
        c.setLineDash([6, 4]);
        c.strokeStyle = HC.orange + 'aa';
        c.lineWidth = 2;
        c.beginPath();
        c.moveTo(critX, chartArea.top);
        c.lineTo(critX, chartArea.bottom);
        c.stroke();

        // Pulsing circle
        c.setLineDash([]);
        c.beginPath();
        c.arc(critX, critY, 10, 0, Math.PI * 2);
        c.fillStyle = HC.orange + '44';
        c.fill();
        c.beginPath();
        c.arc(critX, critY, 6, 0, Math.PI * 2);
        c.fillStyle = HC.orange;
        c.fill();

        // Label
        c.font = 'bold 11px JetBrains Mono';
        c.fillStyle = HC.orange;
        c.textAlign = 'left';
        c.fillText('BIFORCAZIONE', critX + 14, critY - 12);
        c.font = '9px JetBrains Mono';
        c.fillStyle = HC.muted;
        c.fillText(`γ_crit ≈ ${bf.rate[critIdx].toFixed(2)}`, critX + 14, critY + 2);

        // Left zone label
        c.font = '10px JetBrains Mono';
        c.fillStyle = HC.cyan + 'aa';
        c.textAlign = 'center';
        c.fillText('MORTE', scales.x.getPixelForValue(3), chartArea.top + 20);

        // Right zone label
        c.fillStyle = HC.red + 'aa';
        c.fillText('ESPLOSIONE', scales.x.getPixelForValue(45), chartArea.top + 20);

        c.restore();
      }
    }]
  });
}


/* =========================================================
   #16  Strategy Radar — Sez. 10
   ========================================================= */
function createStrategyRadarChart() {
  const ctx = document.getElementById('strategy-radar-chart');
  if (!ctx) return;
  const d = HIDDEN_DATA.strategyRadar;

  new Chart(ctx, {
    type: 'radar',
    data: {
      labels: d.labels,
      datasets: [
        {
          label: 'Strategia ottimale',
          data: d.optimal,
          borderColor: HC.green,
          backgroundColor: HC.green + '1a',
          borderWidth: 3,
          pointBackgroundColor: HC.green,
          pointBorderColor: HC.bg,
          pointBorderWidth: 3,
          pointRadius: 5,
          pointHoverRadius: 8
        },
        {
          label: 'Strategia avanzata',
          data: d.advanced,
          borderColor: HC.cyan,
          backgroundColor: HC.cyan + '12',
          borderWidth: 2,
          pointBackgroundColor: HC.cyan,
          pointBorderColor: HC.bg,
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 7
        },
        {
          label: 'Utente medio',
          data: d.average,
          borderColor: HC.muted,
          backgroundColor: HC.muted + '10',
          borderWidth: 2,
          borderDash: [6, 3],
          pointBackgroundColor: HC.muted,
          pointBorderColor: HC.bg,
          pointBorderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      scales: {
        r: {
          min: 0, max: 100,
          angleLines: { color: 'rgba(255,255,255,0.08)', lineWidth: 1 },
          grid: { color: 'rgba(255,255,255,0.06)', lineWidth: 1 },
          pointLabels: {
            color: HC.text,
            font: { family: "'JetBrains Mono', monospace", size: 10, weight: 'bold' }
          },
          ticks: {
            color: HC.muted + '88',
            backdropColor: 'transparent',
            font: { size: 8 },
            stepSize: 25,
            callback: v => v + '%'
          }
        }
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.r}%`
          }
        }
      }
    }
  });
}


/* =========================================================
   INIT — Lazy loading con IntersectionObserver
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  setupHiddenChartDefaults();

  const charts = {
    'factor-loadings-chart':   createFactorLoadingsChart,
    'bayesian-prior-chart':    createBayesianPriorChart,
    'bayesian-update-chart':   createBayesianUpdateChart,
    'mi-signals-chart':        createMISignalsChart,
    'conditional-mi-chart':    createConditionalMIChart,
    'kl-divergence-chart':     createKLDivergenceChart,
    'drift-paths-chart':       createDriftPathsChart,
    'first-passage-chart':     createFirstPassageChart,
    'hawkes-intensity-chart':  createHawkesIntensityChart,
    'hawkes-phase-chart':      createHawkesPhaseChart,
    'fisher-info-chart':       createFisherInfoChart,
    'cramer-rao-chart':        createCramerRaoChart,
    'score-landscape-chart':   createScoreLandscapeChart,
    'sensitivity-chart':       createSensitivityChart,
    'bifurcation-chart':       createBifurcationChart,
    'strategy-radar-chart':    createStrategyRadarChart
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
