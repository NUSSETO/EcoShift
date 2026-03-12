import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from ml.ml_forecast import EnergyForecaster

app = FastAPI(title="EcoShift API")

# Load model lazily
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

@app.get("/api/v1/metrics/report")
def generate_report(format: str = "csv"):
    """
    Generates a CSV report of the time-series data.
    """
    if format != "csv":
        return {"error": "Only CSV format is supported at this time."}

    data = get_metrics_timeseries("24H")  # Or could take range parameter for report too
    if "error" in data:
        return data

    timeseries = data.get("timeseries", [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Timestamp",
        "Energy Draw Actual (kWh)",
        "Energy Draw Predicted (kWh)",
        "Carbon Emissions Actual (kgCO2)",
        "Carbon Emissions Predicted (kgCO2)"
    ])
    
    # Write rows
    for row in timeseries:
        writer.writerow([
            row.get("timestamp", ""),
            row.get("energy_draw", {}).get("actual", ""),
            row.get("energy_draw", {}).get("predicted", ""),
            row.get("carbon_emissions", {}).get("actual", ""),
            row.get("carbon_emissions", {}).get("predicted", "")
        ])
        
    output.seek(0)
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"EcoShift_Report_{timestamp_str}.csv"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
