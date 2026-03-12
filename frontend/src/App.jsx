import { useState } from 'react';
import { useData } from './api/useData';
import { useSettings } from './context/SettingsContext';
import AlertPanel from './components/AlertPanel';
import Controls from './components/Controls';
import OverlayChart from './components/OverlayChart';
import SettingsModal from './components/SettingsModal';
import Reports from './components/Reports';
import { Loader2 } from 'lucide-react';
import './index.css';

/**
 * Main App Component for the EcoShift Dashboard.
 * 
 * Responsibilities:
 * - Fetches timeseries data and active alerts from the backend API.
 * - Manages global UI state (selected time range, active metric to display).
 * - Renders the main dashboard layout, including the sidebar, header, AlertPanel, Controls, and OverlayChart.
 */
function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [timeRange, setTimeRange] = useState('24H');
  const [metric, setMetric] = useState('energy_draw');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const { settings } = useSettings();
  
  // Pass timeRange to hook
  const { data, loading, error } = useData(timeRange);

  // ── Alert evaluation ──────────────────────────────────────────────────────
  // Alerts are computed entirely client-side from user-configured thresholds
  // so they react instantly to Settings changes without a network round-trip.
  // We evaluate the most recent 24H of available actual data.
  // NOTE: NESO data can lag 24-28h behind real-time, so we anchor the 24H
  // window to the LATEST actual timestamp in the dataset — not Date.now().
  const currentThreshold = settings.thresholds[metric];
  let isExceeded = false;
  const activeAlerts = [];

  if (data?.timeseries && data.timeseries.length > 0) {
    // Find the most recent actual data point timestamp in the dataset
    const latestActualMs = data.timeseries.reduce((max, item) => {
      const hasActual = item.energy_draw?.actual != null || item.carbon_emissions?.actual != null;
      if (!hasActual) return max;
      const t = new Date(item.timestamp).getTime();
      return t > max ? t : max;
    }, 0);

    // 24H window anchored to the latest actual (not wall-clock time)
    const cutoff24H = latestActualMs - 24 * 60 * 60 * 1000;

    // Actuals within the last 24H of available data
    const recent24H = data.timeseries.filter(item => {
      const ts = new Date(item.timestamp).getTime();
      return ts >= cutoff24H && ts <= latestActualMs && (
        item.energy_draw?.actual != null ||
        item.carbon_emissions?.actual != null
      );
    });

    // Latest actual for chart-glow calculation
    const latestActual = [...data.timeseries]
      .reverse()
      .find(item => item[metric]?.actual != null);
    if (latestActual && latestActual[metric].actual > currentThreshold) {
      isExceeded = true;
    }

    // Energy threshold — find most recent breach in last 24H
    const energyBreach = [...recent24H]
      .reverse()
      .find(item => (item.energy_draw?.actual ?? 0) > settings.thresholds.energy_draw);
    if (energyBreach) {
      const unit = settings.unitPreference === 'large' ? 'MWh' : 'kWh';
      activeAlerts.push({
        alert_id: `energy_draw_exceed_${energyBreach.timestamp}`,
        type: 'PEAK_GRID_DRAW',
        message: `Energy draw of ${energyBreach.energy_draw.actual} ${unit} exceeded the ${settings.thresholds.energy_draw} ${unit} threshold.`,
        timestamp: energyBreach.timestamp,
        severity: 'CRITICAL',
      });
    }

    // Carbon threshold — find most recent breach in last 24H
    const carbonBreach = [...recent24H]
      .reverse()
      .find(item => (item.carbon_emissions?.actual ?? 0) > settings.thresholds.carbon_emissions);
    if (carbonBreach) {
      const unit = settings.unitPreference === 'large' ? 'Tonnes CO2' : 'kgCO2';
      activeAlerts.push({
        alert_id: `carbon_emissions_exceed_${carbonBreach.timestamp}`,
        type: 'HIGH_CARBON_EMISSIONS',
        message: `Carbon emissions of ${carbonBreach.carbon_emissions.actual} ${unit} exceeded the ${settings.thresholds.carbon_emissions} ${unit} threshold.`,
        timestamp: carbonBreach.timestamp,
        severity: 'CRITICAL',
      });
    }
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Failed to Load Data</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Top Bar Navigation — Logo | Alerts (center) | Status */}
      <header className="dashboard-header">
        <div className="header-brand">
          <h2>EcoShift</h2>
          <p className="brand-subtitle">Energy & Emissions Tracker</p>
        </div>
        <div className="header-alerts-slot">
          <AlertPanel alerts={activeAlerts} mode="header" />
        </div>
        <div className="status-indicator">
          <span className="pulse-dot"></span>
          <span>Live Integration</span>
        </div>
      </header>

      <div className="app-content-layout">
        {/* Sidebar Navigation */}
        <nav className="sidebar">
          <ul className="nav-links">
            <li className={activeTab === 'dashboard' ? 'active' : ''}>
              <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('dashboard'); }}>Dashboard</a>
            </li>
            <li className={activeTab === 'reports' ? 'active' : ''}>
              <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('reports'); }}>Reports</a>
            </li>
          </ul>
          <div className="sidebar-bottom">
            <ul className="nav-links">
              <li><a href="#" onClick={(e) => { e.preventDefault(); setIsSettingsOpen(true); }}>Settings</a></li>
            </ul>
          </div>
        </nav>

        <div className="main-wrapper">
          <main className="dashboard-container">
          {activeTab === 'dashboard' ? (
            <>
              <section className="controls-section">
                <Controls
                  timeRange={timeRange}
                  setTimeRange={setTimeRange}
                  metric={metric}
                  setMetric={setMetric}
                />
              </section>

              <section className="charts-grid">
                <div className={`chart-container glass-panel ${isExceeded ? 'critical-glow' : ''}`}>
                  <div className="chart-header">
                    <h2>{metric === 'energy_draw' ? 'Energy Draw' : 'Carbon Emissions'} {settings.unitPreference === 'large' ? (metric === 'energy_draw' ? '(MWh)' : '(Tonnes)') : (metric === 'energy_draw' ? '(kWh)' : '(kgCO2)')}</h2>
                    <span className="info-tooltip" data-tip="Solid lines show observed actuals. Dashed lines show the ML 24-hour forecast. Hover any point for exact values.">?</span>
                  </div>
                  
                  {/* Wrapping chart to overlay local loader */}
                  <div className="chart-relative-wrapper">
                      {loading && (
                          <div className="chart-loading-overlay">
                              <Loader2 className="spinner" size={48} />
                          </div>
                      )}
                      <OverlayChart data={data?.timeseries} metric={metric} />
                  </div>

                  <div className="ml-disclaimer">
                    Note: Predictive forecasting is generated by a Machine Learning model and should be used for estimation purposes only. Actual energy draw and carbon emissions may vary.
                  </div>
                </div>
              </section>
            </>
          ) : (
             <Reports />
          )}

          <SettingsModal
            isOpen={isSettingsOpen}
            onClose={() => setIsSettingsOpen(false)}
          />

          {activeTab !== 'dashboard' && (
            <footer className="dashboard-footer">
              <p>Data powered by NESO Demand &amp; Carbon Intensity APIs. ML forecasts are estimates only.</p>
            </footer>
          )}
        </main>
        </div>
      </div>
    </div>
  );
}

export default App;
