import asyncio
import httpx
import json

async def main():
    print("--- Testing Monolithic POST /career-plan ---")
    payload = {
        "user_id": "test_user_123",
        "query": "I want to become an ML Engineer in 6 months",
        "profile": {
            "skills": ["Python", "Basic SQL", "Git"],
            "experience": ["1 year as a Backend Developer"],
            "education": ["B.Sc. in Computer Science"]
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Sending request...")
        res = await client.post("http://127.0.0.1:8004/career-plan/", json=payload)
        
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Response JSON:")
            print(json.dumps(res.json(), indent=2))
        else:
            print("Error Details:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
