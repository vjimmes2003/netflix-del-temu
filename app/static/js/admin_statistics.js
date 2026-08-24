(() => {
    const data = window.adminStatisticsData;

    if (!data || typeof Chart === "undefined") {
        return;
    }

    const VIOLET = "#7c5cfc";
    const BLUE = "#5b8def";
    const VIOLET_SOFT = "#9b86ff";
    const BLUE_SOFT = "#82a8f5";

    Chart.defaults.color = "rgba(225, 229, 239, .72)";
    Chart.defaults.borderColor = "rgba(225, 229, 239, .10)";
    Chart.defaults.font.family =
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

    const commonTooltip = {
        backgroundColor: "rgba(20, 26, 42, .97)",
        titleColor: "#ffffff",
        bodyColor: "#e7eaf1",
        borderColor: "rgba(124, 92, 252, .28)",
        borderWidth: 1,
        padding: 11,
    };

    const clientCanvas = document.getElementById(
        "adminClientChart"
    );

    if (
        clientCanvas
        && data.clients
        && data.clients.labels.length
    ) {
        new Chart(clientCanvas, {
            type: "bar",
            data: {
                labels: data.clients.labels,
                datasets: [
                    {
                        label: "Películas (h)",
                        data: data.clients.movies,
                        backgroundColor: VIOLET,
                        hoverBackgroundColor: VIOLET_SOFT,
                        borderRadius: 7,
                        borderSkipped: false,
                    },
                    {
                        label: "Series (h)",
                        data: data.clients.series,
                        backgroundColor: BLUE,
                        hoverBackgroundColor: BLUE_SOFT,
                        borderRadius: 7,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y",
                plugins: {
                    legend: {
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                        },
                    },
                    tooltip: commonTooltip,
                },
                scales: {
                    x: {
                        stacked: true,
                        beginAtZero: true,
                        grid: {
                            color: "rgba(225, 229, 239, .07)",
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
            },
        });
    }

    const monthlyCanvas = document.getElementById(
        "adminMonthlyChart"
    );

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
                        borderRadius: 7,
                        borderSkipped: false,
                    },
                    {
                        label: "Episodios",
                        data: data.monthly.episodes,
                        backgroundColor: BLUE,
                        hoverBackgroundColor: BLUE_SOFT,
                        borderRadius: 7,
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
                    tooltip: commonTooltip,
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
                            color: "rgba(225, 229, 239, .07)",
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
