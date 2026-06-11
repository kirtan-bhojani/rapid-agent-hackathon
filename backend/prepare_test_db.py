import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get("MONGO_URI") or os.environ.get("MDB_MCP_CONNECTION_STRING")
client = MongoClient(uri)
db = client.get_database("rapid")

user_id = "test_opp_user"

# 1. Insert Dummy Profile
db.unified_profiles.delete_many({"user_id": user_id})
db.unified_profiles.insert_one({
    "_id": "dummy_prof_1",
    "user_id": user_id,
    "skills": ["Python", "Machine Learning", "Data Analysis"],
    "experience": ["Internship at Tech Corp"],
    "education": "B.S. Computer Science"
})

# 2. Insert Dummy Career Plan
db.career_plans.delete_many({"user_id": user_id})
db.career_plans.insert_one({
    "_id": "dummy_plan_1",
    "user_id": user_id,
    "goal": {"target_role": "Machine Learning Engineer", "timeline": "6 months"},
    "gaps": {"missing_skills": ["TensorFlow", "MLOps", "Cloud Deployment"]}
})

print("Database seeded for test_opp_user using PyMongo.")
