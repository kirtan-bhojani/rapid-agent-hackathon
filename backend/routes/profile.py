from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.profile_service import build_unified_profile, get_unified_profile

# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/profile", tags=["Profile"])

# ── Request / Response schemas ────────────────────────────────────────────────

class BuildProfileRequest(BaseModel):
    user_id: str

class BuildProfileResponse(BaseModel):
    status: str
    user_id: str
    profile: dict

class GetProfileResponse(BaseModel):
    status: str
    user_id: str
    profile: dict

# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/build", response_model=BuildProfileResponse)
def build_profile(req: BuildProfileRequest):
    """
    Aggregate all extracted documents for a user into a unified profile.

    - Fetches all records from public_data.profiles for **user_id**
    - Merges them across document types (resume, transcript, passport, etc.)
    - Upserts the result into public_data.unified_profiles
    - Returns the freshly built profile
    """
    if not req.user_id or not req.user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="'user_id' must not be empty.",
        )

    try:
        profile = build_unified_profile(req.user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build profile: {exc}",
        ) from exc

    return {
        "status": "success",
        "user_id": req.user_id,
        "profile": profile,
    }


@router.get("/{user_id}", response_model=GetProfileResponse)
def get_profile(user_id: str):
    """
    Return the pre-built unified profile for **user_id**.

    - Reads directly from public_data.unified_profiles
    - Returns HTTP 404 if the profile has not been built yet
    """
    try:
        profile = get_unified_profile(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch profile: {exc}",
        ) from exc

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"No unified profile found for user_id '{user_id}'. Call POST /profile/build first.",
        )

    return {
        "status": "success",
        "user_id": user_id,
        "profile": profile,
    }