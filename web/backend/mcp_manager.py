import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from agent.mcp_connection import connect

project_root = Path(__file__).parent.parent.parent
server_script_path = str(project_root / "server" / "app.py")


class MCPSessionManager:
    """
    Manages MCP sessions with two modes: 'pool' (default) and 'per_user'.
    """
    def __init__(self):
        self.mode = os.getenv("MCP_MODE", "pool").lower()
        self.pool_size = int(os.getenv("MCP_POOL_SIZE", "3"))
        
        # For pool mode
        self.queue = None
        self.active_contexts = []
        
        # Tools cached globally since they don't change
        self.tools = []

    async def initialize(self):
        """Initialize the connection manager."""
        print(f"Initializing MCPSessionManager in '{self.mode}' mode...")
        
        if self.mode == "pool":
            self.queue = asyncio.Queue(maxsize=self.pool_size)
            for i in range(self.pool_size):
                try:
                    ctx = connect(server_script_path)
                    session = await ctx.__aenter__()
                    
                    # If this is the first session, fetch tools
                    if i == 0:
                        tools_result = await session.list_tools()
                        self.tools = tools_result.tools
                        
                    self.active_contexts.append(ctx)
                    self.queue.put_nowait({"context": ctx, "session": session})
                except Exception as e:
                    print(f"Failed to initialize pool session {i}: {e}")
            
            print(f"Started MCP Session Pool with {self.pool_size} processes.")
        
        elif self.mode == "per_user":
            # For per_user, we just fetch tools once to verify it works
            temp_ctx = connect(server_script_path)
            temp_session = await temp_ctx.__aenter__()
            tools_result = await temp_session.list_tools()
            self.tools = tools_result.tools
            await temp_ctx.__aexit__(None, None, None)
            
            print("Verified MCP connection for per_user mode.")

    async def cleanup(self):
        """Cleanup all persistent sessions."""
        if self.mode == "pool":
            for ctx in self.active_contexts:
                try:
                    await ctx.__aexit__(None, None, None)
                except Exception as e:
                    print(f"Error cleaning up pool context: {e}")

    @asynccontextmanager
    async def get_session(self):
        """
        Check out a session from the pool or spawn a new one,
        depending on the configured mode.
        """
        if self.mode == "pool":
            # Wait for an available session
            session_info = await self.queue.get()
            try:
                yield session_info["session"]
            finally:
                # Return the session to the pool
                self.queue.put_nowait(session_info)
        
        elif self.mode == "per_user":
            # Spawn a dedicated session for this request
            ctx = connect(server_script_path)
            session = await ctx.__aenter__()
            try:
                yield session
            finally:
                # Cleanup the process when the request ends
                await ctx.__aexit__(None, None, None)
