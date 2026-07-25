"""
gap_analysis_agent.py — Gap Analysis Agent

Single responsibility: compare the user's unified profile against the requirements
identified by the Goal Analysis Agent and produce a structured gap report.

This is the central feature of RAPID. It answers: "What exactly am I missing?"

Public API
──────────
    run_gap_analysis(user_id, profile, goal_analysis, mcp_client) → dict
        Compares profile vs goal requirements. Stores result in MongoDB.
        Returns the gap_analysis document.

    get_cached_gap_analysis(user_id, mcp_client) → dict | None
        Returns the latest stored gap analysis for a user, or None.
"""

from __future__ import annotations

import json
import datetime
import uuid
import hashlib
from typing import Any, Dict, Optional, List
from google import genai
from google.genai import types
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# =====================================================================
#  PYDANTIC MODELS
# =====================================================================

class GapItem(BaseModel):
    item: str           # e.g. "Passport", "IELTS Score", "Research Experience"
    status: str         # "completed" | "missing_critical" | "missing_recommended" | "partial" | "unknown"
    evidence: str       # What in the profile confirms this (or "Not found in profile")
    reason: str         # Why this is needed (tied to goal analysis)
    action: str         # What the user should do about it
    is_optional: bool   # From the goal analysis requirement


class GapAnalysisOutput(BaseModel):
    completed: List[GapItem]           # Items confirmed satisfied by the profile
    missing_critical: List[GapItem]    # Mandatory items not found or insufficient
    missing_recommended: List[GapItem] # Optional but important items missing
    partial: List[GapItem]             # Items partially satisfied (e.g. IELTS done but score too low)
    gap_score: int                     # 0-100, higher = closer to goal (computed from completed vs total)
    summary: str                       # One paragraph summarising the gap situation
    next_critical_action: str          # Single most important next step


# =====================================================================
#  PROMPT
# =====================================================================

_GAP_ANALYSIS_PROMPT = """
You are RAPID's Gap Analysis Agent.

Your job is to compare the user's CURRENT PROFILE against the REQUIREMENTS identified
for their goal, and classify every requirement into one of these statuses:
  - "completed"           — Profile clearly satisfies this requirement
  - "missing_critical"    — Mandatory requirement not satisfied or not present in profile
  - "missing_recommended" — Optional but important requirement not in profile
  - "partial"             — Requirement exists but is insufficient (e.g. IELTS 5.5 when 6.5 needed)
  - "unknown"             — Cannot determine from current profile data

CURRENT PROFILE:
{profile_json}

GOAL ANALYSIS (requirements to check against):
Goal: {raw_query}
Goal Type: {goal_type}
Destination: {destination}
Field: {field}
Degree: {degree}

Required Qualifications: {required_qualifications}
Required Exams: {required_exams}
Required Documents: {required_documents}
Financial Requirements: {financial_requirements}
Visa Requirements: {visa_requirements}
Language Requirements: {language_requirements}
Experience Expectations: {experience_expectations}
Application Requirements: {application_requirements}

RULES:
1. Be honest. If a requirement is not in the profile, mark it missing.
2. Do NOT fabricate or assume data not present in the profile.
3. For documents: check profile.meta.documents_merged. E.g. if "passport" is in documents_merged, passport is completed.
4. For IELTS: check profile.language_tests.ielts. If overall_band is present, compare vs requirement.
5. For GPA: check profile.academic.gpa. Compare vs typical requirement for the destination.
6. For experience: check profile.professional.experience list length and content.
7. Evidence: be specific — say "GPA 3.7 found in profile" or "No IELTS score in profile".
8. Action: be actionable — "Register for IELTS Academic. Scores typically arrive in 2 weeks." NOT "Get IELTS".
9. reason: connect back to the goal — "Required by most German universities for English-taught MSc programs."

Compute gap_score as: round(completed_count / max(total_requirements_count, 1) * 100)

next_critical_action: the single most important mandatory item to work on first.

Return ALL fields for EVERY requirement. Be thorough. Do not omit any requirement from the goal analysis.
"""


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================

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


def _fmt_requirements(items: list) -> str:
    """Format a list of requirement dicts into a readable string for the prompt."""
    if not items:
        return "None specified"
    lines = []
    for item in items:
        if isinstance(item, dict):
            optional_str = " [OPTIONAL]" if item.get("is_optional") else " [REQUIRED]"
            lines.append(f"  - {item.get('item', '')}{optional_str}: {item.get('detail', '')}")
        else:
            lines.append(f"  - {item}")
    return "\n".join(lines) if lines else "None"


# =====================================================================
#  PUBLIC API
# =====================================================================

async def get_cached_gap_analysis(user_id: str, mcp_client: Any) -> Optional[Dict[str, Any]]:
    """Return the latest stored gap analysis for user_id, or None."""
    try:
        result = await mcp_client.session.call_tool("find", arguments={
            "database": "rapid",
            "collection": "gap_analyses",
            "filter": {"user_id": user_id},
        })
        docs = await _parse_mcp_docs(result)
        if docs:
            docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return docs[0]
    except Exception as e:
        print(f"[GapAnalysis] Cache fetch error: {e}")
    return None


async def run_gap_analysis(
    user_id: str,
    profile: Dict[str, Any],
    goal_analysis_doc: Dict[str, Any],
    mcp_client: Any,
) -> Dict[str, Any]:
    """
    Run Gap Analysis: compare profile vs goal requirements.

    Steps:
    1. Build cache key from user_id + goal query hash
    2. If cache is fresh (< 24h), return cached
    3. Call Gemini with full profile + goal analysis
    4. Store result in MongoDB gap_analyses
    5. Return the gap analysis document
    """

    goal_analysis = goal_analysis_doc.get("analysis", {})
    raw_query = goal_analysis_doc.get("raw_query", "")
    query_hash = goal_analysis_doc.get("query_hash", "")

    # 1. Check cache
    cache_key = hashlib.md5(f"{user_id}:{query_hash}:gap".encode()).hexdigest()
    try:
        result = await mcp_client.session.call_tool("find", arguments={
            "database": "rapid",
            "collection": "gap_analyses",
            "filter": {"user_id": user_id, "cache_key": cache_key},
        })
        cached_docs = await _parse_mcp_docs(result)
        if cached_docs:
            cached_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            latest = cached_docs[0]
            # Fresh if < 24h
            try:
                created = datetime.datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
                age = (datetime.datetime.now(datetime.timezone.utc) - created).total_seconds()
                if age < 86400:
                    print(f"[GapAnalysis] Cache hit for user {user_id}")
                    return latest
            except Exception:
                pass
    except Exception as e:
        print(f"[GapAnalysis] Cache check error: {e}")

    # 2. Build prompt
    prompt = _GAP_ANALYSIS_PROMPT.format(
        profile_json=json.dumps(profile, indent=2),
        raw_query=raw_query,
        goal_type=goal_analysis.get("goal_type", "Unknown"),
        destination=goal_analysis.get("destination", "Unknown"),
        field=goal_analysis.get("field", "Unknown"),
        degree=goal_analysis.get("degree", "Unknown"),
        required_qualifications=_fmt_requirements(goal_analysis.get("required_qualifications", [])),
        required_exams=_fmt_requirements(goal_analysis.get("required_exams", [])),
        required_documents=_fmt_requirements(goal_analysis.get("required_documents", [])),
        financial_requirements=_fmt_requirements(goal_analysis.get("financial_requirements", [])),
        visa_requirements=_fmt_requirements(goal_analysis.get("visa_requirements", [])),
        language_requirements=_fmt_requirements(goal_analysis.get("language_requirements", [])),
        experience_expectations=_fmt_requirements(goal_analysis.get("experience_expectations", [])),
        application_requirements=_fmt_requirements(goal_analysis.get("application_requirements", [])),
    )

    print(f"[GapAnalysis] Calling Gemini for user {user_id}")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GapAnalysisOutput,
            ),
        )
        gap_data = json.loads(response.text)
    except Exception as e:
        print(f"[GapAnalysis] Gemini error: {e}")
        gap_data = {
            "completed": [],
            "missing_critical": [],
            "missing_recommended": [],
            "partial": [],
            "gap_score": 0,
            "summary": "Gap analysis could not be completed. Please try again.",
            "next_critical_action": "Retry gap analysis.",
        }

    # 3. Store in MongoDB
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "cache_key": cache_key,
        "query_hash": query_hash,
        "raw_query": raw_query,
        "gap_analysis": gap_data,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        await mcp_client.session.call_tool("insert-many", arguments={
            "database": "rapid",
            "collection": "gap_analyses",
            "documents": [doc],
        })
        print(f"[GapAnalysis] Stored gap analysis for user {user_id}")
    except Exception as e:
        print(f"[GapAnalysis] Storage error: {e}")

    return doc
