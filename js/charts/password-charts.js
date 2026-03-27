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

    // ── Chart 1: Entropia teorica vs reale ──
    var ctx1 = document.getElementById('entropy-chart');
    if (ctx1) {
        var lengths = [4, 5, 6, 7, 8, 9, 10, 11, 12];
        var teorica = lengths.map(function(l) { return +(l * Math.log2(94)).toFixed(1); });
        // Entropia reale da analisi RockYou 32M (distribuzione password a quella lunghezza)
        var reale = [7.8, 9.6, 12.1, 13.8, 15.2, 15.8, 16.5, 17.1, 17.9];

        new Chart(ctx1, {
            type: 'line',
            data: {
                labels: lengths,
                datasets: [
                    {
                        label: 'Entropia teorica (94^n)',
                        data: teorica,
                        borderColor: purple,
                        backgroundColor: purple + '33',
                        borderWidth: 2,
                        pointRadius: 5,
                        pointBackgroundColor: purple,
                        tension: 0.3,
                        fill: false
                    },
                    {
                        label: 'Entropia reale (password umane)',
                        data: reale,
                        borderColor: red,
                        backgroundColor: red + '33',
                        borderWidth: 2,
                        pointRadius: 5,
                        pointBackgroundColor: red,
                        tension: 0.3,
                        fill: false
                    }
                ]
            },
            options: Object.assign({}, commonOptions, {
                plugins: Object.assign({}, commonOptions.plugins, {
                    title: { display: false }
                }),
                scales: {
                    x: {
                        title: { display: true, text: 'Lunghezza password', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    },
                    y: {
                        title: { display: true, text: 'Entropia (bit)', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                }
            })
        });
    }

    // ── Chart 2: Riduzione spazio di ricerca ──
    var ctx2 = document.getElementById('space-reduction-chart');
    if (ctx2) {
        new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: ['Bruteforce\npuro (94\u2078)', 'Solo\nlowercase', 'Dizionario\n+ regole', 'Markov\nchain', 'Top 10k\n(leak)'],
                datasets: [{
                    label: 'Spazio di ricerca (log\u2081\u2080)',
                    data: [15.76, 11.09, 8.0, 6.0, 4.0],
                    backgroundColor: [purple, cyan, orange, green, red],
                    borderColor: [purple, cyan, orange, green, red],
                    borderWidth: 1
                }]
            },
            options: Object.assign({}, commonOptions, {
                plugins: Object.assign({}, commonOptions.plugins, {
                    legend: { display: false },
                    tooltip: Object.assign({}, commonOptions.plugins.tooltip, {
                        callbacks: {
                            label: function(context) {
                                return '10^' + context.raw.toFixed(1) + ' combinazioni';
                            }
                        }
                    })
                }),
                scales: {
                    x: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor } },
                    y: {
                        title: { display: true, text: 'Spazio (log\u2081\u2080)', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                }
            })
        });
    }

    // ── Chart 3: Curva di crack cumulativa ──
    var ctx3 = document.getElementById('crack-curve-chart');
    if (ctx3) {
        // Dati simulati basati su statistiche reali
        var tentativi = [10, 100, 1000, 5000, 10000, 50000, 100000, 500000, 1000000];
        var labels3 = tentativi.map(function(t) {
            if (t >= 1000000) return (t / 1000000) + 'M';
            if (t >= 1000) return (t / 1000) + 'k';
            return '' + t;
        });

        new Chart(ctx3, {
            type: 'line',
            data: {
                labels: labels3,
                datasets: [
                    {
                        label: 'Markov (probabilistico)',
                        data: [2.1, 8.5, 22.4, 35.2, 44.8, 62.1, 71.3, 82.5, 88.2],
                        borderColor: green,
                        backgroundColor: green + '22',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: green,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Dizionario (frequenza)',
                        data: [1.8, 7.2, 19.6, 31.0, 40.1, 56.8, 65.4, 77.2, 83.5],
                        borderColor: orange,
                        backgroundColor: orange + '22',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: orange,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Bruteforce puro',
                        data: [0, 0, 0, 0, 0, 0, 0, 0.001, 0.002],
                        borderColor: purple,
                        backgroundColor: purple + '22',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: purple,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: Object.assign({}, commonOptions, {
                scales: {
                    x: {
                        title: { display: true, text: 'Tentativi', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    },
                    y: {
                        title: { display: true, text: 'Password crackate (%)', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor },
                        min: 0,
                        max: 100
                    }
                }
            })
        });
    }

    // ── Chart 4: Distribuzione lunghezze ──
    var ctx4 = document.getElementById('length-dist-chart');
    if (ctx4) {
        var lengthData = {
            labels: ['1-3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13+'],
            values: [1.5, 3.8, 5.9, 23.4, 17.2, 19.8, 13.1, 8.4, 3.5, 1.8, 1.6]
        };

        var bgColors = lengthData.values.map(function(v) {
            return v === 23.4 ? red : green;
        });

        new Chart(ctx4, {
            type: 'bar',
            data: {
                labels: lengthData.labels,
                datasets: [{
                    label: 'Percentuale (%)',
                    data: lengthData.values,
                    backgroundColor: bgColors.map(function(c) { return c + 'cc'; }),
                    borderColor: bgColors,
                    borderWidth: 1
                }]
            },
            options: Object.assign({}, commonOptions, {
                plugins: Object.assign({}, commonOptions.plugins, {
                    legend: { display: false }
                }),
                scales: {
                    x: {
                        title: { display: true, text: 'Lunghezza', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    },
                    y: {
                        title: { display: true, text: '%', color: textColor },
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                }
            })
        });
    }

    // ── Chart 5: Composizione charset (doughnut) ──
    var ctx5 = document.getElementById('charset-chart');
    if (ctx5) {
        new Chart(ctx5, {
            type: 'doughnut',
            data: {
                labels: ['Solo lowercase', 'Solo cifre', 'Lower + cifre', 'Con maiuscole', 'Con speciali'],
                datasets: [{
                    data: [30, 28, 22, 12, 8],
                    backgroundColor: [green + 'cc', red + 'cc', orange + 'cc', purple + 'cc', cyan + 'cc'],
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
                        labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 }, padding: 15 }
                    },
                    tooltip: commonOptions.plugins.tooltip
                }
            }
        });
    }

    // ── Chart 6: Transizioni Markov (radar) ──
    var ctx6 = document.getElementById('markov-radar-chart');
    if (ctx6) {
        // Dopo 'p': probabilita' dei caratteri successivi (da analisi RockYou)
        var afterP = {
            labels: ['a', 'e', 'i', 'o', 'u', 'r', 'l', 'h', 'altro'],
            data: [28, 12, 15, 18, 6, 8, 5, 3, 5]
        };

        new Chart(ctx6, {
            type: 'radar',
            data: {
                labels: afterP.labels,
                datasets: [{
                    label: 'Dopo "p" — probabilita\u0300 (%)',
                    data: afterP.data,
                    backgroundColor: green + '33',
                    borderColor: green,
                    borderWidth: 2,
                    pointBackgroundColor: green,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
                    },
                    tooltip: commonOptions.plugins.tooltip
                },
                scales: {
                    r: {
                        angleLines: { color: gridColor },
                        grid: { color: gridColor },
                        pointLabels: { color: textColor, font: { size: 12, family: "'JetBrains Mono', monospace" } },
                        ticks: { color: textColor, backdropColor: 'transparent' }
                    }
                }
            }
        });
    }

})();
