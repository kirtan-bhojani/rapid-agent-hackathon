import os, sys
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv('MONGO_URI'))
db = client['rapid']
db.opportunities_cache.delete_many({})
print('Opportunities cache cleared')
