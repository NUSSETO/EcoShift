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

  // Check if latest data exceeds threshold
  const currentThreshold = settings.thresholds[metric];
  let isExceeded = false;
  let dynamicAlerts = [];

  if (data?.timeseries && data.timeseries.length > 0) {
    // Find the latest entry that has actual recorded data (not future predictions)
    const latestData = [...data.timeseries].reverse().find(item => item.energy_draw?.actual != null) || data.timeseries[data.timeseries.length - 1];
    
    // Check metric threshold for chart glow
    if (latestData[metric]?.actual > currentThreshold) {
      isExceeded = true;
    }

    // Generate dynamic alerts based on global settings
    if (latestData['energy_draw']?.actual > settings.thresholds.energy_draw) {
        dynamicAlerts.push({
            alert_id: `energy_draw_exceed_${latestData.timestamp}`,
            type: 'HIGH_ENERGY_DRAW',
            message: `Energy draw exceeded the ${settings.thresholds.energy_draw} ${settings.unitPreference === 'large' ? 'MWh' : 'kWh'} threshold.`,
            timestamp: latestData.timestamp,
            severity: 'CRITICAL'
        });
    }

    if (latestData['carbon_emissions']?.actual > settings.thresholds.carbon_emissions) {
        dynamicAlerts.push({
            alert_id: `carbon_emissions_exceed_${latestData.timestamp}`,
            type: 'HIGH_CARBON_EMISSIONS',
            message: `Carbon emissions exceeded the ${settings.thresholds.carbon_emissions} ${settings.unitPreference === 'large' ? 'Tonnes CO2' : 'kgCO2'} threshold.`,
            timestamp: latestData.timestamp,
            severity: 'CRITICAL'
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
          <AlertPanel alerts={[...(data?.active_alerts || []), ...dynamicAlerts]} mode="header" />
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
                    <span className="info-tooltip" title="Displays actual energy consumption or carbon emissions from the facility compared to the Machine Learning 24-hour forecast. Solid lines represent observed actuals. Dashed lines project the ML forecasts.">?</span>
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
