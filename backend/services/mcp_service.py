import os
import asyncio
import logging
import time
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_manager")

class MCPManager:
    def __init__(self):
        uri = os.environ.get("MDB_MCP_CONNECTION_STRING") or os.environ.get("MONGO_URI", "")
        env_vars = os.environ.copy()
        env_vars["MDB_MCP_CONNECTION_STRING"] = uri
        
        self.server_params = StdioServerParameters(
            command="node",
            args=["node_modules/mongodb-mcp-server/dist/index.js", "--transport", "stdio", "--loggers", "stderr"],
            env=env_vars
        )
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.startup_timestamp = None

    async def start(self):
        """Initializes the MCP Client. Raises an exception if it fails."""
        try:
            logger.info("MCPManager: Starting MCP Server subprocess...")
            cm_stdio = stdio_client(self.server_params)
            
            read, write = await self.exit_stack.enter_async_context(cm_stdio)
            cm_session = ClientSession(read, write)
            self.session = await self.exit_stack.enter_async_context(cm_session)
            
            await self.session.initialize()
            self.startup_timestamp = time.time()
            logger.info("MCPManager: Server initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB MCP Server: {e}")
            raise RuntimeError(f"Failed to initialize MongoDB MCP Server: {e}")

    async def stop(self):
        """Cleanly stops the MCP Client, suppressing known teardown exceptions."""
        logger.info("MCPManager: Stopping MCP Server...")
        try:
            await asyncio.wait_for(self.exit_stack.aclose(), timeout=3.0)
        except Exception as e:
            # We expect an ExceptionGroup because the Node process exits non-zero on EOF
            logger.info(f"MCPManager: Expected shutdown exception caught and suppressed ({type(e).__name__}).")
        finally:
            self.session = None
            logger.info("MCPManager: Shutdown complete.")

    async def check_health(self) -> bool:
        """Pings the MCP server to check if the pipe is alive."""
        if not self.session:
            return False
        try:
            await asyncio.wait_for(self.session.list_tools(), timeout=2.0)
            return True
        except Exception:
            return False

    async def reconnect(self):
        """Forces a restart of the MCP Client."""
        await self.stop()
        self.exit_stack = AsyncExitStack()
        await self.start()
