"""
Shared FastMCP instance for CineMCP tools server.

This module exists as a standalone file to avoid circular imports between
app.py (which imports all tool modules to trigger their registration) and
the tool modules themselves (which need access to the shared `mcp` object
to register their @mcp.tool() decorators).

Usage:
    from server.mcp_instance import mcp
    
    @mcp.tool()
    def my_tool(arg: str) -> dict:
        return {"result": arg}
"""

from mcp.server.fastmcp import FastMCP

# Shared MCP server instance that all tool modules register against
mcp = FastMCP("CineMCP")
