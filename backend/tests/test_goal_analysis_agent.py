import datetime

from services.goal_analysis_agent import run_goal_analysis, GoalAnalysisOutput, RequirementItem
from services.llm_mock import FakeLLMClient
from tests.conftest import FakeMCPClient


def _sample_output():
    req = RequirementItem(item="IELTS", detail="Band 6.5+", is_optional=False, reasoning="Required for English-taught MSc.")
    return GoalAnalysisOutput(
        goal_type="Higher Studies", destination="Germany", field="Microelectronics", degree="MSc",
        target_role="", timeline="Fall 2026", raw_query="Master's in Germany in Microelectronics",
        required_qualifications=[], required_exams=[req], required_documents=[], financial_requirements=[],
        visa_requirements=[], language_requirements=[], experience_expectations=[], application_requirements=[],
        scholarships=[], additional_notes=[],
        reasoning="Based on standard German MSc admission patterns for this field.",
    )


async def test_cache_hit_skips_llm_call():
    """A fresh cached doc should be returned without ever touching the LLM."""
    cached_doc = {
        "_id": "1", "user_id": "u1", "query_hash": "irrelevant", "raw_query": "goal",
        "analysis": {"goal_type": "Higher Studies"},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    mcp = FakeMCPClient(find_docs=[cached_doc])
    llm = FakeLLMClient()  # no responses configured — would KeyError if called

    result = await run_goal_analysis(
        user_id="u1", raw_query="goal", profile={}, mcp_client=mcp, llm_client=llm,
    )
    assert result["analysis"]["goal_type"] == "Higher Studies"
    assert llm.calls == []


async def test_successful_run_stores_reasoning_and_persists():
    mcp = FakeMCPClient(find_docs=[])  # cache miss
    output = _sample_output()
    llm = FakeLLMClient(structured_responses={GoalAnalysisOutput: output})

    doc = await run_goal_analysis(
        user_id="u1", raw_query="Master's in Germany in Microelectronics",
        profile={"academic": {}}, mcp_client=mcp, llm_client=llm,
    )

    assert doc["analysis"]["reasoning"]
    assert doc["analysis"]["required_exams"][0]["reasoning"]
    assert mcp.session.inserted, "expected the analysis to be persisted via insert-many"
    assert mcp.session.inserted[0]["collection"] == "goal_analyses"


async def test_llm_error_returns_safe_placeholder_not_fabricated_data():
    mcp = FakeMCPClient(find_docs=[])

    def _raise(*a, **kw):
        raise RuntimeError("simulated LLM outage")

    llm = FakeLLMClient(structured_fn=_raise)

    doc = await run_goal_analysis(
        user_id="u1", raw_query="Master's in Germany", profile={}, mcp_client=mcp, llm_client=llm,
    )
    analysis = doc["analysis"]
    assert analysis["destination"] == "Unknown"
    assert analysis["required_exams"] == []
    assert "failed" in analysis["additional_notes"][0].lower()
