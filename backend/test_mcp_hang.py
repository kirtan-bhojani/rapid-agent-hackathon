import asyncio
import os
import concurrent.futures
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define server parameters
# Assuming standard mongodb-mcp-server usage. We pass the environment so it can pick up MONGODB_URI if it's set.
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-mongodb"],
    env=os.environ.copy() 
)

async def manual_e1_wait_for():
    print("--- E1: asyncio.wait_for on Teardown ---")
    try:
        cm_stdio = stdio_client(server_params)
        read, write = await cm_stdio.__aenter__()
        cm_session = ClientSession(read, write)
        session = await cm_session.__aenter__()
        
        await session.initialize()
        tools = await session.list_tools()
        print(f"E1 Success: Tools listed: {len(tools.tools)}")
        print("E1: Entering cleanup phase (wrapped in wait_for)...")
        
        try:
            await asyncio.wait_for(cm_session.__aexit__(None, None, None), timeout=2.0)
            print("E1: Session cleanup finished.")
        except asyncio.TimeoutError:
            print("E1: Session cleanup TIMEOUT (Hangs here!)")
            
        try:
            await asyncio.wait_for(cm_stdio.__aexit__(None, None, None), timeout=2.0)
            print("E1: Stdio cleanup finished.")
        except asyncio.TimeoutError:
            print("E1: Stdio cleanup TIMEOUT (Hangs here!)")
    except Exception as e:
        print(f"E1 Exception: {e}")

def run_e2_background_thread():
    print("\n--- E2: Background Thread Execution ---")
    def sync_worker():
        async def async_worker():
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    print(f"E2 Success: Tools listed: {len(tools.tools)}")
        asyncio.run(async_worker())
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(sync_worker)
            future.result(timeout=10.0) # Wait up to 10 seconds
        print("E2: Thread worker finished without hang!")
    except concurrent.futures.TimeoutError:
        print("E2: Thread worker TIMEOUT (Hangs!)")
    except Exception as e:
        print(f"E2 Exception: {e}")

async def run_e4_cleanup_elimination():
    print("\n--- E4: Cleanup Elimination Test ---")
    try:
        cm = stdio_client(server_params)
        read, write = await cm.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        tools = await session.list_tools()
        print(f"E4 Success: Tools listed: {len(tools.tools)}")
        print("E4: Intentionally skipping cleanup (Not calling aexit)")
        return True
    except Exception as e:
        print(f"E4 Failed: {e}")
        return False

async def main():
    print("Starting Diagnostic Matrix...")
    await manual_e1_wait_for()
    run_e2_background_thread()
    await run_e4_cleanup_elimination()
    print("\nDiagnostic Matrix Complete.")
    
    # Force exit to kill any dangling subprocesses from E4
    os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
