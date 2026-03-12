#!/usr/bin/env bash

# Exit if any command fails
set -e

echo "Starting EcoShift Integration Pipeline..."

# 1. Start the API Backend
echo "-> Installing Backend dependencies..."
cd backend
# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

echo "-> Starting FastAPI Backend on port 8000..."
uvicorn api.main:app --port 8000 &
BACKEND_PID=$!

# 2. Wait a moment for it to start
sleep 2

# 3. Start the Vite Frontend Dev Server
echo "-> Installing Frontend dependencies..."
cd ../frontend
npm install

echo "-> Starting Vite Frontend on port 3000..."
npm run dev -- --port 3000 &
FRONTEND_PID=$!

echo "Both Backend and Frontend are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both."

# Function to clean up background processes on script exit
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Trap the SIGINT (Ctrl+C) signal to run the cleanup function
trap cleanup SIGINT

# Wait indefinitely until interrupted
wait
