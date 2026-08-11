"""
career_pipeline.py — Justified Roadmap Generator

Replaces the original generic pipeline with a goal-driven, justified roadmap.

Every roadmap step now includes:
  - reason: WHY this step exists (tied to a specific gap)
  - reasoning: WHY this step's priority/ordering/effort estimate was chosen this way
  - estimated_effort: how long this realistically takes
  - dependencies: what must be done before this
  - priority: "critical" | "high" | "medium" | "low"
  - deadline_hint: any time sensitivity

Public API
──────────
    run_career_pipeline(user_id, query, profile, mcp_client, llm_client) → dict
        Goal Analysis → Gap Analysis → Justified Roadmap → persist → return
"""

from __future__ import annotations

import uuid
import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel


# =====================================================================
#  PYDANTIC MODELS
# =====================================================================

class RoadmapStep(BaseModel):
    step_id: int
    title: str
    description: str           # Specific, actionable description
    reason: str                # WHY: which gap this addresses
    reasoning: str              # WHY: why this priority/ordering/effort estimate was chosen
    estimated_effort: str      # e.g. "2–3 weeks", "1 day", "Ongoing"
    dependencies: List[str]    # Titles of steps that must complete first
    priority: str              # "critical" | "high" | "medium" | "low"
    deadline_hint: str         # e.g. "Before October 2025", "No fixed deadline"
    status: str                # Always "Pending" on creation


class RoadmapList(BaseModel):
    """Wraps the bare list[RoadmapStep] so the schema has a top-level object —
    Gemini's response_schema handles bare lists natively, but Groq's JSON mode
    (used as this call's fallback path) has no top-level-array equivalent."""
    steps: List[RoadmapStep]


# =====================================================================
#  ROADMAP GENERATION PROMPT
# =====================================================================

_ROADMAP_PROMPT = """
You are RAPID's Roadmap Planning Agent.

Generate a personalised, justified roadmap for the user based on the gap analysis below.

CRITICAL RULES:
1. Every step must exist because of a specific gap identified in the gap analysis.
2. Each step's "reason" must explicitly reference the gap it addresses.
3. Steps must be concrete and actionable — NOT generic advice.
4. BAD: "Take IELTS." GOOD: "Register for IELTS Academic. Target band 7.0+. Book at least 8 weeks before
   your first application deadline to allow time for score reporting and any retakes."
5. Order steps by dependency and priority.
6. Mark steps as "critical" only if missing them would prevent the goal entirely.
7. deadline_hint: if you know a realistic deadline, state it. If not, say "No fixed deadline" or "Check university portal".
8. estimated_effort: be realistic. "Register for IELTS" → "30 minutes". "Prepare for IELTS" → "4–8 weeks of study".
9. Never fabricate specific university deadlines. Use approximate ranges like "typically October–January".
10. "reasoning" (distinct from "reason"): explain WHY this step's priority/ordering/effort estimate
    was chosen the way it was — e.g. why it's "critical" not "high", why it comes before/after
    other steps, why the effort estimate is what it is.

GOAL: {raw_query}
DESTINATION: {destination}
FIELD: {field}
DEGREE: {degree}
TIMELINE: {timeline}

GAP ANALYSIS SUMMARY:
{gap_summary}

Missing Critical Items: {missing_critical}
Missing Recommended Items: {missing_recommended}
Partial Items: {partial}

Generate a complete step-by-step roadmap ("steps" list). Start with the most critical/time-sensitive steps.
"""


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================

def _fmt_gap_items(items: list) -> str:
    if not items:
        return "None"
    lines = []
    for item in items:
        if isinstance(item, dict):
            lines.append(f"  - {item.get('item', '')}: {item.get('action', item.get('evidence', ''))}")
        else:
            lines.append(f"  - {item}")
    return "\n".join(lines)


async def generate_justified_roadmap(
    goal_analysis: Dict[str, Any],
    gap_data: Dict[str, Any],
    raw_query: str,
    llm_client: Any,
) -> List[Dict[str, Any]]:
    """Generate a justified roadmap from goal analysis + gap analysis."""

    prompt = _ROADMAP_PROMPT.format(
        raw_query=raw_query,
        destination=goal_analysis.get("destination", "Unknown"),
        field=goal_analysis.get("field", "Unknown"),
        degree=goal_analysis.get("degree", "Unknown"),
        timeline=goal_analysis.get("timeline", "Unknown"),
        gap_summary=gap_data.get("summary", ""),
        missing_critical=_fmt_gap_items(gap_data.get("missing_critical", [])),
        missing_recommended=_fmt_gap_items(gap_data.get("missing_recommended", [])),
        partial=_fmt_gap_items(gap_data.get("partial", [])),
    )

    try:
        output = await llm_client.generate_structured(prompt, RoadmapList)
        return [step.model_dump() for step in output.steps]
    except Exception as e:
        print(f"[Roadmap] LLM error: {e}")
        return []


# =====================================================================
#  PUBLIC ENTRY POINT
# =====================================================================

async def run_career_pipeline(
    user_id: str,
    query: str,
    profile: Dict[str, Any],
    mcp_client: Any,
    llm_client: Any,
    goal_analysis_doc: Optional[Dict[str, Any]] = None,
    gap_analysis_doc: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Justified Roadmap Pipeline.

    If goal_analysis_doc and gap_analysis_doc are provided (already computed),
    skip straight to roadmap generation. Otherwise, they should have been run first.

    Returns: {"data": plan_doc, "trace_logs": [...]}
    """
    trace_logs = []

    # ── Unpack pre-computed analysis docs ─────────────────────────────
    goal_analysis = {}
    gap_data = {}

    if goal_analysis_doc:
        goal_analysis = goal_analysis_doc.get("analysis", {})
        trace_logs.append({
            "type": "agent",
            "message": f"Goal Analysis loaded: {goal_analysis.get('goal_type')} — {goal_analysis.get('destination')}",
        })

    if gap_analysis_doc:
        gap_data = gap_analysis_doc.get("gap_analysis", {})
        critical_count = len(gap_data.get("missing_critical", []))
        trace_logs.append({
            "type": "agent",
            "message": f"Gap Analysis loaded. {critical_count} critical gaps identified. Gap score: {gap_data.get('gap_score', 0)}%",
        })

    # ── Generate justified roadmap ─────────────────────────────────────
    trace_logs.append({
        "type": "agent",
        "message": "Generating personalised, justified roadmap based on gap analysis...",
    })

    roadmap = await generate_justified_roadmap(goal_analysis, gap_data, query, llm_client)

    if not roadmap:
        trace_logs.append({"type": "agent", "message": "Roadmap generation failed. Using empty plan."})

    trace_logs.append({
        "type": "agent",
        "message": f"Roadmap generated with {len(roadmap)} steps, each justified by a specific gap.",
    })

    # ── Check for existing plan to update or insert new ───────────────
    plan_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "goal": {
            "target_role": goal_analysis.get("target_role", query),
            "timeline": goal_analysis.get("timeline", "Unknown"),
            "destination": goal_analysis.get("destination", ""),
            "field": goal_analysis.get("field", ""),
            "degree": goal_analysis.get("degree", ""),
            "goal_type": goal_analysis.get("goal_type", ""),
            "raw_query": query,
        },
        "gaps": {
            "gap_score": gap_data.get("gap_score", 0),
            "missing_critical": gap_data.get("missing_critical", []),
            "missing_recommended": gap_data.get("missing_recommended", []),
            "completed": gap_data.get("completed", []),
            "next_critical_action": gap_data.get("next_critical_action", ""),
        },
        "roadmap": roadmap,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    trace_logs.append({
        "type": "mcp",
        "message": "Persisting career plan to rapid.career_plans...",
    })

    try:
        await mcp_client.session.call_tool("insert-many", arguments={
            "database": "rapid",
            "collection": "career_plans",
            "documents": [plan_doc],
        })
        trace_logs.append({"type": "mcp", "message": "Career plan stored successfully."})
    except Exception as e:
        trace_logs.append({"type": "error", "message": f"Storage error: {e}"})

    return {"data": plan_doc, "trace_logs": trace_logs}
