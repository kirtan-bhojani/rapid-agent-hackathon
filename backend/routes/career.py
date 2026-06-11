from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import json
import re
from typing import List, Dict, Any, Optional
from services.career_pipeline import run_career_pipeline
from services.progress_agent import run_progress_agent
from services.profile_service import get_unified_profile

router = APIRouter(prefix="/career-plan", tags=["career"])

class CareerPlanRequest(BaseModel):
    user_id: str
    goal: str

@router.post("/")
async def create_career_plan(req: CareerPlanRequest, request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    try:
        profile = get_unified_profile(req.user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Unified profile not found. Please upload a resume first.")

        plan = await run_career_pipeline(
            user_id=req.user_id,
            query=req.goal,
            profile=profile,
            mcp_client=mcp_client
        )
        return {"status": "success", "data": plan["data"], "trace_logs": plan["trace_logs"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class StatusUpdateRequest(BaseModel):
    user_id: str
    update: str

@router.post("/career-status-update")
async def update_career_status(req: StatusUpdateRequest, request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    try:
        result = await run_progress_agent(
            user_id=req.user_id,
            update_text=req.update,
            mcp_client=mcp_client
        )
        return {"status": "success", "data": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_career_plan(user_id: str, request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    try:
        result = await mcp_client.session.call_tool("find", arguments={
            "database": "rapid",
            "collection": "career_plans",
            "filter": {"user_id": user_id}
        })
        
        all_plans = []
        for c in result.content:
            if c.type == "text":
                text = c.text
                # Find first [ or {
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
                    json_str = text[start:end+1]
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            all_plans.extend(parsed)
                        elif isinstance(parsed, dict) and "user_id" in parsed:
                            all_plans.append(parsed)
                    except Exception:
                        pass
                        
        if not all_plans:
            raise HTTPException(status_code=404, detail="Career plan not found.")
            
        # Sort plans by created_at descending to get the newest one
        all_plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        plan = all_plans[0]
            
        return {"status": "success", "data": plan}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
