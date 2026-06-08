import os
from dotenv import load_dotenv, find_dotenv
from pymongo import MongoClient

# This actively hunts for the .env file
dotenv_path = find_dotenv()
print(f"DEBUG: Found .env file at: {dotenv_path}")

load_dotenv(dotenv_path)

mongo_uri = os.getenv("MONGO_URI")

# If it's still None, we stop before PyMongo crashes
if not mongo_uri:
    raise ValueError("MONGO_URI is completely empty. Stop and check your .env file!")

client = MongoClient(mongo_uri)

# ── Databases ─────────────────────────────────────────────────────────────────

public_db = client["public_data"]
vault_db  = client["secure_vault"]

# ── Collections ───────────────────────────────────────────────────────────────

public_profiles   = public_db["profiles"]           # one record per uploaded doc
encrypted_records = vault_db["pii_records"]          # sensitive PII
unified_profiles  = public_db["unified_profiles"]  # ← NEW: one record per user
users = public_db["users"]

# =====================================================================
#  EXISTING FUNCTIONS — unchanged
# =====================================================================

def save_user_profile(user_id, public_data, sensitive_data):
    public_data["user_id"] = user_id
    public_profiles.insert_one(public_data)

    sensitive_data["user_id"] = user_id
    encrypted_records.insert_one(sensitive_data)


def get_user_profile(user_id):
    return public_profiles.find_one({"user_id": user_id}, {"_id": 0})


# =====================================================================
#  NEW FUNCTIONS — required by profile_service.py
# =====================================================================

def get_all_user_documents(user_id: str) -> list[dict]:
    """
    Return every record in public_data.profiles for *user_id*.

    Uses find() — not find_one() — because each upload creates a
    separate document in this collection (one per document type).
    MongoDB's _id field is excluded so records are JSON-serialisable.
    """
    cursor = public_profiles.find({"user_id": user_id}, {"_id": 0})
    return list(cursor)


def upsert_unified_profile(user_id: str, profile: dict) -> None:
    """
    Insert or replace the unified profile for *user_id* in
    public_data.unified_profiles.

    Uses replace_one with upsert=True so:
      - First call  → inserts a new document.
      - Every subsequent call → replaces it in-place.
    This guarantees exactly one unified profile per user at all times.
    """
    unified_profiles.replace_one(
        {"user_id": user_id},   # filter
        profile,                # replacement document
        upsert=True,            # create if not found
    )


def fetch_unified_profile(user_id: str) -> dict | None:
    """
    Return the unified profile for *user_id* from unified_profiles,
    or None if build_unified_profile() has never been called for this user.

    _id is excluded so the result is directly JSON-serialisable.
    """
    return unified_profiles.find_one({"user_id": user_id}, {"_id": 0})