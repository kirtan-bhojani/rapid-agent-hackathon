import json
import re
import uuid
import datetime
import hashlib
from typing import Dict, Any, List
from google import genai
from google.genai import types
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

async def fetch_opportunities_from_mcp(mcp_client: Any, cache_key: str) -> List[Dict[str, Any]]:
    result = await mcp_client.session.call_tool("find", arguments={
        "database": "rapid",
        "collection": "opportunities",
        "filter": {"cache_key": cache_key}
    })
    
    docs = []
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
                    if isinstance(parsed, list):
                        docs.extend(parsed)
                    elif isinstance(parsed, dict) and "title" in parsed:
                        docs.append(parsed)
                except Exception:
                    pass
    return docs

async def run_opportunity_agent(user_id: str, profile: Dict[str, Any], plan: Dict[str, Any], category: str, mcp_client: Any) -> Dict[str, Any]:
    trace_logs = []
    
    target_role = plan.get("goal", {}).get("target_role", "Unknown")
    raw_key = f"{user_id}_{category}_{target_role}"
    cache_key = hashlib.md5(raw_key.encode()).hexdigest()
    
    trace_logs.append({"type": "agent", "message": f"Checking opportunity cache for {category}..."})
    print(f"[Opportunity Agent] Cache key generated: {cache_key}")
    
    cached_docs = await fetch_opportunities_from_mcp(mcp_client, cache_key)
    if cached_docs:
        # Filter for those less than 24h old
        valid_docs = []
        now = datetime.datetime.now()
        for doc in cached_docs:
            if "created_at" in doc:
                try:
                    doc_time = datetime.datetime.fromisoformat(doc["created_at"])
                    if (now - doc_time).total_seconds() < 86400:
                        valid_docs.append(doc)
                except Exception:
                    pass
        if valid_docs:
            trace_logs.append({"type": "mcp", "message": f"Found {len(valid_docs)} fresh opportunities in MongoDB cache."})
            return {"data": valid_docs, "trace_logs": trace_logs}

    trace_logs.append({"type": "agent", "message": f"Cache expired or empty. Triggering Gemini Live Search for {category}s..."})
    print("[Opportunity Agent] Running live search...")
    
    prompt = f"""
    You are an elite Career Intelligence Agent.
    Find 3 real, live, currently open {category} opportunities for a {target_role}.
    
    User Strengths: {json.dumps(profile.get('skills', []))}
    User Gap Analysis (Missing Skills): {json.dumps(plan.get('gaps', {}).get('missing_skills', []))}
    
    For each opportunity, calculate a deeply personalized 'fit_score' (0-100) based on their strengths and gaps.
    
    Return a JSON ARRAY of 3 objects exactly matching this schema:
    [
      {{
        "title": "Job/Scholarship/Course Title",
        "organization": "Company/University Name",
        "description": "Short description",
        "deadline": "Date or Rolling",
        "application_url": "Real URL to apply",
        "fit_score": 85,
        "reasoning": "1 sentence explanation of score",
        "strengths": ["Matched skill 1", "Matched skill 2"],
        "risks": ["Risk 1", "Risk 2"],
        "missing_requirements": ["Missing skill 1", "Missing skill 2"],
        "improvement_actions": ["Action to improve chance 1", "Action 2"]
      }}
    ]
    """
    
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2
            )
        )
        
        raw_json = clean_json(res.text)
        new_opportunities = json.loads(raw_json)
    except Exception as e:
        print(f"[Opportunity Agent] Error during Gemini search: {e}")
        # Fallback dummy if API fails
        new_opportunities = [{
            "title": f"Example {category}",
            "organization": "Example Org",
            "description": "Fallback description",
            "deadline": "Rolling",
            "application_url": "https://example.com",
            "fit_score": 50,
            "reasoning": "Fallback due to search error.",
            "strengths": ["General background"],
            "risks": ["Unknown requirements"],
            "missing_requirements": ["Specific skills"],
            "improvement_actions": ["Review detailed description"]
        }]

    if not isinstance(new_opportunities, list):
        new_opportunities = [new_opportunities]

    trace_logs.append({"type": "agent", "message": f"Found 3 live {category}s. Calculating Intelligence Scores..."})
    
    final_docs = []
    for opp in new_opportunities:
        opp["_id"] = str(uuid.uuid4())
        opp["user_id"] = user_id
        opp["category"] = category
        opp["cache_key"] = cache_key
        opp["created_at"] = datetime.datetime.now().isoformat()
        final_docs.append(opp)
        
    trace_logs.append({"type": "mcp", "message": "Persisting Opportunity Intelligence to rapid.opportunities..."})
    
    await mcp_client.session.call_tool("insert-many", arguments={
        "database": "rapid",
        "collection": "opportunities",
        "documents": final_docs
    })
    
    trace_logs.append({"type": "agent", "message": "Opportunities successfully analyzed and cached."})
    
    return {"data": final_docs, "trace_logs": trace_logs}
