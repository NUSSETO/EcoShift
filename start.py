import subprocess
import time
import webbrowser
import os
import sys
import socket

def wait_for_port(port, host='localhost', timeout=15.0):
    """Wait until a port starts accepting TCP connections."""
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
            if time.time() - start_time >= timeout:
                return False

def main():
    print("Step 1: Updating data...")
    try:
        subprocess.run([sys.executable, "data/data_ingest.py"], cwd="backend", check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while updating data: {e}")
        sys.exit(1)

    print("Step 2: Starting server...")
    # Launch FastAPI backend as a subprocess
    server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"], cwd="backend")

    # Wait for the server to be fully ready
    if not wait_for_port(8000):
        print("Error: Server did not start in time. Exiting.")
        server_process.terminate()
        sys.exit(1)

    print("Step 3: Opening dashboard!")
    # Open index.html automatically using absolute path
    index_path = os.path.abspath("frontend/index.html")
    webbrowser.open(f"file://{index_path}")

    print("\nEcoShift system is running. Press Ctrl+C to stop.")

    try:
        # Keep start.py running so the server stays alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Cleanly terminate the uvicorn subprocess
        print("\nShutting down server gracefully...")
        server_process.terminate()
        server_process.wait()
        print("Done.")

if __name__ == "__main__":
    main()
