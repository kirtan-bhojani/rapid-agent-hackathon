import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.parser_service import process_document

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_DOCUMENT_TYPES = ["resume", "transcript", "passport", "ielts", "sop", "lor"]

# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/extract", tags=["Extract"])

# ── Request schema ────────────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    file_path: str
    document_type: str
    user_id: str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_request(req: ExtractRequest) -> None:
    """Run all validations before touching the filesystem or calling Gemini."""

    # 1. user_id must be a non-empty string
    if not req.user_id or not req.user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="'user_id' must not be empty.",
        )

    # 2. document_type must be supported
    if req.document_type not in SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported document type: '{req.document_type}'. "
                f"Supported types: {SUPPORTED_DOCUMENT_TYPES}."
            ),
        )

    # 3. file must exist on disk
    if not os.path.isfile(req.file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found at path: '{req.file_path}'.",
        )

# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/")
def extract_document(req: ExtractRequest):
    """
    Extract structured data from an already-uploaded document.

    - **file_path**: path returned by POST /upload/ (e.g. uploads/resume/1749123456_resume.pdf)
    - **document_type**: currently only "resume" is supported
    - **user_id**: identifier used to store the profile in MongoDB
    """

    # 1. Validate all inputs
    _validate_request(req)

    # 2. Dispatch to the correct processor
    try:
        profile = process_document(req.document_type, req.file_path, req.user_id)


    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {exc}",
        ) from exc

    # 3. Surface a parsing-level error returned by process_resume itself
    #    (parser_service returns {"error": ..., "raw": ...} on bad Gemini output)
    if isinstance(profile, dict) and "error" in profile:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Gemini returned unparseable output.",
                "error": profile.get("error"),
                "raw": profile.get("raw"),
            },
        )

    # 4. Return structured response
    return {
        "status": "success",
        "document_type": req.document_type,
        "profile": profile,
    }