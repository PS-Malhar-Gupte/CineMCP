"""
Agent client for CineMCP.

This package implements the LLM-driven "brain" that decides which MCP
tools to call for a given user question. It follows a decide → act →
observe loop against a local LLM (via Ollama) with optional one-shot
reflection to self-check final answers before returning them to the user.

Key modules:
- config: Model selection, system prompt, and runtime parameters
- llm_client: Ollama API wrapper with tolerant JSON extraction
- mcp_connection: MCP client setup over stdio transport
- loop: Core decide/act/observe iteration logic
- main: CLI entrypoint for terminal-based interaction
"""
