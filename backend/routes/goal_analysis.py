"""
goal_analysis.py — Goal Analysis & Gap Analysis Routes

POST /goal-analysis/          — Run Goal Analysis + Gap Analysis + Roadmap for a user
GET  /goal-analysis/{user_id} — Return latest stored analysis for a user
POST /goal-analysis/{user_id}/refresh — Force re-run (clears cache)
"""

import asyncio

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any

from services.profile_service import get_unified_profile
from services.goal_analysis_agent import run_goal_analysis, get_cached_goal_analysis
from services.gap_analysis_agent import run_gap_analysis, get_cached_gap_analysis
from services.career_pipeline import run_career_pipeline
from services.opportunity_service import get_opportunities
from dependencies import get_mcp_client, get_llm_client

router = APIRouter(prefix="/goal-analysis", tags=["goal-analysis"])


class GoalAnalysisRequest(BaseModel):
    user_id: str
    goal: str


@router.post("/")
async def create_goal_analysis(
    req: GoalAnalysisRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
):
    """
    Full pipeline: Goal Analysis → Gap Analysis → Justified Roadmap.

    Returns all three artifacts and trace logs for the UI.
    """
    trace_logs = []

    # 1. Fetch unified profile
    profile = get_unified_profile(req.user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please upload at least a resume first.",
        )

    # 2. Goal Analysis
    trace_logs.append({
        "type": "agent",
        "message": f"Analysing goal: \"{req.goal[:80]}...\"" if len(req.goal) > 80 else f"Analysing goal: \"{req.goal}\"",
    })

    goal_analysis_doc = await run_goal_analysis(
        user_id=req.user_id,
        raw_query=req.goal,
        profile=profile,
        mcp_client=mcp_client,
        llm_client=llm_client,
    )
    goal_analysis = goal_analysis_doc.get("analysis", {})

    trace_logs.append({
        "type": "agent",
        "message": f"Goal identified: {goal_analysis.get('goal_type')} in {goal_analysis.get('destination')} — {goal_analysis.get('field')}. Found {sum(len(goal_analysis.get(k, [])) for k in ['required_qualifications','required_exams','required_documents','financial_requirements','visa_requirements','language_requirements'])} requirements.",
    })

    # 3+4. Gap Analysis → Roadmap (real data dependency, stays sequential) runs
    # CONCURRENTLY with Opportunity Discovery (only needs Goal Analysis + profile —
    # never touches Gap Analysis or Roadmap output). By the time the user visits
    # the Opportunities page, its cache is usually already warm.
    trace_logs.append({
        "type": "agent",
        "message": "Comparing your profile against all identified requirements, and scouting opportunities in parallel...",
    })

    async def _gap_and_roadmap():
        gap_doc = await run_gap_analysis(
            user_id=req.user_id,
            profile=profile,
            goal_analysis_doc=goal_analysis_doc,
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        plan = await run_career_pipeline(
            user_id=req.user_id,
            query=req.goal,
            profile=profile,
            mcp_client=mcp_client,
            llm_client=llm_client,
            goal_analysis_doc=goal_analysis_doc,
            gap_analysis_doc=gap_doc,
        )
        return gap_doc, plan

    async def _opportunities():
        goal_for_od = {
            "goal_type": goal_analysis.get("goal_type"),
            "field": goal_analysis.get("field"),
            "degree": goal_analysis.get("degree"),
            "country": goal_analysis.get("destination"),
            "target_role": goal_analysis.get("target_role"),
            "timeline": goal_analysis.get("timeline"),
            "raw_query": req.goal,
            "needs_scholarship": False,
        }
        try:
            return await get_opportunities(req.user_id, goal_for_od, profile, mcp_client, llm_client)
        except Exception as e:
            # Opportunity discovery is a best-effort side branch here — a failure
            # must not take down the Goal/Gap/Roadmap pipeline it runs alongside.
            print(f"[GoalAnalysis] Opportunity discovery branch failed: {e}")
            return None

    (gap_analysis_doc, plan_result), opportunities_result = await asyncio.gather(
        _gap_and_roadmap(), _opportunities(),
    )

    gap_data = gap_analysis_doc.get("gap_analysis", {})
    critical_count = len(gap_data.get("missing_critical", []))
    completed_count = len(gap_data.get("completed", []))
    gap_score = gap_data.get("gap_score", 0)

    trace_logs.append({
        "type": "agent",
        "message": f"Gap Analysis complete. {completed_count} requirements satisfied, {critical_count} critical gaps identified. Readiness score: {gap_score}%.",
    })
    trace_logs.extend(plan_result.get("trace_logs", []))

    roadmap = plan_result.get("data", {}).get("roadmap", [])
    trace_logs.append({
        "type": "agent",
        "message": f"Roadmap ready with {len(roadmap)} steps, each justified by a specific gap.",
    })

    if opportunities_result:
        eligible_count = opportunities_result.get("metadata", {}).get("eligible_count", 0)
        growth_count = opportunities_result.get("metadata", {}).get("growth_count", 0)
        trace_logs.append({
            "type": "agent",
            "message": f"Opportunity scouting complete. {eligible_count} eligible, {growth_count} growth opportunities cached for you.",
        })
    else:
        trace_logs.append({
            "type": "agent",
            "message": "Opportunity scouting did not complete this time — visit the Opportunities page to retry.",
        })

    return {
        "status": "success",
        "goal_analysis": goal_analysis_doc,
        "gap_analysis": gap_analysis_doc,
        "career_plan": plan_result.get("data"),
        "trace_logs": trace_logs,
    }


@router.get("/{user_id}")
async def get_goal_analysis(
    user_id: str,
    mcp_client: Any = Depends(get_mcp_client),
):
    """
    Return the latest stored goal analysis + gap analysis for a user.
    Does NOT trigger new Gemini calls.
    """
    goal_analysis_doc = await get_cached_goal_analysis(user_id, mcp_client)
    if not goal_analysis_doc:
        raise HTTPException(
            status_code=404,
            detail="No goal analysis found. Please set a goal first.",
        )

    gap_analysis_doc = await get_cached_gap_analysis(user_id, mcp_client)

    return {
        "status": "success",
        "goal_analysis": goal_analysis_doc,
        "gap_analysis": gap_analysis_doc,
    }
