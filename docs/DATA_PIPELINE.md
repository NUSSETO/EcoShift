# EcoShift Data Pipeline

## Overview
This document explains the data ingestion pipeline for EcoShift, transitioning from synthetic data to real-world energy datasets. The pipeline fetches historical demand from the UK National Energy System Operator (NESO) and grid carbon intensity from the official UK Carbon Intensity API.

## Data Sources
1.  **National Grid ESO (NESO)**:
    *   **Dataset**: Historic Demand Data
    *   **Metric**: National Demand (`ND`) in MW
    *   **Interval**: 30 minutes
    *   **Normalization**: Since this is national-level data (often around 20,000 to 40,000 MW), we scale it down by a factor of `0.00001` to simulate a single industrial site (`site_001`). `30,000 MW * 0.00001 = 0.3 MW = 300 kW`.

2.  **UK Carbon Intensity API**:
    *   **Metric**: Grid Carbon Intensity in `gCO2/kWh`
    *   **Interval**: 30 minutes
    *   **Matching**: The carbon data is fetched specifically for the exact timeframe that the NESO dataset covers, ensuring alignment even when NESO data is delayed by several weeks.

## ETL Process (`data_ingest.py`)
1.  **Extract**: Connect to both APIs and download the last 7 days of available NESO data, alongside corresponding Carbon Intensity Data.
2.  **Transform**:
    *   Parsed the timestamps to ensure timezone-awareness (UTC).
    *   Merge the datasets on their timestamp index through an inner join.
    *   Resample down to 1-hour intervals (mean averaging).
    *   Calculate `energy_draw_kwh` by scaling the demand.
    *   Calculate `carbon_emissions_kg` using `(energy_draw_kwh * intensity) / 1000`.
3.  **Load**:
    *   Save the fully cleaned hourly timeseries to `data/historical_data.parquet` for Machine Learning usage.
    *   Format the ultimate 24 hours into the mandated **Unified JSON Schema** and save it to `data/latest_data.json`.

## Automation
The pipeline is fully automated using a cron job.
*   **Script**: `cron_pipeline.sh`
*   **Setup**:
    To run this script automatically every day at 1 AM, add the following line to your crontab (`crontab -e`):
    ```bash
    0 1 * * * /Users/seto-macair/Desktop/MyWork/Code/Super_Agent_Test/cron_pipeline.sh >> /tmp/ecoshift_cron.log 2>&1
    ```
