(function() {
    'use strict';

    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--chart-text').trim() || 'rgba(255,255,255,0.6)';
    var gridColor = style.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.06)';
    var green = '#00ff88';
    var red = '#ff6b6b';
    var purple = '#7c4dff';
    var cyan = '#4ecdc4';

    var monoFont = "'JetBrains Mono', monospace";

    var tooltipStyle = {
        backgroundColor: 'rgba(18,18,26,0.95)',
        titleColor: green,
        bodyColor: '#e0e0e0',
        borderColor: 'rgba(0,255,136,0.3)',
        borderWidth: 1,
        titleFont: { family: monoFont },
        bodyFont: { family: monoFont }
    };

    // ── Chart 1: Engagement grezzo (Punti vs Commenti per caso) ──
    var ctx1 = document.getElementById('engagement-bar-chart');
    if (ctx1) {
        new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: [
                    ['xz-utils', 'CVSS 10.0'],
                    ['Heartbleed', 'CVSS ~7.5'],
                    ['Log4Shell', 'CVSS 10.0'],
                    ['rsync / Claude', 'CVSS ~0']
                ],
                datasets: [
                    {
                        label: 'Punti HN',
                        data: [4549, 1768, 1385, 503],
                        backgroundColor: cyan + 'cc',
                        borderColor: cyan,
                        borderWidth: 1
                    },
                    {
                        label: 'Commenti HN',
                        data: [1849, 528, 503, 403],
                        backgroundColor: green + 'cc',
                        borderColor: green,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, font: { family: monoFont, size: 11 }, padding: 18 }
                    },
                    tooltip: Object.assign({}, tooltipStyle, {
                        callbacks: {
                            title: function(items) {
                                var l = items[0].label;
                                return l.replace(',', ' · ');
                            }
                        }
                    })
                },
                scales: {
                    x: {
                        ticks: { color: textColor, font: { family: monoFont, size: 10 } },
                        grid: { color: gridColor }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Engagement', color: textColor, font: { family: monoFont } },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                }
            }
        });
    }

    // ── Chart 2: Gravità tecnica (CVSS) vs Attenzione (commenti HN) ──
    var ctx2 = document.getElementById('severity-scatter-chart');
    if (ctx2) {
        new Chart(ctx2, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'CVE reali',
                        data: [
                            { x: 10,  y: 1849, name: 'xz-utils backdoor' },
                            { x: 7.5, y: 528,  name: 'Heartbleed' },
                            { x: 10,  y: 503,  name: 'Log4Shell' }
                        ],
                        backgroundColor: cyan,
                        borderColor: cyan,
                        pointRadius: 7,
                        pointHoverRadius: 10
                    },
                    {
                        label: 'rsync / Claude (nessuna CVE)',
                        data: [
                            { x: 0, y: 403, name: 'rsync / Claude' }
                        ],
                        backgroundColor: red,
                        borderColor: '#fff',
                        borderWidth: 1.5,
                        pointRadius: 11,
                        pointHoverRadius: 14
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, font: { family: monoFont, size: 11 }, padding: 18 }
                    },
                    tooltip: Object.assign({}, tooltipStyle, {
                        callbacks: {
                            label: function(ctx) {
                                var p = ctx.raw;
                                return p.name + ': CVSS ' + p.x + ', ' + p.y + ' commenti';
                            }
                        }
                    })
                },
                scales: {
                    x: {
                        min: -0.6,
                        max: 10.6,
                        title: { display: true, text: 'Gravità tecnica (CVSS)', color: textColor, font: { family: monoFont } },
                        ticks: { color: textColor, stepSize: 2, font: { family: monoFont, size: 10 } },
                        grid: { color: gridColor }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Attenzione (commenti HN)', color: textColor, font: { family: monoFont } },
                        ticks: { color: textColor, font: { family: monoFont, size: 10 } },
                        grid: { color: gridColor }
                    }
                }
            }
        });
    }

})();
