# EcoShift

**Real-time UK Energy & Carbon Emissions Dashboard**

EcoShift monitors UK national electricity grid demand and carbon intensity in real time. It pairs live government data with a 24-hour XGBoost ML forecast, configurable threshold alerts, and downloadable CSV reports — all presented through a dark-themed React dashboard.

---

## Architecture

```
frontend/          React 18 + Vite SPA
  src/
    App.jsx            Root layout, client-side alert evaluation, tab routing
    api/useData.js     Data-fetching hook (polling + caching)
    components/
      OverlayChart.jsx   Recharts line chart (actual vs predicted overlay)
      AlertPanel.jsx     Header alert cards (dismissible, dual-metric)
      Controls.jsx       Time-range + metric toggle bar
      Reports.jsx        CSV export cards (timeseries / summary / forecast / alerts)
      About.jsx          Data-source info and metric glossary
      SettingsModal.jsx  Unit preference + threshold configuration
    context/
      SettingsContext.jsx  Persisted settings (localStorage)

backend/           Python 3.10 — FastAPI
  api/
    main.py            API endpoints, in-memory cache, background refresh
    alerting.py        Threshold evaluation (env-configurable)
  data/
    data_ingest.py     NESO + Carbon Intensity API fetch -> Parquet
  ml/
    train_model.py     XGBoost MultiOutput training (17 features)
    ml_forecast.py     Inference + level-correction bias anchoring
```

### Data Flow

```
NESO National Grid API ---+
                          +--> data_ingest.py --> historical_data.parquet
Carbon Intensity API -----+                              |
                                                         v
                                               train_model.py --> forecaster.pkl
                                                         |
                                                         v
                                               FastAPI (main.py)
                                                   |         |
                                            /timeseries   /report
                                                   |         |
                                                   v         v
                                               React SPA (Vite)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service readiness check (data + model status) |
| `GET` | `/api/v1/metrics/timeseries?range=24H\|7D\|MTD` | Timeseries JSON — actuals + 24h ML forecast + alerts |
| `GET` | `/api/v1/metrics/report?type=...&range=...` | CSV download (types: `timeseries`, `summary`, `forecast`, `alerts`) |

### Timeseries Response Schema

```json
{
  "metadata": {
    "device_or_site_id": "site_001",
    "timezone": "UTC",
    "range_start": "2026-03-10T12:00:00Z",
    "range_end": "2026-03-11T12:00:00Z",
    "units": { "energy_draw": "kWh", "carbon_emissions": "kgCO2" }
  },
  "timeseries": [
    {
      "timestamp": "2026-03-10T12:00:00Z",
      "energy_draw": { "actual": 283.5, "predicted": 279.1 },
      "carbon_emissions": { "actual": 54.2, "predicted": 53.1 }
    }
  ],
  "active_alerts": []
}
```

---

## Data Sources

| Source | What it provides | Update frequency |
|--------|-----------------|------------------|
| [NESO National Grid](https://data.nationalgrideso.com/) (resource `177f6fa4`) | UK national electricity demand (MW) per half-hour settlement period | Daily — typically lags **24-28 hours** behind real time |
| [Carbon Intensity API](https://carbonintensity.org.uk/) | Grid carbon intensity (gCO2/kWh) — actual + forecast | Half-hourly |

### Derived Metrics

- **Energy Draw (kWh)** — National demand (MW) scaled by `0.00001 * 1000` to simulate a single-site reading, resampled to hourly.
- **Carbon Emissions (kgCO2)** — `energy_draw_kwh * intensity_gCO2_per_kWh / 1000`.

---

## ML Forecast

- **Model**: `MultiOutputRegressor(XGBRegressor)` — predicts both energy and carbon simultaneously.
- **Features (17)**: `hour`, `dayofweek`, `month`, lag features at 1/6/24/48h for both metrics, rolling means at 6/12/24h windows.
- **Hyperparameters**: 300 estimators, max depth 6, learning rate 0.05, subsample 0.8, colsample 0.8.
- **Bias correction**: After inference, a linearly decaying offset anchors h=0 prediction to the latest actual value (100% correction at h=0, 0% at h=24).
- **Retraining**: Automatic — every 7th hourly background refresh (~weekly).

---

## Alert System

Alerts are evaluated **entirely client-side** in `App.jsx`. This ensures they react instantly when the user adjusts thresholds in Settings, with no network round-trip.

- The 24-hour scan window is anchored to the **latest actual data timestamp** (not `Date.now()`) because NESO data lags 24-28h.
- Two independent alerts: `PEAK_GRID_DRAW` (energy) and `HIGH_CARBON_EMISSIONS` (carbon).
- Default thresholds: **300 kWh** energy, **60 kgCO2** carbon (configurable via Settings).

---

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+

### Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd ecoshift

# 2. Backend
cd backend
pip install -r requirements.txt
python data/data_ingest.py          # fetch live data -> .parquet
python ml/train_model.py            # train model -> forecaster.pkl
uvicorn api.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev -- --port 3000
```

- **Backend API**: http://localhost:8000 (Swagger docs at `/docs`)
- **Frontend UI**: http://localhost:3000

### Environment Variables (Backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000,...` | CORS origins (comma-separated) |
| `PEAK_GRID_DRAW` | `300.0` | Backend alert threshold for energy (kWh) |
| `MAX_CARBON_EMISSIONS` | `60.0` | Backend alert threshold for carbon (kgCO2) |
| `DISABLE_BACKGROUND_REFRESH` | `0` | Set to `1` to skip hourly data refresh |

### Environment Variables (Frontend)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## Deployment

### Backend -> Render

Configured via `render.yaml`. The `buildCommand` runs data ingestion and model training on each deploy (Render's filesystem is ephemeral, so `.parquet` and `.pkl` must be rebuilt).

```yaml
buildCommand: "pip install -r requirements.txt && python data/data_ingest.py && python ml/train_model.py"
startCommand: "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
```

### Frontend -> Netlify

- **Build command**: `npm run build`
- **Publish directory**: `dist`
- **Environment**: Set `VITE_API_URL` to the live Render backend URL.

---

## Testing

Tests live in `/tests/` (Playwright E2E) and `/frontend/` (filtering spec).

```bash
# From the tests/ directory
npx playwright test

# Performance test (requires backend running)
cd tests && python test_performance.py
```

---

## Project Structure

```
EcoShift/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app, endpoints, cache, background tasks
│   │   └── alerting.py          # Threshold evaluation
│   ├── data/
│   │   └── data_ingest.py       # NESO + Carbon Intensity -> Parquet
│   ├── ml/
│   │   ├── train_model.py       # XGBoost training pipeline
│   │   └── ml_forecast.py       # Inference with bias correction
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Layout, routing, alert evaluation
│   │   ├── main.jsx             # React entry point
│   │   ├── index.css            # Full stylesheet (dark theme)
│   │   ├── api/useData.js       # Data-fetching hook
│   │   ├── components/          # UI components
│   │   └── context/             # Settings context (localStorage)
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── e2e_frontend.spec.js     # Playwright E2E
│   ├── test_performance.py      # Async non-blocking test
│   └── playwright.config.js
├── render.yaml                  # Render IaC deployment config
└── README.md
```
