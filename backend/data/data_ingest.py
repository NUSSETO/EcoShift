"""
Data ingestion pipeline — fetches live data from two UK government APIs and
merges them into a single hourly Parquet file for the ML model and API layer.

Sources:
    1. NESO National Grid (resource 177f6fa4) — half-hourly national electricity demand
    2. Carbon Intensity API — half-hourly grid carbon intensity (gCO2/kWh)

Output:
    backend/data/historical_data.parquet  (columns: energy_draw_kwh, carbon_emissions_kg)
"""

import os
import logging
import time
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd

def fetch_with_retry(fetch_fn, retries=3, delay=5):
    """Call fetch_fn, retrying up to `retries` times on failure."""
    for attempt in range(1, retries + 1):
        try:
            return fetch_fn()
        except Exception as e:
            logging.warning(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError(f"All {retries} attempts failed.")

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
OUTPUT_DIR = "data"
PARQUET_PATH = os.path.join(OUTPUT_DIR, "historical_data.parquet")

NESO_RESOURCE_ID = "177f6fa4-ae49-4182-81ea-0c6b35f26ca6" # Demand Data Update (live, daily updated)
NESO_API_URL = "https://api.neso.energy/api/3/action/datastore_search"

CARBON_API_URL_BASE = "https://api.carbonintensity.org.uk/intensity"

def fetch_carbon_intensity(start_time, end_time):
    start_str = start_time.strftime("%Y-%m-%dT%H:%MZ")
    end_str = end_time.strftime("%Y-%m-%dT%H:%MZ")
    url = f"{CARBON_API_URL_BASE}/{start_str}/{end_str}"
    
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json().get('data', [])
    records = []
    for item in data:
        records.append({
            'timestamp': item['from'],
            'intensity_actual': item['intensity']['actual'],
            'intensity_forecast': item['intensity']['forecast']
        })
    df_carbon = pd.DataFrame(records)
    if not df_carbon.empty:
        df_carbon['timestamp'] = pd.to_datetime(df_carbon['timestamp'])
        df_carbon.set_index('timestamp', inplace=True)
    return df_carbon

def fetch_neso_demand(limit=500):
    params = {
        'resource_id': NESO_RESOURCE_ID,
        'limit': limit,
        'sort': '_id desc',
        'filters': '{"FORECAST_ACTUAL_INDICATOR": "A"}'  # Actuals only, exclude future forecasts
    }
    response = requests.get(NESO_API_URL, params=params)
    response.raise_for_status()
    records = response.json()['result']['records']
    
    # NESO data comes with SETTLEMENT_DATE and SETTLEMENT_PERIOD.
    # 1 period = 30 minutes.
    parsed_records = []
    for r in records:
        try:
            # Date format often DD-MON-YYYY like 01-JAN-2026
            dt = datetime.strptime(r['SETTLEMENT_DATE'], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            dt = datetime.strptime(r['SETTLEMENT_DATE'], "%Y-%m-%d")
            
        period_offset = int(r['SETTLEMENT_PERIOD']) - 1
        record_time = dt + timedelta(minutes=30 * period_offset)
        record_time = record_time.replace(tzinfo=timezone.utc)
        
        parsed_records.append({
            'timestamp': record_time,
            'national_demand_mw': float(r['ND']) if r.get('ND') else None
        })
        
    df_neso = pd.DataFrame(parsed_records)
    if not df_neso.empty:
        df_neso.set_index('timestamp', inplace=True)
        # Sort index because _id desc means reverse chronological
        df_neso.sort_index(inplace=True)
    return df_neso

def calculate_fetch_limit():
    """Fetch enough records to cover max(7 days, month-to-date) + 1 day buffer."""
    from datetime import datetime, timezone
    days_since_month_start = datetime.now(timezone.utc).day
    days_needed = max(7, days_since_month_start) + 1
    return days_needed * 48  # 48 half-hour periods per day

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    limit = calculate_fetch_limit()
    logging.info(f"Fetching NESO Demand data (limit={limit})")
    try:
        df_neso = fetch_with_retry(lambda: fetch_neso_demand(limit=limit))
    except RuntimeError as e:
        logging.error(f"NESO fetch failed after retries: {e}")
        return

    if df_neso.empty:
        logging.error("NESO returned empty dataset.")
        return

    # NESO data often lags. Use its date range to fetch Carbon Intensity data.
    start_time = df_neso.index.min()
    end_time = df_neso.index.max()

    logging.info(f"Fetching Carbon Intensity data from {start_time} to {end_time}")
    try:
        df_carbon = fetch_with_retry(lambda: fetch_carbon_intensity(start_time, end_time))
    except RuntimeError as e:
        logging.error(f"Carbon Intensity fetch failed after retries: {e}")
        return
    
    if df_carbon.empty:
        logging.error("Failed to fetch Carbon data for the given range.")
        return
        
    logging.info(f"NESO demand index range: {df_neso.index.min()} to {df_neso.index.max()}")
    logging.info(f"Carbon intensity index range: {df_carbon.index.min()} to {df_carbon.index.max()}")
        
    # NESO data often lags a bit, so we merge inner or left
    logging.info("Merging and aligning datasets")
    # Both are tz-aware now. Use combine_first or join. Let's merge on index.
    df_merged = df_neso.join(df_carbon, how='inner')
    
    # Fill actual intensity with forecast if actual is missing
    df_merged['intensity'] = df_merged['intensity_actual'].fillna(df_merged['intensity_forecast'])
    
    # Downsample to 1 hour frequency. 
    # For demand (MW), taking the mean over the hour is appropriate.
    # For intensity (gCO2/kWh), taking the mean is appropriate.
    logging.info("Resampling to 1-hour intervals")
    df_hourly = df_merged.resample('1h').mean()
    
    # Scale demand to simulate a single site.
    # Suppose UK demand is 30,000 MW. We scale by 0.00001 = 0.3 MW = 300 kW.
    # Since it's for 1 hour, kW * 1h = kWh.
    SCALE_FACTOR = 0.00001
    df_hourly['energy_draw_kwh'] = df_hourly['national_demand_mw'] * 1000 * SCALE_FACTOR
    
    # Calculate carbon emissions
    # kgCO2 = energy_draw (kWh) * intensity (gCO2/kWh) / 1000
    df_hourly['carbon_emissions_kg'] = df_hourly['energy_draw_kwh'] * df_hourly['intensity'] / 1000.0
    
    # Clean up columns
    final_cols = ['energy_draw_kwh', 'carbon_emissions_kg']
    df_final = df_hourly[final_cols].copy()
    
    # Drop rows where all are NaN
    df_final.dropna(how='all', inplace=True)
    
    if df_final.empty:
        logging.warning("No overlapping data found after merge and resampling.")
        return
        
    # Save to Parquet
    logging.info(f"Saving {len(df_final)} records to {PARQUET_PATH}")
    df_final.to_parquet(PARQUET_PATH)
    
if __name__ == "__main__":
    main()
