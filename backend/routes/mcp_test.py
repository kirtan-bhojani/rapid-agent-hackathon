from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/health")
async def mcp_health(request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    is_healthy = await mcp_client.check_health()
    tools = await mcp_client.session.list_tools()
    
    return {
        "status": "connected" if is_healthy else "disconnected",
        "tool_count": len(tools.tools),
        "startup_timestamp": mcp_client.startup_timestamp
    }

@router.get("/tools")
async def mcp_tools(request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    tools = await mcp_client.session.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools.tools
        ]
    }

@router.get("/test-databases")
async def mcp_test_databases(request: Request):
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    
    try:
        result = await mcp_client.session.call_tool("list-databases", arguments={})
        texts = [c.text for c in result.content if c.type == "text"]
        return {"databases": texts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
