import os
from dotenv import load_dotenv, find_dotenv
from pymongo import MongoClient

# This actively hunts for the .env file
dotenv_path = find_dotenv()
print(f"DEBUG: Found .env file at: {dotenv_path}")

load_dotenv(dotenv_path)

mongo_uri = os.getenv("MONGO_URI")
print(f"DEBUG: Loaded URI: {mongo_uri}")

# If it's still None, we stop before PyMongo crashes
if not mongo_uri:
    raise ValueError("MONGO_URI is completely empty. Stop and check your .env file!")

client = MongoClient(mongo_uri)

# ... rest of your database code ...
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)

public_db = client["public_data"]
vault_db = client["secure_vault"]

public_profiles = public_db["profiles"]
encrypted_records = vault_db["pii_records"]

def save_user_profile(user_id, public_data, sensitive_data):
    public_data["user_id"] = user_id
    public_profiles.insert_one(public_data)
    
    sensitive_data["user_id"] = user_id
    encrypted_records.insert_one(sensitive_data)

def get_user_profile(user_id):
    return public_profiles.find_one({"user_id": user_id}, {"_id": 0})


# test_public = {"name": "Test User", "skills": "Python, MongoDB"}
# test_sensitive = {"email": "test@example.com"}

# save_user_profile("user_123", test_public, test_sensitive)

# result = get_user_profile("user_123")
# print(result)