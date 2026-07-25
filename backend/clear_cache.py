import os, sys
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv('MONGO_URI'))
db = client['rapid']
db.goal_analyses.delete_many({})
db.gap_analyses.delete_many({})
print('Caches cleared')
