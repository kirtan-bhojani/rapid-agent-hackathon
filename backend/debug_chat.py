import asyncio
import httpx
import json

async def main():
    print("--- Debugging POST /career-plan ---")
    payload = {
        "user_id": "test_user_123",
        "goal": "I want to be an ML Engineer"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Sending request...")
        try:
            res = await client.post("http://127.0.0.1:8000/career-plan/", json=payload)
            print(f"Status Code: {res.status_code}")
            data = res.json()
            if res.status_code == 200:
                print("Trace Logs returned:")
                logs = data.get("trace_logs", [])
                for i, log in enumerate(logs):
                    print(f"[{i}] {log}")
            else:
                print("Error Details:", res.text)
        except Exception as e:
            print("Request failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
