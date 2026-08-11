import datetime

from services.gap_analysis_agent import run_gap_analysis, GapAnalysisOutput, GapItem
from services.llm_mock import FakeLLMClient
from tests.conftest import FakeMCPClient


def _sample_output():
    return GapAnalysisOutput(
        completed=[GapItem(item="Passport", status="completed", evidence="passport in documents_merged",
                            reason="Required for visa", action="None", is_optional=False)],
        missing_critical=[GapItem(item="IELTS", status="missing_critical", evidence="No IELTS score in profile",
                                   reason="Required for English-taught MSc", action="Register for IELTS",
                                   is_optional=False)],
        missing_recommended=[], partial=[], gap_score=50,
        summary="Halfway there.", next_critical_action="Register for IELTS.",
        reasoning="Score computed from 1 of 2 requirements satisfied.",
    )


def _goal_analysis_doc():
    return {"analysis": {"goal_type": "Higher Studies", "destination": "Germany"},
            "raw_query": "goal", "query_hash": "hash1"}


async def test_fresh_cache_hit_skips_llm_call():
    fresh_doc = {
        "_id": "1", "user_id": "u1", "cache_key": "irrelevant", "query_hash": "hash1", "raw_query": "goal",
        "gap_analysis": {"gap_score": 80},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    mcp = FakeMCPClient(find_docs=[fresh_doc])
    llm = FakeLLMClient()

    result = await run_gap_analysis(
        user_id="u1", profile={}, goal_analysis_doc=_goal_analysis_doc(), mcp_client=mcp, llm_client=llm,
    )
    assert result["gap_analysis"]["gap_score"] == 80
    assert llm.calls == []


async def test_stale_cache_triggers_new_llm_call():
    stale_doc = {
        "_id": "1", "user_id": "u1", "cache_key": "irrelevant", "query_hash": "hash1", "raw_query": "goal",
        "gap_analysis": {"gap_score": 10},
        "created_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)).isoformat(),
    }
    mcp = FakeMCPClient(find_docs=[stale_doc])
    output = _sample_output()
    llm = FakeLLMClient(structured_responses={GapAnalysisOutput: output})

    result = await run_gap_analysis(
        user_id="u1", profile={}, goal_analysis_doc=_goal_analysis_doc(), mcp_client=mcp, llm_client=llm,
    )
    assert result["gap_analysis"]["gap_score"] == 50  # fresh LLM result, not the stale 10
    assert len(llm.calls) == 1


async def test_successful_run_includes_reasoning_and_persists():
    mcp = FakeMCPClient(find_docs=[])
    output = _sample_output()
    llm = FakeLLMClient(structured_responses={GapAnalysisOutput: output})

    doc = await run_gap_analysis(
        user_id="u1", profile={"meta": {"documents_merged": ["passport"]}},
        goal_analysis_doc=_goal_analysis_doc(), mcp_client=mcp, llm_client=llm,
    )
    assert doc["gap_analysis"]["reasoning"]
    assert mcp.session.inserted[0]["collection"] == "gap_analyses"
