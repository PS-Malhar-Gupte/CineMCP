"""
MCP tools server for CineMCP.

This package exposes narrow, single-purpose MCP tools backed by free
third-party APIs (OMDb for movie search/details/ratings, TMDb for current
India theatrical releases). Tools are deliberately kept overlapping in
scope to require genuine LLM-driven tool selection rather than fixed
routing logic.

Key modules:
- mcp_instance: Shared FastMCP server instance for tool registration
- http_utils: API request helpers with credential handling and error normalization
- movie_tools: OMDb-backed tools (search, details, ratings)
- release_tools: TMDb-backed tools (now playing, upcoming releases in India)
- app: MCP server entrypoint (stdio transport)
"""
