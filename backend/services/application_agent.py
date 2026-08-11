"""
application_agent.py — Application Assistant Agent

Produces an "Application Readiness Report": the user pastes the field labels
from a real application form (no browser extension — most university sites
block automated form-filling anyway, so this is deliberately a manual-paste
assist tool, not live-site automation). The agent maps each field against the
user's stored unified profile and reports what can be autofilled (with the
value, for the user to copy-paste themselves), what's missing, what document
is needed, or what warning applies (e.g. an expiring passport).

Public API
──────────
    run_application_readiness(user_id, raw_text, profile, mcp_client, llm_client) → dict
        Runs the full readiness pipeline. Stores result in MongoDB. Returns
        the application_reports document.

    get_cached_application_report(user_id, mcp_client) → dict | None
        Returns the latest stored report for a user, or None.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from utils.mcp_helpers import find_latest


# =====================================================================
#  PYDANTIC MODELS
# =====================================================================

class FieldLabelList(BaseModel):
    labels: List[str]


class FieldResult(BaseModel):
    field_label: str              # verbatim, as the user pasted it
    status: str                   # "can_autofill" | "missing" | "missing_document" | "warning"
    value: Optional[str] = None   # the value to copy-paste, only when can_autofill
    profile_path: Optional[str] = None   # e.g. "personal.full_name" — traceability
    message: str                  # human-readable explanation shown in the UI
    reasoning: str                # WHY this classification/value was chosen
    action_needed: Optional[str] = None  # e.g. "Upload passport in Documents", "Retake IELTS"


class ApplicationReadinessOutput(BaseModel):
    fields: List[FieldResult]
    can_autofill_count: int
    missing_count: int
    missing_document_count: int
    warning_count: int
    estimated_completion_pct: int   # 0-100
    overall_reasoning: str          # top-level summary — the report's headline explainability field


# =====================================================================
#  FIELD LABEL SEGMENTATION — heuristic first, LLM fallback
# =====================================================================

def _heuristic_split(raw_text: str) -> List[str]:
    """Split on newlines/commas, strip, drop empties."""
    parts: List[str] = []
    for line in raw_text.replace(",", "\n").splitlines():
        label = line.strip().strip("*").strip("-").strip()
        if label:
            parts.append(label)
    return parts


def _looks_like_prose(labels: List[str]) -> bool:
    """True if the heuristic split likely failed (e.g. the user pasted a
    paragraph of prose/OCR text rather than a clean field-label list)."""
    if len(labels) < 2:
        return True
    return any(len(label) > 60 for label in labels)


async def _segment_field_labels(raw_text: str, llm_client: Any) -> List[str]:
    labels = _heuristic_split(raw_text)
    if not _looks_like_prose(labels):
        return labels

    prompt = f"""
Extract every distinct application form field label from the text below.
The text may be messy (pasted prose, OCR output, or a mix of labels and
instructions). Return only the field labels themselves (e.g. "Full Name",
"Passport Number", "IELTS Overall Score"), one per entry, no duplicates.

TEXT:
{raw_text}
"""
    try:
        output = await llm_client.generate_structured(prompt, FieldLabelList)
        return output.labels
    except Exception as e:
        print(f"[ApplicationAgent] Field segmentation LLM error: {e}")
        return labels  # fall back to whatever the heuristic produced


# =====================================================================
#  DATE-FACT PRECOMPUTATION — never ask the LLM to do date arithmetic
# =====================================================================

def _parse_date(value: str) -> Optional[datetime.date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _compute_date_facts(profile: Dict[str, Any]) -> Dict[str, Any]:
    today = datetime.date.today()
    facts: Dict[str, Any] = {"today": today.isoformat()}

    passport_expiry = _parse_date(profile.get("personal", {}).get("passport_expiry_date", ""))
    if passport_expiry:
        facts["passport_expiry_date"] = passport_expiry.isoformat()
        facts["passport_days_until_expiry"] = (passport_expiry - today).days

    ielts_expiry = _parse_date(profile.get("language_tests", {}).get("ielts", {}).get("validity_expiry", ""))
    if ielts_expiry:
        facts["ielts_validity_expiry"] = ielts_expiry.isoformat()
        facts["ielts_days_until_expiry"] = (ielts_expiry - today).days

    return facts


# =====================================================================
#  PROMPT
# =====================================================================

_READINESS_PROMPT = """
You are RAPID's Application Assistant Agent.

The user pasted these field labels from a real application form:
{field_labels}

Here is their full stored profile:
{profile_json}

Precomputed date facts (already calculated in Python — trust these, do NOT
recompute any date arithmetic yourself):
{date_facts_json}

For EACH field label, classify it into exactly one status:
  - "can_autofill"     — a value exists in the profile for this field. Provide
                          the exact "value" to copy-paste and the "profile_path"
                          (dot notation, e.g. "personal.full_name") it came from.
  - "missing"           — no document/value exists in the profile for this yet,
                          and no document upload would fix it (e.g. a free-text
                          essay, an application-specific answer).
  - "missing_document"  — the value depends on a document the user hasn't
                          uploaded yet (e.g. passport, IELTS, transcript). Set
                          action_needed to name the document.
  - "warning"           — a value exists but there's a problem with it — e.g.
                          the passport/IELTS validity is expiring too soon
                          relative to what the field/context implies. Use the
                          precomputed date facts for this; state the concrete
                          day count in your message.

RULES:
1. Match field labels to profile data by meaning, not exact string match
   (e.g. "Applicant Full Name" matches profile.personal.full_name).
2. Never fabricate a value. If it's not in the profile, it's "missing" or
   "missing_document", never "can_autofill".
3. For any date-validity concern (passport expiry, IELTS validity), use ONLY
   the precomputed date facts above — never estimate or recompute dates yourself.
4. "reasoning": one sentence on WHY this field got this classification.
5. "message": a short, user-facing explanation (e.g. "Passport expires in 143
   days — check the destination's minimum validity requirement.").
6. estimated_completion_pct: round(can_autofill_count / total_fields * 100).
7. overall_reasoning: 1-2 sentences summarizing the overall readiness picture.

Return a result for EVERY field label provided. Do not omit or merge any.
"""


def _fmt_field_labels(labels: List[str]) -> str:
    return "\n".join(f"  - {label}" for label in labels)


# =====================================================================
#  PUBLIC API
# =====================================================================

def _cache_key(user_id: str, raw_text: str, profile: Dict[str, Any]) -> str:
    last_built_at = profile.get("meta", {}).get("last_built_at", "")
    return hashlib.md5(f"{user_id}:{raw_text}:{last_built_at}".encode()).hexdigest()


async def get_cached_application_report(user_id: str, mcp_client: Any) -> Optional[Dict[str, Any]]:
    """Return the latest stored application readiness report for user_id, or None."""
    return await find_latest(mcp_client, "rapid", "application_reports", {"user_id": user_id})


async def run_application_readiness(
    user_id: str,
    raw_text: str,
    profile: Dict[str, Any],
    mcp_client: Any,
    llm_client: Any,
) -> Dict[str, Any]:
    """
    Run the Application Readiness pipeline.

    Steps:
    1. Segment raw_text into field labels (heuristic, LLM fallback).
    2. Check cache (invalidates whenever the profile is rebuilt).
    3. Precompute date facts in Python (passport/IELTS expiry).
    4. Call the LLM once with labels + profile + date facts.
    5. Store result in MongoDB application_reports.
    6. Return the report document.
    """
    import json

    cache_key = _cache_key(user_id, raw_text, profile)
    cached = await find_latest(mcp_client, "rapid", "application_reports", {"user_id": user_id, "cache_key": cache_key})
    if cached:
        print(f"[ApplicationAgent] Cache hit for user {user_id}")
        return cached

    field_labels = await _segment_field_labels(raw_text, llm_client)
    date_facts = _compute_date_facts(profile)

    prompt = _READINESS_PROMPT.format(
        field_labels=_fmt_field_labels(field_labels),
        profile_json=json.dumps(profile, indent=2),
        date_facts_json=json.dumps(date_facts, indent=2),
    )

    print(f"[ApplicationAgent] Calling LLM for user {user_id} ({len(field_labels)} fields)")

    try:
        output = await llm_client.generate_structured(prompt, ApplicationReadinessOutput)
        report_data = output.model_dump()
    except Exception as e:
        print(f"[ApplicationAgent] LLM error: {e}")
        report_data = {
            "fields": [
                {
                    "field_label": label, "status": "missing", "value": None, "profile_path": None,
                    "message": "Could not be analyzed due to an error. Please try again.",
                    "reasoning": "Application readiness analysis failed due to an LLM error.",
                    "action_needed": None,
                }
                for label in field_labels
            ],
            "can_autofill_count": 0,
            "missing_count": len(field_labels),
            "missing_document_count": 0,
            "warning_count": 0,
            "estimated_completion_pct": 0,
            "overall_reasoning": "Application readiness analysis could not be completed; this is a placeholder, not an analyzed result.",
        }

    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "cache_key": cache_key,
        "raw_text": raw_text,
        "report": report_data,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        await mcp_client.session.call_tool("insert-many", arguments={
            "database": "rapid",
            "collection": "application_reports",
            "documents": [doc],
        })
        print(f"[ApplicationAgent] Stored report for user {user_id}")
    except Exception as e:
        print(f"[ApplicationAgent] Storage error: {e}")

    return doc
