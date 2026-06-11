import asyncio
import httpx
import json

async def main():
    user_id = "test_user_123"
    print(f"--- Testing Monolithic GET /career-plan/{user_id} ---")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(f"http://127.0.0.1:8005/career-plan/{user_id}")
        
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Successfully retrieved plan:")
            data = res.json()["data"]
            print(f"User ID: {data['user_id']}")
            print(f"Target Role: {data['goal']['target_role']}")
            print(f"Roadmap Steps: {len(data['roadmap'])}")
            print(f"First Step: {data['roadmap'][0]['title']}")
        else:
            print("Error Details:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
