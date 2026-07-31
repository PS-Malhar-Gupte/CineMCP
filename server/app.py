"""
Server entrypoint for CineMCP MCP tools server.

This module serves as the main entrypoint that:
1. Imports the shared mcp_instance (the FastMCP server object)
2. Imports all tool modules as side-effect imports to trigger their
   @mcp.tool() decorator registration
3. Calls mcp.run() on stdio to start the MCP server

The import order is important: mcp_instance must be imported before the
tool modules, since they depend on the mcp object to register their tools.

Usage:
    python -m server.app
    
    Or via MCP client that spawns this as a subprocess on stdio transport.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Find the .env file in the project root (parent of server directory)
env_path = Path(__file__).parent.parent / ".env"
loaded = load_dotenv(dotenv_path=env_path)

# Debug logging to stderr (won't interfere with MCP stdio protocol)
print(f"[DEBUG] .env path: {env_path}", file=sys.stderr)
print(f"[DEBUG] .env exists: {env_path.exists()}", file=sys.stderr)
print(f"[DEBUG] .env loaded: {loaded}", file=sys.stderr)
print(f"[DEBUG] OMDB_API_KEY present: {'OMDB_API_KEY' in os.environ}", file=sys.stderr)
print(f"[DEBUG] TMDB_API_KEY present: {'TMDB_API_KEY' in os.environ}", file=sys.stderr)

try:
    from server.mcp_instance import mcp
    print(f"[DEBUG] mcp_instance imported successfully", file=sys.stderr)
    
    # Side-effect imports: importing these modules triggers the @mcp.tool()
    # decorators inside them, which register the tools against the shared mcp instance
    import server.movie_tools
    print(f"[DEBUG] movie_tools imported successfully", file=sys.stderr)
    
    import server.release_tools
    print(f"[DEBUG] release_tools imported successfully", file=sys.stderr)
    
except Exception as e:
    print(f"[DEBUG] Import error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Start the MCP server on stdio transport
# This blocks and handles the MCP protocol communication
if __name__ == "__main__":
    print(f"[DEBUG] Starting MCP server...", file=sys.stderr)
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"[DEBUG] Server error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
