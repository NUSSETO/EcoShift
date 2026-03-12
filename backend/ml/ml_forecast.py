"""
ML inference module — loads a trained XGBoost model and generates 24-hour
energy + carbon forecasts from the most recent historical data.

Key technique: level-correction bias anchoring.
    After raw model prediction, the bias between the actual h=0 value and the
    predicted h=0 value is computed. A linearly decaying correction is applied
    (100% at h=0, 0% at h=24) to anchor the forecast to current reality
    without retraining. This dramatically reduces the visual gap at the
    actual-to-predicted transition.
"""

import pandas as pd
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

        def lookup(target_dt):
            """Return the row closest in time to target_dt (within 30 min), else last row."""
            row = df[df['datetime'] == target_dt]
            if not row.empty:
                return row.iloc[0]
            # nearest within 30 min
            diff = (df['datetime'] - target_dt).abs()
            if diff.min() <= pd.Timedelta(minutes=30):
                return df.loc[diff.idxmin()]
            return df.iloc[-1]  # final fallback

        def rolling_mean(end_dt, window_hours):
            start_dt = end_dt - pd.Timedelta(hours=window_hours - 1)
            mask = (df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)
            subset = df[mask]
            if subset.empty:
                # fallback: tail of available data
                subset = df.tail(window_hours)
            return float(subset['energy_draw'].mean()), float(subset['carbon_emissions'].mean())

        feature_rows = []
        for h in range(0, 25):
            target_t = last_time + pd.Timedelta(hours=h)

            r1   = lookup(target_t - pd.Timedelta(hours=1))
            r6   = lookup(target_t - pd.Timedelta(hours=6))
            r24  = lookup(target_t - pd.Timedelta(hours=24))
            r48  = lookup(target_t - pd.Timedelta(hours=48))

            roll6_e,  roll6_c  = rolling_mean(target_t - pd.Timedelta(hours=1),  6)
            roll12_e, roll12_c = rolling_mean(target_t - pd.Timedelta(hours=1),  12)
            roll24_e, roll24_c = rolling_mean(target_t - pd.Timedelta(hours=24), 24)

            feature_rows.append({
                'hour':             target_t.hour,
                'dayofweek':        target_t.dayofweek,
                'month':            target_t.month,
                'lag_1_energy':     float(r1['energy_draw']),
                'lag_1_carbon':     float(r1['carbon_emissions']),
                'lag_6_energy':     float(r6['energy_draw']),
                'lag_6_carbon':     float(r6['carbon_emissions']),
                'lag_24_energy':    float(r24['energy_draw']),
                'lag_24_carbon':    float(r24['carbon_emissions']),
                'lag_48_energy':    float(r48['energy_draw']),
                'lag_48_carbon':    float(r48['carbon_emissions']),
                'rolling_6_energy':  roll6_e,
                'rolling_6_carbon':  roll6_c,
                'rolling_12_energy': roll12_e,
                'rolling_12_carbon': roll12_c,
                'rolling_24_energy': roll24_e,
                'rolling_24_carbon': roll24_c,
            })

        X_pred = pd.DataFrame(feature_rows)
        preds = self.model.predict(X_pred)

        # ── Level-correction bias anchoring ──────────────────────────────────
        # The raw model prediction at h=0 often diverges from the latest actual
        # value (e.g. seasonal shifts the model hasn't fully learned). We compute
        # the bias = actual_h0 - predicted_h0 and apply a linearly decaying
        # correction: full bias at h=0, zero correction by h=24.
        # This anchors the forecast to current reality without retraining.
        actual_h0_energy = float(df.iloc[-1]['energy_draw'])
        actual_h0_carbon = float(df.iloc[-1]['carbon_emissions'])
        energy_bias = actual_h0_energy - float(preds[0, 0])
        carbon_bias = actual_h0_carbon - float(preds[0, 1])

        HORIZON = 24
        for i in range(len(preds)):
            decay = max(0.0, (HORIZON - i) / HORIZON)
            preds[i, 0] = max(0.0, preds[i, 0] + energy_bias * decay)
            preds[i, 1] = max(0.0, preds[i, 1] + carbon_bias * decay)

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
