"""
goal_analysis_agent.py — Goal Analysis Agent

Single responsibility: take a raw user goal string + unified profile and
produce an exhaustive, structured decomposition of what achieving that goal
actually requires.

This is NOT a roadmap generator. It is a requirements extractor.

Public API
──────────
    run_goal_analysis(user_id, raw_query, profile, mcp_client, llm_client) → dict
        Runs full goal decomposition. Stores result in MongoDB.
        Returns the goal_analysis document.

    get_cached_goal_analysis(user_id, mcp_client) → dict | None
        Returns the latest stored goal analysis for a user, or None.
"""

from __future__ import annotations

import datetime
import uuid
import hashlib
from typing import Any, Dict, Optional

from pydantic import BaseModel

from utils.mcp_helpers import find_latest


# =====================================================================
#  PYDANTIC MODELS — structured output schema
# =====================================================================

class RequirementItem(BaseModel):
    item: str
    detail: str
    is_optional: bool
    reasoning: str      # WHY this item is/isn't optional, tied to the goal

class GoalAnalysisOutput(BaseModel):
    # Core goal fields
    goal_type: str              # "Higher Studies" | "Job" | "Internship" | "Scholarship" | "Research"
    destination: str            # country or company
    field: str                  # e.g. "Microelectronics", "Machine Learning", "Software Engineering"
    degree: str                 # e.g. "Master of Science", "PhD", "N/A"
    target_role: str            # e.g. "Embedded Engineer at Qualcomm", "Research Intern"
    timeline: str               # e.g. "Apply by Winter 2025", "12–18 months"
    raw_query: str              # original user query, preserved

    # Requirement categories
    required_qualifications: list[RequirementItem]   # GPA, degree level, publications
    required_exams: list[RequirementItem]             # GRE, GMAT, IELTS, TOEFL, APS
    required_documents: list[RequirementItem]         # Passport, SOP, LOR, transcript, CV
    financial_requirements: list[RequirementItem]     # Blocked account, proof of funds, tuition estimate
    visa_requirements: list[RequirementItem]          # Visa type, APS, embassy appointment
    language_requirements: list[RequirementItem]      # IELTS band, TOEFL score, German B1/B2
    experience_expectations: list[RequirementItem]    # Industry experience, research, internships
    application_requirements: list[RequirementItem]   # Deadlines, portals, application fees
    scholarships: list[RequirementItem]               # DAAD, Erasmus, etc.
    additional_notes: list[str]                       # Anything else worth noting
    reasoning: str                                    # WHY this requirement set is exhaustive for this goal type/destination


# =====================================================================
#  PROMPT
# =====================================================================

_GOAL_ANALYSIS_PROMPT = """
You are RAPID's Goal Analysis Agent. Your job is to decompose a user's ambitious goal
into an exhaustive, structured list of every requirement they will need to satisfy.

You are NOT generating a roadmap.
You are identifying WHAT is needed to achieve this goal.

Be exhaustive. Think like an expert advisor who has helped hundreds of students and
professionals achieve exactly this type of goal.

User's Goal: "{raw_query}"

User's Current Profile (for context only — do NOT gap analyse here):
{profile_context}

Instructions:
1. Identify the goal_type: one of "Higher Studies" | "Job" | "Internship" | "Scholarship" | "Research"
2. Extract destination (country or company), field, degree, target_role, timeline
3. For EACH requirement category, list every item a person realistically needs.
   - required_qualifications: academic grades, degree level, publications, research experience
   - required_exams: language tests (IELTS/TOEFL), aptitude tests (GRE/GMAT/APS), entrance exams
   - required_documents: every document needed (passport, SOP, LOR x2/x3, transcript, CV, APS certificate, etc.)
   - financial_requirements: blocked account amount, proof of funds, tuition estimate, living costs
   - visa_requirements: visa type, APS certificate for Germany, embassy appointment, processing time
   - language_requirements: specific band scores required, optional language courses, B1/B2 German
   - experience_expectations: minimum research/industry experience, preferred backgrounds
   - application_requirements: application portals, deadlines, fees, references count
   - scholarships: relevant funding sources (DAAD, Erasmus+, KAAD, etc.)
   - additional_notes: any quirks, tips, or warnings specific to this goal

For is_optional: true means "helpful but not required". false means "mandatory".
For each item's "reasoning": explain WHY this specific item is/isn't optional for this goal.

Return ALL fields. Be specific. For Germany MSc in Microelectronics, for example:
- APS certificate IS required (is_optional: false)
- German B2 is optional for English-taught programs but strongly recommended (is_optional: true)
- Blocked account of ~11,208 EUR is required (is_optional: false)
- IELTS minimum 6.5 for most programs (is_optional: false)

Also provide a top-level "reasoning" field: explain WHY this requirement set is exhaustive
for this specific goal_type + destination + field combination — what expertise or pattern
you drew on to be confident nothing major was missed.

CRITICAL RULES:
1. Do NOT list the components of the goal itself as requirements! For example, if the goal is "Master's in Germany", do NOT add "Master's degree" or "Destination: Germany" to the requirements lists. The requirements are what the user NEEDS TO DO or HAVE in order to GET the Master's in Germany (e.g. Bachelor's degree, IELTS, blocked account).
2. Do not invent deadlines. Use phrases like "typically" or "check university portal" for variable items.
"""


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================

def _build_profile_context(profile: Dict[str, Any]) -> str:
    """Summarise the unified profile for use in the prompt."""
    if not profile:
        return "No profile available."

    academic = profile.get("academic", {})
    professional = profile.get("professional", {})
    personal = profile.get("personal", {})
    lang = profile.get("language_tests", {})
    docs = profile.get("meta", {}).get("documents_merged", [])

    lines = []
    if personal.get("full_name"):
        lines.append(f"Name: {personal['full_name']}")
    if personal.get("nationality"):
        lines.append(f"Nationality: {personal['nationality']}")
    if academic.get("institution"):
        lines.append(f"Institution: {academic['institution']}")
    if academic.get("degree"):
        lines.append(f"Degree: {academic['degree']}")
    if academic.get("major"):
        lines.append(f"Major: {academic['major']}")
    if academic.get("gpa"):
        lines.append(f"GPA: {academic['gpa']}")
    if professional.get("skills"):
        lines.append(f"Skills: {', '.join(str(s) for s in professional['skills'][:10])}")
    if lang.get("ielts"):
        ielts = lang["ielts"]
        if ielts.get("overall_band"):
            lines.append(f"IELTS: {ielts['overall_band']}")
    if docs:
        lines.append(f"Documents uploaded: {', '.join(docs)}")

    return "\n".join(lines) if lines else "Profile partially filled."


# =====================================================================
#  PUBLIC API
# =====================================================================

async def get_cached_goal_analysis(user_id: str, mcp_client: Any) -> Optional[Dict[str, Any]]:
    """Return the latest stored goal analysis for user_id, or None."""
    return await find_latest(mcp_client, "rapid", "goal_analyses", {"user_id": user_id})


async def run_goal_analysis(
    user_id: str,
    raw_query: str,
    profile: Dict[str, Any],
    mcp_client: Any,
    llm_client: Any,
) -> Dict[str, Any]:
    """
    Run exhaustive Goal Analysis for user_id + raw_query.

    Steps:
    1. Check MongoDB cache — if a recent analysis for the same query exists, return it.
    2. Call the LLM (Gemini, falling back to Groq) with the exhaustive prompt.
    3. Store result in MongoDB goal_analyses collection.
    4. Return the analysis document.
    """

    # 1. Check cache by query hash
    query_hash = hashlib.md5(f"{user_id}:{raw_query}".encode()).hexdigest()

    cached = await find_latest(mcp_client, "rapid", "goal_analyses", {"user_id": user_id, "query_hash": query_hash})
    if cached:
        print(f"[GoalAnalysis] Cache hit for user {user_id}")
        return cached

    # 2. Call LLM
    profile_context = _build_profile_context(profile)
    prompt = _GOAL_ANALYSIS_PROMPT.format(
        raw_query=raw_query,
        profile_context=profile_context,
    )

    print(f"[GoalAnalysis] Calling LLM for: {raw_query[:80]}")

    try:
        output = await llm_client.generate_structured(prompt, GoalAnalysisOutput)
        analysis_data = output.model_dump()
    except Exception as e:
        print(f"[GoalAnalysis] LLM error: {e}")
        # Minimal safe fallback — preserves the query without fabricating requirements
        analysis_data = {
            "goal_type": "Higher Studies",
            "destination": "Unknown",
            "field": "Unknown",
            "degree": "Unknown",
            "target_role": raw_query,
            "timeline": "Unknown",
            "raw_query": raw_query,
            "required_qualifications": [],
            "required_exams": [],
            "required_documents": [],
            "financial_requirements": [],
            "visa_requirements": [],
            "language_requirements": [],
            "experience_expectations": [],
            "application_requirements": [],
            "scholarships": [],
            "additional_notes": ["Goal analysis failed. Please try again."],
            "reasoning": "Goal analysis could not be completed due to an LLM error; this is a placeholder, not an analyzed result.",
        }

    # 3. Store in MongoDB
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "query_hash": query_hash,
        "raw_query": raw_query,
        "analysis": analysis_data,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        await mcp_client.session.call_tool("insert-many", arguments={
            "database": "rapid",
            "collection": "goal_analyses",
            "documents": [doc],
        })
        print(f"[GoalAnalysis] Stored analysis for user {user_id}")
    except Exception as e:
        print(f"[GoalAnalysis] Storage error: {e}")

    return doc
