"""
MCP connection management.

Handles spawning the MCP tools server subprocess, completing the handshake,
and discovering available tools. Carries over from Repo Pulse with no changes.
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def connect(server_script_path: str) -> AsyncIterator[ClientSession]:
    """
    Connect to an MCP server via stdio transport.
    
    Spawns the server as a subprocess, completes the MCP initialization
    handshake, and yields an active session. The session is automatically
    cleaned up when the context exits.
    
    Args:
        server_script_path: Absolute path to the server entrypoint script
        
    Yields:
        Active MCP ClientSession
        
    Example:
        async with connect("/path/to/server/app.py") as session:
            tools = await session.list_tools()
            result = await session.call_tool("some_tool", {"arg": "value"})
    """
    # Determine Python executable
    # Use the same Python that's running the agent
    python_executable = sys.executable
    
    # Get the project root directory from the server script path
    # server_script_path is like "/path/to/project/server/app.py"
    # We need to run from the project root with "python -m server.app"
    from pathlib import Path
    server_path = Path(server_script_path)
    project_root = server_path.parent.parent  # Go up from server/app.py to project root
    
    server_params = StdioServerParameters(
        command=python_executable,
        args=["-m", "server.app"],  # Run as module instead of script
        cwd=str(project_root),  # Set working directory to project root
        # Explicitly pass the full parent environment to the subprocess
        # (MCP's StdioServerParameters does not inherit environment by default)
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Complete the MCP initialization handshake
            await session.initialize()
            
            # Session is now ready for tool discovery and calls
            yield session
