import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor
import joblib

def main():
    base_dir = Path(__file__).parent
    data_file = base_dir.parent / "data" / "historical_data.parquet"

    print(f"Loading data from {data_file}...")
    df = pd.read_parquet(data_file)

    df = df.reset_index()
    time_col = 'timestamp' if 'timestamp' in df.columns else df.columns[0]
    df['datetime'] = pd.to_datetime(df[time_col])
    df = df.sort_values('datetime').reset_index(drop=True)

    df['energy_draw']     = df['energy_draw_kwh']
    df['carbon_emissions'] = df['carbon_emissions_kg']

    # ── Time features ──────────────────────────────────────────────────────
    df['hour']       = df['datetime'].dt.hour
    df['dayofweek']  = df['datetime'].dt.dayofweek
    df['month']      = df['datetime'].dt.month

    # ── Lag features (shifted so we only use past values) ──────────────────
    # 24h lag — same hour yesterday (primary predictor)
    df['lag_24_energy'] = df['energy_draw'].shift(24)
    df['lag_24_carbon'] = df['carbon_emissions'].shift(24)
    # 48h lag — same hour 2 days ago (captures weekly/multi-day patterns)
    df['lag_48_energy'] = df['energy_draw'].shift(48)
    df['lag_48_carbon'] = df['carbon_emissions'].shift(48)
    # 1h lag — immediate prior value (captures short-term momentum)
    df['lag_1_energy']  = df['energy_draw'].shift(1)
    df['lag_1_carbon']  = df['carbon_emissions'].shift(1)
    # 6h lag — intraday context
    df['lag_6_energy']  = df['energy_draw'].shift(6)
    df['lag_6_carbon']  = df['carbon_emissions'].shift(6)

    # ── Rolling mean features (built on lagged values to avoid leakage) ────
    df['rolling_24_energy'] = df['lag_24_energy'].rolling(window=24).mean()
    df['rolling_24_carbon'] = df['lag_24_carbon'].rolling(window=24).mean()
    df['rolling_6_energy']  = df['lag_1_energy'].rolling(window=6).mean()
    df['rolling_6_carbon']  = df['lag_1_carbon'].rolling(window=6).mean()
    df['rolling_12_energy'] = df['lag_1_energy'].rolling(window=12).mean()
    df['rolling_12_carbon'] = df['lag_1_carbon'].rolling(window=12).mean()

    df_clean = df.dropna().copy()

    features = [
        'hour', 'dayofweek', 'month',
        'lag_1_energy',  'lag_1_carbon',
        'lag_6_energy',  'lag_6_carbon',
        'lag_24_energy', 'lag_24_carbon',
        'lag_48_energy', 'lag_48_carbon',
        'rolling_6_energy',  'rolling_6_carbon',
        'rolling_12_energy', 'rolling_12_carbon',
        'rolling_24_energy', 'rolling_24_carbon',
    ]
    targets = ['energy_draw', 'carbon_emissions']

    X = df_clean[features]
    y = df_clean[targets]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, shuffle=False)

    print("Training XGBoost MultiOutput model with enriched features...")
    model = MultiOutputRegressor(
        XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            random_state=42,
            n_jobs=-1,
        )
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mae_energy  = mean_absolute_error(y_test['energy_draw'],     y_pred[:, 0])
    rmse_energy = np.sqrt(mean_squared_error(y_test['energy_draw'],  y_pred[:, 0]))
    mae_carbon  = mean_absolute_error(y_test['carbon_emissions'], y_pred[:, 1])
    rmse_carbon = np.sqrt(mean_squared_error(y_test['carbon_emissions'], y_pred[:, 1]))

    print("\nModel Training Complete.")
    print(f"Energy Draw      — MAE: {mae_energy:.2f} kWh,   RMSE: {rmse_energy:.2f} kWh")
    print(f"Carbon Emissions — MAE: {mae_carbon:.2f} kgCO2, RMSE: {rmse_carbon:.2f} kgCO2")

    model_file = base_dir / 'forecaster.pkl'
    joblib.dump(model, model_file)
    print(f"\nSaved model artifact to {model_file.name}")

if __name__ == "__main__":
    main()
