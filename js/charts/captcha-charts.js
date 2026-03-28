(function() {
    'use strict';

    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--chart-text').trim() || 'rgba(255,255,255,0.6)';
    var gridColor = style.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';
    var green = '#00ff88';
    var red = '#ff6b6b';
    var purple = '#7c4dff';
    var orange = '#ff8800';
    var cyan = '#4ecdc4';
    var yellow = '#f5c518';

    var commonOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
            },
            tooltip: {
                backgroundColor: 'rgba(18,18,26,0.95)',
                titleColor: green,
                bodyColor: '#e0e0e0',
                borderColor: 'rgba(0,255,136,0.3)',
                borderWidth: 1,
                titleFont: { family: "'JetBrains Mono', monospace" },
                bodyFont: { family: "'JetBrains Mono', monospace" }
            }
        },
        scales: {
            x: { ticks: { color: textColor }, grid: { color: gridColor } },
            y: { ticks: { color: textColor }, grid: { color: gridColor } }
        }
    };

    // ── Chart 1: Training Curve CNN (dual axis: loss + accuracy) ──
    var ctx1 = document.getElementById('training-curve-chart');
    if (ctx1) {
        var epochs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                      21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40];
        var loss = [14.907, 9.193, 7.397, 6.526, 5.806, 5.304, 4.931, 4.580, 4.336, 4.074,
                    3.848, 3.634, 3.443, 3.255, 3.075, 2.898, 2.792, 2.635, 2.552, 2.430,
                    2.316, 2.193, 2.105, 2.005, 1.953, 1.884, 1.825, 1.760, 1.724, 1.677,
                    1.640, 1.621, 1.601, 1.562, 1.535, 1.502, 1.538, 1.523, 1.496, 1.507];
        var acc = [12.3, 36.3, 47.5, 54.0, 59.5, 63.5, 66.4, 69.2, 71.1, 73.1,
                   74.8, 76.4, 77.8, 79.3, 80.5, 81.8, 82.7, 83.6, 84.2, 85.0,
                   85.8, 86.4, 87.1, 87.7, 88.0, 88.5, 88.9, 89.3, 89.5, 89.8,
                   90.0, 90.2, 90.3, 90.5, 90.7, 90.9, 90.7, 90.8, 90.9, 91.0];

        new Chart(ctx1, {
            type: 'line',
            data: {
                labels: epochs,
                datasets: [
                    {
                        label: 'Loss',
                        data: loss,
                        borderColor: red,
                        backgroundColor: red + '15',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: red,
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Char Accuracy %',
                        data: acc,
                        borderColor: green,
                        backgroundColor: green + '15',
                        borderWidth: 2.5,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: green,
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18,18,26,0.95)',
                        titleColor: green,
                        bodyColor: '#e0e0e0',
                        borderColor: 'rgba(0,255,136,0.3)',
                        borderWidth: 1,
                        titleFont: { family: "'JetBrains Mono', monospace" },
                        bodyFont: { family: "'JetBrains Mono', monospace" },
                        callbacks: {
                            title: function(items) { return 'Epoca ' + items[0].label; }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Epoca', color: textColor, font: { family: "'JetBrains Mono', monospace" } },
                        ticks: { color: textColor, maxTicksLimit: 10 },
                        grid: { color: gridColor }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Loss', color: red, font: { family: "'JetBrains Mono', monospace" } },
                        ticks: { color: red },
                        grid: { color: gridColor }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        title: { display: true, text: 'Accuracy %', color: green, font: { family: "'JetBrains Mono', monospace" } },
                        ticks: { color: green, callback: function(v) { return v + '%'; } },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // ── Chart 2: Radar CIFAR-10 vs STL-10 ──
    var ctx2 = document.getElementById('radar-chart');
    if (ctx2) {
        new Chart(ctx2, {
            type: 'radar',
            data: {
                labels: ['Truck', 'Ship', 'Automobile', 'Airplane', 'Deer', 'Bird', 'Horse', 'Cat'],
                datasets: [
                    {
                        label: 'STL-10 (96px)',
                        data: [97.6, 98.4, 95.8, 87.2, 92.4, 79.0, 77.6, 58.8],
                        borderColor: green,
                        backgroundColor: green + '20',
                        borderWidth: 2,
                        pointBackgroundColor: green,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'CIFAR-10 (32px)',
                        data: [90.8, 75.2, 34.2, 55.6, 55.4, 34.0, 55.8, 30.0],
                        borderColor: purple,
                        backgroundColor: purple + '20',
                        borderWidth: 2,
                        pointBackgroundColor: purple,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 }, padding: 20 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18,18,26,0.95)',
                        titleColor: green,
                        bodyColor: '#e0e0e0',
                        borderColor: 'rgba(0,255,136,0.3)',
                        borderWidth: 1,
                        titleFont: { family: "'JetBrains Mono', monospace" },
                        bodyFont: { family: "'JetBrains Mono', monospace" },
                        callbacks: {
                            label: function(ctx) { return ctx.dataset.label + ': ' + ctx.raw + '%'; }
                        }
                    }
                },
                scales: {
                    r: {
                        min: 0,
                        max: 100,
                        ticks: {
                            stepSize: 25,
                            color: textColor,
                            backdropColor: 'transparent',
                            font: { family: "'JetBrains Mono', monospace", size: 9 },
                            callback: function(v) { return v + '%'; }
                        },
                        pointLabels: {
                            color: textColor,
                            font: { family: "'JetBrains Mono', monospace", size: 11 }
                        },
                        grid: { color: gridColor },
                        angleLines: { color: gridColor }
                    }
                }
            }
        });
    }

    // ── Chart 3: Bypass Probability (area chart) ──
    var ctx3 = document.getElementById('bypass-chart');
    if (ctx3) {
        var attempts = [];
        for (var i = 1; i <= 20; i++) { attempts.push(i); }

        function bypassProb(p, n) {
            return +((1 - Math.pow(1 - p, n)) * 100).toFixed(1);
        }

        var targets = [
            { name: 'Truck (p=0.275)', p: 0.275, color: green },
            { name: 'Ship (p=0.305)', p: 0.305, color: cyan },
            { name: 'Airplane (p=0.190)', p: 0.190, color: purple },
            { name: 'Automobile (p=0.135)', p: 0.135, color: orange }
        ];

        var datasets = targets.map(function(t) {
            return {
                label: t.name,
                data: attempts.map(function(n) { return bypassProb(t.p, n); }),
                borderColor: t.color,
                backgroundColor: t.color + '10',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: t.color,
                tension: 0.4,
                fill: true
            };
        });

        new Chart(ctx3, {
            type: 'line',
            data: {
                labels: attempts,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 }, padding: 15 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18,18,26,0.95)',
                        titleColor: green,
                        bodyColor: '#e0e0e0',
                        borderColor: 'rgba(0,255,136,0.3)',
                        borderWidth: 1,
                        titleFont: { family: "'JetBrains Mono', monospace" },
                        bodyFont: { family: "'JetBrains Mono', monospace" },
                        callbacks: {
                            title: function(items) { return items[0].label + ' tentativi'; },
                            label: function(ctx) { return ctx.dataset.label + ': ' + ctx.raw + '%'; }
                        }
                    },
                    annotation: {
                        annotations: {
                            line80: {
                                type: 'line',
                                yMin: 80,
                                yMax: 80,
                                borderColor: red + '60',
                                borderWidth: 1,
                                borderDash: [6, 4],
                                label: {
                                    display: true,
                                    content: '80% bypass',
                                    position: 'end',
                                    color: red,
                                    font: { family: "'JetBrains Mono', monospace", size: 9 },
                                    backgroundColor: 'transparent'
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Tentativi', color: textColor, font: { family: "'JetBrains Mono', monospace" } },
                        ticks: { color: textColor, maxTicksLimit: 10 },
                        grid: { color: gridColor }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        title: { display: true, text: 'P(bypass)', color: textColor, font: { family: "'JetBrains Mono', monospace" } },
                        ticks: { color: textColor, callback: function(v) { return v + '%'; } },
                        grid: { color: gridColor }
                    }
                }
            }
        });
    }

})();
