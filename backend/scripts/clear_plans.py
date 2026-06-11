import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get("MONGO_URI") or os.environ.get("MDB_MCP_CONNECTION_STRING")
client = MongoClient(uri)
db = client.get_database("rapid")
result = db.career_plans.delete_many({})
print(f"Deleted {result.deleted_count} corrupted career plans from the database.")
