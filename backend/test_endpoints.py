import asyncio
import httpx
import time

async def test_endpoint(client, url):
    t0 = time.time()
    try:
        res = await client.get(url, timeout=10.0)
        t_req = time.time() - t0
        return {"success": res.status_code == 200, "latency": t_req, "status": res.status_code, "body": res.text[:200]}
    except Exception as e:
        return {"success": False, "latency": time.time() - t0, "error": str(e)}

async def main():
    endpoints = [
        "http://127.0.0.1:8001/mcp/health",
        "http://127.0.0.1:8001/mcp/tools",
        "http://127.0.0.1:8001/mcp/test-databases"
    ]
    
    print("--- 10-Cycle Endpoint Stress Test ---")
    async with httpx.AsyncClient() as client:
        for ep in endpoints:
            successes = 0
            failures = 0
            latencies = []
            
            print(f"\nTesting {ep}...")
            for i in range(10):
                res = await test_endpoint(client, ep)
                if res["success"]:
                    successes += 1
                else:
                    failures += 1
                    print(f"  Failure {i+1}: {res}")
                latencies.append(res["latency"])
            
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            print(f"Results for {ep}:")
            print(f"  Successes: {successes}/10")
            print(f"  Failures: {failures}/10")
            print(f"  Average Latency: {avg_lat:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
