"""
dashboard.py — Dashboard Data Route

GET /dashboard/{user_id} — Returns real, computed dashboard stats for a user.

No hardcoded values. Everything is derived from real MongoDB data.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from services.profile_service import get_unified_profile
from utils.mcp_helpers import find_latest
from dependencies import get_mcp_client

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _compute_profile_completion(profile: dict) -> int:
    """
    Compute a profile completion score (0–100) based on how many
    fields in the unified profile are filled.
    """
    if not profile:
        return 0

    checks = []
    personal = profile.get("personal", {})
    academic = profile.get("academic", {})
    professional = profile.get("professional", {})
    lang = profile.get("language_tests", {})
    materials = profile.get("application_materials", {})
    docs = profile.get("meta", {}).get("documents_merged", [])

    # Personal (10 pts each)
    checks.append(bool(personal.get("full_name")))
    checks.append(bool(personal.get("nationality")))

    # Academic (10 pts each)
    checks.append(bool(academic.get("institution")))
    checks.append(bool(academic.get("degree")))
    checks.append(bool(academic.get("major")))
    checks.append(bool(academic.get("gpa")))

    # Professional (10 pts each)
    checks.append(bool(professional.get("skills")))
    checks.append(bool(professional.get("experience")))

    # Language tests (10 pts)
    checks.append(bool(lang.get("ielts", {}).get("overall_band")))

    # Application materials (10 pts)
    checks.append(bool(materials.get("sop_summary")))

    # Document types bonus: passport, transcript, lor
    checks.append("passport" in docs)
    checks.append("transcript" in docs)

    score = round(sum(1 for c in checks if c) / len(checks) * 100)
    return score


def _compute_roadmap_progress(roadmap: list) -> dict:
    """Compute completed vs total roadmap steps."""
    if not roadmap:
        return {"completed": 0, "total": 0, "percentage": 0}
    completed = sum(1 for step in roadmap if step.get("status") == "Completed")
    total = len(roadmap)
    return {
        "completed": completed,
        "total": total,
        "percentage": round(completed / total * 100) if total > 0 else 0,
    }


def _extract_upcoming_deadlines(roadmap: list, max_count: int = 3) -> list:
    """
    Extract steps with deadline_hint that aren't completed.
    Returns up to max_count items.
    """
    deadlines = []
    for step in roadmap:
        if step.get("status") == "Completed":
            continue
        hint = step.get("deadline_hint", "")
        if hint and hint.lower() not in ("no fixed deadline", "check university portal", ""):
            deadlines.append({
                "task": step.get("title", ""),
                "deadline": hint,
                "priority": step.get("priority", "medium"),
            })
    return deadlines[:max_count]


@router.get("/{user_id}")
async def get_dashboard(user_id: str, mcp_client: Any = Depends(get_mcp_client)):
    """
    Return computed dashboard stats for user_id.

    All values are derived from real data — no hardcoded values.
    """

    # 1. Fetch unified profile
    profile = get_unified_profile(user_id)
    profile_completion = _compute_profile_completion(profile)
    docs_merged = profile.get("meta", {}).get("documents_merged", []) if profile else []

    # 2. Fetch latest career plan
    roadmap_progress = {"completed": 0, "total": 0, "percentage": 0}
    upcoming_deadlines = []
    next_critical_action = None
    goal_summary = None

    latest_plan = await find_latest(mcp_client, "rapid", "career_plans", {"user_id": user_id})
    if latest_plan:
        roadmap = latest_plan.get("roadmap", [])
        roadmap_progress = _compute_roadmap_progress(roadmap)
        upcoming_deadlines = _extract_upcoming_deadlines(roadmap)
        goal_summary = latest_plan.get("goal", {})
        next_critical_action = latest_plan.get("gaps", {}).get("next_critical_action")

    # 3. Fetch gap score from gap_analyses
    gap_score = None
    gap_doc = await find_latest(mcp_client, "rapid", "gap_analyses", {"user_id": user_id})
    if gap_doc:
        gap_score = gap_doc.get("gap_analysis", {}).get("gap_score")
        if next_critical_action is None:
            next_critical_action = gap_doc.get("gap_analysis", {}).get("next_critical_action")

    return {
        "status": "success",
        "profile_completion": profile_completion,
        "documents_uploaded": docs_merged,
        "roadmap_progress": roadmap_progress,
        "gap_score": gap_score,
        "goal_summary": goal_summary,
        "next_critical_action": next_critical_action,
        "upcoming_deadlines": upcoming_deadlines,
        "has_profile": profile is not None,
        "has_goal": goal_summary is not None,
    }
