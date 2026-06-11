import json
import re
from typing import Dict, Any, List
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def clean_json(text: str) -> str:
    text = text.strip()
    start = -1
    for i, char in enumerate(text):
        if char in '[{':
            start = i
            break
    end = -1
    for i in range(len(text)-1, -1, -1):
        if text[i] in ']}':
            end = i
            break
            
    if start != -1 and end != -1 and start <= end:
        return text[start:end+1]
    return text

async def determine_progress(roadmap: List[Dict[str, Any]], update_text: str) -> Dict[str, Any]:
    prompt = f"""
    The user provided a progress update: "{update_text}"
    
    Here is their current roadmap:
    {json.dumps(roadmap, indent=2)}
    
    Identify which step_id the user is talking about, and mark its status as "Completed".
    Also provide a short encouraging message for the "next_action" based on the next pending step.
    
    Return ONLY valid JSON with exactly these fields:
    - completed_step_id (integer, or null if no match found)
    - completed_step_title (string)
    - next_action (string)
    """
    res = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return json.loads(clean_json(res.text))

async def run_progress_agent(user_id: str, update_text: str, mcp_client: Any) -> Dict[str, Any]:
    trace_logs = []
    
    print("[Progress Agent] Fetching current roadmap via MCP...")
    trace_logs.append({"type": "mcp", "message": f"Fetching active career plan for {user_id} from rapid.career_plans..."})
    
    result = await mcp_client.session.call_tool("find", arguments={
        "database": "rapid",
        "collection": "career_plans",
        "filter": {"user_id": user_id}
    })
    
    all_plans = []
    for c in result.content:
        if c.type == "text":
            text = c.text
            start = -1
            for i, char in enumerate(text):
                if char in '[{':
                    start = i
                    break
            end = -1
            for i in range(len(text)-1, -1, -1):
                if text[i] in ']}':
                    end = i
                    break
            if start != -1 and end != -1 and start < end:
                try:
                    parsed = json.loads(text[start:end+1])
                    if isinstance(parsed, list) and len(parsed) > 0:
                        all_plans.extend(parsed)
                    elif isinstance(parsed, dict) and "user_id" in parsed:
                        all_plans.append(parsed)
                except Exception:
                    pass
    
    plan = None
    if all_plans:
        all_plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        plan = all_plans[0]
                    
    if not plan:
        trace_logs.append({"type": "error", "message": "Career plan not found in database."})
        raise ValueError("Career plan not found")
        
    trace_logs.append({"type": "mcp", "message": "Successfully retrieved career plan."})
    
    print("[Progress Agent] Analyzing update with Gemini...")
    trace_logs.append({"type": "agent", "message": f"Analyzing user update: '{update_text}' against current roadmap..."})
    
    progress = await determine_progress(plan["roadmap"], update_text)
    
    completed_id = progress.get("completed_step_id")
    if completed_id is not None:
        trace_logs.append({"type": "agent", "message": f"Identified matching roadmap milestone: {progress.get('completed_step_title')}"})
        # Update roadmap state
        for step in plan["roadmap"]:
            if step["step_id"] == completed_id:
                step["status"] = "Completed"
        
        trace_logs.append({"type": "agent", "message": "Roadmap state updated in memory."})
        print("[Progress Agent] Persisting changes via MCP...")
        trace_logs.append({"type": "mcp", "message": f"Persisting updated roadmap to rapid.career_plans using update-many..."})
        
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
