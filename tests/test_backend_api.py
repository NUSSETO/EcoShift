import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime
import sys
import os

# Add backend directory to path so we can import api modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from api.main import app

client = TestClient(app)

def test_metrics_timeseries_schema():
    response = client.get("/api/v1/metrics/timeseries")
    assert response.status_code == 200
    data = response.json()
    
    # It might return an error if the model is not trained
    if "error" in data:
        pytest.skip(f"Model not trained yet: {data['error']}. Please run train_model.py first.")
        
    # 1. Metadata Checks
    assert "metadata" in data
    metadata = data["metadata"]
    assert "device_or_site_id" in metadata
    assert "timezone" in metadata
    assert "range_start" in metadata
    assert "range_end" in metadata
    assert "units" in metadata
    assert metadata["units"].get("energy_draw") == "kWh"
    assert metadata["units"].get("carbon_emissions") == "kgCO2"
    
    # 2. Timeseries Checks
    assert "timeseries" in data
    timeseries = data["timeseries"]
    assert len(timeseries) > 0
    
    current_time = datetime.utcnow()
    
    for entry in timeseries:
        assert "timestamp" in entry
        timestamp_str = entry["timestamp"]
        # Ensure timestamp has Z
        assert timestamp_str.endswith("Z")
        
        # Parse timestamp to compare with current time
        # Handle format: '2026-03-10T12:00:00Z'
        try:
            entry_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            entry_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).replace(tzinfo=None)
            
        is_future = entry_time > current_time
        
        assert "energy_draw" in entry
        assert "carbon_emissions" in entry
        
        energy = entry["energy_draw"]
        carbon = entry["carbon_emissions"]
        
        # Check 'predicted' contains valid floats or None (for historical data)
        if energy.get("predicted") is not None:
            assert isinstance(energy.get("predicted"), float) or isinstance(energy.get("predicted"), int)
        if carbon.get("predicted") is not None:
            assert isinstance(carbon.get("predicted"), float) or isinstance(carbon.get("predicted"), int)
        
        # If timestamp is in the future, 'actual' must accurately map to null
        if is_future:
            assert energy.get("actual") is None, f"Expected energy actual to be None for future timestamp {timestamp_str}, got {energy.get('actual')}"
            assert carbon.get("actual") is None, f"Expected carbon actual to be None for future timestamp {timestamp_str}, got {carbon.get('actual')}"
        else:
            # If past/present, actual can be a float or int or None (if data is missing)
            if energy.get("actual") is not None:
                assert isinstance(energy.get("actual"), float) or isinstance(energy.get("actual"), int)
            if carbon.get("actual") is not None:
                assert isinstance(carbon.get("actual"), float) or isinstance(carbon.get("actual"), int)

    # 3. Active Alerts Checks
    assert "active_alerts" in data
    alerts = data["active_alerts"]
    for alert in alerts:
        assert "alert_id" in alert
        assert "timestamp" in alert
        assert "type" in alert
        assert "severity" in alert
        assert alert["severity"] in ["WARNING", "CRITICAL", "INFO"]
        assert "threshold_value" in alert
        assert "triggered_value" in alert
        assert "message" in alert


