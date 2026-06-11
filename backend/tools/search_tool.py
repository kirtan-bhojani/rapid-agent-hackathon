# backend/tools/search_tool.py
from services.gemini_service import client
from google.genai import types
import json
# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _is_recitation(response):
    """Check if the Gemini response was blocked due to RECITATION."""
    try:
        if response and response.candidates:
            finish_reason = response.candidates[0].finish_reason
            # finish_reason can be an enum or string depending on SDK version
            reason_str = str(finish_reason).upper()
            if "RECITATION" in reason_str:
                return True
    except Exception:
        pass
    return False
def _parse_response(response):
    if response is None:
        return {
            "error": "Gemini request failed",
            "raw": None
        }
    # --- RECITATION detection (before accessing .text) ---
    if _is_recitation(response):
        print("\nSEARCH AGENT: RECITATION BLOCKED")
        return {
            "error": "RECITATION_BLOCKED",
            "raw": str(response)
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
def _call_gemini_with_recitation_retry(prompt, retry_prompt):
    """
    Call Gemini with the primary prompt. If RECITATION is detected,
    retry ONCE with the stricter retry_prompt. Never retries more than once.
    """
    response = _call_gemini(prompt)
    if _is_recitation(response):
        print("SEARCH AGENT: RECITATION detected on first attempt — retrying with stricter prompt")
        response = _call_gemini(retry_prompt)
        if _is_recitation(response):
            print("SEARCH AGENT: RECITATION persisted after retry")
    return response
def _deduplicate_results(results, key_field):
    """
    Remove duplicate entries from a list of dicts based on a key field.
    Preserves order, keeps the first occurrence.
    """
    if not isinstance(results, list):
        return results
    seen = set()
    unique = []
    for item in results:
        if not isinstance(item, dict):
            unique.append(item)
            continue
        # Build a dedup key from the key field, lowercased and stripped
        val = item.get(key_field, "").strip().lower()
        if val and val != "unknown" and val in seen:
            continue
        if val and val != "unknown":
            seen.add(val)
        unique.append(item)
    return unique
def _merge_results(*result_lists, key_field):
    """
    Merge multiple Gemini result sets, skipping error dicts.
    Deduplicates by key_field.
    """
    merged = []
    for result in result_lists:
        if isinstance(result, list):
            merged.extend(result)
        # If it's an error dict, skip it silently
    return _deduplicate_results(merged, key_field)
# ---------------------------------------------------------------------------
# search_universities — MULTI-QUERY for broad coverage
# ---------------------------------------------------------------------------
def search_universities(query):
    # Build multiple sub-queries for broad coverage
    queries = _build_university_queries(query)
    all_results = []
    for sub_query in queries:
        prompt = _university_prompt(sub_query)
        response = _call_gemini(prompt)
        parsed = _parse_response(response)
        if isinstance(parsed, list):
            all_results.extend(parsed)
    merged = _deduplicate_results(all_results, "name")
    if not merged:
        # All queries failed — return last error
        return parsed if not isinstance(parsed, list) else {"error": "No results found"}
    return merged
def _build_university_queries(query):
    """
    Generate 3-4 sub-queries from the original query to maximize coverage.
    """
    return [
        query,
        f"Top ranked programs: {query}",
        f"Affordable and mid-tier programs: {query}",
        f"Public universities and technical institutions: {query}",
    ]
def _university_prompt(query):
    return f"""
Search the web for university degree programs matching this query:
{query}
Return a JSON array of upto 6 results. Prioritize BREADTH — include top-ranked,
mid-tier, and less competitive institutions from multiple countries/regions.
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
# ---------------------------------------------------------------------------
# search_scholarships — RECITATION-safe with retry + multi-query
# ---------------------------------------------------------------------------
def search_scholarships(query):
    queries = _build_scholarship_queries(query)
    all_results = []
    for sub_query in queries:
        prompt = _scholarship_prompt(sub_query)
        retry_prompt = _scholarship_retry_prompt(sub_query)
        response = _call_gemini_with_recitation_retry(prompt, retry_prompt)
        parsed = _parse_response(response)
        if isinstance(parsed, list):
            all_results.extend(parsed)
    merged = _deduplicate_results(all_results, "name")
    if not merged:
        return parsed if not isinstance(parsed, list) else {"error": "No results found"}
    return merged
def _build_scholarship_queries(query):
    """
    Generate sub-queries for broad scholarship coverage.
    """
    return [
        f"Government and DAAD scholarships: {query}",
        f"University-specific scholarships and funding: {query}",
        f"Foundation and private scholarships: {query}",
        f"Merit-based and need-based scholarships: {query}",
    ]
def _scholarship_prompt(query):
    return f"""
Search the web for scholarships matching this query:
{query}
IMPORTANT INSTRUCTIONS:
- Summarize and PARAPHRASE all information in your own words.
- NEVER copy eligibility criteria, requirements, or descriptions verbatim from sources.
- NEVER reproduce long passages from scholarship pages.
- Extract facts into the structured JSON fields below.
- Use concise, original wording for all text fields.
Return a JSON array of upto 10 results. Include government, university-specific,
foundation, and private scholarships. Include both merit-based and need-based.
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
  A BRIEF, ORIGINAL summary in your own words. Do NOT copy text from any source.
  Summarize the scholarship purpose, key requirements, and benefits in 2-3 sentences.
"""
def _scholarship_retry_prompt(query):
    """
    Stricter paraphrasing prompt used when the first attempt triggers RECITATION.
    """
    return f"""
Search the web for scholarships matching this query:
{query}
CRITICAL: You MUST write everything in your OWN words.
- Summarize eligibility requirements — do NOT quote source material.
- Describe funding in your own words — do NOT reproduce exact text from websites.
- Return ONLY structured facts in concise form.
- Every text field must be original paraphrasing, not copied.
Return a JSON array of 10 to 15 results.
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
- source_type: "official" | "government" | "scholarship_portal" | "unknown"
- eligible_nationalities: "All" | specific group | "Unknown"
- eligible_degree_levels: "Bachelor" | "Master" | "PhD" | "All" | "Unknown"
- eligible_fields: "STEM" | "All" | specific fields | "Unknown"
- max_age: numeric string | "Unknown"
- min_gpa: stated scale | "Unknown"
- scholarship_type: "Merit" | "Need-based" | "Both" | "Unknown"
- funding_amount: concise amount | "Unknown"
- covers_tuition: "Yes" | "Partial" | "No" | "Unknown"
- covers_living: "Yes" | "No" | "Unknown"
- duration: concise | "Unknown"
- required_documents: list of strings | []
- deadline: date | "Unknown"
- application_rounds: "Annual" | "Twice/year" | "Rolling" | "Unknown"
- description: 1-2 sentence ORIGINAL summary. Do NOT copy from any source.
"""
# ---------------------------------------------------------------------------
# search_jobs — MULTI-QUERY for broad coverage
# ---------------------------------------------------------------------------
def search_jobs(query):
    queries = _build_job_queries(query)
    all_results = []
    for sub_query in queries:
        prompt = _job_prompt(sub_query)
        response = _call_gemini(prompt)
        parsed = _parse_response(response)
        if isinstance(parsed, list):
            all_results.extend(parsed)
    merged = _deduplicate_results(all_results, "title")
    if not merged:
        return parsed if not isinstance(parsed, list) else {"error": "No results found"}
    return merged
def _build_job_queries(query):
    """
    Generate sub-queries for broad job coverage.
    """
    return [
        query,
        f"Entry level and junior positions: {query}",
        f"Startup and mid-size company jobs: {query}",
        f"Remote and hybrid opportunities: {query}",
    ]
def _job_prompt(query):
    return f"""
Search the web for job postings matching this query:
{query}
Return a JSON array of 15 to 20 results. Include opportunities from large companies,
mid-size firms, and startups. Include varied experience levels when available.
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
# ---------------------------------------------------------------------------
# search_internships — MULTI-QUERY for broad coverage
# ---------------------------------------------------------------------------
def search_internships(query):
    queries = _build_internship_queries(query)
    all_results = []
    for sub_query in queries:
        prompt = _internship_prompt(sub_query)
        response = _call_gemini(prompt)
        parsed = _parse_response(response)
        if isinstance(parsed, list):
            all_results.extend(parsed)
    merged = _deduplicate_results(all_results, "title")
    if not merged:
        return parsed if not isinstance(parsed, list) else {"error": "No results found"}
    return merged
def _build_internship_queries(query):
    """
    Generate sub-queries for broad internship coverage.
    """
    return [
        query,
        f"Research internships and academic programs: {query}",
        f"Industry and startup internships: {query}",
        f"Paid internships with stipend: {query}",
    ]
def _internship_prompt(query):
    return f"""
Search the web for internship opportunities matching this query:
{query}
Return a JSON array of 15 to 20 results. Include research internships,
industry internships, and startup opportunities. Cover multiple companies.
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
    return _parse_response(response)