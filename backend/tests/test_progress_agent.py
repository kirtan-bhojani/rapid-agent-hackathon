import datetime

import pytest

from services.progress_agent import run_progress_agent, ProgressUpdate
from services.llm_mock import FakeLLMClient
from tests.conftest import FakeMCPClient


def _plan_doc():
    return {
        "user_id": "u1",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "roadmap": [
            {"step_id": 1, "title": "Register for IELTS", "status": "Pending"},
            {"step_id": 2, "title": "Prepare SOP", "status": "Pending"},
        ],
    }


async def test_matching_step_marked_completed_and_persisted():
    mcp = FakeMCPClient(find_docs=[_plan_doc()])
    update = ProgressUpdate(completed_step_id=1, completed_step_title="Register for IELTS",
                             next_action="Great, now work on your SOP!",
                             reasoning="The user explicitly said they booked their IELTS exam.")
    llm = FakeLLMClient(structured_responses={ProgressUpdate: update})

    result = await run_progress_agent("u1", "I booked my IELTS exam", mcp, llm)

    assert result["completed_step"] == "Register for IELTS"
    assert mcp.session.updated, "expected update-many to persist the completed step"
    updated_roadmap = mcp.session.updated[0]["update"]["$set"]["roadmap"]
    assert updated_roadmap[0]["status"] == "Completed"
    assert updated_roadmap[1]["status"] == "Pending"


async def test_no_match_does_not_persist():
    mcp = FakeMCPClient(find_docs=[_plan_doc()])
    update = ProgressUpdate(completed_step_id=None, completed_step_title="", next_action="",
                             reasoning="Nothing in the update matched a roadmap step.")
    llm = FakeLLMClient(structured_responses={ProgressUpdate: update})

    result = await run_progress_agent("u1", "just saying hi", mcp, llm)

    assert not mcp.session.updated
    assert "couldn't find" in result["next_step"].lower()


async def test_missing_plan_raises():
    mcp = FakeMCPClient(find_docs=[])
    llm = FakeLLMClient()
    with pytest.raises(ValueError):
        await run_progress_agent("u1", "anything", mcp, llm)
