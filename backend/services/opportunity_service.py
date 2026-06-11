# backend/services/opportunity_service.py

import json
from typing import Dict, Any, List

from tools.search_tool import (
    search_universities,
    search_scholarships,
    search_jobs,
    search_internships,
)
from services.gemini_service import client


# ---------------------------------------------------------------------------
# generate_queries
# Pure function. No I/O. Builds search query strings from goal fields.
# Never injects the string "Unknown" into a query.
# ---------------------------------------------------------------------------

def generate_queries(goal: Dict[str, Any]) -> Dict[str, str]:

    goal_type   = goal.get("goal_type",   "Unknown")
    degree      = goal.get("degree",      "Unknown")
    field       = goal.get("field",       "Unknown")
    country     = goal.get("country",     "Unknown")
    target_role = goal.get("target_role", "Unknown")

    # Build reusable parts — drop anything that is "Unknown"
    field_part   = field       if field       != "Unknown" else ""
    country_part = country     if country     != "Unknown" else ""
    degree_part  = degree      if degree      != "Unknown" else ""
    role_part    = target_role if target_role != "Unknown" else field_part

    def build(*parts):
        return " ".join(p for p in parts if p)

    queries = {}

    if goal_type == "Higher Studies":
        queries["universities"] = build(degree_part, field_part, "universities", country_part)
        if goal.get("needs_scholarship"):
            queries["scholarships"] = build(
                "Scholarships for international students",
                degree_part, field_part, country_part
            )

    elif goal_type == "Scholarship":
        queries["scholarships"] = build("Scholarships", degree_part, field_part, country_part)

    elif goal_type == "Job":
        queries["jobs"] = build(role_part, "jobs", country_part)

    elif goal_type == "Internship":
        queries["internships"] = build(field_part or role_part, "internships", country_part)

    elif goal_type == "Career Switch":
        queries["jobs"] = build(role_part or field_part, "jobs", country_part)

    else:
        # Unknown — best-effort fallback
        queries["universities"] = build(field_part, "universities", country_part) or "top universities"
        queries["jobs"]         = build(field_part, "jobs",         country_part) or "graduate jobs"

    return queries


# ---------------------------------------------------------------------------
# fetch_results
# Calls search_tool functions. Skips error dicts silently.
# search_tool handles multi-query and deduplication internally.
# ---------------------------------------------------------------------------

def fetch_results(queries: Dict[str, str]) -> Dict[str, List]:

    search_map = {
        "universities": search_universities,
        "scholarships": search_scholarships,
        "jobs":         search_jobs,
        "internships":  search_internships,
    }

    raw_results = {}

    for result_type, query in queries.items():

        if not query:
            continue

        fn = search_map.get(result_type)
        if not fn:
            continue

        print(f"\nSEARCH: {result_type} — {query}")
        result = fn(query)

        if isinstance(result, list):
            raw_results[result_type] = result
            print(f"  → {len(result)} results")
        else:
            # Error dict from search_tool — log and skip
            print(f"  → SEARCH ERROR: {result.get('error', 'Unknown error')}")
            raw_results[result_type] = []

    return raw_results


# ---------------------------------------------------------------------------
# _parse_gemini_response
# Same pattern as goal_agent.py and search_tool.py.
# ---------------------------------------------------------------------------

def _parse_gemini_response(response) -> Dict[str, Any]:

    if response is None:
        return {"error": "Gemini request failed", "raw": None}

    try:

        text = response.text

        if not text:
            return {"error": "No text returned", "raw": str(response)}

        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"JSON ERROR: {e}")
        return {"error": str(e), "raw": getattr(response, "text", None)}

    except Exception as e:
        return {"error": str(e), "raw": getattr(response, "text", None)}


# ---------------------------------------------------------------------------
# _build_profile_context
# Extracts the profile fields the classification prompt needs.
# ---------------------------------------------------------------------------

def _build_profile_context(profile: Dict[str, Any]) -> str:

    academic     = profile.get("academic",     {})
    professional = profile.get("professional", {})
    personal     = profile.get("personal",     {})

    return f"""
STUDENT PROFILE:
  Full Name:    {personal.get("full_name",    "Unknown")}
  Nationality:  {personal.get("nationality",  "Unknown")}
  Age:          {personal.get("age",          "Unknown")}
  Institution:  {academic.get("institution",  "Unknown")}
  GPA:          {academic.get("gpa",          "Unknown")}
  Degree Level: {academic.get("degree_level", "Unknown")}
  Skills:       {professional.get("skills",     [])}
  Experience:   {professional.get("experience", [])}
"""


# ---------------------------------------------------------------------------
# classify_opportunities
# Single Gemini call. Classifies every result into one of 5 categories
# or excludes it via a hard disqualifier. Never discards for soft signals.
# ---------------------------------------------------------------------------

def classify_opportunities(
    raw_results: Dict[str, List],
    profile: Dict[str, Any],
    goal: Dict[str, Any],
) -> Dict[str, Any]:

    profile_context = _build_profile_context(profile)

    goal_context = f"""
STUDENT GOAL:
  Goal Type:         {goal.get("goal_type")}
  Field:             {goal.get("field")}
  Degree:            {goal.get("degree")}
  Country:           {goal.get("country")}
  Timeline:          {goal.get("timeline")}
  Needs Scholarship: {goal.get("needs_scholarship")}
  Original Query:    {goal.get("raw_query")}
"""

    results_context = json.dumps(raw_results, indent=2)

    prompt = f"""
You are RAPID's Opportunity Classification Agent.

Evaluate EVERY opportunity in the search results below and classify it for this student.

{profile_context}
{goal_context}

---

CLASSIFICATION RULES

STEP 1 — HARD DISQUALIFICATION
Completely exclude an opportunity ONLY when ALL three conditions are true:
  1. The disqualifying field is NOT "Unknown"
  2. The student definitively does not satisfy it
  3. The requirement cannot be satisfied at any future point

The ONLY two hard disqualifiers are:
  A. eligible_nationalities / eligible_nationals:
       Student's nationality is explicitly listed as ineligible.
       If the field is "Unknown" or "All" → do NOT exclude.

  B. max_age:
       Student's age explicitly exceeds the stated numeric limit.
       If age or max_age is "Unknown" → do NOT exclude.

Do NOT exclude for: GPA, IELTS, TOEFL, GRE, missing documents, missing skills,
experience level, ranking, tuition cost, or competitiveness.
These go into growth categories instead.

---

STEP 2 — EVALUATE requirements using a three-stage process for EVERY requirement field:

  Stage 1 — Is the requirement value known?
    Requirement field = "Unknown" → skip entirely. Do nothing.

  Stage 2 — Is the student's profile value known?
    Profile value = "Unknown" or missing → add to unknown_requirements. STOP.
    Do NOT treat this as a gap. Do NOT downgrade the classification.
    Unknown information is NEUTRAL.

  Stage 3 — Both values are known. Compare.
    Student passes → no action.
    Student fails  → add to known_gaps. This affects classification.

CRITICAL: Classification tier (safe/target/ambitious/near_eligible/long_term_stretch)
is determined ONLY by known_gaps. unknown_requirements have ZERO weight.

DOCUMENTS ARE NOT GAPS:
The following are standard preparation tasks, not eligibility requirements.
NEVER add them to known_gaps or unknown_requirements:
  SOP, Statement of Purpose, Letter of Recommendation, LOR, Resume, CV,
  Transcript, Passport, APS Certificate.
These are already captured in the result's required_documents field.

Fields that CAN produce known_gaps (when both values are known and student fails):
  min_gpa, ielts_min, toefl_min, gre_required, degree_level,
  eligible_degree_levels, eligible_fields, required_skills, min_experience.

---

STEP 3 — CLASSIFY every non-excluded opportunity into exactly one of these 5 statuses.
Classification is based ONLY on known_gaps count and severity.

"safe"
  known_gaps is empty.
  Student comfortably meets all known requirements.
  GPA exceeds minimum by 0.3+ (where both values are known).
  IELTS exceeds minimum by 0.5+ (where both values are known).
  Program is not highly selective.

"target"
  known_gaps is empty.
  Student meets requirements with a small margin, OR key requirements are unknown.
  Program is well-ranked or moderately selective.

"ambitious"
  known_gaps is empty.
  Program is highly competitive:
    — qs_ranking <= 100, OR
    — acceptance_rate < 15%, OR
    — competitiveness = "High"
  Admission is uncertain due to selectivity, not eligibility gaps.

"near_eligible"
  known_gaps has 1–2 entries, ALL with severity "minor".
  Minor gap thresholds:
    — GPA: < 0.3 below required
    — IELTS: < 1.0 band below required
    — TOEFL: < 10 points below required
    — Skills: 1–2 skills missing
    — Experience: 1 year short
  Do NOT classify as near_eligible due to unknown_requirements.

"long_term_stretch"
  known_gaps has 3+ entries, OR has any entry with severity "major".
  Major gap thresholds:
    — GPA: >= 0.3 below required
    — IELTS: >= 1.0 band below required
    — TOEFL: >= 10 points below required
    — Skills: 3+ core skills missing
    — Experience: 2+ years short
    — Degree level: one or more levels below requirement
  Do NOT classify as long_term_stretch due to unknown_requirements.

When all evaluable fields are "Unknown" in both requirement and profile,
use the description text to infer classification.
If truly nothing can be determined, classify as "target" by default.

---

STEP 4 — ADD these 5 fields to every classified opportunity:

"status"
  One of: "safe" | "target" | "ambitious" | "near_eligible" | "long_term_stretch"

"fit_reason"
  One sentence explaining why this opportunity is relevant to the student's goal.

"known_gaps"
  Requirements where BOTH the profile value AND the requirement value are known,
  AND the student fails the requirement.
  Use [] for safe / target / ambitious.
  For near_eligible and long_term_stretch, list each confirmed failure as:
  {{
    "requirement": "IELTS",
    "current":     6.0,
    "required":    7.0,
    "gap":         1.0,
    "severity":    "minor"
  }}
  severity: "minor" | "major" (use thresholds from STEP 3 above)
  Use null for current / required / gap only if numeric parsing fails.
  NEVER put documents (SOP, LOR, Transcript, etc.) here.

"unknown_requirements"
  Requirements where the requirement value is known but the student's profile
  value is missing or "Unknown". These cannot be evaluated.
  Use [] if all evaluable requirements are known.
  List each unevaluable requirement as:
  {{
    "requirement": "IELTS",
    "required":    7.0
  }}
  No "current", no "gap", no "severity".
  NEVER put documents (SOP, LOR, Transcript, etc.) here.

"gap_summary"
  For safe / target / ambitious: use ""
  For near_eligible and long_term_stretch: one sentence describing
  what the student needs to close the known gaps.
  Base this ONLY on known_gaps, not on unknown_requirements.

---

SEARCH RESULTS:

{results_context}

---

Return ONLY valid JSON. No markdown. No explanation. No extra keys.

Every opportunity must appear in exactly one category, or be excluded.
Every item must contain ALL original fields from the search result
PLUS the 5 classification fields: status, fit_reason, known_gaps, unknown_requirements, gap_summary.

{{
  "eligible": {{
    "safe":      [],
    "target":    [],
    "ambitious": []
  }},
  "growth": {{
    "near_eligible":     [],
    "long_term_stretch": []
  }},
  "excluded_count": 0
}}
"""

    print("\nOPPORTUNITY AGENT: Classifying results with Gemini...")

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

    except Exception as e:

        print(f"GEMINI ERROR: {repr(e)}")

        return {
            "eligible": {"safe": [], "target": [], "ambitious": []},
            "growth":   {"near_eligible": [], "long_term_stretch": []},
            "excluded_count": 0,
            "error": str(e),
        }

    classified = _parse_gemini_response(response)

    if "error" in classified:
        print(f"CLASSIFICATION PARSE ERROR: {classified['error']}")
        return {
            "eligible": {"safe": [], "target": [], "ambitious": []},
            "growth":   {"near_eligible": [], "long_term_stretch": []},
            "excluded_count": 0,
            "error": classified["error"],
        }

    return classified


# ---------------------------------------------------------------------------
# get_opportunities — public entry point
# Orchestrates: generate_queries → fetch_results → classify_opportunities
# ---------------------------------------------------------------------------

def get_opportunities(goal: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:

    print("\n" + "=" * 50)
    print("OPPORTUNITY AGENT STARTED")
    print(f"  Goal Type : {goal.get('goal_type')}")
    print(f"  Field     : {goal.get('field')}")
    print(f"  Country   : {goal.get('country')}")
    print(f"  Degree    : {goal.get('degree')}")
    print("=" * 50)

    # Step 1 — Build queries
    queries = generate_queries(goal)
    print(f"\nQueries generated: {queries}")

    # Step 2 — Fetch from Search Agent
    raw_results = fetch_results(queries)

    total_fetched = sum(len(v) for v in raw_results.values())
    print(f"\nTotal results fetched: {total_fetched}")

    # Empty results — return clean empty response, skip Gemini call
    if total_fetched == 0:
        print("No results to classify.")
        return {
            "goal_summary": {
                "goal_type": goal.get("goal_type"),
                "field":     goal.get("field"),
                "country":   goal.get("country"),
                "degree":    goal.get("degree"),
                "timeline":  goal.get("timeline"),
            },
            "eligible": {"safe": [], "target": [], "ambitious": []},
            "growth":   {"near_eligible": [], "long_term_stretch": []},
            "metadata": {
                "total_fetched":  0,
                "queries_used":   queries,
                "eligible_count": 0,
                "growth_count":   0,
                "excluded_count": 0,
            },
        }

    # Step 3 — Classify all results
    classified = classify_opportunities(raw_results, profile, goal)

    # Step 4 — Assemble final response
    eligible = classified.get("eligible", {"safe": [], "target": [], "ambitious": []})
    growth   = classified.get("growth",   {"near_eligible": [], "long_term_stretch": []})

    eligible_count = (
        len(eligible.get("safe",      [])) +
        len(eligible.get("target",    [])) +
        len(eligible.get("ambitious", []))
    )
    growth_count = (
        len(growth.get("near_eligible",     [])) +
        len(growth.get("long_term_stretch", []))
    )
    excluded_count = classified.get("excluded_count", 0)

    print(f"\n{'=' * 50}")
    print("OPPORTUNITY AGENT COMPLETE")
    print(f"  Eligible  : {eligible_count}")
    print(f"  Growth    : {growth_count}")
    print(f"  Excluded  : {excluded_count}")
    print("=" * 50)

    return {
        "goal_summary": {
            "goal_type": goal.get("goal_type"),
            "field":     goal.get("field"),
            "country":   goal.get("country"),
            "degree":    goal.get("degree"),
            "timeline":  goal.get("timeline"),
        },
        "eligible": eligible,
        "growth":   growth,
        "metadata": {
            "total_fetched":  total_fetched,
            "queries_used":   queries,
            "eligible_count": eligible_count,
            "growth_count":   growth_count,
            "excluded_count": excluded_count,
        },
    }