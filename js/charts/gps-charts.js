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
   * Chart 1: Drift 24h — km di deriva senza vs con correzione
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('drift-24h-chart');
    if (!ctx) return;

    var labels = [];
    var driftNoCorrKm = [];
    var driftCorrM = [];

    /* 38.512 us/giorno => 11545.6 m/giorno => 0.481 km/ora senza correzione */
    var driftRate_m_per_hour = 11545.6 / 24;

    for (var h = 0; h <= 24; h++) {
      labels.push(h + 'h');
      driftNoCorrKm.push(Math.round(driftRate_m_per_hour * h) / 1000);
      /* Con correzione: errore tipico GPS ~3-5 m, random walk */
      driftCorrM.push(h === 0 ? 0 : Math.round((3 + Math.random() * 2) * 100) / 100);
    }

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Senza correzione (km)',
            data: driftNoCorrKm,
            borderColor: RED,
            backgroundColor: RED + '20',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 6,
            yAxisID: 'y'
          },
          {
            label: 'Con correzione (m)',
            data: driftCorrM,
            borderColor: GREEN,
            backgroundColor: GREEN + '20',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 6,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: baseLegend,
          tooltip: baseTooltip
        },
        scales: {
          x: {
            title: { display: true, text: 'Ore', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          },
          y: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'Deriva senza correzione (km)', color: RED, font: { family: FONT_MONO, size: 10 } },
            ticks: { color: RED, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          },
          y1: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'Errore con correzione (m)', color: GREEN, font: { family: FONT_MONO, size: 10 } },
            ticks: { color: GREEN, font: { family: FONT_MONO, size: 10 } },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Mappa Leaflet: percorso GPS reale su mappa stradale
   * ======================================================== */
  (function() {
    var mapEl = document.getElementById('gps-map');
    if (!mapEl || typeof L === 'undefined') return;

    var coords = [
      [45.01638,9.6772],[45.13784,10.07042],[45.14043,10.07117],[45.14305,10.07192],
      [45.14564,10.07269],[45.14817,10.07336],[45.15076,10.07412],[45.15344,10.07496],
      [45.1561,10.07606],[45.1588,10.07751],[45.16154,10.07906],[45.1642,10.08059],
      [45.16682,10.08209],[45.16938,10.08354],[45.17178,10.08489],[45.17406,10.08619],
      [45.17637,10.08751],[45.17888,10.08894],[45.18142,10.09036],[45.18393,10.09178],
      [45.18646,10.09323],[45.18888,10.09462],[45.191,10.09583],[45.19305,10.09698],
      [45.19517,10.09818],[45.19751,10.09951],[45.19995,10.10089],[45.20246,10.10233],
      [45.2049,10.10379],[45.20733,10.10519],[45.20971,10.10652],[45.21209,10.10785],
      [45.21452,10.10925],[45.21706,10.11069],[45.21963,10.11214],[45.22222,10.11336],
      [45.22483,10.11423],[45.22728,10.115],[45.22957,10.1157],[45.32661,10.15041],
      [45.3316,10.15292],[45.33644,10.15532],[45.34131,10.15769],[45.34609,10.16006],
      [45.35083,10.16242],[45.35534,10.16468],[45.36022,10.16713],[45.36503,10.16953],
      [45.3696,10.17187],[45.37372,10.17401],[45.37864,10.17652],[45.38359,10.17904],
      [45.38852,10.18165],[45.39365,10.18425],[45.39887,10.18688],[45.40396,10.18942],
      [45.4088,10.19185],[45.41363,10.19428],[45.41858,10.19674],[45.42386,10.19938],
      [45.42916,10.20207],[45.43447,10.20469],[45.43963,10.20711],[45.44415,10.20931],
      [45.44586,10.21039],[45.44609,10.21126],[45.4464,10.21123],[45.44636,10.21126],
      [45.44652,10.21137],[45.44631,10.21121],[45.44621,10.21117],[45.44678,10.21128],
      [45.44834,10.21125],[45.45165,10.2128],[45.45569,10.21468],[45.45988,10.21662],
      [45.46544,10.21905],[45.46983,10.22053],[45.47423,10.222],[45.47903,10.22362],
      [45.48368,10.22515],[45.48857,10.22671],[45.49396,10.22865],[45.49844,10.23219],
      [45.50175,10.23651],[45.5038,10.24048],[45.5032,10.24519],[45.502,10.25062],
      [45.50047,10.25586],[45.49883,10.26171],[45.49715,10.26769],[45.49479,10.27593],
      [45.49348,10.28145],[45.49087,10.28765],[45.48921,10.29327],[45.48788,10.29908],
      [45.48649,10.30453],[45.48511,10.31009],[45.48368,10.31576],[45.48231,10.3218],
      [45.48106,10.32738],[45.47977,10.33322],[45.47837,10.33947],[45.47698,10.34561],
      [45.47573,10.35124],[45.47434,10.35749],[45.47272,10.36448],[45.47128,10.37088],
      [45.46991,10.37697],[45.46853,10.38309],[45.4674,10.38937],[45.4663,10.396],
      [45.46541,10.40286],[45.46483,10.40963],[45.4643,10.41608],[45.46381,10.42244],
      [45.46322,10.42927],[45.46204,10.43608],[45.46067,10.44275],[45.45929,10.44951],
      [45.4577,10.45651],[45.45605,10.46312],[45.45442,10.46988],[45.45369,10.47746],
      [45.45323,10.48485],[45.45248,10.4914],[45.45166,10.4981],[45.45098,10.50604],
      [45.45019,10.51431],[45.44935,10.52282],[45.44775,10.53104],[45.44553,10.53889],
      [45.44402,10.54698],[45.44261,10.55459],[45.44127,10.56185],[45.43985,10.56955],
      [45.43842,10.57738],[45.43721,10.58384],[45.43594,10.59066],[45.43463,10.59808],
      [45.43401,10.60595],[45.4336,10.61414],[45.43319,10.62265],[45.43277,10.6312],
      [45.43236,10.63972],[45.43181,10.64807],[45.43144,10.65383],[45.43101,10.66049],
      [45.43054,10.66759],[45.43011,10.67429],[45.4296,10.68202],[45.42921,10.69007],
      [45.42925,10.69749],[45.42931,10.70507],[45.42935,10.71285],[45.42941,10.72073],
      [45.42935,10.72902],[45.42864,10.7369],[45.42788,10.74437],[45.4271,10.75202],
      [45.4263,10.75971],[45.42547,10.76762],[45.42387,10.77512],[45.42153,10.78112],
      [45.41951,10.78725],[45.41796,10.79441],[45.41705,10.80204],[45.41625,10.8097],
      [45.41646,10.81741],[45.41703,10.82521],[45.41762,10.83309],[45.41781,10.84108],
      [45.41682,10.84907],[45.4154,10.85712],[45.41465,10.86532],[45.41418,10.87326],
      [45.41373,10.881],[45.41332,10.8883],[45.41249,10.89571],[45.41072,10.90303],
      [45.40866,10.91044],[45.40665,10.91794],[45.40464,10.9252],[45.40313,10.93209],
      [45.4018,10.93888],[45.40028,10.94624],[45.39883,10.95331],[45.39784,10.95989],
      [45.3974,10.96593],[45.39719,10.9685],[45.39654,10.96922],[45.39725,10.96752],
      [45.39946,10.97035],[45.40008,10.97229],[45.40039,10.97277]
    ];

    var map = L.map(mapEl, { scrollWheelZoom: false }).setView([45.2084, 10.325], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(map);

    /* Traccia GPS */
    L.polyline(coords, {
      color: '#4ecdc4',
      weight: 3,
      opacity: 0.9
    }).addTo(map);

    /* Marker partenza */
    L.circleMarker(coords[0], {
      radius: 8,
      fillColor: '#00ff88',
      color: '#00ff88',
      weight: 2,
      fillOpacity: 0.9
    }).addTo(map).bindPopup('<b>Partenza</b><br>45.016\u00b0N, 9.677\u00b0E');

    /* Marker arrivo */
    L.circleMarker(coords[coords.length - 1], {
      radius: 8,
      fillColor: '#ff6b6b',
      color: '#ff6b6b',
      weight: 2,
      fillOpacity: 0.9
    }).addTo(map).bindPopup('<b>Arrivo — Verona</b><br>45.400\u00b0N, 10.973\u00b0E');

    /* Fit bounds */
    map.fitBounds(L.polyline(coords).getBounds().pad(0.1));
  })();

  /* ========================================================
   * Chart 2: Time dilation breakdown — SR vs GR vs netto
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('time-dilation-chart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Speciale (SR)', 'Generale (GR)', 'Netto'],
        datasets: [{
          label: 'us/giorno',
          data: [-7.214, 45.726, 38.512],
          backgroundColor: [CYAN, PURPLE, GREEN],
          borderColor: [CYAN, PURPLE, GREEN],
          borderWidth: 0,
          borderRadius: 4
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
              label: function(item) {
                return item.raw.toFixed(3) + ' us/giorno';
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            grid: { display: false }
          },
          y: {
            title: { display: true, text: 'us/giorno', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 3: Position scatter — traccia GPS reale iPhone
   * Dati: viaggio Piacenza-Verona, 26 feb 2026, 101 min
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('position-scatter-chart');
    if (!ctx) return;

    /* Percorso reale: offset in km dal punto di partenza */
    var routeData = [
      {x:0.0,y:0.0},{x:30.91,y:13.51},{x:30.97,y:13.79},{x:31.03,y:14.08},
      {x:31.09,y:14.37},{x:31.14,y:14.66},{x:31.2,y:14.94},{x:31.27,y:15.24},
      {x:31.35,y:15.54},{x:31.47,y:15.84},{x:31.59,y:16.14},{x:31.71,y:16.44},
      {x:31.83,y:16.73},{x:31.94,y:17.01},{x:32.05,y:17.28},{x:32.15,y:17.53},
      {x:32.25,y:17.79},{x:32.36,y:18.07},{x:32.48,y:18.35},{x:32.59,y:18.63},
      {x:32.7,y:18.91},{x:32.81,y:19.18},{x:32.91,y:19.42},{x:33.0,y:19.65},
      {x:33.09,y:19.88},{x:33.2,y:20.14},{x:33.3,y:20.41},{x:33.42,y:20.69},
      {x:33.53,y:20.96},{x:33.64,y:21.23},{x:33.75,y:21.5},{x:33.85,y:21.76},
      {x:33.96,y:22.03},{x:34.07,y:22.31},{x:34.19,y:22.6},{x:34.28,y:22.89},
      {x:34.35,y:23.18},{x:34.41,y:23.45},{x:34.47,y:23.71},{x:37.2,y:34.5},
      {x:37.39,y:35.05},{x:37.58,y:35.59},{x:37.77,y:36.13},{x:37.95,y:36.66},
      {x:38.14,y:37.19},{x:38.32,y:37.69},{x:38.51,y:38.23},{x:38.7,y:38.77},
      {x:38.88,y:39.28},{x:39.05,y:39.73},{x:39.25,y:40.28},{x:39.45,y:40.83},
      {x:39.65,y:41.38},{x:39.86,y:41.95},{x:40.06,y:42.53},{x:40.26,y:43.1},
      {x:40.45,y:43.64},{x:40.64,y:44.17},{x:40.84,y:44.72},{x:41.05,y:45.31},
      {x:41.26,y:45.9},{x:41.46,y:46.49},{x:41.65,y:47.06},{x:41.83,y:47.57},
      {x:41.91,y:47.76},{x:41.98,y:47.78},{x:41.98,y:47.82},{x:41.98,y:47.81},
      {x:41.99,y:47.83},{x:41.98,y:47.81},{x:41.97,y:47.8},{x:41.98,y:47.86},
      {x:41.98,y:48.03},{x:42.1,y:48.4},{x:42.25,y:48.85},{x:42.4,y:49.31},
      {x:42.59,y:49.93},{x:42.71,y:50.42},{x:42.82,y:50.91},{x:42.95,y:51.44},
      {x:43.07,y:51.96},{x:43.19,y:52.51},{x:43.35,y:53.1},{x:43.62,y:53.6},
      {x:43.96,y:53.97},{x:44.28,y:54.2},{x:44.65,y:54.13},{x:45.07,y:54.0},
      {x:45.48,y:53.83},{x:45.94,y:53.65},{x:46.41,y:53.46},{x:47.06,y:53.2},
      {x:47.5,y:53.05},{x:47.98,y:52.76},{x:48.43,y:52.58},{x:48.88,y:52.43},
      {x:49.31,y:52.27},{x:49.75,y:52.12},{x:50.19,y:51.96},{x:50.67,y:51.81},
      {x:51.11,y:51.67},{x:51.57,y:51.53},{x:52.06,y:51.37},{x:52.54,y:51.22},
      {x:52.98,y:51.08},{x:53.47,y:50.92},{x:54.02,y:50.74},{x:54.53,y:50.58},
      {x:55.0,y:50.43},{x:55.49,y:50.28},{x:55.98,y:50.15},{x:56.5,y:50.03},
      {x:57.04,y:49.93},{x:57.57,y:49.87},{x:58.08,y:49.81},{x:58.58,y:49.75},
      {x:59.12,y:49.69},{x:59.65,y:49.56},{x:60.18,y:49.4},{x:60.71,y:49.25},
      {x:61.26,y:49.07},{x:61.78,y:48.89},{x:62.31,y:48.71},{x:62.9,y:48.63},
      {x:63.48,y:48.58},{x:64.0,y:48.49},{x:64.53,y:48.4},{x:65.15,y:48.33},
      {x:65.8,y:48.24},{x:66.47,y:48.14},{x:67.12,y:47.97},{x:67.73,y:47.72},
      {x:68.37,y:47.55},{x:68.97,y:47.4},{x:69.54,y:47.25},{x:70.14,y:47.09},
      {x:70.76,y:46.93},{x:71.27,y:46.79},{x:71.8,y:46.65},{x:72.38,y:46.51},
      {x:73.0,y:46.44},{x:73.65,y:46.39},{x:74.32,y:46.35},{x:74.99,y:46.3},
      {x:75.66,y:46.25},{x:76.31,y:46.19},{x:76.77,y:46.15},{x:77.29,y:46.11},
      {x:77.85,y:46.05},{x:78.38,y:46.0},{x:78.98,y:45.95},{x:79.62,y:45.91},
      {x:80.2,y:45.91},{x:80.79,y:45.92},{x:81.41,y:45.92},{x:82.03,y:45.93},
      {x:82.68,y:45.92},{x:83.3,y:45.84},{x:83.88,y:45.76},{x:84.48,y:45.67},
      {x:85.09,y:45.58},{x:85.71,y:45.49},{x:86.3,y:45.31},{x:86.77,y:45.05},
      {x:87.25,y:44.83},{x:87.82,y:44.65},{x:88.42,y:44.55},{x:89.02,y:44.46},
      {x:89.62,y:44.49},{x:90.24,y:44.55},{x:90.86,y:44.62},{x:91.48,y:44.64},
      {x:92.11,y:44.53},{x:92.75,y:44.37},{x:93.39,y:44.29},{x:94.01,y:44.23},
      {x:94.62,y:44.18},{x:95.2,y:44.14},{x:95.78,y:44.05},{x:96.35,y:43.85},
      {x:96.94,y:43.62},{x:97.53,y:43.4},{x:98.1,y:43.17},{x:98.64,y:43.01},
      {x:99.17,y:42.86},{x:99.75,y:42.69},{x:100.31,y:42.53},{x:100.82,y:42.42},
      {x:101.3,y:42.37},{x:101.5,y:42.34},{x:101.56,y:42.27},{x:101.42,y:42.35},
      {x:101.65,y:42.6},{x:101.8,y:42.67},{x:101.84,y:42.7}
    ];

    /* Primo e ultimo punto per evidenziare partenza/arrivo */
    var startPt = [routeData[0]];
    var endPt = [routeData[routeData.length - 1]];

    new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Traccia GPS',
            data: routeData,
            backgroundColor: CYAN + '50',
            borderColor: CYAN,
            pointRadius: 2,
            pointHoverRadius: 4,
            showLine: true,
            borderWidth: 1.5,
            fill: false,
            tension: 0.1
          },
          {
            label: 'Partenza',
            data: startPt,
            backgroundColor: GREEN,
            borderColor: GREEN,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'triangle'
          },
          {
            label: 'Arrivo (Verona)',
            data: endPt,
            backgroundColor: RED,
            borderColor: RED,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'rect'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: baseLegend,
          tooltip: {
            titleFont: { family: FONT_MONO },
            bodyFont: { family: FONT_SANS },
            callbacks: {
              label: function(item) {
                return item.dataset.label + ': ' + item.parsed.x.toFixed(1) + ' km E, ' + item.parsed.y.toFixed(1) + ' km N';
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Est (km)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          },
          y: {
            title: { display: true, text: 'Nord (km)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 4: Velocita' e altitudine reali — dati iPhone
   * Viaggio Piacenza-Verona, 26 feb 2026
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('dop-satellites-chart');
    if (!ctx) return;

    /* Dati reali dal GPX */
    var speedLabels = [41,42,43,43,44,45,45,46,47,47,48,49,49,51,56,60,60,61,62,63,63,64,65,65,66,67,67,68,69,69,70,71,71,72,73,73,74,75,75,76,77,77,78,79,79,80,81,81,82,83,83,84,85,85,86,87,87,88,89,89,90,91,91,92,93,93,94,95,95,96,97,97,98,99,99,100,101,102];
    var speedData = [106.8,102.9,96.6,103.5,90.2,107.6,106.6,111.1,102.5,108.8,108.5,107.7,23.8,1.8,0.2,16.5,53.0,87.6,85.4,93.0,92.7,110.5,81.8,75.1,88.0,90.8,57.0,98.3,80.6,83.2,80.4,90.9,87.2,99.3,90.3,92.2,97.5,89.3,95.8,98.7,99.6,104.8,98.8,100.5,121.7,121.4,117.2,109.6,106.4,109.8,112.1,117.5,121.0,70.4,87.5,112.8,104.7,109.6,118.6,106.5,108.1,103.2,104.0,110.3,111.9,109.0,114.5,112.9,107.1,106.0,108.1,106.7,109.1,102.2,42.9,36.9,48.8,2.4];

    var altLabels = [0,28,29,29,29,30,30,30,31,31,31,32,32,32,33,33,33,34,34,34,41,42,43,43,44,45,45,46,47,47,48,49,49,51,56,60,60,61,62,63,63,64,65,65,66,67,67,68,69,69,70,71,71,72,73,73,74,75,75,76,77,77,78,79,79,80,81,81,82,83,83,84,85,85,86,87,87,88,89,89,90,91,91,92,93,93,94,95,95,96,97,97,98,99,99,100,101,102];
    var altData = [78.5,51.6,52.5,46.5,48.3,49.6,48.5,47.5,50.0,49.6,49.7,49.5,50.5,50.8,51.3,52.2,52.1,51.9,51.6,52.8,67.9,67.8,61.5,68.0,71.1,71.8,74.2,75.4,79.5,86.4,89.9,96.3,97.4,97.3,96.9,96.9,98.3,105.6,110.1,115.7,110.7,115.2,117.1,121.5,125.8,127.0,131.6,135.2,135.9,139.7,139.4,142.8,141.0,140.9,141.4,137.7,136.1,148.1,135.9,137.3,143.3,151.2,161.2,185.2,147.5,117.6,100.8,92.9,88.4,89.8,88.2,81.3,82.0,82.8,84.9,89.7,81.4,102.3,114.6,104.1,105.5,116.9,129.3,121.9,121.6,114.6,99.5,84.0,86.2,84.5,75.1,71.6,69.5,63.0,58.0,57.7,60.0,64.1];

    /* Unifica le label: usa i minuti di velocita' */
    var labels = speedLabels.map(function(m) { return m + ' min'; });

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Velocita\u0300 (km/h)',
            data: speedData,
            borderColor: GREEN,
            backgroundColor: GREEN + '20',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            yAxisID: 'y'
          },
          {
            label: 'Altitudine (m)',
            data: altData.slice(altData.length - speedData.length),
            borderColor: ORANGE,
            backgroundColor: ORANGE + '15',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: baseLegend,
          tooltip: baseTooltip
        },
        scales: {
          x: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, maxTicksLimit: 12 },
            grid: { color: GRID_COLOR }
          },
          y: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'km/h', color: GREEN, font: { family: FONT_MONO, size: 10 } },
            ticks: { color: GREEN, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            min: 0
          },
          y1: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'Altitudine (m)', color: ORANGE, font: { family: FONT_MONO, size: 10 } },
            ticks: { color: ORANGE, font: { family: FONT_MONO, size: 10 } },
            grid: { drawOnChartArea: false },
            min: 0
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 5: Signal travel time — ritardo per satellite
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('signal-travel-chart');
    if (!ctx) return;

    /* 8 satelliti con distanze e tempi di volo realistici */
    var satellites = [
      { id: 'PRN 02', dist_km: 20200, elev: 72 },
      { id: 'PRN 05', dist_km: 21300, elev: 58 },
      { id: 'PRN 10', dist_km: 22100, elev: 45 },
      { id: 'PRN 12', dist_km: 23500, elev: 32 },
      { id: 'PRN 17', dist_km: 24100, elev: 25 },
      { id: 'PRN 21', dist_km: 24800, elev: 18 },
      { id: 'PRN 25', dist_km: 25200, elev: 15 },
      { id: 'PRN 31', dist_km: 25800, elev: 10 }
    ];

    var labelsS = [];
    var travelMs = [];
    var colors = [];

    for (var s = 0; s < satellites.length; s++) {
      labelsS.push(satellites[s].id);
      var ms = (satellites[s].dist_km * 1000) / 299792458 * 1000;
      travelMs.push(Math.round(ms * 100) / 100);
      /* Colore basato su elevazione */
      if (satellites[s].elev > 50) colors.push(GREEN);
      else if (satellites[s].elev > 25) colors.push(CYAN);
      else colors.push(ORANGE);
    }

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labelsS,
        datasets: [{
          label: 'Tempo di volo (ms)',
          data: travelMs,
          backgroundColor: colors,
          borderColor: colors,
          borderWidth: 0,
          borderRadius: 4
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
              afterLabel: function(item) {
                var sat = satellites[item.dataIndex];
                return 'Distanza: ' + sat.dist_km.toLocaleString() + ' km\nElevazione: ' + sat.elev + '\u00b0';
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
            title: { display: true, text: 'ms', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR },
            min: 60
          }
        }
      }
    });
  })();

  /* ========================================================
   * Chart 6: DOP vs errore — come il DOP moltiplica l'errore
   * ======================================================== */
  (function() {
    var ctx = document.getElementById('dop-error-chart');
    if (!ctx) return;

    var dopLabels = ['DOP 1.0\n(ideale)', 'DOP 1.5\n(buono)', 'DOP 2.0\n(OK)', 'DOP 3.0\n(medio)', 'DOP 5.0\n(scarso)', 'DOP 8.0\n(pessimo)'];
    var dopValues = [1.0, 1.5, 2.0, 3.0, 5.0, 8.0];
    var baseError = 3; /* errore base URE ~3 m */

    var errData = [];
    var bgColors = [];

    for (var d = 0; d < dopValues.length; d++) {
      errData.push(Math.round(dopValues[d] * baseError * 10) / 10);
      if (dopValues[d] <= 1.5) bgColors.push(GREEN);
      else if (dopValues[d] <= 3) bgColors.push(YELLOW);
      else bgColors.push(RED);
    }

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: dopLabels,
        datasets: [{
          label: 'Errore posizione (m)',
          data: errData,
          backgroundColor: bgColors,
          borderColor: bgColors,
          borderWidth: 0,
          borderRadius: 4
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
              label: function(item) {
                return 'Errore: ' + item.raw + ' m (DOP \u00d7 ' + baseError + ' m URE)';
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, maxRotation: 0 },
            grid: { display: false }
          },
          y: {
            title: { display: true, text: 'Errore posizione (m)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 11 } },
            ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
            grid: { color: GRID_COLOR }
          }
        }
      }
    });
  })();

})();
