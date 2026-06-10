# backend/tools/search_tool.py

from services.gemini_service import client
from google.genai import types
import json


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_response(response):

    if response is None:
        return {
            "error": "Gemini request failed",
            "raw": None
        }

    try:

        text = response.text

        if not text:
            return {
                "error": "No text returned",
                "raw": str(response)
            }

        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:

        return {
            "error": str(e),
            "raw": getattr(response, "text", None)
        }

def _call_gemini(prompt):

    print("CALL GEMINI CALLED")
    
    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            ),
        )

        return response

    except Exception as e:

        print("\nGEMINI ERROR:")
        print(repr(e))

        return None


# ---------------------------------------------------------------------------
# search_universities
# ---------------------------------------------------------------------------

def search_universities(query):

    prompt = f"""
Search the web for university degree programs matching this query:

{query}

Return a JSON array of up to 5 results.
Each object must follow the EXACT schema below.
Every field must be present in every result.
Use "Unknown" for any missing string field.
Use [] for any missing list field.
Do NOT invent deadlines, GPA requirements, or rankings.
Return ONLY valid JSON. No markdown. No explanation.

Schema:

[
  {{
    "name":                     "",
    "university":               "",
    "country":                  "",
    "city":                     "",
    "link":                     "",

    "source_type":              "",

    "degree_level":             "",
    "eligible_nationals":       "",

    "min_gpa":                  "",
    "ielts_min":                "",
    "toefl_min":                "",
    "gre_required":             "",

    "qs_ranking":               "",
    "acceptance_rate":          "",
    "competitiveness":          "",

    "required_documents":       [],
    "application_requirements": [],

    "intake":                   "",
    "deadline":                 "",
    "duration":                 "",
    "tuition":                  "",
    "scholarships_available":   "",

    "description":              ""
  }}
]

Field rules:

source_type:
  "official"     — university or department admissions page
  "ranking_site" — QS, THE, Mastersportal, Studyportals
  "unknown"      — cannot be determined from source

degree_level:
  "Bachelor" | "Master" | "PhD" | "Unknown"

eligible_nationals:
  "All" | "Non-EU" | specific group e.g. "Indian nationals" | "Unknown"

min_gpa:
  Use the program's stated scale e.g. "3.0/4.0" | "7.5/10" | "Unknown"

ielts_min / toefl_min:
  Numeric string e.g. "6.5" | "90" | "Unknown"

gre_required:
  "Yes" | "No" | "Unknown"

qs_ranking:
  "#50" | "Top 100" | "Unknown"
  Include only if clearly stated. Do NOT estimate.

acceptance_rate:
  "8%" | "Unknown"
  Include only if clearly stated. Do NOT estimate.

competitiveness:
  "High" | "Medium" | "Low" | "Unknown"

required_documents:
  List of strings e.g. ["Transcript", "Statement of Purpose", "Letter of Recommendation"]
  Use [] if not found.

application_requirements:
  List of strings e.g. ["GRE", "Portfolio", "Research Proposal", "Interview"]
  Use [] if not found.

intake:
  "Winter 2026" | "Fall 2026" | "Summer 2026" | "Unknown"

deadline:
  "January 15, 2026" | "Rolling" | "Unknown"

duration:
  "2 years" | "3 years" | "Unknown"

tuition:
  "€1,500/year" | "Free" | "€30,000/year" | "Unknown"

scholarships_available:
  "Yes" | "No" | "Unknown"

description:
  Full text snippet from the source. Include all useful detail found.
"""

    response = _call_gemini(prompt)
    return _parse_response(response)


# ---------------------------------------------------------------------------
# search_scholarships
# ---------------------------------------------------------------------------

def search_scholarships(query):

    prompt = f"""
Search the web for scholarships matching this query:

{query}

Return a JSON array of up to 5 results.
Each object must follow the EXACT schema below.
Every field must be present in every result.
Use "Unknown" for any missing string field.
Use [] for any missing list field.
Do NOT invent deadlines or funding amounts.
Return ONLY valid JSON. No markdown. No explanation.

Schema:

[
  {{
    "name":                   "",
    "provider":               "",
    "link":                   "",

    "source_type":            "",

    "eligible_nationalities": "",
    "eligible_degree_levels": "",
    "eligible_fields":        "",
    "max_age":                "",

    "min_gpa":                "",
    "scholarship_type":       "",

    "funding_amount":         "",
    "covers_tuition":         "",
    "covers_living":          "",
    "duration":               "",

    "required_documents":     [],

    "deadline":               "",
    "application_rounds":     "",

    "description":            ""
  }}
]

Field rules:

source_type:
  "official"           — foundation or university scholarship page
  "government"         — DAAD, ministry, embassy pages
  "scholarship_portal" — Scholars4Dev, ScholarshipPortal, Opportunitiescircle
  "unknown"            — cannot be determined

eligible_nationalities:
  "All" | "Developing countries" | "Indian nationals" | specific group | "Unknown"

eligible_degree_levels:
  "Bachelor" | "Master" | "PhD" | "All" | "Unknown"

eligible_fields:
  "STEM" | "All" | specific fields e.g. "Engineering, Computer Science" | "Unknown"

max_age:
  Numeric string e.g. "30" | "35" | "Unknown"

min_gpa:
  "3.5/4.0" | "First class" | "80%" | "Unknown"

scholarship_type:
  "Merit" | "Need-based" | "Both" | "Unknown"

funding_amount:
  "€850/month" | "Full tuition" | "$20,000/year" | "Unknown"

covers_tuition:
  "Yes" | "Partial" | "No" | "Unknown"

covers_living:
  "Yes" | "No" | "Unknown"

duration:
  "2 years" | "1 year" | "Program length" | "Unknown"

required_documents:
  List of strings e.g. ["CV", "Statement of Purpose", "Two Letters of Recommendation"]
  Use [] if not found.

deadline:
  Exact date if available | "Unknown"

application_rounds:
  "Annual" | "Twice/year" | "Rolling" | "Unknown"

description:
  Full text snippet. Include all eligibility details and conditions found.
"""

    response = _call_gemini(prompt)
    return _parse_response(response)


# ---------------------------------------------------------------------------
# search_jobs
# ---------------------------------------------------------------------------

def search_jobs(query):

    prompt = f"""
Search the web for job postings matching this query:

{query}

Return a JSON array of up to 5 results.
Each object must follow the EXACT schema below.
Every field must be present in every result.
Use "Unknown" for any missing string field.
Use [] for any missing list field.
Return ONLY valid JSON. No markdown. No explanation.

Schema:

[
  {{
    "title":            "",
    "company":          "",
    "location":         "",
    "link":             "",

    "source_type":      "",

    "visa_sponsorship": "",
    "degree_required":  "",
    "degree_field":     "",

    "required_skills":  [],
    "min_experience":   "",

    "role_level":       "",
    "employment_type":  "",
    "remote_option":    "",
    "salary":           "",

    "deadline":         "",
    "posted_date":      "",

    "description":      ""
  }}
]

Field rules:

source_type:
  "job_board" — LinkedIn, Indeed, Glassdoor, Naukri, Stepstone
  "official"  — company careers page
  "unknown"   — cannot be determined

visa_sponsorship:
  "Yes" | "No" | "Unknown"
  Only mark "No" if the posting explicitly states no sponsorship.

degree_required:
  "Bachelor" | "Master" | "PhD" | "Any" | "Unknown"

degree_field:
  e.g. "Computer Science" | "Engineering" | "Any" | "Unknown"

required_skills:
  List of strings e.g. ["Python", "Machine Learning", "SQL", "TensorFlow"]
  Extract all skills mentioned. Use [] if none stated.

min_experience:
  "Entry level" | "1 year" | "2 years" | "5 years" | "Unknown"

role_level:
  "Junior" | "Mid" | "Senior" | "Lead" | "Unknown"
  Infer from title or description if not explicitly stated.

employment_type:
  "Full-time" | "Part-time" | "Contract" | "Unknown"

remote_option:
  "Yes" | "Hybrid" | "No" | "Unknown"

salary:
  "€60,000–€80,000/year" | "$120,000/year" | "Unknown"

deadline:
  Exact date | "Unknown"
  Most jobs are rolling — use "Unknown" unless a close date is stated.

posted_date:
  "2 days ago" | "June 1, 2026" | "Unknown"

description:
  Full text snippet. Include responsibilities, requirements, and any benefits found.
"""

    response = _call_gemini(prompt)
    return _parse_response(response)


# ---------------------------------------------------------------------------
# search_internships
# ---------------------------------------------------------------------------

def search_internships(query):

    prompt = f"""
Search the web for internship opportunities matching this query:

{query}

Return a JSON array of up to 5 results.
Each object must follow the EXACT schema below.
Every field must be present in every result.
Use "Unknown" for any missing string field.
Use [] for any missing list field.
Return ONLY valid JSON. No markdown. No explanation.

Schema:

[
  {{
    "title":                  "",
    "company":                "",
    "location":               "",
    "link":                   "",

    "source_type":            "",

    "visa_sponsorship":       "",
    "eligible_degree_levels": "",
    "eligible_fields":        "",

    "required_skills":        [],
    "eligible_year":          "",

    "duration":               "",
    "stipend":                "",
    "remote_option":          "",
    "season":                 "",

    "deadline":               "",

    "description":            ""
  }}
]

Field rules:

source_type:
  "job_board" — LinkedIn, Indeed, Internshala, Glassdoor
  "official"  — company careers page
  "unknown"   — cannot be determined

visa_sponsorship:
  "Yes" | "No" | "Unknown"
  Only mark "No" if the posting explicitly states no sponsorship.

eligible_degree_levels:
  "Bachelor" | "Master" | "Any" | "Unknown"

eligible_fields:
  e.g. "Computer Science" | "STEM" | "Any" | "Unknown"

required_skills:
  List of strings e.g. ["Python", "Data Analysis", "TensorFlow", "Excel"]
  Extract all skills mentioned. Use [] if none stated.

eligible_year:
  "2nd year+" | "Final year" | "Any" | "Unknown"

duration:
  "3 months" | "6 months" | "12 months" | "Unknown"

stipend:
  "€1,200/month" | "$2,000/month" | "Unpaid" | "Unknown"

remote_option:
  "Yes" | "Hybrid" | "No" | "Unknown"

season:
  "Summer 2026" | "Winter 2026" | "Fall 2026" | "Rolling" | "Unknown"

deadline:
  Exact date | "Unknown"

description:
  Full text snippet. Include all eligibility and role details found.
"""

    response = _call_gemini(prompt)
    return _parse_response(response)