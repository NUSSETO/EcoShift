import json
from pathlib import Path

def load_processed_data(file_path: Path):
    """Loads historical processed energy data."""
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)

def load_forecast_data(file_path: Path):
    """Loads 24-hour predictive forecast data."""
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)
