"""
parser_service.py — Generalized document extraction layer.

Supports: resume | transcript | passport | ielts | sop | lor

Public API
──────────
    extract_pdf_text(pdf_path)                        — unchanged
    parse_resume_text(text)                           — unchanged (backward compat)
    parse_resume(pdf_path)                            — unchanged (backward compat)
    parse_document_text(document_type, text)          — NEW generic dispatcher
    process_document(document_type, pdf_path, user_id)— NEW generic pipeline
    process_resume(pdf_path, user_id)                 — unchanged (now a thin wrapper)
"""

from __future__ import annotations

import json
from pypdf import PdfReader

from services.gemini_service import client
from database import save_user_profile


# =====================================================================
#  SENSITIVE FIELDS — per document type
#  Any key listed here is routed to secure_vault instead of public_data
# =====================================================================

SENSITIVE_FIELDS: dict[str, set[str]] = {
    "resume": {
        "email",
        "phone",
        "address",
        "date_of_birth",
    },
    "transcript": {
        "date_of_birth",
        "student_id",
        "national_id",
    },
    "passport": {
        "passport_number",
        "date_of_birth",
        "national_id",
        "nationality",
        "mrz",
        "place_of_birth",
        "issue_date",
        "expiry_date",
    },
    "ielts": {
        "candidate_id",
        "date_of_birth",
        "passport_number",
        "test_date",
    },
    "sop": set(),           # SOPs carry no sensitive PII by nature
    "lor": set(),           # LORs carry no sensitive PII by nature
}

# =====================================================================
#  GEMINI PROMPTS — one per document type
# =====================================================================

_PROMPTS: dict[str, str] = {

    # ── Resume ────────────────────────────────────────────────────────
    "resume": """
You are a resume parser.
Extract information from the resume text below.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "name": "",
    "email": "",
    "phone": "",
    "address": "",

    "institution": "",
    "degree": "",
    "major": "",

    "education": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "extra_curriculars": [],
    "awards": [],
    "certifications": [],
    "languages": []
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "" or [].
- institution, degree and major should represent the applicant's current or most recent primary degree.

Resume:
{text}
""",

    # ── Transcript ────────────────────────────────────────────────────
    "transcript": """
You are an academic transcript parser.
Extract information from the transcript text below.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "student_name": "",
    "student_id": "",
    "institution": "",
    "degree": "",
    "major": "",
    "gpa": "",
    "total_credits": "",
    "graduation_date": "",
    "courses": [
        {{"code": "", "name": "", "grade": "", "credits": ""}}
    ]
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "" or [].

Transcript:
{text}
""",

    # ── Passport ──────────────────────────────────────────────────────
    "passport": """
You are a passport document parser.
Extract information from the passport text below.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "full_name": "",
    "passport_number": "",
    "nationality": "",
    "date_of_birth": "",
    "place_of_birth": "",
    "gender": "",
    "issue_date": "",
    "expiry_date": "",
    "issuing_country": "",
    "issuing_authority": "",
    "national_id": "",
    "mrz": ""
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "".

Passport text:
{text}
""",

    # ── IELTS ─────────────────────────────────────────────────────────
    "ielts": """
You are an IELTS score report parser.
Extract information from the IELTS report text below.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "candidate_name": "",
    "candidate_id": "",
    "passport_number": "",
    "date_of_birth": "",
    "test_date": "",
    "test_centre": "",
    "test_type": "",
    "overall_band": "",
    "listening": "",
    "reading": "",
    "writing": "",
    "speaking": "",
    "validity_expiry": ""
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "".

IELTS report:
{text}
""",

    # ── Statement of Purpose ──────────────────────────────────────────
    "sop": """
You are a Statement of Purpose (SOP) analyser.
Analyse the SOP text below and extract structured insights.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "applicant_name": "",
    "target_program": "",
    "target_university": "",
    "motivation_summary": "",
    "academic_background": "",
    "research_interests": [],
    "career_goals": "",
    "relevant_experience": [],
    "strengths_highlighted": [],
    "word_count": 0
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "" or [].
- "motivation_summary" should be a concise 1–2 sentence synthesis, not a copy-paste.

SOP:
{text}
""",

    # ── Letter of Recommendation ──────────────────────────────────────
    "lor": """
You are a Letter of Recommendation (LOR) analyser.
Analyse the LOR text below and extract structured insights.
Return ONLY valid JSON — no markdown, no explanation.

Format:
{{
    "applicant_name": "",
    "recommender_name": "",
    "recommender_title": "",
    "recommender_institution": "",
    "recommender_email": "",
    "relationship_to_applicant": "",
    "duration_known": "",
    "key_qualities": [],
    "academic_strengths": [],
    "personal_strengths": [],
    "recommendation_strength": "",
    "summary": ""
}}

Rules:
- Return only JSON.
- Do not use markdown or code fences.
- If a field is missing, use "" or [].
- "recommendation_strength" should be one of: "strong" | "moderate" | "weak".
- "summary" should be a concise 1–2 sentence synthesis, not a copy-paste.

LOR:
{text}
""",
}


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================

def _clean_json(raw: str) -> str:
    """Strip markdown code fences that Gemini sometimes wraps output in."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        cleaned = cleaned.split("\n", 1)[-1]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def _call_gemini(prompt: str) -> str:
    """Send a prompt to Gemini and return the raw text response."""
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )
    return response.text


def _parse_gemini_response(raw: str) -> dict:
    """Clean and JSON-parse a Gemini response. Returns error dict on failure."""
    try:
        return json.loads(_clean_json(raw))
    except Exception as exc:
        return {"error": str(exc), "raw": raw}


def _split_data(document_type: str, data: dict) -> tuple[dict, dict]:
    """
    Split extracted data into public and sensitive buckets based on
    the SENSITIVE_FIELDS mapping for the given document_type.
    """
    sensitive_keys = SENSITIVE_FIELDS.get(document_type, set())
    public_data: dict = {}
    sensitive_data: dict = {}

    for key, value in data.items():
        if key in sensitive_keys:
            sensitive_data[key] = value
        else:
            public_data[key] = value

    return public_data, sensitive_data


# =====================================================================
#  BACKWARD-COMPATIBLE FUNCTIONS (unchanged signatures)
# =====================================================================

def extract_pdf_text(pdf_path: str) -> str:
    """Extract raw text from every page of a PDF. Unchanged."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def parse_resume_text(text: str) -> str:
    """Call Gemini with the resume prompt and return raw response. Unchanged."""
    prompt = _PROMPTS["resume"].format(text=text)
    return _call_gemini(prompt)


def parse_resume(pdf_path: str) -> dict:
    """Extract text from PDF and parse as resume. Unchanged."""
    text = extract_pdf_text(pdf_path)
    raw = parse_resume_text(text)
    return _parse_gemini_response(raw)


# =====================================================================
#  NEW GENERIC API
# =====================================================================

def parse_document_text(document_type: str, text: str) -> dict:
    """
    Select the correct Gemini prompt for *document_type*, call the model,
    and return the parsed dict.

    Parameters
    ----------
    document_type : one of resume | transcript | passport | ielts | sop | lor
    text          : raw text already extracted from the PDF

    Returns
    -------
    Parsed dict on success, or {"error": ..., "raw": ...} on failure.
    """
    if document_type not in _PROMPTS:
        return {
            "error": f"No prompt defined for document type: '{document_type}'.",
            "raw": "",
        }

    prompt = _PROMPTS[document_type].format(text=text)
    raw = _call_gemini(prompt)
    return _parse_gemini_response(raw)


def process_document(document_type: str, pdf_path: str, user_id: str) -> dict:
    """
    Full extraction pipeline for any supported document type.

    Steps
    ─────
    1. Extract raw text from the PDF.
    2. Call parse_document_text() to get structured data from Gemini.
    3. Split into public / sensitive buckets.
    4. Save both buckets to MongoDB via save_user_profile().
    5. Return the full extracted data dict.

    Parameters
    ----------
    document_type : one of resume | transcript | passport | ielts | sop | lor
    pdf_path      : absolute or relative path to the uploaded PDF
    user_id       : identifier used as the MongoDB record key
    """
    # 1. Extract text
    text = extract_pdf_text(pdf_path)

    # 2. Parse via Gemini
    data = parse_document_text(document_type, text)

    # NEW: stop if Gemini failed
    if "error" in data:
        return data
    
    # 3. Split public / sensitive
    public_data, sensitive_data = _split_data(document_type, data)

    # 4. Persist — tag the document type so records are queryable later
    public_data["document_type"] = document_type
    save_user_profile(user_id, public_data, sensitive_data)

    # 5. Return full data to caller
    return data


# =====================================================================
#  BACKWARD-COMPATIBLE WRAPPER
# =====================================================================

def process_resume(pdf_path: str, user_id: str) -> dict:
    """
    Thin wrapper around process_document() for backward compatibility.
    All existing calls to process_resume() continue to work unchanged.
    """
    return process_document("resume", pdf_path, user_id)