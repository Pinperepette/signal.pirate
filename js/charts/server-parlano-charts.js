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

    var baseScaleX = {
        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
        grid: { color: GRID_COLOR }
    };

    var baseScaleY = {
        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
        grid: { color: GRID_COLOR }
    };

    /* ========================================================
     * Chart 1: Security Headers — bar orizzontale
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-headers');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['HSTS', 'X-Frame-Options', 'X-Content-Type', 'CSP', 'Referrer-Policy', 'Permissions-Policy'],
                datasets: [
                    {
                        label: 'Presente',
                        data: [46.7, 48.7, 46.2, 32.3, 30.3, 19.6],
                        backgroundColor: GREEN + '90',
                        borderColor: GREEN,
                        borderWidth: 1
                    },
                    {
                        label: 'Assente',
                        data: [53.3, 51.3, 53.8, 67.7, 69.7, 80.4],
                        backgroundColor: RED + '40',
                        borderColor: RED,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: baseLegend,
                    tooltip: baseTooltip
                },
                scales: {
                    x: Object.assign({}, baseScaleX, {
                        stacked: true,
                        max: 100,
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, callback: function(v) { return v + '%'; } }
                    }),
                    y: Object.assign({}, baseScaleY, { stacked: true })
                }
            }
        });
    })();


    /* ========================================================
     * Chart 2: Server distribution — donut
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-servers');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['nginx', 'Apache', 'Aruba', 'Non dichiarato', 'Microsoft IIS', 'LiteSpeed', 'Cloudflare', 'Altro'],
                datasets: [{
                    data: [8101, 4073, 1949, 1822, 1090, 526, 280, 363],
                    backgroundColor: [
                        GREEN + 'cc',
                        ORANGE + 'cc',
                        PURPLE + 'cc',
                        'rgba(255,255,255,0.15)',
                        CYAN + 'cc',
                        YELLOW + 'cc',
                        RED + 'cc',
                        'rgba(255,255,255,0.08)'
                    ],
                    borderColor: 'rgba(0,0,0,0.3)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: Object.assign({}, baseLegend, { position: 'right' }),
                    tooltip: baseTooltip
                }
            }
        });
    })();


    /* ========================================================
     * Chart 3: Email auth — stacked bar
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-email');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['SPF', 'DMARC', 'DKIM'],
                datasets: [
                    {
                        label: 'Configurato (efficace)',
                        data: [24.8, 6.4, 19.0],
                        backgroundColor: GREEN + '90',
                        borderColor: GREEN,
                        borderWidth: 1
                    },
                    {
                        label: 'Parziale / debole',
                        data: [56.8, 41.9, 0],
                        backgroundColor: YELLOW + '60',
                        borderColor: YELLOW,
                        borderWidth: 1
                    },
                    {
                        label: 'Assente',
                        data: [18.3, 51.7, 81.0],
                        backgroundColor: RED + '60',
                        borderColor: RED,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: baseLegend,
                    tooltip: baseTooltip
                },
                scales: {
                    x: baseScaleX,
                    y: Object.assign({}, baseScaleY, {
                        stacked: true,
                        max: 100,
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, callback: function(v) { return v + '%'; } }
                    })
                }
            }
        });
    })();


    /* ========================================================
     * Chart 4: Spoofability per tipo di ente — bar
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-enti');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Scuole', 'Comuni', 'Universita\'', 'Ordini prof.', 'Regioni', 'ASL'],
                datasets: [
                    {
                        label: 'Spoofabile %',
                        data: [97.6, 86.6, 91.6, 90.6, 89.3, 64.9],
                        backgroundColor: [RED+'cc', ORANGE+'cc', PURPLE+'cc', YELLOW+'cc', CYAN+'cc', GREEN+'cc'],
                        borderWidth: 0,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: baseTooltip
                },
                scales: {
                    x: baseScaleX,
                    y: Object.assign({}, baseScaleY, {
                        max: 100,
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, callback: function(v) { return v + '%'; } }
                    })
                }
            }
        });
    })();


    /* ========================================================
     * Chart 5: PA Exposure Score per regione — bar orizzontale
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-regioni');
        if (!ctx) return;

        var regions = [
            'Trentino-Alto Adige', 'Veneto', 'Valle d\'Aosta', 'Lombardia',
            'Emilia-Romagna', 'Marche', 'Sardegna', 'Friuli Venezia Giulia',
            'Toscana', 'Abruzzo', 'Puglia', 'Lazio', 'Umbria',
            'Sicilia', 'Piemonte', 'Basilicata', 'Liguria',
            'Calabria', 'Campania', 'Molise'
        ];

        var scores = [
            4.19, 4.86, 5.14, 5.19,
            5.29, 5.34, 5.41, 5.50,
            5.54, 5.64, 5.66, 5.73, 5.73,
            5.77, 5.79, 5.87, 5.91,
            5.96, 5.97, 6.30
        ];

        var colors = scores.map(function(s) {
            if (s < 5.0) return GREEN + 'cc';
            if (s < 5.5) return CYAN + 'cc';
            if (s < 5.8) return YELLOW + 'cc';
            if (s < 6.0) return ORANGE + 'cc';
            return RED + 'cc';
        });

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: regions,
                datasets: [{
                    label: 'Exposure Score',
                    data: scores,
                    backgroundColor: colors,
                    borderWidth: 0,
                    borderRadius: 3
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: baseTooltip
                },
                scales: {
                    x: Object.assign({}, baseScaleX, {
                        min: 3,
                        max: 7,
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } }
                    }),
                    y: baseScaleY
                }
            }
        });
    })();


    /* ========================================================
     * Chart 6: HTTPS overview — donut
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-https');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['HTTPS OK + redirect', 'HTTPS OK, no redirect', 'HTTPS fallito'],
                datasets: [{
                    data: [16998, 1206, 4109],
                    backgroundColor: [GREEN + 'cc', YELLOW + '90', RED + '90'],
                    borderColor: 'rgba(0,0,0,0.3)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: Object.assign({}, baseLegend, { position: 'bottom' }),
                    tooltip: baseTooltip
                }
            }
        });
    })();


    /* ========================================================
     * Chart 7: Radar — confronto enti multi-dimensione
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-radar-enti');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['HTTPS %', 'Headers (almeno 1)', 'DMARC reject %', 'Non spoofabile %', 'DNSSEC %'],
                datasets: [
                    {
                        label: 'Scuole',
                        data: [84.9, 71.8, 0.6, 2.4, 0.5],
                        borderColor: RED,
                        backgroundColor: RED + '20',
                        pointBackgroundColor: RED,
                        borderWidth: 2
                    },
                    {
                        label: 'Comuni',
                        data: [80.4, 83.3, 4.3, 13.4, 1.2],
                        borderColor: ORANGE,
                        backgroundColor: ORANGE + '20',
                        pointBackgroundColor: ORANGE,
                        borderWidth: 2
                    },
                    {
                        label: 'ASL',
                        data: [57.9, 78.9, 13.2, 35.1, 2.6],
                        borderColor: GREEN,
                        backgroundColor: GREEN + '20',
                        pointBackgroundColor: GREEN,
                        borderWidth: 2
                    },
                    {
                        label: 'Universita\'',
                        data: [64.1, 71.6, 2.7, 8.4, 3.8],
                        borderColor: PURPLE,
                        backgroundColor: PURPLE + '20',
                        pointBackgroundColor: PURPLE,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: baseLegend,
                    tooltip: baseTooltip
                },
                scales: {
                    r: {
                        angleLines: { color: GRID_COLOR },
                        grid: { color: GRID_COLOR },
                        pointLabels: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
                        ticks: { color: TEXT_COLOR, font: { size: 8 }, backdropColor: 'transparent' },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });
    })();


    /* ========================================================
     * Chart 8: Polar area — information leakage bit
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-polar-bits');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: ['DNS provider', 'Sec. headers', 'Server header', 'X-Powered-By', 'Cert. Authority', 'SPF policy', 'DMARC policy', 'TLS version'],
                datasets: [{
                    data: [5.29, 3.61, 3.07, 2.24, 2.05, 1.75, 1.34, 1.04],
                    backgroundColor: [
                        GREEN + '90',
                        CYAN + '90',
                        ORANGE + '90',
                        YELLOW + '90',
                        PURPLE + '90',
                        RED + '90',
                        '#ff99cc90',
                        'rgba(255,255,255,0.25)'
                    ],
                    borderColor: 'rgba(0,0,0,0.3)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: Object.assign({}, baseLegend, { position: 'right' }),
                    tooltip: Object.assign({}, baseTooltip, {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ' + ctx.raw + ' bit';
                            }
                        }
                    })
                },
                scales: {
                    r: {
                        grid: { color: GRID_COLOR },
                        ticks: { color: TEXT_COLOR, font: { size: 8 }, backdropColor: 'transparent' }
                    }
                }
            }
        });
    })();


    /* ========================================================
     * Chart 9: TTL — scatter distribution
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-ttl');
        if (!ctx) return;

        var ttlData = [
            { x: 2,     y: 45,   label: 'Sogei' },
            { x: 10,    y: 680,  label: 'CDN' },
            { x: 60,    y: 544,  label: '1 min' },
            { x: 300,   y: 2231, label: '5 min' },
            { x: 600,   y: 1834, label: '10 min' },
            { x: 900,   y: 1099, label: '15 min' },
            { x: 1800,  y: 1488, label: '30 min' },
            { x: 3600,  y: 7705, label: '1 ora' },
            { x: 7200,  y: 823,  label: '2 ore' },
            { x: 14400, y: 1128, label: '4 ore' },
            { x: 21600, y: 605,  label: '6 ore' },
            { x: 43200, y: 298,  label: '12 ore' },
            { x: 86400, y: 1200, label: '1 giorno' },
            { x: 604800,y: 73,   label: '7 giorni (Trentino)' }
        ];

        new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Domini',
                    data: ttlData.map(function(d) {
                        return { x: Math.log10(d.x), y: d.y, r: Math.max(Math.sqrt(d.y) / 2, 4), raw: d };
                    }),
                    backgroundColor: ttlData.map(function(d) {
                        if (d.x <= 60) return CYAN + 'bb';
                        if (d.x <= 3600) return GREEN + 'bb';
                        if (d.x <= 86400) return YELLOW + 'bb';
                        return RED + 'bb';
                    }),
                    borderColor: ttlData.map(function(d) {
                        if (d.x <= 60) return CYAN;
                        if (d.x <= 3600) return GREEN;
                        if (d.x <= 86400) return YELLOW;
                        return RED;
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: Object.assign({}, baseTooltip, {
                        callbacks: {
                            label: function(ctx) {
                                var d = ttlData[ctx.dataIndex];
                                return d.label + ': ' + d.y.toLocaleString('it') + ' domini (TTL ' + d.x.toLocaleString('it') + 's)';
                            }
                        }
                    })
                },
                scales: {
                    x: Object.assign({}, baseScaleX, {
                        title: { display: true, text: 'TTL (scala logaritmica)', color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } },
                        ticks: {
                            color: TEXT_COLOR,
                            font: { family: FONT_MONO, size: 9 },
                            callback: function(v) {
                                var map = { 0: '1s', 1: '10s', 2: '100s', 3: '~15min', 4: '~3h', 5: '~1g', 6: '~7g' };
                                return map[v] || '';
                            }
                        }
                    }),
                    y: Object.assign({}, baseScaleY, {
                        title: { display: true, text: 'Domini', color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } }
                    })
                }
            }
        });
    })();


    /* ========================================================
     * Chart 10: DNS provider treemap (as horizontal bar)
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-dns-providers');
        if (!ctx) return;

        var providers = ['Aruba', 'Argo/Nettuno', 'Nessun NS', 'AB DNS', 'Register.it', 'DNS Italia', 'DNS High', 'Si-Tek', 'Cloudflare', 'Sele.it', 'Azure', 'Altro'];
        var counts = [6587, 1833, 1344, 1236, 1229, 760, 449, 403, 370, 340, 190, 5572];
        var colors = [
            ORANGE + 'dd',
            PURPLE + 'cc',
            'rgba(255,255,255,0.15)',
            CYAN + 'cc',
            YELLOW + 'cc',
            GREEN + 'cc',
            '#ff99cc' + 'cc',
            RED + '99',
            ORANGE + '99',
            PURPLE + '99',
            CYAN + '99',
            'rgba(255,255,255,0.08)'
        ];

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: providers,
                datasets: [{
                    data: counts,
                    backgroundColor: colors,
                    borderWidth: 0,
                    borderRadius: 3
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: Object.assign({}, baseTooltip, {
                        callbacks: {
                            label: function(ctx) {
                                var pct = (ctx.raw / 22313 * 100).toFixed(1);
                                return ctx.raw.toLocaleString('it') + ' domini (' + pct + '%)';
                            }
                        }
                    })
                },
                scales: {
                    x: Object.assign({}, baseScaleX, {
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 } }
                    }),
                    y: baseScaleY
                }
            }
        });
    })();


    /* ========================================================
     * Chart 11: MX email provider — donut
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-mx');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Self-hosted / altro', 'Google Workspace', 'Microsoft 365', 'Register.it', 'Senza MX'],
                datasets: [{
                    data: [11467, 5881, 2292, 661, 1899],
                    backgroundColor: [
                        'rgba(255,255,255,0.15)',
                        RED + 'cc',
                        CYAN + 'cc',
                        YELLOW + 'cc',
                        PURPLE + '60'
                    ],
                    borderColor: 'rgba(0,0,0,0.3)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: Object.assign({}, baseLegend, { position: 'right' }),
                    tooltip: Object.assign({}, baseTooltip, {
                        callbacks: {
                            label: function(ctx) {
                                var pct = (ctx.raw / 22313 * 100).toFixed(1);
                                return ctx.label + ': ' + ctx.raw.toLocaleString('it') + ' (' + pct + '%)';
                            }
                        }
                    })
                }
            }
        });
    })();


    /* ========================================================
     * Chart 12: SAN — cosa rivelano i certificati (stacked bar)
     * ======================================================== */
    (function() {
        var ctx = document.getElementById('chart-san');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Cert condivisi', 'Wildcard', 'Mail', 'Admin', 'Nomi interni', 'Test/staging'],
                datasets: [
                    {
                        label: 'Presente',
                        data: [66.5, 19.1, 2.6, 2.0, 1.1, 1.0],
                        backgroundColor: RED + 'bb',
                        borderColor: RED,
                        borderWidth: 1,
                        borderRadius: 3
                    },
                    {
                        label: 'Non presente',
                        data: [33.5, 80.9, 97.4, 98.0, 98.9, 99.0],
                        backgroundColor: 'rgba(255,255,255,0.06)',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        borderRadius: 3
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: baseLegend,
                    tooltip: Object.assign({}, baseTooltip, {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.dataset.label + ': ' + ctx.raw + '%';
                            }
                        }
                    })
                },
                scales: {
                    x: Object.assign({}, baseScaleX, {
                        stacked: true,
                        max: 100,
                        ticks: { color: TEXT_COLOR, font: { family: FONT_MONO, size: 10 }, callback: function(v) { return v + '%'; } }
                    }),
                    y: Object.assign({}, baseScaleY, { stacked: true })
                }
            }
        });
    })();


    /* Map is handled inline via Leaflet in the HTML */

})();
