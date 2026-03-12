# EcoShift Data Pipeline

## Overview

The data ingestion pipeline fetches live data from two UK government APIs, merges and resamples them into a single hourly Parquet file, which is then used by the ML model and the FastAPI backend.

## Data Sources

1. **National Grid ESO (NESO)**
   - **Dataset**: Historic Demand Data (resource `177f6fa4`)
   - **Metric**: National Demand (`ND`) in MW
   - **Interval**: 30-minute settlement periods
   - **Lag**: Data typically arrives **24-28 hours** behind real time
   - **Normalization**: National demand is scaled by `0.00001` to simulate a single site. For example, `30,000 MW * 0.00001 = 0.3 MW = 300 kW`. Since the data is resampled to 1-hour intervals, kW = kWh.

2. **UK Carbon Intensity API**
   - **Metric**: Grid carbon intensity in `gCO2/kWh`
   - **Interval**: 30 minutes
   - **Matching**: Carbon data is fetched for the exact timeframe that NESO data covers, ensuring alignment even when NESO data is delayed.

## ETL Process (`backend/data/data_ingest.py`)

1. **Extract**: Fetch data from both APIs. The fetch limit is calculated dynamically to cover `max(7 days, month-to-date) + 1 day buffer`. Retries up to 3 times on failure.
2. **Transform**:
   - Parse timestamps to UTC-aware datetime
   - Inner join on timestamp index
   - Fill missing carbon actuals with forecast values
   - Resample to 1-hour intervals (mean)
   - Derive `energy_draw_kwh` from scaled national demand
   - Derive `carbon_emissions_kg` from `energy_draw_kwh * intensity / 1000`
3. **Load**: Save to `backend/data/historical_data.parquet`

## Refresh Mechanisms

### Background Refresh (Production)

The FastAPI backend runs a background task (`refresh_data_periodically` in `main.py`) that:
- Re-ingests data every **1 hour**
- Retrains the ML model every **7th refresh** (~weekly)
- Can be disabled with `DISABLE_BACKGROUND_REFRESH=1`

### Cron Job (Optional)

For standalone ingestion outside the API process:

```bash
# cron_pipeline.sh — runs data_ingest.py from the backend directory
0 1 * * * /path/to/EcoShift/cron_pipeline.sh >> /tmp/ecoshift_cron.log 2>&1
```

### Build-time Bootstrap (Render Deploy)

On Render, the filesystem is ephemeral. The `buildCommand` in `render.yaml` runs both ingestion and training on every deploy:

```yaml
buildCommand: "pip install -r requirements.txt && python data/data_ingest.py && python ml/train_model.py"
```
