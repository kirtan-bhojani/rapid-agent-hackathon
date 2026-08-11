from services.opportunity_service import generate_queries, _cache_key_for_goal, classify_opportunities
from services.llm_mock import FakeLLMClient


def test_generate_queries_never_includes_unknown():
    goal = {"goal_type": "Higher Studies", "degree": "Unknown", "field": "Unknown", "country": "Germany"}
    queries = generate_queries(goal)
    assert "Unknown" not in queries["universities"]
    assert "Germany" in queries["universities"]


def test_generate_queries_job_type():
    goal = {"goal_type": "Job", "target_role": "Embedded Engineer", "country": "Germany"}
    queries = generate_queries(goal)
    assert queries == {"jobs": "Embedded Engineer jobs Germany"}


def test_cache_key_is_deterministic_and_goal_sensitive():
    goal_a = {"goal_type": "Job", "field": "ECE", "degree": "N/A", "country": "Germany"}
    goal_b = {"goal_type": "Job", "field": "ECE", "degree": "N/A", "country": "France"}
    assert _cache_key_for_goal(goal_a) == _cache_key_for_goal(goal_a)
    assert _cache_key_for_goal(goal_a) != _cache_key_for_goal(goal_b)


async def test_classify_opportunities_returns_empty_shape_on_llm_error():
    def _raise(*a, **kw):
        raise RuntimeError("simulated outage")
    llm = FakeLLMClient(text_fn=_raise)

    result = await classify_opportunities({"jobs": []}, profile={}, goal={}, llm_client=llm)
    assert result["eligible"] == {"safe": [], "target": [], "ambitious": []}
    assert "error" in result


async def test_classify_opportunities_parses_reasoning_field():
    import json
    fixture = {
        "eligible": {"safe": [], "target": [{"title": "Job A", "status": "target", "fit_reason": "fits",
                                              "known_gaps": [], "unknown_requirements": [], "gap_summary": ""}],
                     "ambitious": []},
        "growth": {"near_eligible": [], "long_term_stretch": []},
        "excluded_count": 0,
        "reasoning": "One target-tier job matched the profile.",
    }
    llm = FakeLLMClient(text=json.dumps(fixture))
    result = await classify_opportunities({"jobs": [{"title": "Job A"}]}, profile={}, goal={}, llm_client=llm)
    assert result["reasoning"] == "One target-tier job matched the profile."
    assert len(result["eligible"]["target"]) == 1
