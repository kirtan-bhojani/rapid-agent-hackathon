import datetime

from services.application_agent import (
    _heuristic_split, _looks_like_prose, _compute_date_facts,
    run_application_readiness, ApplicationReadinessOutput, FieldResult,
)
from services.llm_mock import FakeLLMClient
from tests.conftest import FakeMCPClient


def test_heuristic_split_handles_newlines_and_commas():
    assert _heuristic_split("Full Name\nEmail, Passport Number") == ["Full Name", "Email", "Passport Number"]


def test_looks_like_prose_flags_long_single_blob():
    assert _looks_like_prose(["This is a very long sentence that looks like pasted prose, not a field label at all really"])
    assert not _looks_like_prose(["Full Name", "Email", "Passport Number"])


def test_compute_date_facts_never_fabricates_missing_dates():
    facts = _compute_date_facts({"personal": {}, "language_tests": {"ielts": {}}})
    assert "passport_days_until_expiry" not in facts
    assert "ielts_days_until_expiry" not in facts


def test_compute_date_facts_computes_real_day_count():
    expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
    facts = _compute_date_facts({"personal": {"passport_expiry_date": expiry}, "language_tests": {"ielts": {}}})
    assert facts["passport_days_until_expiry"] == 100


def _sample_output():
    return ApplicationReadinessOutput(
        fields=[
            FieldResult(field_label="Full Name", status="can_autofill", value="Priya Sharma",
                        profile_path="personal.full_name", message="Found in profile.",
                        reasoning="Full name is present in the profile."),
            FieldResult(field_label="IELTS Score", status="missing_document", value=None,
                        profile_path=None, message="No IELTS uploaded.",
                        reasoning="IELTS data is absent from the profile.", action_needed="Upload IELTS report"),
        ],
        can_autofill_count=1, missing_count=0, missing_document_count=1, warning_count=0,
        estimated_completion_pct=50, overall_reasoning="Half the fields are ready.",
    )


async def test_run_application_readiness_caches_by_profile_state():
    mcp = FakeMCPClient(find_docs=[])
    llm = FakeLLMClient(structured_responses={ApplicationReadinessOutput: _sample_output()})
    profile = {"personal": {"full_name": "Priya Sharma"}, "language_tests": {"ielts": {}},
               "meta": {"last_built_at": "2026-08-01T00:00:00+00:00"}}

    doc = await run_application_readiness("u1", "Full Name\nIELTS Score", profile, mcp, llm)

    assert doc["report"]["can_autofill_count"] == 1
    assert mcp.session.inserted[0]["collection"] == "application_reports"


async def test_cache_hit_skips_llm_call():
    cached_doc = {
        "_id": "1", "user_id": "u1", "cache_key": "will-not-match-but-thats-ok-for-this-test",
        "raw_text": "Full Name", "report": {"can_autofill_count": 1},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    mcp = FakeMCPClient(find_docs=[cached_doc])
    llm = FakeLLMClient()  # would KeyError if called

    doc = await run_application_readiness("u1", "Full Name", {"meta": {}}, mcp, llm)
    assert doc["report"]["can_autofill_count"] == 1
    assert llm.calls == []
