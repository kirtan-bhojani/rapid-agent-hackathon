from typing import Dict, Any, List

from pydantic import BaseModel

from utils.mcp_helpers import find_latest


class ProgressUpdate(BaseModel):
    completed_step_id: int | None
    completed_step_title: str
    next_action: str
    reasoning: str      # WHY this step_id was matched to the user's free-text update


async def determine_progress(roadmap: List[Dict[str, Any]], update_text: str, llm_client: Any) -> Dict[str, Any]:
    import json

    prompt = f"""
    The user provided a progress update: "{update_text}"

    Here is their current roadmap:
    {json.dumps(roadmap, indent=2)}

    Identify which step_id the user is talking about, and mark its status as "Completed".
    Also provide a short encouraging message for the "next_action" based on the next pending step.
    Also provide a "reasoning" field: explain WHY you matched this step_id to the user's update
    (or why none matched, if completed_step_id is null).
    """
    output = await llm_client.generate_structured(prompt, ProgressUpdate)
    return output.model_dump()


async def run_progress_agent(user_id: str, update_text: str, mcp_client: Any, llm_client: Any) -> Dict[str, Any]:
    trace_logs = []

    print("[Progress Agent] Fetching current roadmap via MCP...")
    trace_logs.append({"type": "mcp", "message": f"Fetching active career plan for {user_id} from rapid.career_plans..."})

    plan = await find_latest(mcp_client, "rapid", "career_plans", {"user_id": user_id})

    if not plan:
        trace_logs.append({"type": "error", "message": "Career plan not found in database."})
        raise ValueError("Career plan not found")

    trace_logs.append({"type": "mcp", "message": "Successfully retrieved career plan."})

    print("[Progress Agent] Analyzing update with LLM...")
    trace_logs.append({"type": "agent", "message": f"Analyzing user update: '{update_text}' against current roadmap..."})

    progress = await determine_progress(plan["roadmap"], update_text, llm_client)

    completed_id = progress.get("completed_step_id")
    if completed_id is not None:
        trace_logs.append({"type": "agent", "message": f"Identified matching roadmap milestone: {progress.get('completed_step_title')}"})
        # Update roadmap state
        for step in plan["roadmap"]:
            if step["step_id"] == completed_id:
                step["status"] = "Completed"

        trace_logs.append({"type": "agent", "message": "Roadmap state updated in memory."})
        print("[Progress Agent] Persisting changes via MCP...")
        trace_logs.append({"type": "mcp", "message": "Persisting updated roadmap to rapid.career_plans using update-many..."})

        await mcp_client.session.call_tool("update-many", arguments={
            "database": "rapid",
            "collection": "career_plans",
            "filter": {"user_id": user_id},
            "update": {"$set": {"roadmap": plan["roadmap"]}}
        })
        trace_logs.append({"type": "mcp", "message": "Database update complete."})
        trace_logs.append({"type": "agent", "message": f"Next recommendation: {progress.get('next_action')}"})
    else:
        trace_logs.append({"type": "agent", "message": "No matching milestone found for this update."})
        progress["next_action"] = "I couldn't find a matching milestone. Keep up the good work!"

    return {
        "completed_step": progress.get("completed_step_title"),
        "next_step": progress.get("next_action"),
        "roadmap": plan["roadmap"],
        "trace_logs": trace_logs
    }
