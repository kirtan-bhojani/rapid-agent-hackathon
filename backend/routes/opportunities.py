"""
opportunities.py — Opportunities Route

GET  /opportunities/{user_id}  — Fetch personalized opportunities based on goal + profile
POST /opportunities/feedback    — Store user feedback on an opportunity

Uses opportunity_service.py (Google Search + LLM classification). Caching
lives in opportunity_service.get_opportunities() itself, shared with the
concurrent cache-warming branch triggered from POST /goal-analysis/.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
import datetime
import uuid
from typing import Any, Optional

from services.profile_service import get_unified_profile
from services.opportunity_service import get_opportunities
from utils.mcp_helpers import find_latest
from dependencies import get_mcp_client, get_llm_client

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


async def resolve_goal_for_opportunities(user_id: str, mcp_client: Any) -> Optional[dict]:
    """Resolve the goal dict opportunity_service expects, preferring the latest
    goal_analysis and falling back to the latest career_plan's goal."""
    goal_doc = await find_latest(mcp_client, "rapid", "goal_analyses", {"user_id": user_id})
    if goal_doc:
        goal = goal_doc.get("analysis", {})
    else:
        goal = None

    if not goal:
        plan_doc = await find_latest(mcp_client, "rapid", "career_plans", {"user_id": user_id})
        if plan_doc:
            plan_goal = plan_doc.get("goal", {})
            goal = {
                "goal_type": plan_goal.get("goal_type", "Higher Studies"),
                "field": plan_goal.get("field", ""),
                "degree": plan_goal.get("degree", ""),
                "country": plan_goal.get("destination", ""),
                "target_role": plan_goal.get("target_role", ""),
                "timeline": plan_goal.get("timeline", ""),
                "raw_query": plan_goal.get("raw_query", ""),
                "needs_scholarship": False,
            }

    if goal and not goal.get("country") and goal.get("destination"):
        goal["country"] = goal["destination"]

    return goal


@router.get("/{user_id}")
async def get_user_opportunities(
    user_id: str,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
):
    """
    Fetch personalised opportunities for a user.

    Pipeline:
    1. Load unified profile
    2. Resolve the user's goal (goal_analyses, falling back to career_plans)
    3. Run opportunity_service.get_opportunities(...) (cache-aware)
    4. Return eligible + growth categories with fit reasons
    """

    profile = get_unified_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please upload a resume first.",
        )

    goal = await resolve_goal_for_opportunities(user_id, mcp_client)
    if not goal:
        raise HTTPException(
            status_code=404,
            detail="No goal found. Please set your goal first via the Goal Analysis page.",
        )

    return await get_opportunities(user_id, goal, profile, mcp_client, llm_client)


class FeedbackRequest(BaseModel):
    user_id: str
    opportunity_id: str
    action: str


@router.post("/feedback")
async def store_feedback(req: FeedbackRequest, mcp_client: Any = Depends(get_mcp_client)):
    """Store user feedback (saved / dismissed) on an opportunity."""

    feedback_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": req.user_id,
        "opportunity_id": req.opportunity_id,
        "action": req.action,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    await mcp_client.session.call_tool("insert-many", arguments={
        "database": "rapid",
        "collection": "opportunity_feedback",
        "documents": [feedback_doc],
    })

    return {"status": "success"}
