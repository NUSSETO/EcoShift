import json
import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from utils import load_processed_data, load_forecast_data

app = FastAPI(title="EcoShift API")

async def refresh_data_periodically():
    while True:
        try:
            print("Running background data refresh...")
            proc1 = await asyncio.create_subprocess_exec(sys.executable, "generate_raw_data.py")
            await proc1.communicate()
            proc2 = await asyncio.create_subprocess_exec(sys.executable, "process_data.py")
            await proc2.communicate()
            print("Data refresh complete.")
        except Exception as e:
            print(f"Background refresh failed: {e}")
        # Wait for 1 hour (3600 seconds)
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(refresh_data_periodically())

# Setup CORS to allow a local frontend to communicate with the API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "https://funny-zuccutto-f43fad.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).parent / "processed_data.json"
FORECAST_FILE = Path(__file__).parent / "forecast_data.json"

@app.get("/api/summary")
def get_summary():
    """Returns total energy across all sources and total emissions."""
    data = load_processed_data(DATA_FILE)
    
    total_energy = sum(
        item.get("solar_kwh", 0) + item.get("wind_kwh", 0) + item.get("grid_kwh", 0)
        for item in data
    )
    total_emissions = sum(item.get("carbon_emissions_kg", 0) for item in data)
    
    return {
        "total_energy_kwh": total_energy,
        "total_emissions_kg": total_emissions
    }

@app.get("/api/timeseries")
def get_timeseries():
    """Returns the full array of data for charting purposes."""
    return load_processed_data(DATA_FILE)

@app.get("/api/forecast")
def get_forecast():
    """Returns the 24-hour predictive forecast data."""
    return load_forecast_data(FORECAST_FILE)
