(function () {
    "use strict";

    const COLORS = [
        "#2563EB", "#7C3AED", "#10B981", "#F59E0B", "#EF4444",
        "#06B6D4", "#8B5CF6", "#F97316", "#14B8A6", "#EC4899",
    ];

    const fmtVnd = (value) => {
        const n = Number(value) || 0;
        return n.toLocaleString("vi-VN") + "₫";
    };

    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }, boxWidth: 12 },
            },
            tooltip: {
                titleFont: { family: "'Plus Jakarta Sans', sans-serif" },
                bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
            },
        },
    };

    function readData() {
        const el = document.getElementById("admin-chart-data");
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (_) {
            return null;
        }
    }

    function makeChart(id, config) {
        const canvas = document.getElementById(id);
        if (!canvas || typeof Chart === "undefined") return null;
        return new Chart(canvas, config);
    }

    function lineChart(id, labels, values, label, color, fill) {
        return makeChart(id, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label,
                    data: values,
                    borderColor: color,
                    backgroundColor: fill || color + "22",
                    fill: !!fill,
                    tension: 0.35,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderWidth: 2.5,
                }],
            },
            options: {
                ...defaultOptions,
                scales: {
                    x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } },
                    y: { beginAtZero: true, ticks: { font: { size: 10 } } },
                },
                plugins: {
                    ...defaultOptions.plugins,
                    tooltip: {
                        ...defaultOptions.plugins.tooltip,
                        callbacks: label === "Doanh thu" ? {
                            label: (ctx) => " " + fmtVnd(ctx.parsed.y),
                        } : {},
                    },
                },
            },
        });
    }

    function barChart(id, labels, values, label, horizontal, color) {
        const bg = color || COLORS[0];
        return makeChart(id, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label,
                    data: values,
                    backgroundColor: horizontal
                        ? labels.map((_, i) => COLORS[i % COLORS.length] + "CC")
                        : bg + "CC",
                    borderRadius: 6,
                    borderSkipped: false,
                }],
            },
            options: {
                ...defaultOptions,
                indexAxis: horizontal ? "y" : "x",
                scales: {
                    x: { beginAtZero: true, grid: { display: !horizontal }, ticks: { font: { size: 10 } } },
                    y: { beginAtZero: true, grid: { display: horizontal }, ticks: { font: { size: 10 } } },
                },
                plugins: {
                    ...defaultOptions.plugins,
                    legend: { display: false },
                    tooltip: {
                        ...defaultOptions.plugins.tooltip,
                        callbacks: label === "Doanh thu" ? {
                            label: (ctx) => " " + fmtVnd(ctx.parsed.x ?? ctx.parsed.y),
                        } : {},
                    },
                },
            },
        });
    }

    function doughnutChart(id, labels, values, colors) {
        const bg = colors || labels.map((_, i) => COLORS[i % COLORS.length]);
        return makeChart(id, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: bg.map((c) => c + (c.length === 7 ? "DD" : "")),
                    borderWidth: 2,
                    borderColor: "#fff",
                }],
            },
            options: {
                ...defaultOptions,
                cutout: "62%",
                plugins: {
                    ...defaultOptions.plugins,
                    legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 12 } },
                },
            },
        });
    }

    function pieChart(id, labels, values, money) {
        return makeChart(id, {
            type: "pie",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: labels.map((_, i) => COLORS[i % COLORS.length] + "DD"),
                    borderWidth: 2,
                    borderColor: "#fff",
                }],
            },
            options: {
                ...defaultOptions,
                plugins: {
                    ...defaultOptions.plugins,
                    legend: { position: "right", labels: { font: { size: 11 } } },
                    tooltip: money ? {
                        callbacks: {
                            label: (ctx) => " " + fmtVnd(ctx.parsed),
                        },
                    } : {},
                },
            },
        });
    }

    function initDashboardCharts(data) {
        lineChart("chartRevenue7", data.revenue7.labels, data.revenue7.values, "Doanh thu", "#2563EB", "#2563EB18");
        barChart("chartOrders7", data.orders7.labels, data.orders7.values, "Đơn hàng", false, "#7C3AED");
        doughnutChart("chartStatus", data.statusBreakdown.labels, data.statusBreakdown.values);
        pieChart("chartCategory", data.categorySales.labels, data.categorySales.values, true);
        barChart("chartTopProducts", data.topProductsQty.labels, data.topProductsQty.values, "Số lượng", true);
        doughnutChart("chartStock", data.stockHealth.labels, data.stockHealth.values, ["#10B981", "#F59E0B", "#EF4444"]);
        barChart("chartTickets", data.ticketStatus.labels, data.ticketStatus.values, "Ticket", false, "#06B6D4");
        lineChart("chartCustomers", data.customerGrowth.labels, data.customerGrowth.values, "Khách mới", "#10B981", "#10B98118");
    }

    function initReportsCharts(data) {
        lineChart("chartRevenue30", data.revenue30.labels, data.revenue30.values, "Doanh thu", "#2563EB", "#2563EB18");
        lineChart("chartOrders30", data.orders30.labels, data.orders30.values, "Đơn hàng", "#7C3AED", null);
        barChart("chartTopRevenue", data.topProductsRevenue.labels, data.topProductsRevenue.values, "Doanh thu", true);
        barChart("chartBrands", data.brandSales.labels, data.brandSales.values, "Doanh thu", true);
        barChart("chartOrderValue", data.orderValueBuckets.labels, data.orderValueBuckets.values, "Đơn hàng", false, "#F59E0B");
        barChart("chartHourly", data.ordersByHour.labels, data.ordersByHour.values, "Đơn hàng", false, "#06B6D4");
        doughnutChart("chartStatusReport", data.statusBreakdown.labels, data.statusBreakdown.values);
        pieChart("chartCategoryReport", data.categorySales.labels, data.categorySales.values, true);
    }

    document.addEventListener("DOMContentLoaded", function () {
        const data = readData();
        if (!data) return;
        const mode = document.body.dataset.adminCharts;
        if (mode === "dashboard") initDashboardCharts(data);
        if (mode === "reports") initReportsCharts(data);
    });
})();
