from services.career_pipeline import generate_justified_roadmap, run_career_pipeline, RoadmapList, RoadmapStep
from services.llm_mock import FakeLLMClient
from tests.conftest import FakeMCPClient


def _sample_roadmap_list():
    return RoadmapList(steps=[
        RoadmapStep(step_id=1, title="Register for IELTS", description="Book the exam.",
                    reason="Addresses missing IELTS gap", reasoning="Time-sensitive, must happen first.",
                    estimated_effort="30 minutes", dependencies=[], priority="critical",
                    deadline_hint="Before September 2026", status="Pending"),
        RoadmapStep(step_id=2, title="Prepare SOP", description="Draft motivation letter.",
                    reason="Addresses missing SOP gap", reasoning="Can run in parallel with IELTS prep.",
                    estimated_effort="1 week", dependencies=[], priority="high",
                    deadline_hint="No fixed deadline", status="Pending"),
    ])


async def test_generate_justified_roadmap_unwraps_list_and_keeps_reasoning():
    llm = FakeLLMClient(structured_responses={RoadmapList: _sample_roadmap_list()})
    roadmap = await generate_justified_roadmap(
        goal_analysis={"destination": "Germany"}, gap_data={"missing_critical": []}, raw_query="goal",
        llm_client=llm,
    )
    assert len(roadmap) == 2
    assert roadmap[0]["reasoning"] == "Time-sensitive, must happen first."
    assert roadmap[0]["reason"] == "Addresses missing IELTS gap"


async def test_generate_justified_roadmap_returns_empty_on_llm_error():
    def _raise(*a, **kw):
        raise RuntimeError("simulated outage")
    llm = FakeLLMClient(structured_fn=_raise)
    roadmap = await generate_justified_roadmap(
        goal_analysis={}, gap_data={}, raw_query="goal", llm_client=llm,
    )
    assert roadmap == []


async def test_run_career_pipeline_persists_plan():
    mcp = FakeMCPClient()
    llm = FakeLLMClient(structured_responses={RoadmapList: _sample_roadmap_list()})

    result = await run_career_pipeline(
        user_id="u1", query="goal", profile={}, mcp_client=mcp, llm_client=llm,
        goal_analysis_doc={"analysis": {"goal_type": "Higher Studies", "destination": "Germany"}},
        gap_analysis_doc={"gap_analysis": {"gap_score": 40, "missing_critical": []}},
    )
    assert len(result["data"]["roadmap"]) == 2
    assert mcp.session.inserted[0]["collection"] == "career_plans"
