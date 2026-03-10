# EcoShift

[![Live Demo](https://img.shields.io/badge/Live_Demo-ecoshift--frontend.netlify.app-blue)](https://ecoshift-frontend.netlify.app)
![EcoShift Dashboard](https://img.shields.io/badge/Status-Production%20Ready-success)

EcoShift is an AI-powered energy dashboard designed to track, analyze, and forecast renewable (Solar, Wind) and non-renewable (Grid) energy consumption, alongside carbon emissions. The platform provides insights and predictions using historical data and simple heuristic ML models to promote sustainable energy usage.

> **Disclaimer**: All data presented in this application (historical, current, and forecasted) is synthetically generated for demonstration purposes and does not represent a real-world situation or actual energy grid.

## Technology Stack

### Backend
- **Python**: Core logic and data processing.
- **FastAPI**: High-performance API routing and serving.
- **Uvicorn**: ASGI server for running the FastAPI application.
- **Pandas & NumPy**: Data manipulation, cleaning, and heuristic ML forecasting.

### Frontend
- **HTML5 & Vanilla JavaScript**: Core structure and dynamic UI logic.
- **CSS3 (Vanilla)**: Custom styling featuring glassmorphism and modern dynamic gradients.
- **Chart.js**: Interactive data visualization (Line and Bar charts).

## Installation

1. **Clone the repository** or navigate to the project directory:
   ```bash
   cd EcoShift
   ```

2. **Set up Python environment** (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   Ensure you install all required packages listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Automated Launch (Recommended)
You can launch the entire application seamlessly using the provided automation script:
```bash
python3 start.py
```
This script will automatically generate the data, start the backend API server, and instantly open the dashboard in your default browser.

### Manual Launch
If you prefer to run the components individually:

1. **Generate Raw Data**: Creates `raw_energy_data.csv` with simulated historical energy usage.
   ```bash
   python3 generate_raw_data.py
   ```

2. **Process Data and Forecast**: Cleans the data, calculates emissions, and generates the predictive forecast using ML (`ml_forecast.py`), outputting `processed_data.json` and `forecast_data.json`.
   ```bash
   python3 process_data.py
   ```

3. **Start the API Server**: Launch the FastAPI server.
   ```bash
   uvicorn main:app --reload
   ```

4. **Launch the Dashboard**: 
   Open `index.html` in your preferred modern web browser. 
   *(Note: The frontend will attempt to fetch from `http://localhost:8000/api/...`. If the server is offline, it will gracefully fall back to local mock data).*

## Features
- **Historical Timeseries Data**: View past energy generation across Solar, Wind, and Grid.
- **Carbon Emission Tracking**: Dynamically measure carbon footprint based on user-adjustable grid carbon intensity factors.
- **24-Hour Predictive Forecast**: Anticipate tomorrow’s energy mix to maximize clear-energy usage, powered by a dedicated Predictive Forecasting ML module.
- **Auto-Refresh Background Task**: Executes an automated hourly regeneration of synthetic data and forecasts, ensuring the live application is continually updated without manual restarts.
- **CSV Export**: Built-in utility directly on the dashboard that allows users to instantly download timeseries and emissions data as a CSV file for external use.
- **Interactive UI**: Fluid animations and highly-responsive styling.
