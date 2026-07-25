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

    profile = build_unified_profile(req.user_id)

    return {
        "status": "success",
        "user_id": req.user_id,
        "profile": profile,
    }


@router.get("/{user_id}/documents")
def get_user_documents(user_id: str):
    """
    Return the list of all documents uploaded by user_id with key extracted fields.

    This powers the Documents page history section.
    Each entry includes: document_type, and key summary fields (non-sensitive only).
    Sensitive fields (passport_number, DOB, etc.) remain in secure_vault and are NOT returned.
    """
    from database import get_all_user_documents

    docs = get_all_user_documents(user_id)

    if not docs:
        return {"status": "success", "user_id": user_id, "documents": []}

    summaries = []
    for doc in docs:
        doc_type = doc.get("document_type", "unknown")
        summary = {"document_type": doc_type}

        if doc_type == "resume":
            summary["name"] = doc.get("name", "")
            summary["institution"] = doc.get("institution", "")
            summary["degree"] = doc.get("degree", "")
            summary["skills_count"] = len(doc.get("skills", []))

        elif doc_type == "transcript":
            summary["institution"] = doc.get("institution", "")
            summary["gpa"] = doc.get("gpa", "")
            summary["degree"] = doc.get("degree", "")
            summary["major"] = doc.get("major", "")

        elif doc_type == "passport":
            summary["full_name"] = doc.get("full_name", "")
            summary["issuing_country"] = doc.get("issuing_country", "")
            summary["gender"] = doc.get("gender", "")

        elif doc_type == "ielts":
            summary["candidate_name"] = doc.get("candidate_name", "")
            summary["overall_band"] = doc.get("overall_band", "")
            summary["test_type"] = doc.get("test_type", "")
            summary["test_centre"] = doc.get("test_centre", "")
            summary["validity_expiry"] = doc.get("validity_expiry", "")

        elif doc_type == "sop":
            summary["applicant_name"] = doc.get("applicant_name", "")
            summary["target_program"] = doc.get("target_program", "")
            summary["target_university"] = doc.get("target_university", "")
            summary["word_count"] = doc.get("word_count", 0)

        elif doc_type == "lor":
            summary["applicant_name"] = doc.get("applicant_name", "")
            summary["recommender_name"] = doc.get("recommender_name", "")
            summary["recommender_institution"] = doc.get("recommender_institution", "")
            summary["recommendation_strength"] = doc.get("recommendation_strength", "")

        summaries.append(summary)

    return {
        "status": "success",
        "user_id": user_id,
        "documents": summaries,
    }


@router.get("/{user_id}", response_model=GetProfileResponse)
def get_profile(user_id: str):
    """
    Return the pre-built unified profile for **user_id**.

    - Reads directly from public_data.unified_profiles
    - Returns HTTP 404 if the profile has not been built yet
    """
    profile = get_unified_profile(user_id)

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
