"""
profile_service.py — Profile Agent

Aggregates all extracted document records for a user into a single
unified profile, persists it in MongoDB, and exposes a retrieval function.

Public API
──────────
    build_unified_profile(user_id) → dict
        Fetches all public_data.profiles records for user_id,
        merges them into a unified schema, upserts into unified_profiles,
        and returns the result.

    get_unified_profile(user_id) → dict | None
        Returns the pre-built unified profile from unified_profiles,
        or None if it has not been built yet.
"""

from __future__ import annotations

from datetime import datetime, timezone

from database import (
    get_all_user_documents,
    upsert_unified_profile,
    fetch_unified_profile,
)


# =====================================================================
#  MERGE HELPERS — one per document type
#  Each helper receives the unified profile dict (mutates it in-place)
#  and the raw MongoDB document for that type.
#  Helpers are intentionally defensive: missing keys never raise.
# =====================================================================

def _merge_resume(profile: dict, doc: dict) -> None:
    """Merge resume fields into personal, academic, and professional sections."""

    # personal — name only (resume rarely has nationality/DOB)
    personal = profile["personal"]
    if not personal["full_name"]:
        personal["full_name"] = doc.get("name", "")

    # professional
    prof = profile["professional"]
    if not prof["skills"]:
        prof["skills"] = doc.get("skills", [])
    if not prof["experience"]:
        prof["experience"] = doc.get("experience", [])
    if not prof["projects"]:
        prof["projects"] = doc.get("projects", [])

    #academic
    academic = profile["academic"]
    if not academic["institution"]:
        academic["institution"] = doc.get("institution", "")
    if not academic["degree"]:
        academic["degree"] = doc.get("degree", "")
    if not academic["major"]:
        academic["major"] = doc.get("major", "")
    if not academic["gpa"]:
        academic["gpa"] = doc.get("gpa", "")
    if not academic["education"]:
        academic["education"] = doc.get("education", "")

def _merge_transcript(profile: dict, doc: dict) -> None:
    """Merge transcript fields into the academic section."""

    academic = profile["academic"]

    if doc.get("institution"):
        academic["institution"] = doc["institution"]
    if doc.get("degree"):
        academic["degree"] = doc["degree"]
    if doc.get("major"):
        academic["major"] = doc["major"]
    if doc.get("gpa"):
        academic["gpa"] = doc["gpa"]
    if doc.get("graduation_date"):
        academic["graduation_date"] = doc["graduation_date"]
    if doc.get("courses"):
        academic["courses"] = doc["courses"]

    # Transcript may also carry the student's name
    personal = profile["personal"]
    if not personal["full_name"]:
        personal["full_name"] = doc.get("student_name", "")


def _merge_passport(profile: dict, doc: dict) -> None:
    """Merge passport fields into the personal section."""

    personal = profile["personal"]

    if not personal["full_name"]:
        personal["full_name"] = doc.get("full_name", "")
    if not personal["nationality"]:
        personal["nationality"] = doc.get("nationality", "")
    if not personal["date_of_birth"]:
        personal["date_of_birth"] = doc.get("date_of_birth", "")


def _merge_ielts(profile: dict, doc: dict) -> None:
    """Merge IELTS fields into language_tests.ielts."""

    profile["language_tests"]["ielts"] = {
        "overall_band":   doc.get("overall_band", ""),
        "listening":      doc.get("listening", ""),
        "reading":        doc.get("reading", ""),
        "writing":        doc.get("writing", ""),
        "speaking":       doc.get("speaking", ""),
        "test_date":      doc.get("test_date", ""),
        "validity_expiry": doc.get("validity_expiry", ""),
        "test_type":      doc.get("test_type", ""),
    }


def _merge_sop(profile: dict, doc: dict) -> None:
    """Merge SOP fields into application_materials."""

    materials = profile["application_materials"]

    if not materials["sop_summary"]:
        materials["sop_summary"] = doc.get("motivation_summary", "")

    # Enrich personal name if still missing
    personal = profile["personal"]
    if not personal["full_name"]:
        personal["full_name"] = doc.get("applicant_name", "")


def _merge_lor(profile: dict, doc: dict) -> None:
    """Append an LOR summary entry to application_materials.lor_summaries."""

    entry = {
        "recommender_name":        doc.get("recommender_name", ""),
        "recommender_title":       doc.get("recommender_title", ""),
        "recommender_institution": doc.get("recommender_institution", ""),
        "relationship":            doc.get("relationship_to_applicant", ""),
        "recommendation_strength": doc.get("recommendation_strength", ""),
        "summary":                 doc.get("summary", ""),
    }
    profile["application_materials"]["lor_summaries"].append(entry)


# Registry — maps document_type → merge helper
# Adding support for a new document type means adding one entry here.
_MERGE_HANDLERS: dict[str, callable] = {
    "resume":     _merge_resume,
    "transcript": _merge_transcript,
    "passport":   _merge_passport,
    "ielts":      _merge_ielts,
    "sop":        _merge_sop,
    "lor":        _merge_lor,
}


# =====================================================================
#  BLANK PROFILE FACTORY
# =====================================================================

def _blank_profile(user_id: str) -> dict:
    """Return an empty unified profile skeleton for *user_id*."""
    return {
        "user_id": user_id,
        "personal": {
            "full_name":     "",
            "nationality":   "",
            "date_of_birth": "",
        },
        "academic": {
            "institution":     "",
            "degree":          "",
            "major":           "",
            "gpa":             "",
            "graduation_date": "",
            "courses":         [],
            "education":       [],
        },
        "professional": {
            "skills":     [],
            "experience": [],
            "projects":   [],
        },
        "language_tests": {
            "ielts": {},
        },
        "application_materials": {
            "sop_summary":   "",
            "lor_summaries": [],
        },
        "meta": {
            "documents_merged": [],
            "last_built_at":    "",
        },
    }


# =====================================================================
#  PUBLIC API
# =====================================================================

def build_unified_profile(user_id: str) -> dict:
    """
    Aggregate all extracted documents for *user_id* into a single profile.

    Steps
    ─────
    1. Fetch every record from public_data.profiles where user_id matches.
    2. For each record, call the matching merge helper (if one exists).
    3. Upsert the result into unified_profiles.
    4. Return the unified profile.

    Never raises on missing document types — absent types are simply skipped.
    """

    # 1. Fetch all raw documents for this user
    documents = get_all_user_documents(user_id)

    # 2. Start with a blank profile
    profile = _blank_profile(user_id)
    merged_types: list[str] = []

    # 3. Merge each document into the profile
    for doc in documents:
        doc_type = doc.get("document_type", "")
        handler = _MERGE_HANDLERS.get(doc_type)

        if handler:
            handler(profile, doc)
            if doc_type not in merged_types:
                merged_types.append(doc_type)

    # 4. Record metadata
    profile["meta"]["documents_merged"] = merged_types
    profile["meta"]["last_built_at"] = datetime.now(timezone.utc).isoformat()

    # 5. Upsert into unified_profiles
    upsert_unified_profile(user_id, profile)

    return profile


def get_unified_profile(user_id: str) -> dict | None:
    """
    Return the pre-built unified profile from unified_profiles.

    Returns None if build_unified_profile() has never been called
    for this user_id.
    """
    return fetch_unified_profile(user_id)