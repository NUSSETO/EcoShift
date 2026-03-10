const mockTimeseriesData = [
    { "timestamp": "2024-03-01T08:00:00", "solar_kwh": 60.5, "wind_kwh": 20.2, "grid_kwh": 120.0, "carbon_emissions_kg": 54.0 },
    { "timestamp": "2024-03-01T20:00:00", "solar_kwh": 5.5, "wind_kwh": 30.5, "grid_kwh": 140.0, "carbon_emissions_kg": 63.0 },
    { "timestamp": "2024-03-02T08:00:00", "solar_kwh": 65.2, "wind_kwh": 18.0, "grid_kwh": 110.0, "carbon_emissions_kg": 49.5 },
    { "timestamp": "2024-03-02T20:00:00", "solar_kwh": 4.8, "wind_kwh": 25.5, "grid_kwh": 135.5, "carbon_emissions_kg": 61.0 },
    { "timestamp": "2024-03-03T08:00:00", "solar_kwh": 70.8, "wind_kwh": 14.5, "grid_kwh": 105.5, "carbon_emissions_kg": 47.5 },
    { "timestamp": "2024-03-03T20:00:00", "solar_kwh": 6.0, "wind_kwh": 28.0, "grid_kwh": 125.0, "carbon_emissions_kg": 56.2 },
    { "timestamp": "2024-03-04T08:00:00", "solar_kwh": 85.0, "wind_kwh": 12.0, "grid_kwh": 90.0, "carbon_emissions_kg": 40.5 },
    { "timestamp": "2024-03-04T20:00:00", "solar_kwh": 8.5, "wind_kwh": 22.5, "grid_kwh": 115.5, "carbon_emissions_kg": 52.0 },
    { "timestamp": "2024-03-05T08:00:00", "solar_kwh": 90.5, "wind_kwh": 10.0, "grid_kwh": 80.0, "carbon_emissions_kg": 36.0 },
    { "timestamp": "2024-03-05T20:00:00", "solar_kwh": 10.0, "wind_kwh": 15.5, "grid_kwh": 130.0, "carbon_emissions_kg": 58.5 }
];

const mockForecastData = [
    { "timestamp": "2024-03-06T08:00:00", "solar_kwh": 92.0, "wind_kwh": 12.0, "grid_kwh": 85.0, "carbon_emissions_kg": 38.25 },
    { "timestamp": "2024-03-06T20:00:00", "solar_kwh": 12.0, "wind_kwh": 18.0, "grid_kwh": 125.0, "carbon_emissions_kg": 56.25 }
];

Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

let energyChartInstance = null;
let emissionsChartInstance = null;
let forecastChartInstance = null;

let globalTimeseriesData = [];
let globalSummaryData = {};

const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://ecoshift-api-qan2.onrender.com';

/**
 * Fetches timeseries, forecast, and summary data from the API.
 * Uses local mock data as a fallback if the API is unavailable.
 */
async function fetchData() {
    let timeseriesData = mockTimeseriesData;
    let summaryData = null;
    let forecastData = mockForecastData;

    try {
        const tsRes = await fetch(`${API_BASE_URL}/api/timeseries`);
        if (tsRes.ok) {
            timeseriesData = await tsRes.json();
            console.log("Successfully fetched API timeseries data.");
        } else {
            console.warn('API returned non-200. Using fallback.');
        }
    } catch (e) {
        console.warn('API fetch failed. Using fallback.', e);
    }

    try {
        const fcRes = await fetch(`${API_BASE_URL}/api/forecast`);
        if (fcRes.ok) {
            forecastData = await fcRes.json();
            console.log("Successfully fetched API forecast data.");
        } else {
            console.warn('API returned non-200. Using fallback forecast.');
        }
    } catch (e) {
        console.warn('API fetch failed. Using fallback forecast.', e);
    }

    // Ensure all numeric values are properly cast to Floats to prevent string concatenation bugs
    timeseriesData = timeseriesData.map(d => ({
        ...d,
        solar_kwh: parseFloat(d.solar_kwh ?? 0),
        wind_kwh: parseFloat(d.wind_kwh ?? 0),
        grid_kwh: parseFloat(d.grid_kwh ?? 0),
        carbon_emissions_kg: parseFloat(d.carbon_emissions_kg ?? 0)
    }));


    try {
        const sumRes = await fetch(`${API_BASE_URL}/api/summary`);
        if (sumRes.ok) {
            const rawSummary = await sumRes.json();
            // The API might not return peak_grid and cost_savings yet. 
            // Calculate locally first, then override totals with API data to be safe.
            const localSummary = calculateSummary(timeseriesData);
            summaryData = {
                total_energy: parseFloat(rawSummary.total_energy_kwh ?? localSummary.total_energy),
                total_emissions: parseFloat(rawSummary.total_emissions_kg ?? localSummary.total_emissions),
                peak_grid: localSummary.peak_grid,
                cost_savings: localSummary.cost_savings
            };
            console.log("Successfully fetched API summary data, augmented with local calculations.");
        } else {
            summaryData = calculateSummary(timeseriesData);
        }
    } catch (e) {
        summaryData = calculateSummary(timeseriesData);
    }

    globalTimeseriesData = timeseriesData;
    globalSummaryData = summaryData;

    updateUI(timeseriesData, summaryData, forecastData);
}

/**
 * Calculates summary metrics (total energy, emissions, peak grid, cost savings) from historical data.
 * @param {Array<Object>} data - The historical timeseries data array.
 * @returns {Object} An object containing the calculated summary statistics.
 */
function calculateSummary(data) {
    let totalEnergy = 0;
    let totalEmissions = 0;
    let peakGrid = 0;
    let totalRenewables = 0;

    data.forEach(d => {
        totalEnergy += (d.solar_kwh + d.wind_kwh + d.grid_kwh);
        totalEmissions += d.carbon_emissions_kg;
        if (d.grid_kwh > peakGrid) {
            peakGrid = d.grid_kwh;
        }
        totalRenewables += (d.solar_kwh + d.wind_kwh);
    });

    const costSavings = totalRenewables * 0.12;

    return {
        total_energy: totalEnergy,
        total_emissions: totalEmissions,
        peak_grid: peakGrid,
        cost_savings: costSavings
    };
}

/**
 * Updates the dashboard UI with fetched data.
 * @param {Array<Object>} timeseries - The historical timeseries data.
 * @param {Object} summary - The summary statistics data.
 * @param {Array<Object>} forecast - The predictive forecast data.
 */
function updateUI(timeseries, summary, forecast) {
    // Animate numbers
    animateValue(document.getElementById('total-energy'), 0, summary.total_energy, 1000, ' kWh');
    animateValue(document.getElementById('total-emissions'), 0, summary.total_emissions, 1000, ' kg');
    animateValue(document.getElementById('peak-grid'), 0, summary.peak_grid, 1000, ' kWh');
    animateValue(document.getElementById('cost-savings'), 0, summary.cost_savings, 1000, ' USD', '$');

    const labels = timeseries.map(d => {
        return new Date(d.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    });

    renderHistoricalCharts(labels, timeseries);

    if (forecast && forecast.length > 0) {
        const forecastLabels = forecast.map(d => {
            return new Date(d.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        });
        renderForecast(forecastLabels, forecast);
    }
}

/**
 * Renders the historical energy and emissions charts.
 * @param {Array<string>} labels - Array of formatted timestamp labels.
 * @param {Array<Object>} timeseries - Array of historical data objects.
 */
function renderHistoricalCharts(labels, timeseries) {
    renderEnergyChart(labels, timeseries);
    renderEmissionsChart(labels, timeseries);
}

/**
 * Animates a numeric value from a start to an end value over a duration.
 * @param {HTMLElement} obj - The DOM element to update.
 * @param {number} start - The starting value.
 * @param {number} end - The ending value.
 * @param {number} duration - The animation duration in milliseconds.
 * @param {string} suffix - Optional suffix (e.g., ' kWh').
 * @param {string} prefix - Optional prefix (e.g., '$').
 */
function animateValue(obj, start, end, duration, suffix = '', prefix = '') {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 4);
        obj.textContent = prefix + (start + ease * (end - start)).toFixed(1) + suffix;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

/**
 * Renders the energy generation area chart.
 * @param {Array<string>} labels - Chart X-axis labels.
 * @param {Array<Object>} data - Timeseries data array.
 */
function renderEnergyChart(labels, data) {
    const ctx = document.getElementById('energyChart').getContext('2d');
    if (energyChartInstance) energyChartInstance.destroy();

    const solarGrad = ctx.createLinearGradient(0, 0, 0, 400);
    solarGrad.addColorStop(0, 'rgba(0, 255, 136, 0.5)');
    solarGrad.addColorStop(1, 'rgba(0, 255, 136, 0.05)');

    const windGrad = ctx.createLinearGradient(0, 0, 0, 400);
    windGrad.addColorStop(0, 'rgba(0, 225, 255, 0.5)');
    windGrad.addColorStop(1, 'rgba(0, 225, 255, 0.05)');

    const gridGrad = ctx.createLinearGradient(0, 0, 0, 400);
    gridGrad.addColorStop(0, 'rgba(139, 148, 158, 0.5)');
    gridGrad.addColorStop(1, 'rgba(139, 148, 158, 0.05)');

    energyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Solar (kWh)',
                    data: data.map(d => d.solar_kwh),
                    backgroundColor: solarGrad,
                    borderColor: '#00ff88',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                },
                {
                    label: 'Wind (kWh)',
                    data: data.map(d => d.wind_kwh),
                    backgroundColor: windGrad,
                    borderColor: '#00e1ff',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                },
                {
                    label: 'Grid (kWh)',
                    data: data.map(d => d.grid_kwh),
                    backgroundColor: gridGrad,
                    borderColor: '#8b949e',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            layout: {
                padding: { right: 20 }
            },
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, boxWidth: 8, padding: 20 }
                },
                tooltip: {
                    backgroundColor: 'rgba(11, 15, 25, 0.9)',
                    titleColor: '#e6edf3',
                    bodyColor: '#e6edf3',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        footer: function (tooltipItems) {
                            let total = 0;
                            tooltipItems.forEach(function (tooltipItem) {
                                total += tooltipItem.parsed.y;
                            });
                            return 'Total: ' + total.toFixed(1) + ' kWh';
                        }
                    }
                }
            },
            scales: {
                y: { stacked: true, grid: { display: false }, beginAtZero: true },
                x: { stacked: true, grid: { display: false } }
            }
        }
    });
}

/**
 * Renders the carbon emissions bar chart.
 * @param {Array<string>} labels - Chart X-axis labels.
 * @param {Array<Object>} data - Timeseries data array.
 */
function renderEmissionsChart(labels, data) {
    const ctx = document.getElementById('emissionsChart').getContext('2d');
    if (emissionsChartInstance) emissionsChartInstance.destroy();

    const barGrad = ctx.createLinearGradient(0, 0, 0, 400);
    barGrad.addColorStop(0, '#00ff88');
    barGrad.addColorStop(1, '#00b8ff');

    emissionsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Carbon Emissions (kg)',
                data: data.map(d => d.carbon_emissions_kg),
                backgroundColor: barGrad,
                borderRadius: 6,
                barPercentage: 0.5
            }]
        },
        options: {
            layout: {
                padding: { right: 20 }
            },
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(11, 15, 25, 0.9)',
                    titleColor: '#e6edf3',
                    bodyColor: '#e6edf3',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function (ctx) { return ctx.parsed.y.toFixed(1) + ' kg CO₂'; }
                    }
                }
            },
            scales: {
                y: { grid: { display: false }, beginAtZero: true },
                x: { grid: { display: false } }
            }
        }
    });
}

/**
 * Renders the predictive forecast chart.
 * @param {Array<string>} labels - Chart X-axis labels.
 * @param {Array<Object>} data - Forecast data array.
 */
function renderForecast(labels, data) {
    const ctx = document.getElementById('forecastChart').getContext('2d');
    if (forecastChartInstance) forecastChartInstance.destroy();

    forecastChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Solar Forecast (kWh)',
                    data: data.map(d => d.solar_kwh),
                    borderColor: '#00ff88',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                },
                {
                    label: 'Wind Forecast (kWh)',
                    data: data.map(d => d.wind_kwh),
                    borderColor: '#00e1ff',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                },
                {
                    label: 'Grid Forecast (kWh)',
                    data: data.map(d => d.grid_kwh),
                    borderColor: '#8b949e',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            layout: {
                padding: { right: 20 }
            },
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, boxWidth: 8, padding: 20 }
                },
                tooltip: {
                    backgroundColor: 'rgba(11, 15, 25, 0.9)',
                    titleColor: '#e6edf3',
                    bodyColor: '#e6edf3',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        footer: function (tooltipItems) {
                            let total = 0;
                            tooltipItems.forEach(function (tooltipItem) {
                                total += tooltipItem.parsed.y;
                            });
                            return 'Total: ' + total.toFixed(1) + ' kWh';
                        }
                    }
                }
            },
            scales: {
                y: { grid: { display: false }, beginAtZero: true },
                x: { grid: { display: false } }
            }
        }
    });
}

/**
 * Initializes the user interface, sets up event listeners, and fetches initial data.
 */
function initializeUI() {
    fetchData();
    setupNavigation();
    setupSettingsModifiers();
    setupReports();
}

document.addEventListener('DOMContentLoaded', initializeUI);

/**
 * Sets up event listeners for the reports view.
 */
function setupReports() {
    const downloadBtn = document.querySelector('#view-reports .btn-primary');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const headers = ['timestamp', 'solar_kwh', 'wind_kwh', 'grid_kwh', 'carbon_emissions_kg'];
            let csvContent = headers.join(',') + '\n';

            globalTimeseriesData.forEach(row => {
                const rowData = headers.map(header => row[header]);
                csvContent += rowData.join(',') + '\n';
            });

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.setAttribute('href', url);
            link.setAttribute('download', 'ecoshift_export.csv');
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
}

/**
 * Sets up navigation links and view switching.
 */
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-links a[data-view]');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = link.getAttribute('data-view');
            switchView(viewId, link);
        });
    });
}

/**
 * Switches the active view section in the dashboard.
 * @param {string} viewId - The ID of the view to activate.
 * @param {HTMLElement} targetLink - The navigation link that triggered the switch.
 */
function switchView(viewId, targetLink) {
    // Hide all views
    const views = document.querySelectorAll('.view-section');
    views.forEach(view => {
        view.classList.remove('active');
    });

    // Show selected view
    const selectedView = document.getElementById(viewId);
    if (selectedView) {
        selectedView.classList.add('active');
    }

    // Update active nav link
    const navItems = document.querySelectorAll('.nav-links li');
    navItems.forEach(item => {
        item.classList.remove('active');
    });

    if (targetLink) {
        targetLink.parentElement.classList.add('active');
    }
}

/**
 * Sets up event listeners for settings controls (carbon factor and theme toggle).
 */
function setupSettingsModifiers() {
    const carbonInput = document.getElementById('carbon-factor');
    if (carbonInput) {
        carbonInput.addEventListener('input', (e) => {
            const factor = parseFloat(e.target.value) || 0;

            let totalGrid = 0;
            globalTimeseriesData.forEach(d => {
                totalGrid += d.grid_kwh;
                d.carbon_emissions_kg = d.grid_kwh * factor;
            });

            const newEmissions = totalGrid * factor;

            const obj = document.getElementById('total-emissions');
            const currentNum = parseFloat(obj.textContent) || 0;

            globalSummaryData.total_emissions = newEmissions;
            animateValue(obj, currentNum, newEmissions, 500, ' kg');

            const labels = globalTimeseriesData.map(d => {
                return new Date(d.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            });
            renderEmissionsChart(labels, globalTimeseriesData);
        });
    }


}
