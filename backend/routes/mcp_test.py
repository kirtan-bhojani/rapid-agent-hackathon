from fastapi import APIRouter, Request, HTTPException, Depends
from dependencies import get_mcp_client
from typing import Any

router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/health")
async def mcp_health(mcp_client: Any = Depends(get_mcp_client)):
    
    is_healthy = await mcp_client.check_health()
    tools = await mcp_client.session.list_tools()
    
    return {
        "status": "connected" if is_healthy else "disconnected",
        "tool_count": len(tools.tools),
        "startup_timestamp": mcp_client.startup_timestamp
    }

@router.get("/tools")
async def mcp_tools(mcp_client: Any = Depends(get_mcp_client)):
    
    tools = await mcp_client.session.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools.tools
        ]
    }

@router.get("/test-databases")
async def mcp_test_databases(mcp_client: Any = Depends(get_mcp_client)):
    
    result = await mcp_client.session.call_tool("list-databases", arguments={})
    texts = [c.text for c in result.content if c.type == "text"]
    return {"databases": texts}
