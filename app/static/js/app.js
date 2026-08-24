(() => {
    "use strict";

    const COLORS = {
        violet: "#8b5cf6",
        violetSoft: "#b39af9",
        blue: "#3b82f6",
        blueSoft: "#7db0fb",
        cyan: "#22d3ee",
        cyanSoft: "#79e7f4",
        coral: "#fb7185",
        coralSoft: "#fca5b2",
        amber: "#fbbf24",
        emerald: "#34d399",
        grid: "rgba(226, 232, 240, .08)",
        text: "rgba(226, 232, 240, .76)",
        tooltip: "rgba(8, 12, 22, .97)",
    };

    const PALETTE = [
        COLORS.violet,
        COLORS.blue,
        COLORS.cyan,
        COLORS.coral,
        COLORS.amber,
    ];

    const reducedMotion = matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    function initMediaForm() {
        const type = document.getElementById("media_type");
        const series = document.getElementById("series-structure");
        const runtime = document.getElementById("movie-runtime-field");

        if (!type) return;

        const update = () => {
            const isSeries = type.value === "series";

            if (series) {
                series.hidden = !isSeries;
            }

            if (runtime) {
                runtime.hidden = isSeries;
                const input = runtime.querySelector("input");

                if (input) {
                    input.required = !isSeries;
                }
            }
        };

        type.addEventListener("change", update);
        update();
    }

    function initAutoSubmit() {
        document.querySelectorAll("[data-auto-submit]").forEach((field) => {
            field.addEventListener("change", () => {
                field.form?.requestSubmit();
            });
        });
    }

    function initCatalogShortcut() {
        const input = document.querySelector("[data-catalog-search]");

        if (!input) return;

        document.addEventListener("keydown", (event) => {
            const target = event.target;
            const typing = target instanceof HTMLInputElement
                || target instanceof HTMLTextAreaElement
                || target instanceof HTMLSelectElement;

            if (event.key === "/" && !typing) {
                event.preventDefault();
                input.focus();
            }

            if (event.key === "Escape" && document.activeElement === input) {
                input.blur();
            }
        });
    }

    function setupChartTheme() {
        if (typeof Chart === "undefined") return;

        Chart.defaults.color = COLORS.text;
        Chart.defaults.borderColor = COLORS.grid;
        Chart.defaults.font.family =
            getComputedStyle(document.body).fontFamily;
        Chart.defaults.animation.duration = reducedMotion ? 0 : 700;
        Chart.defaults.animation.easing = "easeOutQuart";
    }

    const tooltip = {
        backgroundColor: COLORS.tooltip,
        titleColor: "#fff",
        bodyColor: "#e8edf7",
        borderColor: "rgba(139, 92, 246, .28)",
        borderWidth: 1,
        cornerRadius: 12,
        padding: 12,
        usePointStyle: true,
        displayColors: true,
    };

    const legend = (position = "top") => ({
        position,
        labels: {
            usePointStyle: true,
            pointStyle: "circle",
            boxWidth: 8,
            boxHeight: 8,
            padding: 16,
        },
    });

    const baseOptions = (extra = {}) => ({
        responsive: true,
        maintainAspectRatio: false,
        resizeDelay: 100,
        interaction: {
            mode: "nearest",
            intersect: false,
        },
        plugins: {
            legend: legend(),
            tooltip,
        },
        ...extra,
    });

    const centerText = {
        id: "centerText",

        afterDraw(chart, _args, options) {
            if (!options?.text || !chart.chartArea) return;

            const { ctx, chartArea } = chart;
            const x = (chartArea.left + chartArea.right) / 2;
            const y = (chartArea.top + chartArea.bottom) / 2;

            ctx.save();
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";

            ctx.fillStyle = "#f7f9ff";
            ctx.font = "800 1.35rem system-ui";
            ctx.fillText(options.text, x, y - 8);

            if (options.subtext) {
                ctx.fillStyle = "rgba(226, 232, 240, .62)";
                ctx.font = "600 .72rem system-ui";
                ctx.fillText(options.subtext, x, y + 14);
            }

            ctx.restore();
        },
    };

    function renderMonthlyChart(canvas, data) {
        if (!canvas || !data?.labels?.length) return;

        new Chart(canvas, {
            data: {
                labels: data.labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Películas",
                        data: data.movies,
                        yAxisID: "yMovies",
                        backgroundColor: "rgba(139, 92, 246, .72)",
                        hoverBackgroundColor: COLORS.violetSoft,
                        borderRadius: 9,
                        borderSkipped: false,
                        maxBarThickness: 38,
                    },
                    {
                        type: "line",
                        label: "Episodios",
                        data: data.episodes,
                        yAxisID: "yEpisodes",
                        borderColor: COLORS.cyan,
                        backgroundColor: "rgba(34, 211, 238, .12)",
                        pointBackgroundColor: COLORS.coral,
                        pointBorderColor: "#101827",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 3,
                        tension: .34,
                        fill: true,
                    },
                ],
            },
            options: baseOptions({
                scales: {
                    x: {
                        grid: {
                            display: false,
                        },
                    },
                    yMovies: {
                        beginAtZero: true,
                        position: "left",
                        grid: {
                            color: COLORS.grid,
                        },
                        ticks: {
                            precision: 0,
                            color: "rgba(185, 166, 255, .78)",
                        },
                        title: {
                            display: true,
                            text: "Películas",
                            color: "rgba(185, 166, 255, .72)",
                        },
                    },
                    yEpisodes: {
                        beginAtZero: true,
                        position: "right",
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            precision: 0,
                            color: "rgba(121, 231, 244, .78)",
                        },
                        title: {
                            display: true,
                            text: "Episodios",
                            color: "rgba(121, 231, 244, .72)",
                        },
                    },
                },
            }),
        });
    }

    function initUserCharts() {
        const data = window.statisticsData;

        if (!data || typeof Chart === "undefined") return;

        const time = document.getElementById("timeChart");

        if (time) {
            const totalMinutes = data.time.values.reduce(
                (sum, value) => sum + Number(value || 0),
                0
            );

            new Chart(time, {
                type: "doughnut",
                plugins: [centerText],
                data: {
                    labels: data.time.labels,
                    datasets: [{
                        data: data.time.values,
                        backgroundColor: [
                            COLORS.violet,
                            COLORS.cyan,
                        ],
                        hoverBackgroundColor: [
                            COLORS.violetSoft,
                            COLORS.cyanSoft,
                        ],
                        borderWidth: 0,
                        hoverOffset: 7,
                    }],
                },
                options: baseOptions({
                    cutout: "76%",
                    plugins: {
                        legend: legend("bottom"),
                        tooltip,
                        centerText: {
                            text: `${Math.round(totalMinutes / 60)} h`,
                            subtext: "registradas",
                        },
                    },
                }),
            });
        }

        const genres = document.getElementById("genreChart");

        if (genres && data.genres?.labels?.length) {
            new Chart(genres, {
                type: "bar",
                data: {
                    labels: data.genres.labels,
                    datasets: [{
                        data: data.genres.values,
                        backgroundColor: data.genres.values.map(
                            (_, index) => PALETTE[index % PALETTE.length]
                        ),
                        borderRadius: 9,
                        borderSkipped: false,
                        maxBarThickness: 32,
                    }],
                },
                options: baseOptions({
                    indexAxis: "y",
                    plugins: {
                        legend: {
                            display: false,
                        },
                        tooltip,
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: {
                                color: COLORS.grid,
                            },
                            ticks: {
                                precision: 0,
                            },
                        },
                        y: {
                            grid: {
                                display: false,
                            },
                        },
                    },
                }),
            });
        }

        renderMonthlyChart(
            document.getElementById("monthlyChart"),
            data.monthly
        );
    }

    function initAdminCharts() {
        const data = window.adminStatisticsData;

        if (!data || typeof Chart === "undefined") return;

        const clients = document.getElementById("adminClientChart");

        if (clients && data.clients?.labels?.length) {
            new Chart(clients, {
                type: "bar",
                data: {
                    labels: data.clients.labels,
                    datasets: [
                        {
                            label: "Películas (h)",
                            data: data.clients.movies,
                            backgroundColor: COLORS.violet,
                            hoverBackgroundColor: COLORS.violetSoft,
                            borderRadius: 7,
                            borderSkipped: false,
                            maxBarThickness: 24,
                        },
                        {
                            label: "Series (h)",
                            data: data.clients.series,
                            backgroundColor: COLORS.cyan,
                            hoverBackgroundColor: COLORS.cyanSoft,
                            borderRadius: 7,
                            borderSkipped: false,
                            maxBarThickness: 24,
                        },
                    ],
                },
                options: baseOptions({
                    indexAxis: "y",
                    scales: {
                        x: {
                            stacked: true,
                            beginAtZero: true,
                            grid: {
                                color: COLORS.grid,
                            },
                            title: {
                                display: true,
                                text: "Horas registradas",
                            },
                        },
                        y: {
                            stacked: true,
                            grid: {
                                display: false,
                            },
                        },
                    },
                }),
            });
        }

        renderMonthlyChart(
            document.getElementById("adminMonthlyChart"),
            data.monthly
        );
    }

    initMediaForm();
    initAutoSubmit();
    initCatalogShortcut();

    if (typeof Chart !== "undefined") {
        setupChartTheme();
        initUserCharts();
        initAdminCharts();
    }
})();
