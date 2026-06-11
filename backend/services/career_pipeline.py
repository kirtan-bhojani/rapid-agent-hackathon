import json
import re
import uuid
import datetime
from typing import Dict, Any
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def clean_json(text: str) -> str:
    text = text.strip()
    # Find the first [ or { and the last ] or }
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

async def extract_goal(query: str) -> Dict[str, Any]:
    prompt = f"""
    Extract the career goal from the query.
    Return ONLY valid JSON with exactly these fields:
    - target_role (string: e.g., "Cloud Architect", "ML Engineer", "Data Scientist", "Software Engineer")
    - timeline (string: e.g., "6 months")
    
    Query: "{query}"
    """
    res = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    try:
        data = json.loads(clean_json(res.text))
        if not data.get("target_role") or str(data.get("target_role")).lower() == "none":
            data["target_role"] = "Software Engineer"
        if not data.get("timeline") or str(data.get("timeline")).lower() == "none":
            data["timeline"] = "6 months"
        return data
    except Exception:
        return {"target_role": "Software Engineer", "timeline": "6 months"}

async def perform_gap_analysis(profile: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
    Compare the user's current profile with the role template requirements.
    Return ONLY valid JSON with exactly these fields:
    - missing_skills (list of strings)
    - recommended_actions (list of strings)
    
    User Profile:
    {json.dumps(profile, indent=2)}
    
    Role Template:
    {json.dumps(template, indent=2)}
    """
    res = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return json.loads(clean_json(res.text))

async def generate_roadmap(gaps: Dict[str, Any], timeline: str) -> list:
    prompt = f"""
    Create a step-by-step roadmap to achieve the goal in {timeline} addressing these gaps:
    {json.dumps(gaps, indent=2)}
    
    Return ONLY a valid JSON ARRAY of objects, each with:
    - step_id (integer)
    - title (string)
    - description (string)
    - status (must be exactly "Pending")
    """
    res = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return json.loads(clean_json(res.text))

async def run_career_pipeline(user_id: str, query: str, profile: Dict[str, Any], mcp_client: Any) -> Dict[str, Any]:
    trace_logs = []
    
    print("[Pipeline] Starting goal extraction...")
    trace_logs.append({"type": "agent", "message": f"Analyzing user query to extract career goal..."})
    goal = await extract_goal(query)
    
    print(f"[Pipeline] Goal extracted: {goal['target_role']}. Fetching template via MCP...")
    trace_logs.append({"type": "agent", "message": f"Goal identified: {goal['target_role']}. Timeline: {goal.get('timeline', 'N/A')}"})
    trace_logs.append({"type": "mcp", "message": f"Fetching role template for {goal['target_role']} from rapid.role_templates..."})
    # Fetch template via MCP
    result = await mcp_client.session.call_tool("find", arguments={
        "database": "rapid",
        "collection": "role_templates",
        "filter": {"role": goal["target_role"]}
    })
    
    template_content = None
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
                        template_content = parsed[0]
                    elif isinstance(parsed, dict) and "role" in parsed:
                        template_content = parsed
                except Exception:
                    pass

    if not template_content:
        print("[Pipeline] Template not found via MCP. Fallback to Gemini reasoning.")
        trace_logs.append({"type": "mcp", "message": f"Template not found. Falling back to generalized reasoning."})
        template_content = {"role": goal["target_role"], "required_skills": ["General CS Skills"]}
    else:
        trace_logs.append({"type": "mcp", "message": f"Successfully retrieved role template."})
        
    print("[Pipeline] Performing Gap Analysis...")
    trace_logs.append({"type": "agent", "message": f"Performing Gap Analysis: Comparing user profile against role requirements..."})
    gaps = await perform_gap_analysis(profile, template_content)
    trace_logs.append({"type": "agent", "message": f"Gap Analysis complete. Identified {len(gaps.get('missing_skills', []))} missing skills."})
    
    print("[Pipeline] Generating Roadmap...")
    trace_logs.append({"type": "agent", "message": f"Generating personalized {goal.get('timeline', '6 months')} roadmap..."})
    roadmap = await generate_roadmap(gaps, goal.get("timeline", "6 months"))
    trace_logs.append({"type": "agent", "message": f"Roadmap generated with {len(roadmap)} steps."})
    
    plan_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "goal": goal,
        "gaps": gaps,
        "roadmap": roadmap,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    print("[Pipeline] Persisting state to MongoDB via MCP...")
    trace_logs.append({"type": "mcp", "message": f"Persisting generated career plan to rapid.career_plans..."})
    await mcp_client.session.call_tool("insert-many", arguments={
        "database": "rapid",
        "collection": "career_plans",
        "documents": [plan_doc]
    })
    trace_logs.append({"type": "mcp", "message": f"Career plan successfully stored in MongoDB."})
    
    print("[Pipeline] Complete!")
    return {"data": plan_doc, "trace_logs": trace_logs}
