import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from services.mcp_service import MCPManager

async def main():
    mcp = MCPManager()
    await mcp.start()
    result = await mcp.session.call_tool("find", arguments={
        "database": "rapid",
        "collection": "career_plans",
        "filter": {"user_id": "test_user_123"}
    })
    print("--- RAW RESULT CONTENT ---")
    for c in result.content:
        print(f"Type: {c.type}")
        if c.type == "text":
            print(f"Text: {c.text[:1000]}")
    await mcp.stop()

if __name__ == "__main__":
    asyncio.run(main())
