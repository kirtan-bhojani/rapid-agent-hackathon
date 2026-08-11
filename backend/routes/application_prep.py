"""
application_prep.py — Application Readiness Report Routes

POST /application_prep/analyze     — Run readiness analysis for pasted field labels
GET  /application_prep/{user_id}   — Return the latest stored report for a user
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.application_agent import run_application_readiness, get_cached_application_report
from services.profile_service import get_unified_profile
from dependencies import get_mcp_client, get_llm_client

router = APIRouter(prefix="/application_prep", tags=["application_prep"])


class AnalyzeRequest(BaseModel):
    user_id: str
    raw_text: str


@router.post("/analyze")
async def analyze_application_fields(
    req: AnalyzeRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
):
    """Analyze a pasted list of application form field labels against the
    user's stored profile and report can-autofill / missing / warnings."""

    if not req.raw_text.strip():
        raise HTTPException(status_code=400, detail="'raw_text' must not be empty.")

    profile = get_unified_profile(req.user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please upload at least a resume first.",
        )

    report_doc = await run_application_readiness(
        user_id=req.user_id,
        raw_text=req.raw_text,
        profile=profile,
        mcp_client=mcp_client,
        llm_client=llm_client,
    )

    return {"status": "success", "report": report_doc}


@router.get("/{user_id}")
async def get_latest_report(user_id: str, mcp_client: Any = Depends(get_mcp_client)):
    """Return the latest stored application readiness report for a user."""
    report_doc = await get_cached_application_report(user_id, mcp_client)
    if not report_doc:
        raise HTTPException(
            status_code=404,
            detail="No application readiness report found yet.",
        )
    return {"status": "success", "report": report_doc}
