import json
import re
from typing import Dict, Any, Optional

from services.gemini_service import client
from google.genai import types
from pydantic import BaseModel

class GoalAgentExtraction(BaseModel):
    goal_type: str
    target_role: str
    degree: str
    field: str
    country: str
    timeline: str
    needs_scholarship: bool
    constraints: list[str]
    raw_query: str


def extract_goal(
    query: str,
    unified_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    profile_context = "No unified profile available."

    if unified_profile:
        profile_context = f"""
Skills:
{unified_profile.get("professional", {}).get("skills", [])}

Education:
{unified_profile.get("professional", {}).get("education", [])}

Experience:
{unified_profile.get("professional", {}).get("experience", [])}
"""

    prompt = f"""
You are RAPID's Goal Agent.

Your task is to understand the student's future objective.

Use BOTH:
1. User Query
2. Unified Profile (if provided)

Infer missing details whenever reasonable.

Goal Types:
- Higher Studies
- Job
- Internship
- Career Switch
- Scholarship
- Unknown

Examples:

User Query:
"I want to pursue MS in AI in Germany by Fall 2027 with scholarships."

Output:
{{
    "goal_type": "Higher Studies",
    "target_role": "Unknown",
    "degree": "MS",
    "field": "Artificial Intelligence",
    "country": "Germany",
    "timeline": "Fall 2027",
    "needs_scholarship": true,
    "constraints": [],
    "raw_query": "I want to pursue MS in AI in Germany by Fall 2027 with scholarships."
}}

Unified Profile:
{profile_context}

User Query:
"{query}"
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GoalAgentExtraction,
            )
        )

        raw = response.text.strip()
        print("\nRAW RESPONSE:")
        print(raw)
        print("-" * 80)

        return json.loads(raw)

    except Exception as e:
        print("GEMINI ERROR:", repr(e))

    return {
        "goal_type": "Unknown",
        "target_role": "Unknown",
        "degree": "Unknown",
        "field": "Unknown",
        "country": "Unknown",
        "timeline": "Unknown",
        "needs_scholarship": False,
        "constraints": [],
        "raw_query": query,
    }