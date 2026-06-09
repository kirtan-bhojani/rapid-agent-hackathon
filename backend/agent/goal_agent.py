import json
import re
from typing import Dict, Any, Optional

from services.gemini_service import client


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

User Query:
"I want a software engineer job in Germany."

Output:
{{
    "goal_type": "Job",
    "target_role": "Software Engineer",
    "degree": "Unknown",
    "field": "Software Engineering",
    "country": "Germany",
    "timeline": "Unknown",
    "needs_scholarship": false,
    "constraints": [],
    "raw_query": "I want a software engineer job in Germany."
}}

User Query:
"I want to switch from Electronics to Data Science."

Output:
{{
    "goal_type": "Career Switch",
    "target_role": "Data Scientist",
    "degree": "Unknown",
    "field": "Data Science",
    "country": "Unknown",
    "timeline": "Unknown",
    "needs_scholarship": false,
    "constraints": [],
    "raw_query": "I want to switch from Electronics to Data Science."
}}

Unified Profile:
{profile_context}

User Query:
"{query}"

Return ONLY valid JSON.

Use EXACTLY this schema:

{{
    "goal_type": "",
    "target_role": "",
    "degree": "",
    "field": "",
    "country": "",
    "timeline": "",
    "needs_scholarship": false,
    "constraints": [],
    "raw_query": ""
}}

Do NOT include markdown.
Do NOT include explanations.
Do NOT include extra fields.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )

        raw = response.text.strip()

        print("\nRAW RESPONSE:")
        print(raw)
        print("-" * 80)

        # Remove markdown fences if Gemini returns them
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw)
            raw = re.sub(r"```$", "", raw)
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print("JSON ERROR:", e)
        print("FAILED RAW:", raw)

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