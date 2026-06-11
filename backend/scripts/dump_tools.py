import asyncio
import json
from services.mcp_service import MCPManager

async def main():
    mcp = MCPManager()
    await mcp.start()
    tools = await mcp.session.list_tools()
    for t in tools.tools:
        if t.name == "find":
            print(f"--- {t.name} ---")
            print(json.dumps(t.inputSchema, indent=2))
    await mcp.stop()

if __name__ == "__main__":
    asyncio.run(main())
