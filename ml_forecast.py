import pandas as pd
import json
from pathlib import Path

def generate_forecast(df_final: pd.DataFrame, base_dir: Path):
    """
    Generates a 24-hour predictive forecast based on historical data averages
    for each hour of the day.
    
    Args:
        df_final (pd.DataFrame): The historical data.
        base_dir (Path): The directory to save the forecast JSON file.
    """
    print("Generating 24-hour forecast...")
    df = df_final.copy()
    df['datetime'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['datetime'].dt.hour
    
    # Simple heuristic ML: average power generation/draw per hour across historical data
    hourly_avg = df.groupby('hour')[['solar_kwh', 'wind_kwh', 'grid_kwh']].mean().reset_index()
    
    # Generate next 24 hours of timestamps
    last_time = df['datetime'].max()
    future_times = [last_time + pd.Timedelta(hours=i) for i in range(1, 25)]
    
    forecast_records = []
    for t in future_times:
        h = t.hour
        # Get the averages for this hour
        avg = hourly_avg[hourly_avg['hour'] == h].iloc[0]
        solar = avg['solar_kwh']
        wind = avg['wind_kwh']
        grid = avg['grid_kwh']
        emissions = grid * 0.45
        
        forecast_records.append({
            'timestamp': t.strftime('%Y-%m-%dT%H:%M:%S'),
            'solar_kwh': round(solar, 2),
            'wind_kwh': round(wind, 2),
            'grid_kwh': round(grid, 2),
            'carbon_emissions_kg': round(emissions, 2)
        })
        
    forecast_file = base_dir / 'forecast_data.json'
    with open(forecast_file, 'w') as f:
        json.dump(forecast_records, f, indent=4)
        
    print(f"Successfully exported forecast data to {forecast_file.name}")
