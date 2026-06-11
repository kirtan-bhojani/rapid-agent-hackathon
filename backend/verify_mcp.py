import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

uri = os.environ.get("MDB_MCP_CONNECTION_STRING") or os.environ.get("MONGO_URI")

env_vars = os.environ.copy()
env_vars["MDB_MCP_CONNECTION_STRING"] = uri

server_params = StdioServerParameters(
    command="node",
    args=["node_modules/mongodb-mcp-server/dist/index.js", "--transport", "stdio", "--loggers", "stderr,mcp"],
    env=env_vars
)

async def main():
    print("--- Phase A: Standalone MCP Verification ---")
    print(f"Command: {server_params.command} {' '.join(server_params.args[:-1])} <URI_REDACTED>")
    try:
        async with stdio_client(server_params) as (read, write):
            print("1. Subprocess started successfully.")
            async with ClientSession(read, write) as session:
                print("2. ClientSession context entered.")
                await session.initialize()
                print("3. Session initialized.")
                
                tools_response = await session.list_tools()
                print("\n4. Discovered Tools:")
                for tool in tools_response.tools:
                    print(f" - {tool.name}")
                    
                if tools_response.tools:
                    target_tool = tools_response.tools[0].name
                    print(f"\n5. Attempting to execute tool: {target_tool}")
                    # We try to call it with empty args, or dummy args. If it errors due to validation, that's fine, it proves communication.
                    try:
                        result = await session.call_tool(target_tool, arguments={})
                        print(f"Tool executed successfully. Result: {result}")
                    except Exception as tool_e:
                        print(f"Tool execution returned error (likely schema validation): {tool_e}")
                print("\n6. Exiting context managers...")
        print("7. Cleanup successful. No hangs.")
    except Exception as e:
        print(f"Verification Failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
