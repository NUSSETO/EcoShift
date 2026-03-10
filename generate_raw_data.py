import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_data():
    now = datetime.now()
    # Snap to the current hour to ensure we lead exactly up to the current hour
    end_date = now.replace(minute=0, second=0, microsecond=0)
    
    # 7 days of hourly data = 7 * 24 = 168 hours
    hours = 7 * 24
    start_date = end_date - timedelta(hours=hours - 1)
    
    timestamps = [start_date + timedelta(hours=i) for i in range(hours)]
    dates = [t.strftime('%Y-%m-%d') for t in timestamps]
    hour_of_day = [t.hour for t in timestamps]
    
    t = np.arange(hours)
    
    # 1. Solar Power: Smooth daily bell curve based on time of day
    # Positive half-sine from hour 6 to hour 18
    base_solar = np.sin((np.array(hour_of_day) - 6) * np.pi / 12) * 50
    # Overlap a slow rolling pattern (simulate cloudy vs sunny days)
    cloud_cover = 1 + 0.3 * np.sin(t * 2 * np.pi / 48)  # 2-day period variation
    solar_power = np.clip(base_solar * cloud_cover, 0, None)
    
    # 2. Wind Power: Continuous, naturally flowing variation (not tied strictly to day/night)
    # Combine two slow sine waves for a natural wind stream pattern without jagged noise
    wind_power = 25 + 15 * np.sin(t * 2 * np.pi / 36) + 10 * np.cos(t * 2 * np.pi / 85)
    wind_power = np.clip(wind_power, 0, None)
    
    # 3. Grid Draw: Natural cyclical consumption with regular peaks
    # Simulate human activity: morning peak + evening peak
    # Simple base structure: 100 kWh baseline
    # Add diurnal waves for the two peaks
    morning_peak = 20 * np.exp(-0.1 * (np.array(hour_of_day) - 9)**2)  # Peak around 9 AM
    evening_peak = 30 * np.exp(-0.1 * (np.array(hour_of_day) - 19)**2) # Peak around 7 PM
    # Add a slow background fluctuation (seasonal/weekly)
    base_fluctuation = 10 * np.sin(t * 2 * np.pi / 100)
    grid_draw = np.clip(90 + morning_peak + evening_peak + base_fluctuation, 0, None)
    
    df = pd.DataFrame({
        'date': dates,
        'hour': hour_of_day,
        'solar_power': solar_power,
        'wind_power': wind_power,
        'grid_draw': grid_draw
    })
    
    # Retain the missing values (5%) requirement to test data cleaning step in process_data.py
    # but remove any standard random normal continuous noise for smoothness
    np.random.seed(42)  # For reproducible missingness
    for col in ['solar_power', 'wind_power', 'grid_draw']:
        mask = np.random.rand(hours) < 0.05
        df.loc[mask, col] = np.nan
        
    from pathlib import Path
    df.to_csv(Path(__file__).parent / 'raw_energy_data.csv', index=False)
    print(f"Successfully generated smooth raw_energy_data.csv with {hours} recent historical rows")

if __name__ == "__main__":
    generate_data()
