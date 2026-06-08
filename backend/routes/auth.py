from fastapi import APIRouter
from pydantic import BaseModel

from services.auth_service import (
    register_user,
    login_user
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


class RegisterRequest(BaseModel):

    email: str
    password: str


class LoginRequest(BaseModel):

    email: str
    password: str


@router.post("/register")
def register(data: RegisterRequest):

    return register_user(
        data.email,
        data.password
    )


@router.post("/login")
def login(data: LoginRequest):

    return login_user(
        data.email,
        data.password
    )