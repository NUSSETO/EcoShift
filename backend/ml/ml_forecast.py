import pandas as pd
import json
from pathlib import Path
import joblib

class EnergyForecaster:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path)
        
    def generate_forecast(self, df_historical: pd.DataFrame) -> dict:
        """
        Takes historical DataFrame and returns a 24-hour forecast conforming to the desired JSON schema.
        df_historical must contain at least the last 48 hours of data.
        """
        if df_historical.empty:
            return {"error": "No historical data available to generate forecast."}
            
        df = df_historical.copy()
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Calculate base features
        if 'energy_draw' not in df.columns:
            if 'energy_draw_kwh' in df.columns:
                df['energy_draw'] = df['energy_draw_kwh']
            else:
                df['energy_draw'] = df.get('solar_kwh', 0) + df.get('wind_kwh', 0) + df.get('grid_kwh', 0)
        if 'carbon_emissions' not in df.columns:
            if 'carbon_emissions_kg' in df.columns:
                df['carbon_emissions'] = df['carbon_emissions_kg']
            else:
                df['carbon_emissions'] = df.get('grid_kwh', 0) * 0.45
                
        last_time = df['datetime'].max()
        
        feature_rows = []
        # Predict for the current hour (0) and the next 24 hours (1 to 24)
        for h in range(0, 25):
            target_t = last_time + pd.Timedelta(hours=h)
            lag_time = target_t - pd.Timedelta(hours=24)
            
            lag_row = df[df['datetime'] == lag_time]
            if lag_row.empty:
                lag_row = df.iloc[-1:] # Fallback
                
            lag_24_energy = lag_row['energy_draw'].values[0]
            lag_24_carbon = lag_row['carbon_emissions'].values[0]
            
            # rolling 24 ending at lag_time
            rolling_start = lag_time - pd.Timedelta(hours=23)
            mask = (df['datetime'] >= rolling_start) & (df['datetime'] <= lag_time)
            rolling_df = df[mask]
            
            roll_24_energy = rolling_df['energy_draw'].mean()
            roll_24_carbon = rolling_df['carbon_emissions'].mean()
            
            feature_rows.append({
                'hour': target_t.hour,
                'dayofweek': target_t.dayofweek,
                'lag_24_energy': lag_24_energy,
                'lag_24_carbon': lag_24_carbon,
                'rolling_24_energy': roll_24_energy,
                'rolling_24_carbon': roll_24_carbon
            })
            
        X_pred = pd.DataFrame(feature_rows)
        preds = self.model.predict(X_pred)
        
        # Build JSON Schema Output
        device_id = "site_001"
        timezone = "UTC"
        range_start = last_time.strftime("%Y-%m-%dT%H:00:00Z")
        range_end = (last_time + pd.Timedelta(hours=24)).strftime("%Y-%m-%dT%H:00:00Z")
        
        timeseries = []
        for h in range(-24, 25):
            target_t = last_time + pd.Timedelta(hours=h)
            ts_str = target_t.strftime("%Y-%m-%dT%H:00:00Z")
            
            actual_energy = None
            actual_carbon = None
            if h <= 0:
                actual_row = df[df['datetime'] == target_t]
                if not actual_row.empty:
                    actual_energy = round(float(actual_row['energy_draw'].values[0]), 2)
                    actual_carbon = round(float(actual_row['carbon_emissions'].values[0]), 2)
                    
            pred_energy = None
            pred_carbon = None
            if h >= 0:
                i = h
                pred_energy = round(float(preds[i, 0]), 2)
                pred_carbon = round(float(preds[i, 1]), 2)
            
            timeseries.append({
                "timestamp": ts_str,
                "energy_draw": {
                    "actual": actual_energy,
                    "predicted": pred_energy
                },
                "carbon_emissions": {
                    "actual": actual_carbon,
                    "predicted": pred_carbon
                }
            })
            
        # Active Alerts — use same defaults as api/alerting.py
        import os as _os
        _max_grid = float(_os.getenv("PEAK_GRID_DRAW", "300.0"))
        _max_carbon = float(_os.getenv("MAX_CARBON_EMISSIONS", "60.0"))

        active_alerts = []
        for ts_data in timeseries:
            p_energy = ts_data["energy_draw"]["predicted"]
            if p_energy is not None and p_energy > _max_grid:
                ts_clean = ts_data['timestamp'].replace('-','').replace(':','').replace('T','').replace('Z','')
                active_alerts.append({
                    "alert_id": f"alt_{ts_clean}",
                    "timestamp": ts_data['timestamp'],
                    "type": "PEAK_GRID_DRAW",
                    "severity": "CRITICAL",
                    "threshold_value": _max_grid,
                    "triggered_value": p_energy,
                    "message": f"Peak grid draw exceeded the {_max_grid} kWh maximum threshold."
                })
            p_carbon = ts_data["carbon_emissions"]["predicted"]
            if p_carbon is not None and p_carbon > _max_carbon:
                ts_clean = ts_data['timestamp'].replace('-','').replace(':','').replace('T','').replace('Z','')
                active_alerts.append({
                    "alert_id": f"alt_co2_{ts_clean}",
                    "timestamp": ts_data['timestamp'],
                    "type": "HIGH_CARBON_EMISSIONS",
                    "severity": "CRITICAL",
                    "threshold_value": _max_carbon,
                    "triggered_value": p_carbon,
                    "message": f"Carbon emissions exceeded the {_max_carbon} kgCO2 threshold."
                })
                
        schema_output = {
            "metadata": {
                "device_or_site_id": device_id,
                "timezone": timezone,
                "range_start": range_start,
                "range_end": range_end,
                "units": {
                    "energy_draw": "kWh",
                    "carbon_emissions": "kgCO2"
                }
            },
            "timeseries": timeseries,
            "active_alerts": active_alerts
        }
        
        return schema_output
