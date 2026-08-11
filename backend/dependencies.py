from fastapi import Request, HTTPException
from typing import Any

def get_mcp_client(request: Request) -> Any:
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if not mcp_client or not mcp_client.session:
        raise HTTPException(status_code=503, detail="MCP Client is not initialized.")
    return mcp_client


def get_llm_client(request: Request) -> Any:
    llm_client = getattr(request.app.state, "llm_client", None)
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM Client is not initialized.")
    return llm_client
