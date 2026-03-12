#!/bin/bash
# EcoShift Data Ingestion Cron Wrapper
# This script sets up the environment and runs the data ingestion Python script.

# Navigate to the project directory
PROJECT_DIR="/Users/seto-macair/Desktop/MyWork/Code/EcoShift"
cd "$PROJECT_DIR/backend" || exit

# Run the ingestion script
echo "Starting EcoShift Data Ingestion at $(date)"
python3 data/data_ingest.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Data ingestion completed successfully."
else
    echo "Data ingestion failed with exit code $EXIT_CODE."
fi

# Example crontab entry to run this every day at 1 AM:
# 0 1 * * * /Users/seto-macair/Desktop/MyWork/Code/EcoShift/cron_pipeline.sh >> /tmp/ecoshift_cron.log 2>&1
