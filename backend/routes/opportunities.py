from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
import datetime
import uuid
from typing import Optional
from services.profile_service import get_unified_profile
from services.opportunity_agent import run_opportunity_agent
import json

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

@router.get("/{user_id}")
async def get_opportunities(user_id: str, request: Request, category: str = Query("job")):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
        
    try:
        # 1. Fetch unified profile
        profile = get_unified_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found.")
            
        # 2. Fetch career plan via MCP
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
                        
        if not all_plans:
            raise HTTPException(status_code=404, detail="Career Plan not found. Please create one first.")
            
        all_plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        plan = all_plans[0]
            
        # 3. Run Opportunity Agent
        response = await run_opportunity_agent(
            user_id=user_id,
            profile=profile,
            plan=plan,
            category=category,
            mcp_client=mcp_client
        )
        
        return {"status": "success", "data": response["data"], "trace_logs": response["trace_logs"]}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackRequest(BaseModel):
    user_id: str
    opportunity_id: str
    action: str

@router.post("/feedback")
async def store_feedback(req: FeedbackRequest, request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
        
    try:
        feedback_doc = {
            "_id": str(uuid.uuid4()),
            "user_id": req.user_id,
            "opportunity_id": req.opportunity_id,
            "action": req.action,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        await mcp_client.session.call_tool("insert-many", arguments={
            "database": "rapid",
            "collection": "opportunity_feedback",
            "documents": [feedback_doc]
        })
        
        return {"status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
