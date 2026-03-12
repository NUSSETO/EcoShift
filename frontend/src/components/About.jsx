import { Globe, Database, Cpu, BarChart3 } from 'lucide-react';

const DATA_SOURCES = [
  {
    icon: Globe,
    name: 'NESO National Grid',
    detail: 'UK national electricity demand — half-hourly actual readings (resource 177f6fa4). Data typically lags 24–28 hours behind real-time.',
    url: 'https://data.nationalgrideso.com/',
  },
  {
    icon: BarChart3,
    name: 'Carbon Intensity API',
    detail: 'UK government public API providing regional and national carbon emission intensity of the electricity grid, measured in kgCO₂ per kWh.',
    url: 'https://carbonintensity.org.uk/',
  },
];

export default function About() {
  return (
    <div className="about-container">
      <div className="about-page-header">
        <h2 className="about-page-title">About EcoShift</h2>
      </div>

      {/* What is it */}
      <section className="about-section glow-card">
        <h3 className="about-section-title">What is EcoShift?</h3>
        <p className="about-body">
          EcoShift is a real-time energy and carbon emissions dashboard for the UK national electricity grid.
          It visualises actual grid demand alongside ML-predicted forecasts so operators and analysts can
          spot trends, anticipate peaks, and track carbon output — all in one place.
        </p>
        <ul className="about-feature-list">
          <li><strong>Live data</strong> — Hourly energy draw (kWh) and carbon emissions (kgCO₂) pulled from government APIs.</li>
          <li><strong>24-hour ML forecast</strong> — An XGBoost model predicts the next 24 hours of energy and carbon, anchored to the latest actuals with bias correction.</li>
          <li><strong>Configurable alerts</strong> — Set your own thresholds; breach notifications appear instantly when actuals exceed limits within the last 24 hours of data.</li>
          <li><strong>CSV exports</strong> — Download timeseries, daily summaries, forecast-only, or alert history reports.</li>
        </ul>
      </section>

      {/* Data sources */}
      <section className="about-section glow-card">
        <h3 className="about-section-title">Data Sources</h3>
        <div className="about-sources-grid">
          {DATA_SOURCES.map(src => (
            <div key={src.name} className="about-source-card">
              <div className="about-source-icon">
                <src.icon size={18} />
              </div>
              <div>
                <h4 className="about-source-name">{src.name}</h4>
                <p className="about-source-detail">{src.detail}</p>
                <a className="about-source-link" href={src.url} target="_blank" rel="noopener noreferrer">
                  {src.url.replace(/^https?:\/\//, '').replace(/\/$/, '')} ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Key metrics */}
      <section className="about-section glow-card">
        <h3 className="about-section-title">What the Data Means</h3>
        <div className="about-metrics-grid">
          <div className="about-metric-item">
            <Database size={16} className="about-metric-icon" />
            <div>
              <strong>Energy Draw (kWh)</strong>
              <span>Total electrical energy demanded from the UK national grid per half-hour settlement period.</span>
            </div>
          </div>
          <div className="about-metric-item">
            <BarChart3 size={16} className="about-metric-icon" />
            <div>
              <strong>Carbon Emissions (kgCO₂)</strong>
              <span>Estimated CO₂ produced by the electricity generation mix during that period — influenced by the proportion of fossil vs. renewable sources.</span>
            </div>
          </div>
          <div className="about-metric-item">
            <Cpu size={16} className="about-metric-icon" />
            <div>
              <strong>ML Forecast</strong>
              <span>A 24-hour-ahead prediction from an XGBoost model trained on historical patterns (hour-of-day, day-of-week, lag features, rolling averages). Forecast lines are dashed on the chart.</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
