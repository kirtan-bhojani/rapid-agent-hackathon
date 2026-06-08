import bcrypt
import uuid

from database import users


def register_user(email: str, password: str):

    existing_user = users.find_one(
        {"email": email}
    )

    if existing_user:

        return {
            "status": "error",
            "message": "User already exists"
        }

    user_id = str(uuid.uuid4())

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user = {

        "user_id": user_id,
        "email": email,
        "password_hash": password_hash.decode("utf-8")

    }

    users.insert_one(user)

    return {

        "status": "success",
        "user_id": user_id

    }


def login_user(email: str, password: str):

    user = users.find_one(
        {"email": email}
    )

    if not user:

        return {
            "status": "error",
            "message": "User not found"
        }

    valid = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    )

    if not valid:

        return {
            "status": "error",
            "message": "Invalid password"
        }

    return {

        "status": "success",
        "user_id": user["user_id"]

    }