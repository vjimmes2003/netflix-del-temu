(() => {
    const data = window.statisticsData;

    if (!data || typeof Chart === "undefined") {
        return;
    }

    const VIOLET = "#7c5cfc";
    const VIOLET_SOFT = "#9b86ff";
    const BLUE = "#5b8def";
    const BLUE_SOFT = "#82a8f5";

    Chart.defaults.color = "rgba(232, 236, 246, .72)";
    Chart.defaults.borderColor = "rgba(232, 236, 246, .10)";
    Chart.defaults.font.family =
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

    const tooltip = {
        backgroundColor: "rgba(17, 24, 39, .96)",
        titleColor: "#ffffff",
        bodyColor: "#e9ecf5",
        borderColor: "rgba(124, 92, 252, .25)",
        borderWidth: 1,
        padding: 12,
    };

    const timeCanvas = document.getElementById("timeChart");

    if (timeCanvas) {
        new Chart(timeCanvas, {
            type: "doughnut",
            data: {
                labels: data.time.labels,
                datasets: [{
                    data: data.time.values,
                    backgroundColor: [VIOLET, BLUE],
                    borderColor: [VIOLET, BLUE],
                    hoverBackgroundColor: [VIOLET_SOFT, BLUE_SOFT],
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 16,
                        },
                    },
                    tooltip,
                },
            },
        });
    }

    const genreCanvas = document.getElementById("genreChart");

    if (
        genreCanvas
        && data.genres
        && data.genres.labels.length
    ) {
        new Chart(genreCanvas, {
            type: "bar",
            data: {
                labels: data.genres.labels,
                datasets: [{
                    data: data.genres.values,
                    backgroundColor: data.genres.values.map(
                        (_, index) => index % 2 === 0 ? VIOLET : BLUE
                    ),
                    hoverBackgroundColor: data.genres.values.map(
                        (_, index) => index % 2 === 0
                            ? VIOLET_SOFT
                            : BLUE_SOFT
                    ),
                    borderRadius: 8,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
                            color: "rgba(232, 236, 246, .08)",
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
            },
        });
    }

    const monthlyCanvas = document.getElementById("monthlyChart");

    if (
        monthlyCanvas
        && data.monthly
        && data.monthly.labels.length
    ) {
        new Chart(monthlyCanvas, {
            type: "bar",
            data: {
                labels: data.monthly.labels,
                datasets: [
                    {
                        label: "Películas",
                        data: data.monthly.movies,
                        backgroundColor: VIOLET,
                        hoverBackgroundColor: VIOLET_SOFT,
                        borderRadius: 8,
                        borderSkipped: false,
                    },
                    {
                        label: "Episodios",
                        data: data.monthly.episodes,
                        backgroundColor: BLUE,
                        hoverBackgroundColor: BLUE_SOFT,
                        borderRadius: 8,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                        },
                    },
                    tooltip,
                },
                scales: {
                    x: {
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: "rgba(232, 236, 246, .08)",
                        },
                        ticks: {
                            precision: 0,
                        },
                    },
                },
            },
        });
    }
})();
