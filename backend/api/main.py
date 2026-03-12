import json
import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from api.utils import load_processed_data

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

async def refresh_data_periodically():
    while True:
        try:
            print("Running background data refresh...")
            backend_dir = str(Path(__file__).parent.parent)
            proc1 = await asyncio.create_subprocess_exec(
                sys.executable, "data/data_ingest.py",
                cwd=backend_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc1.communicate()
            if proc1.returncode == 0:
                print("Data refresh complete.")
                # Invalidate cache so next request picks up fresh data
                _forecast_cache["timestamps"].clear()
                _forecast_cache["data"].clear()
            else:
                print(f"Data refresh exited with code {proc1.returncode}: {stderr.decode()}")
        except Exception as e:
            print(f"Background refresh failed: {e}")
        # Wait for 1 hour (3600 seconds)
        await asyncio.sleep(3600)

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
    
    This endpoint merges historical data with 24-hour ML forecasts. It also 
    evaluates thresholds to generate real-time alerts. Responses are cached 
    for 5 minutes to optimize performance under load.
    """
    global _forecast_cache
    
    current_time = time.time()
    cached_timestamp = _forecast_cache["timestamps"].get(range, 0)
    cached_data = _forecast_cache["data"].get(range)
    
    if cached_data and (current_time - cached_timestamp) < CACHE_TTL:
        return cached_data

    import pandas as pd
    from datetime import datetime, timedelta, timezone
    if HISTORICAL_FILE.exists():
        df_historical = pd.read_parquet(HISTORICAL_FILE)
        df_historical = df_historical.reset_index()
        time_col = 'timestamp' if 'timestamp' in df_historical.columns else df_historical.columns[0]
        df_historical = df_historical.rename(columns={time_col: 'timestamp'})
        
        # Ensure timestamp is datetime and timezone aware
        df_historical['timestamp'] = pd.to_datetime(df_historical['timestamp'])
        if df_historical['timestamp'].dt.tz is None:
             df_historical['timestamp'] = df_historical['timestamp'].dt.tz_localize('UTC')

        if not df_historical.empty:
            last_timestamp = df_historical['timestamp'].max()
            
            if range == "24H":
                start_time = last_timestamp - timedelta(hours=24)
                df_historical = df_historical[df_historical['timestamp'] >= start_time]
            elif range == "7D":
                start_time = last_timestamp - timedelta(days=7)
                df_historical = df_historical[df_historical['timestamp'] >= start_time]
            elif range == "MTD":
                # Month-to-date: from the 1st of the current month (based on latest data point to prevent timezone mismatches)
                start_time = last_timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                df_historical = df_historical[df_historical['timestamp'] >= start_time]
            else:
                # Default to 24H if unknown range
                start_time = last_timestamp - timedelta(hours=24)
                df_historical = df_historical[df_historical['timestamp'] >= start_time]
            
            # Do not set_index back to timestamp here, as the ML forecaster expects a 'timestamp' column
            pass
    else:
        df_historical = pd.DataFrame()
    
    model = get_forecaster()
    if not model:
        return {"error": "Model not trained yet."}
    
    # 1. Get the forecast schema which already has the timeseries list
    forecast_data = model.generate_forecast(df_historical)
    
    # 2. Evaluate actual metrics for alerts
    from api.alerting import evaluate_thresholds
    if not df_historical.empty:
        latest_actual = df_historical.iloc[-1].to_dict()
        realtime_alerts = evaluate_thresholds(latest_actual)
        if "active_alerts" not in forecast_data:
            forecast_data["active_alerts"] = []
        forecast_data["active_alerts"].extend(realtime_alerts)
        
    # 3. Cache the result
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
