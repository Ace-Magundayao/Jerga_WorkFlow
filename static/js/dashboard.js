/* Dashboard: Request Overview line chart + 6/12-month range filter. */
document.addEventListener("DOMContentLoaded", function () {
const canvas = document.getElementById("requestChart");
if (!canvas || typeof CHART === "undefined") return;

const GREEN_MAIN = "#1b7a3d";
const GREEN_DARK = "#145c2c";
const GREEN_LIGHT = "#e6f4ea";

let chart;

function buildChart(labels, data) {
    if (chart) chart.destroy();

    chart = new Chart(canvas, {
    type: "line",
    data: {
        labels: labels,
        datasets: [
        {
            label: "Requests submitted",
            data: data,
            borderColor: GREEN_MAIN,
            backgroundColor: "rgba(27, 122, 61, 0.12)",
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointBackgroundColor: "#ffffff",
            pointBorderColor: GREEN_DARK,
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
        },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: GREEN_DARK,
            titleColor: "#fff",
            bodyColor: "#fff",
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
            label: function (ctx) {
                return (
                ctx.parsed.y + " request" + (ctx.parsed.y === 1 ? "" : "s")
                );
            },
            },
        },
        },
        scales: {
        x: {
            grid: { display: false },
            ticks: { color: "#7a8a80", font: { size: 11 } },
        },
        y: {
            beginAtZero: true,
            ticks: {
            color: "#7a8a80",
            font: { size: 11 },
            precision: 0,
            },
            grid: {
            color: "#eef3f0",
            borderDash: [4, 4],
            },
        },
        },
    },
    });
}

  // Range filter buttons
document.querySelectorAll(".btn-range").forEach(function (btn) {
    btn.addEventListener("click", function () {
    document.querySelectorAll(".btn-range").forEach(function (b) {
        b.classList.remove("active");
    });
    btn.classList.add("active");

    const range = btn.dataset.range;
    if (range === "6") {
        buildChart(CHART.labels6, CHART.data6);
    } else {
        buildChart(CHART.labels12, CHART.data12);
    }
    });
});

buildChart(CHART.labels12, CHART.data12);
});
