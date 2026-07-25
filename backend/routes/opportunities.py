"""
opportunities.py — Opportunities Route

GET  /opportunities/{user_id}  — Fetch personalized opportunities based on goal + profile
POST /opportunities/feedback    — Store user feedback on an opportunity

Uses opportunity_service.py (Google Search + Gemini classification).
The old opportunity_agent.py (Gemini Live Search + fake fallback) is retired.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
import datetime
import uuid
import json
from typing import Any, Optional

from services.profile_service import get_unified_profile
from services.opportunity_service import get_opportunities
from dependencies import get_mcp_client

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


async def _parse_mcp_docs(result) -> list:
    docs = []
    for c in result.content:
        if c.type == "text":
            text = c.text.strip()
            start = next((i for i, ch in enumerate(text) if ch in "[{"), -1)
            end = next((i for i in range(len(text) - 1, -1, -1) if text[i] in "]}"), -1)
            if start != -1 and end != -1 and start < end:
                try:
                    parsed = json.loads(text[start : end + 1])
                    if isinstance(parsed, list):
                        docs.extend(parsed)
                    elif isinstance(parsed, dict):
                        docs.append(parsed)
                except Exception:
                    pass
    return docs


@router.get("/{user_id}")
async def get_user_opportunities(
    user_id: str,
    mcp_client: Any = Depends(get_mcp_client),
):
    """
    Fetch personalised opportunities for a user.

    Pipeline:
    1. Load unified profile
    2. Load latest goal analysis from MongoDB (must exist — user must have set a goal)
    3. Run opportunity_service.get_opportunities(goal, profile)
    4. Return eligible + growth categories with fit reasons
    """

    # 1. Fetch unified profile
    profile = get_unified_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please upload a resume first.",
        )

    # 2. Fetch latest goal analysis
    goal = None
    try:
        result = await mcp_client.session.call_tool("find", arguments={
            "database": "rapid",
            "collection": "goal_analyses",
            "filter": {"user_id": user_id},
        })
        goal_docs = await _parse_mcp_docs(result)
        if goal_docs:
            goal_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            goal = goal_docs[0].get("analysis", {})
    except Exception as e:
        print(f"[Opportunities] Goal analysis fetch error: {e}")

    # Fall back to career_plans if no goal_analysis
    if not goal:
        try:
            plan_result = await mcp_client.session.call_tool("find", arguments={
                "database": "rapid",
                "collection": "career_plans",
                "filter": {"user_id": user_id},
            })
            plan_docs = await _parse_mcp_docs(plan_result)
            if plan_docs:
                plan_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                plan_goal = plan_docs[0].get("goal", {})
                # Map to opportunity_service expected shape
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
        except Exception as e:
            print(f"[Opportunities] Career plan fallback error: {e}")

    if not goal:
        raise HTTPException(
            status_code=404,
            detail="No goal found. Please set your goal first via the Goal Analysis page.",
        )

    # Ensure goal has country field (opportunity_service uses 'country')
    if not goal.get("country") and goal.get("destination"):
        goal["country"] = goal["destination"]

    # --- Check Cache ---
    import hashlib
    goal_str = f"{goal.get('goal_type')}_{goal.get('field')}_{goal.get('degree')}_{goal.get('country')}"
    query_hash = hashlib.md5(goal_str.encode()).hexdigest()

    try:
        cache_result = await mcp_client.session.call_tool("find", arguments={
            "database": "rapid",
            "collection": "opportunities_cache",
            "filter": {"user_id": user_id, "query_hash": query_hash},
        })
        cache_docs = await _parse_mcp_docs(cache_result)
        if cache_docs:
            cache_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            print("[Opportunities] Cache hit!")
            return cache_docs[0]["data"]
    except Exception as e:
        print(f"[Opportunities] Cache read error: {e}")

    # 3. Run opportunity service (if not in cache)
    opportunities_data = get_opportunities(goal, profile)

    response_data = {
        "status": "success",
        "goal_summary": opportunities_data.get("goal_summary", {}),
        "eligible": opportunities_data.get("eligible", {"safe": [], "target": [], "ambitious": []}),
        "growth": opportunities_data.get("growth", {"near_eligible": [], "long_term_stretch": []}),
        "metadata": opportunities_data.get("metadata", {}),
    }

    # --- Store in Cache ONLY if we actually got results ---
    if response_data.get("metadata", {}).get("total_fetched", 0) > 0:
        try:
            doc = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "query_hash": query_hash,
                "data": response_data,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            await mcp_client.session.call_tool("insert-many", arguments={
                "database": "rapid",
                "collection": "opportunities_cache",
                "documents": [doc],
            })
            print(f"[Opportunities] Cached results for user {user_id}")
        except Exception as e:
            print(f"[Opportunities] Cache write error: {e}")
    else:
        print(f"[Opportunities] Did not cache because 0 results were fetched (likely rate limit).")

    return response_data


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
