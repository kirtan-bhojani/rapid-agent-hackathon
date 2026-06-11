import asyncio
import httpx
import json

async def main():
    print("--- Testing POST /career-status-update ---")
    payload = {
        "user_id": "test_user_123",
        "update": "I completed Assess Current General CS Knowledge."
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Sending request...")
        res = await client.post("http://127.0.0.1:8005/career-plan/career-status-update", json=payload)
        
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()["data"]
            print(f"Completed Step: {data.get('completed_step')}")
            print(f"Next Action: {data.get('next_step')}")
            print("\nTrace Logs:")
            for log in data.get("trace_logs", []):
                print(f"[{log['type'].upper()}] {log['message']}")
        else:
            print("Error Details:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
