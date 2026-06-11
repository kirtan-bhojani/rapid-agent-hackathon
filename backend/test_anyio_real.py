import asyncio
import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager, AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get("MDB_MCP_CONNECTION_STRING") or os.environ.get("MONGO_URI")
env_vars = os.environ.copy()
env_vars["MDB_MCP_CONNECTION_STRING"] = uri

params = StdioServerParameters(
    command="node",
    args=["node_modules/mongodb-mcp-server/dist/index.js", "--transport", "stdio", "--loggers", "stderr"],
    env=env_vars
)

async def shutdown_server(server, delay):
    await asyncio.sleep(delay)
    print("Test stopping server...")
    server.should_exit = True

async def exp_C():
    print("\n--- EXP C: FastAPI Lifespan ---")
    @asynccontextmanager
    async def lifespan_c(app):
        stack = AsyncExitStack()
        try:
            print("Exp C: Starting MCP via AsyncExitStack...")
            cm = stdio_client(params)
            read, write = await stack.enter_async_context(cm)
            sess = ClientSession(read, write)
            await stack.enter_async_context(sess)
            await sess.initialize()
            print("Exp C: Initialized. Yielding control.")
            yield
        except Exception as e:
            print(f"Exp C Lifespan Error during run: {type(e).__name__}: {e}")
        finally:
            print("Exp C: Shutting down.")
            try:
                await stack.aclose()
                print("Exp C: Shutdown complete.")
            except Exception as e:
                print(f"Exp C Aclose Failed: {type(e).__name__}: {e}")
            
    app = FastAPI(lifespan=lifespan_c)
    config = uvicorn.Config(app, port=8002, log_level="error")
    server = uvicorn.Server(config)
    asyncio.create_task(shutdown_server(server, 2))
    try:
        await server.serve()
    except Exception as e:
         print(f"Exp C Server Failed: {type(e).__name__}: {e}")

async def exp_D():
    print("\n--- EXP D: FastAPI Background Worker ---")
    
    class MCPBg:
        def __init__(self):
            self.stop_event = asyncio.Event()
            self.ready_event = asyncio.Event()
            self.task = None

        async def worker(self):
            try:
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        print("Exp D: Worker initialized.")
                        self.ready_event.set()
                        await self.stop_event.wait()
                        print("Exp D: Worker received stop event. Contexts exiting...")
            except Exception as e:
                print(f"Exp D Worker Failed during shutdown: {type(e).__name__}: {e}")
                
    mcp_bg = MCPBg()
    
    @asynccontextmanager
    async def lifespan_d(app):
        try:
            print("Exp D: Starting worker task...")
            mcp_bg.task = asyncio.create_task(mcp_bg.worker())
            await mcp_bg.ready_event.wait()
            print("Exp D: Worker is ready. Yielding control.")
            yield
        finally:
            print("Exp D: Shutting down worker.")
            mcp_bg.stop_event.set()
            await mcp_bg.task
            print("Exp D: Shutdown complete.")

    app = FastAPI(lifespan=lifespan_d)
    config = uvicorn.Config(app, port=8003, log_level="error")
    server = uvicorn.Server(config)
    asyncio.create_task(shutdown_server(server, 2))
    try:
        await server.serve()
    except Exception as e:
         print(f"Exp D Server Failed: {type(e).__name__}: {e}")

async def main():
    await exp_C()
    await exp_D()
    os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
