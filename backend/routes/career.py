from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.career_pipeline import run_career_pipeline
from services.progress_agent import run_progress_agent
from services.profile_service import get_unified_profile
from utils.mcp_helpers import find_latest
from dependencies import get_mcp_client, get_llm_client
from typing import Any

router = APIRouter(prefix="/career-plan", tags=["career"])

class CareerPlanRequest(BaseModel):
    user_id: str
    goal: str

@router.post("/")
async def create_career_plan(
    req: CareerPlanRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
):

    profile = get_unified_profile(req.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Unified profile not found. Please upload a resume first.")

    plan = await run_career_pipeline(
        user_id=req.user_id,
        query=req.goal,
        profile=profile,
        mcp_client=mcp_client,
        llm_client=llm_client,
    )
    return {"status": "success", "data": plan["data"], "trace_logs": plan["trace_logs"]}

class StatusUpdateRequest(BaseModel):
    user_id: str
    update: str

@router.post("/career-status-update")
async def update_career_status(
    req: StatusUpdateRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
):

    result = await run_progress_agent(
        user_id=req.user_id,
        update_text=req.update,
        mcp_client=mcp_client,
        llm_client=llm_client,
    )
    return {"status": "success", "data": result}

@router.get("/{user_id}")
async def get_career_plan(user_id: str, mcp_client: Any = Depends(get_mcp_client)):

    plan = await find_latest(mcp_client, "rapid", "career_plans", {"user_id": user_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Career plan not found.")

    return {"status": "success", "data": plan}
