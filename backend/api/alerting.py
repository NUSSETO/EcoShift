import os
import uuid
from datetime import datetime, timezone

def evaluate_thresholds(actual_data_point: dict) -> list:
    """
    Evaluates the actual metrics against configured thresholds to generate alerts.
    """
    alerts = []
    
    max_carbon = float(os.getenv("MAX_CARBON_EMISSIONS", "150.0"))
    max_grid_draw = float(os.getenv("PEAK_GRID_DRAW", "250.0"))
    
    timestamp = actual_data_point.get("timestamp")
    
    # If timestamp is a Pandas Timestamp or datetime, convert to ISO string
    if hasattr(timestamp, "isoformat"):
        timestamp = timestamp.isoformat()
    else:
        timestamp = str(timestamp)
        
    # Ensure UTC format for timestamp
    if not timestamp.endswith("Z"):
        try:
            timestamp = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            timestamp = timestamp + "Z"

    # Energy Draw
    actual_grid = actual_data_point.get("energy_draw_kwh", 0) or 0

    if actual_grid > max_grid_draw:
        alerts.append({
            "alert_id": f"alt_{uuid.uuid4().hex[:8]}",
            "timestamp": timestamp,
            "type": "PEAK_GRID_DRAW",
            "severity": "CRITICAL",
            "threshold_value": max_grid_draw,
            "triggered_value": round(actual_grid, 2),
            "message": f"Peak grid draw exceeded the {max_grid_draw} kWh maximum threshold."
        })

    # Carbon Emissions
    actual_carbon = actual_data_point.get("carbon_emissions_kg", 0) or 0
    if actual_carbon > max_carbon:
        alerts.append({
            "alert_id": f"alt_{uuid.uuid4().hex[:8]}",
            "timestamp": timestamp,
            "type": "HIGH_CARBON_EMISSIONS",
            "severity": "CRITICAL",
            "threshold_value": max_carbon,
            "triggered_value": round(actual_carbon, 2),
            "message": f"Carbon emissions exceeded the {max_carbon} kgCO2 threshold."
        })

    return alerts
