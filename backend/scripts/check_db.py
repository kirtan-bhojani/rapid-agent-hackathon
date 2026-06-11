import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get("MONGO_URI") or os.environ.get("MDB_MCP_CONNECTION_STRING")
client = MongoClient(uri)
db = client.get_database("rapid")
docs = list(db.career_plans.find())
print(f"Found {len(docs)} documents.")
for d in docs:
    print(d.get("user_id"))
