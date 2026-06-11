from fastapi.testclient import TestClient
from main import app
import json
import time

def run_tests():
    with TestClient(app) as client:
        user_id = "test_opp_user"
        
        print("=== Test 1: Missing Profile (Failure Handling) ===")
        res = client.get("/opportunities/unknown_user?category=job")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        print("-" * 50)
        
        print("=== Test 2: Live Grounded Search ===")
        start = time.time()
        res = client.get(f"/opportunities/{user_id}?category=job")
        duration = time.time() - start
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Time Taken: {duration:.2f}s")
        print("First Opportunity Returned:")
        if "data" in data and len(data["data"]) > 0:
            print(json.dumps(data["data"][0], indent=2))
        else:
            print("No data returned!")
        print("Trace Logs:")
        print(json.dumps(data.get("trace_logs", []), indent=2))
        print("-" * 50)
        
        print("=== Test 3: Caching Behavior ===")
        start = time.time()
        res2 = client.get(f"/opportunities/{user_id}?category=job")
        duration2 = time.time() - start
        data2 = res2.json()
        print(f"Time Taken: {duration2:.2f}s")
        print("Trace Logs (Notice it says Found in cache):")
        print(json.dumps(data2.get("trace_logs", []), indent=2))
        print("-" * 50)
        
        print("=== Test 4: Feedback Endpoint ===")
        if "data" in data and len(data["data"]) > 0:
            opp_id = data["data"][0]["_id"]
            res3 = client.post("/opportunities/feedback", json={
                "user_id": user_id,
                "opportunity_id": opp_id,
                "action": "saved"
            })
            print(f"Status: {res3.status_code}")
            print(f"Response: {res3.json()}")

if __name__ == "__main__":
    run_tests()
