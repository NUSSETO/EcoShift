import asyncio
import time
import httpx

async def fetch(url: str, client: httpx.AsyncClient):
    start = time.perf_counter()
    response = await client.get(url)
    elapsed = time.perf_counter() - start
    return response.status_code, elapsed

async def test_non_blocking():
    async with httpx.AsyncClient() as client:
        # Start a request to the expensive endpoint (/api/v1/metrics/timeseries)
        # This will trigger ML inference if the cache is empty or expired
        start_time = time.perf_counter()
        
        task_inference = asyncio.create_task(
            fetch("http://127.0.0.1:8000/api/v1/metrics/timeseries", client)
        )
        
        # Give it a tiny moment to start processing
        await asyncio.sleep(0.01)
        
        # Now rapidly fire 5 requests to the lightweight /api/summary endpoint
        # If the inference is blocking the event loop (e.g. CPU-bound and synchronous), 
        # these requests will queue up behind it and take a long time to return.
        lightweight_tasks = [
            fetch("http://127.0.0.1:8000/api/summary", client) for _ in range(5)
        ]
        
        light_results = await asyncio.gather(*lightweight_tasks)
        inf_status, inf_time = await task_inference
        
    print(f"ML Inference Request (/api/v1/metrics/timeseries): {inf_status} - {inf_time:.4f}s")
    
    blocked = False
    for i, (status, t) in enumerate(light_results):
        print(f"Lightweight Request {i+1} (/api/summary): {status} - {t:.4f}s")
        # If a lightweight request takes more than 50ms, it's likely being blocked by the event loop
        if t > 0.1:
            blocked = True
            
    if blocked:
        print("WARNING: ML inference appears to be BLOCKING the event loop! Requests to /api/summary took too long.")
    else:
        print("SUCCESS: ML inference is NOT blocking the event loop.")

if __name__ == "__main__":
    asyncio.run(test_non_blocking())
