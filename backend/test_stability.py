import asyncio
import time
from services.mcp_service import MCPManager

async def test_cycle(i):
    mcp = MCPManager()
    
    t0 = time.time()
    await mcp.start()
    t_start = time.time() - t0
    
    # Tool discovery
    tools = await mcp.session.list_tools()
    tool_count = len(tools.tools)
    
    # Health check
    is_healthy = await mcp.check_health()
    
    t1 = time.time()
    await mcp.stop()
    t_stop = time.time() - t1
    
    return {
        "success": is_healthy and tool_count > 0,
        "startup_time": t_start,
        "shutdown_time": t_stop,
        "tool_count": tool_count
    }

async def main():
    successes = 0
    failures = 0
    start_times = []
    stop_times = []
    
    print("--- Starting 10-Cycle Stability Validation ---")
    for i in range(1, 11):
        try:
            print(f"Cycle {i}...")
            res = await test_cycle(i)
            if res["success"]:
                successes += 1
            else:
                failures += 1
            start_times.append(res["startup_time"])
            stop_times.append(res["shutdown_time"])
        except Exception as e:
            print(f"Cycle {i} FAILED: {e}")
            failures += 1
            
    avg_start = sum(start_times) / len(start_times) if start_times else 0
    avg_stop = sum(stop_times) / len(stop_times) if stop_times else 0
    
    print("\n--- Stability Validation Results ---")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Average Startup Time: {avg_start:.3f}s")
    print(f"Average Shutdown Time: {avg_stop:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
