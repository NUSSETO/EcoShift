import pandas as pd
import json
from pathlib import Path
from ml_forecast import generate_forecast

def process_data():
    """Processes raw data and calls the ML forecasting logic."""
    base_dir = Path(__file__).parent
    raw_file = base_dir / 'raw_energy_data.csv'
    
    # Read the raw data
    print(f"Reading {raw_file.name}...")
    df = pd.read_csv(raw_file)
    
    # 1. Clean missing values
    # By interpolating the time series missing values and filling any remaining NaNs with 0
    df['solar_power'] = df['solar_power'].interpolate(limit_direction='both').fillna(0)
    df['wind_power'] = df['wind_power'].interpolate(limit_direction='both').fillna(0)
    df['grid_draw'] = df['grid_draw'].interpolate(limit_direction='both').fillna(0)
    
    # 2. Calculate carbon emissions
    # Solar/wind = 0kg/kWh, Grid = 0.45kg/kWh
    df['carbon_emissions_kg'] = df['grid_draw'] * 0.45
    
    # 3. Reconstruct timestamp
    # Combine 'date' and 'hour' into a single ISO 8601-like timestamp formatted string
    df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    
    # 4. Map columns to match the expected JSON schema
    df = df.rename(columns={
        'solar_power': 'solar_kwh',
        'wind_power': 'wind_kwh',
        'grid_draw': 'grid_kwh'
    })
    
    final_cols = ['timestamp', 'solar_kwh', 'wind_kwh', 'grid_kwh', 'carbon_emissions_kg']
    df_final = df[final_cols]
    
    # 5. Export to processed_data.json as an array of objects
    records = df_final.to_dict(orient='records')
    
    processed_file = base_dir / 'processed_data.json'
    with open(processed_file, 'w') as f:
        json.dump(records, f, indent=4)
        
    print(f"Successfully exported processed data to {processed_file.name}")
    
    # 6. Generate 24-hour forecast
    generate_forecast(df_final, base_dir)

if __name__ == "__main__":
    process_data()
