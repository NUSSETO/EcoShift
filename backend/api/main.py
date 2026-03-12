"""
EcoShift API — FastAPI backend serving timeseries data, ML forecasts, and CSV reports.

Endpoints:
    GET /health                      Service readiness (data + model status)
    GET /api/v1/metrics/timeseries   Actuals + 24h ML forecast + alerts (cached 5 min)
    GET /api/v1/metrics/report       CSV export (timeseries / summary / forecast / alerts)

Background tasks:
    - Hourly data refresh (NESO + Carbon Intensity re-ingestion)
    - Weekly model retraining (every 7th refresh cycle)
"""

import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from ml.ml_forecast import EnergyForecaster

app = FastAPI(title="EcoShift API")

# Lazy-loaded ML model — rebuilt on retrain, force-reloaded by setting to None
MODEL_FILE = Path(__file__).parent.parent / "ml" / "forecaster.pkl"
forecaster = None

def get_forecaster():
    global forecaster
    if forecaster is None and MODEL_FILE.exists():
        forecaster = EnergyForecaster(str(MODEL_FILE))
    return forecaster

_refresh_count = 0

async def run_subprocess(script: str, backend_dir: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, script,
        cwd=backend_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        print(f"[{script}] failed (code {proc.returncode}): {stderr.decode()[:500]}")
        return False
    return True

async def refresh_data_periodically():
    global _refresh_count, forecaster
    backend_dir = str(Path(__file__).parent.parent)
    while True:
        await asyncio.sleep(3600)  # wait first, build already ran ingest+train
        _refresh_count += 1
        print(f"Background refresh #{_refresh_count}...")
        try:
            ok = await run_subprocess("data/data_ingest.py", backend_dir)
            if ok:
                print("Data ingestion complete.")
                _forecast_cache["timestamps"].clear()
                _forecast_cache["data"].clear()
                # Retrain model every 7 refreshes (~weekly)
                if _refresh_count % 7 == 0:
                    print("Retraining ML model...")
                    trained = await run_subprocess("ml/train_model.py", backend_dir)
                    if trained:
                        forecaster = None  # force lazy reload of new model
                        print("Model retrained.")
            else:
                print("Ingest failed — keeping existing data.")
        except Exception as e:
            print(f"Background refresh error: {e}")

@app.on_event("startup")
async def startup_event():
    import os
    if os.getenv("DISABLE_BACKGROUND_REFRESH") != "1":
        asyncio.create_task(refresh_data_periodically())

# Setup CORS — configure ALLOWED_ORIGINS env var in production (comma-separated)
import os as _os
_default_origins = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5500"
origins = [o.strip() for o in _os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORICAL_FILE = Path(__file__).parent.parent / "data" / "historical_data.parquet"

@app.get("/health")
def health():
    return {
        "status": "ok",
        "data_available": HISTORICAL_FILE.exists(),
        "model_loaded": get_forecaster() is not None,
    }

import time

_forecast_cache = {
    "timestamps": {},  # type: dict[str, float]
    "data": {}         # type: dict[str, dict]
}
CACHE_TTL = 300  # 5 minutes

@app.get("/api/v1/metrics/timeseries")
def get_metrics_timeseries(range: str = "24H"):
    """
    Returns the unified JSON schema containing timeseries data and alerts.

    For 24H: last 24h actuals + 24h ML forecast.
    For 7D/MTD: full historical actuals for the range + 24h ML forecast appended.
    Responses are cached for 5 minutes.
    """
    global _forecast_cache

    current_time = time.time()
    cached_timestamp = _forecast_cache["timestamps"].get(range, 0)
    cached_data = _forecast_cache["data"].get(range)

    if cached_data and (current_time - cached_timestamp) < CACHE_TTL:
        return cached_data

    import pandas as pd
    from datetime import datetime, timedelta, timezone

    if not HISTORICAL_FILE.exists():
        return {"error": "No historical data available."}

    # Load full dataset
    df_all = pd.read_parquet(HISTORICAL_FILE)
    df_all = df_all.reset_index()
    time_col = 'timestamp' if 'timestamp' in df_all.columns else df_all.columns[0]
    df_all = df_all.rename(columns={time_col: 'timestamp'})
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    if df_all['timestamp'].dt.tz is None:
        df_all['timestamp'] = df_all['timestamp'].dt.tz_localize('UTC')

    if df_all.empty:
        return {"error": "No historical data available."}

    last_timestamp = df_all['timestamp'].max()

    # Display range filter
    if range == "7D":
        start_time = last_timestamp - timedelta(days=7)
    elif range == "MTD":
        start_time = last_timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_time = last_timestamp - timedelta(hours=24)

    df_display = df_all[df_all['timestamp'] >= start_time].copy()

    # ML always uses last 48h for reliable lag features
    df_for_ml = df_all[df_all['timestamp'] >= (last_timestamp - timedelta(hours=48))].copy()

    model = get_forecaster()
    if not model:
        return {"error": "Model not trained yet."}

    forecast_data = model.generate_forecast(df_for_ml)

    if range != "24H":
        # Rebuild timeseries: full historical actuals + future ML predictions
        energy_col = 'energy_draw_kwh' if 'energy_draw_kwh' in df_display.columns else 'energy_draw'
        carbon_col = 'carbon_emissions_kg' if 'carbon_emissions_kg' in df_display.columns else 'carbon_emissions'

        historical_ts = []
        for _, row in df_display.sort_values('timestamp').iterrows():
            ts_str = row['timestamp'].strftime("%Y-%m-%dT%H:00:00Z")
            historical_ts.append({
                "timestamp": ts_str,
                "energy_draw": {
                    "actual": round(float(row[energy_col]), 2) if pd.notna(row[energy_col]) else None,
                    "predicted": None
                },
                "carbon_emissions": {
                    "actual": round(float(row[carbon_col]), 2) if pd.notna(row[carbon_col]) else None,
                    "predicted": None
                }
            })

        # Future-only predictions (h > 0, no actual)
        future_preds = [
            ts for ts in forecast_data.get('timeseries', [])
            if ts['energy_draw']['actual'] is None
        ]

        # Attach prediction to the last actual point (h=0 overlap)
        current_point = next(
            (ts for ts in forecast_data.get('timeseries', [])
             if ts['energy_draw']['actual'] is not None and ts['energy_draw']['predicted'] is not None),
            None
        )
        if current_point and historical_ts and historical_ts[-1]['timestamp'] == current_point['timestamp']:
            historical_ts[-1]['energy_draw']['predicted'] = current_point['energy_draw']['predicted']
            historical_ts[-1]['carbon_emissions']['predicted'] = current_point['carbon_emissions']['predicted']

        forecast_data['timeseries'] = historical_ts + future_preds
        forecast_data['metadata']['range_start'] = df_display['timestamp'].min().strftime("%Y-%m-%dT%H:00:00Z")
        forecast_data['metadata']['range_end'] = (last_timestamp + timedelta(hours=24)).strftime("%Y-%m-%dT%H:00:00Z")

    # Evaluate thresholds against latest actual
    from api.alerting import evaluate_thresholds
    if not df_display.empty:
        latest_actual = df_display.sort_values('timestamp').iloc[-1].to_dict()
        realtime_alerts = evaluate_thresholds(latest_actual)
        if "active_alerts" not in forecast_data:
            forecast_data["active_alerts"] = []
        forecast_data["active_alerts"].extend(realtime_alerts)

    _forecast_cache["data"][range] = forecast_data
    _forecast_cache["timestamps"][range] = current_time

    return forecast_data

from fastapi.responses import StreamingResponse
import io
import csv
from datetime import datetime

def _build_timeseries_csv(timeseries: list) -> str:
    """Raw timeseries: one row per hour, actuals + predictions."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp",
        "Energy Draw Actual (kWh)",
        "Energy Draw Predicted (kWh)",
        "Carbon Emissions Actual (kgCO2)",
        "Carbon Emissions Predicted (kgCO2)",
    ])
    for row in timeseries:
        writer.writerow([
            row.get("timestamp", ""),
            row.get("energy_draw", {}).get("actual", ""),
            row.get("energy_draw", {}).get("predicted", ""),
            row.get("carbon_emissions", {}).get("actual", ""),
            row.get("carbon_emissions", {}).get("predicted", ""),
        ])
    return output.getvalue()


def _build_summary_csv(timeseries: list) -> str:
    """Daily summary: one row per calendar day with total, peak, and average."""
    import collections
    days: dict = collections.defaultdict(lambda: {
        "energy_actuals": [], "carbon_actuals": []
    })
    for row in timeseries:
        ts = row.get("timestamp", "")
        if not ts:
            continue
        day = ts[:10]  # "YYYY-MM-DD"
        e_actual = row.get("energy_draw", {}).get("actual")
        c_actual = row.get("carbon_emissions", {}).get("actual")
        if e_actual is not None:
            days[day]["energy_actuals"].append(e_actual)
        if c_actual is not None:
            days[day]["carbon_actuals"].append(c_actual)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Total Energy Draw (kWh)",
        "Peak Energy Draw (kWh)",
        "Avg Hourly Energy Draw (kWh)",
        "Total Carbon Emissions (kgCO2)",
        "Peak Carbon Emissions (kgCO2)",
        "Avg Hourly Carbon Emissions (kgCO2)",
    ])
    for day in sorted(days.keys()):
        e = days[day]["energy_actuals"]
        c = days[day]["carbon_actuals"]
        writer.writerow([
            day,
            round(sum(e), 2) if e else "",
            round(max(e), 2) if e else "",
            round(sum(e) / len(e), 2) if e else "",
            round(sum(c), 2) if c else "",
            round(max(c), 2) if c else "",
            round(sum(c) / len(c), 2) if c else "",
        ])
    return output.getvalue()


def _build_forecast_csv(timeseries: list) -> str:
    """24-hour ML forecast: future-only predicted rows."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Forecast Timestamp",
        "Predicted Energy Draw (kWh)",
        "Predicted Carbon Emissions (kgCO2)",
    ])
    for row in timeseries:
        e = row.get("energy_draw", {})
        c = row.get("carbon_emissions", {})
        # Future-only: no actual value recorded
        if e.get("actual") is None and e.get("predicted") is not None:
            writer.writerow([
                row.get("timestamp", ""),
                e.get("predicted", ""),
                c.get("predicted", ""),
            ])
    return output.getvalue()


def _build_alerts_csv(timeseries: list, energy_threshold: float = 300.0, carbon_threshold: float = 60.0) -> str:
    """Alert history: every hour where an actual reading breached a threshold."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp",
        "Alert Type",
        "Metric",
        "Actual Value",
        "Threshold",
        "Excess",
    ])
    for row in timeseries:
        ts = row.get("timestamp", "")
        e_actual = row.get("energy_draw", {}).get("actual")
        c_actual = row.get("carbon_emissions", {}).get("actual")
        if e_actual is not None and e_actual > energy_threshold:
            writer.writerow([
                ts,
                "PEAK_GRID_DRAW",
                "Energy Draw (kWh)",
                round(e_actual, 2),
                energy_threshold,
                round(e_actual - energy_threshold, 2),
            ])
        if c_actual is not None and c_actual > carbon_threshold:
            writer.writerow([
                ts,
                "HIGH_CARBON_EMISSIONS",
                "Carbon Emissions (kgCO2)",
                round(c_actual, 2),
                carbon_threshold,
                round(c_actual - carbon_threshold, 2),
            ])
    return output.getvalue()


@app.get("/api/v1/metrics/report")
def generate_report(
    type: str = "timeseries",
    range: str = "24H",
    energy_threshold: float = 300.0,
    carbon_threshold: float = 60.0,
):
    """
    Generates a CSV report.

    type:
      - timeseries  — hourly actuals + ML predictions  (range: 24H / 7D / MTD)
      - summary     — daily aggregates (total, peak, avg)  (range: 7D / MTD)
      - forecast    — 24-hour ML-only future predictions
      - alerts      — historical threshold breaches  (range: 24H / 7D / MTD)

    range: 24H | 7D | MTD  (ignored for forecast type)
    """
    valid_types = {"timeseries", "summary", "forecast", "alerts"}
    if type not in valid_types:
        return {"error": f"Unknown report type '{type}'. Valid: {sorted(valid_types)}"}

    # Forecast always uses 24H window (future-only rows, range irrelevant)
    fetch_range = "24H" if type == "forecast" else range

    data = get_metrics_timeseries(fetch_range)
    if "error" in data:
        return data

    timeseries = data.get("timeseries", [])

    if type == "timeseries":
        csv_content = _build_timeseries_csv(timeseries)
        type_label = "Timeseries"
    elif type == "summary":
        csv_content = _build_summary_csv(timeseries)
        type_label = "DailySummary"
    elif type == "forecast":
        csv_content = _build_forecast_csv(timeseries)
        type_label = "Forecast"
    else:  # alerts
        csv_content = _build_alerts_csv(timeseries, energy_threshold, carbon_threshold)
        type_label = "AlertHistory"

    date_str = datetime.now().strftime("%Y-%m-%d")
    range_label = "" if type == "forecast" else f"_{range}"
    filename = f"EcoShift_{type_label}{range_label}_{date_str}.csv"

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([csv_content]), media_type="text/csv", headers=headers)
