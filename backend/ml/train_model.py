import pandas as pd
import json
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
    
    # Parquet file from data_ingest.py has timestamp as the index. Let's make it a column.
    df = df.reset_index()
    # It might already be named 'timestamp' or 'index'. Let's ensure it's 'datetime'.
    time_col = 'timestamp' if 'timestamp' in df.columns else df.columns[0]
    df['datetime'] = pd.to_datetime(df[time_col])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Target variables
    df['energy_draw'] = df['energy_draw_kwh']
    df['carbon_emissions'] = df['carbon_emissions_kg']
    
    # Feature Engineering
    df['hour'] = df['datetime'].dt.hour
    df['dayofweek'] = df['datetime'].dt.dayofweek
    
    # Lag variables - shifted by 24 hours so we can predict the next 24 hours
    df['lag_24_energy'] = df['energy_draw'].shift(24)
    df['lag_24_carbon'] = df['carbon_emissions'].shift(24)
    
    # Rolling means built on the lagged variables
    df['rolling_24_energy'] = df['lag_24_energy'].rolling(window=24).mean()
    df['rolling_24_carbon'] = df['lag_24_carbon'].rolling(window=24).mean()
    
    # Drop rows with NaNs caused by shift and rolling
    df_clean = df.dropna().copy()
    
    features = [
        'hour', 'dayofweek', 'lag_24_energy', 'lag_24_carbon',
        'rolling_24_energy', 'rolling_24_carbon'
    ]
    targets = ['energy_draw', 'carbon_emissions']
    
    X = df_clean[features]
    y = df_clean[targets]
    
    # Split: Keep last 10% for holdout validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, shuffle=False)
    
    print("Training XGBoost MultiOutput model...")
    model = MultiOutputRegressor(XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42))
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    mae_energy = mean_absolute_error(y_test['energy_draw'], y_pred[:, 0])
    import numpy as np
    rmse_energy = np.sqrt(mean_squared_error(y_test['energy_draw'], y_pred[:, 0]))
    mae_carbon = mean_absolute_error(y_test['carbon_emissions'], y_pred[:, 1])
    rmse_carbon = np.sqrt(mean_squared_error(y_test['carbon_emissions'], y_pred[:, 1]))
    
    print("\nModel Training Complete.")
    print(f"Energy Draw - MAE: {mae_energy:.2f}, RMSE: {rmse_energy:.2f}")
    print(f"Carbon Emissions - MAE: {mae_carbon:.2f}, RMSE: {rmse_carbon:.2f}")
    
    model_file = base_dir / 'forecaster.pkl'
    joblib.dump(model, model_file)
    print(f"\nSaved model artifact to {model_file.name}")

if __name__ == "__main__":
    main()
