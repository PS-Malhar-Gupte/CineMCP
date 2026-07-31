"""
CLI entrypoint for the CineMCP agent.

Connects to the MCP tools server, discovers available tools, and runs an
interactive loop where the user can ask questions about movies. Each question
triggers the agent's decide → act → observe loop with a local LLM (via Ollama).

Mirrors the Repo Pulse CLI structure: transparent tool-call logging during
execution, so the user can see the agent's decision-making process.

Usage:
    python -m agent.main
    
    Requires:
    - Ollama running locally on default port (11434) OR OpenRouter API key in .env
    - OMDB_API_KEY and TMDB_API_KEY environment variables set
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

from agent.config import MODEL_NAME, MAX_LOOP_ITERATIONS, SYSTEM_PROMPT, REFLECTION_PROMPT, MAX_HISTORY_TURNS
from agent.mcp_connection import connect
from agent.llm_client import decide, reflect
from agent.loop import run_loop
from agent.conversation import ConversationState
from agent.memory import LocalMemoryService
from agent.observability import set_request_id


async def main():
    """
    Main CLI loop.
    
    Connects to the MCP server, lists available tools, then loops on user input
    until EOF (Ctrl-D on Unix, Ctrl-Z on Windows) or explicit exit command.
    """
    # Determine the absolute path to the server entrypoint
    # agent/main.py is in the agent/ directory, server/app.py is a sibling
    project_root = Path(__file__).parent.parent
    server_script_path = project_root / "server" / "app.py"
    
    if not server_script_path.exists():
        print(f"Error: Server script not found at {server_script_path}", file=sys.stderr)
        sys.exit(1)
    
    print("Connecting to CineMCP tools server...", file=sys.stderr)
    
    async with connect(str(server_script_path)) as session:
        # Discover available tools
        tools_result = await session.list_tools()
        tools = tools_result.tools
        
        print(f"\nConnected! Available tools ({len(tools)}):", file=sys.stderr)
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}", file=sys.stderr)
        
        print("\nReady. Ask me about movies! (Ctrl-D or 'exit' to quit)\n", file=sys.stderr)
        
        # Prompt for user ID (for user-specific memory)
        try:
            user_id = input("Enter your username (default: guest): ").strip()
            if not user_id:
                user_id = "guest"
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!", file=sys.stderr)
            return
            
        print(f"Welcome, {user_id}!\n", file=sys.stderr)
        
        # Initialize conversation state and memory service
        conv_state = ConversationState(max_turns=MAX_HISTORY_TURNS)
        # Using a local JSON file to persist memory across sessions
        memory_file = project_root / ".cine_memory.json"
        memory_service = LocalMemoryService(persist_path=str(memory_file))
        
        # Interactive loop
        while True:
            try:
                user_message = input("> ").strip()
                
                if not user_message:
                    continue
                
                # Generate a new request ID for this interaction
                req_id = set_request_id()
                
                if user_message.lower() in ("exit", "quit", "q"):
                    print("Goodbye!", file=sys.stderr)
                    break
                
                # Check for cached answer
                cache_key = memory_service.generate_key(user_message)
                cached_answer = memory_service.get(user_id, cache_key)
                if cached_answer:
                    print("\n  [Memory] Found cached answer for this exact question:", file=sys.stderr)
                    print(f"\n{cached_answer}\n")
                    # Still add to conversation state so context isn't broken
                    conv_state.add_turn(user_message, cached_answer)
                    continue
                
                # Run the agent loop for this user turn
                try:
                    # Define a step callback that prints each tool call and result
                    # This provides visibility into the agent's decision-making
                    def print_step(step_type: str, data: dict):
                        if step_type == "tool_call":
                            print(f"  → Calling {data['tool']} with {data['arguments']}", file=sys.stderr)
                        elif step_type == "tool_result":
                            result_preview = str(data['result'])[:200]
                            if len(str(data['result'])) > 200:
                                result_preview += "..."
                            print(f"  ← Result: {result_preview}", file=sys.stderr)
                        elif step_type == "tool_error":
                            print(f"  ✗ {data['error']}", file=sys.stderr)
                    
                    # Run the decide → act → observe loop
                    draft_answer, full_conversation = await run_loop(
                        session=session,
                        user_message=user_message,
                        system_prompt=SYSTEM_PROMPT,
                        model_name=MODEL_NAME,
                        max_iterations=MAX_LOOP_ITERATIONS,
                        decide_fn=decide,
                        on_step=print_step,
                        chat_history=conv_state.get_history()
                    )
                    
                    # One-shot reflection pass on the draft answer
                    print("\n  🔍 Reviewing answer...", file=sys.stderr)
                    
                    # Use the REAL conversation (including every tool call and
                    # result) so reflection can verify the draft against actual
                    # evidence instead of judging it blind. Passing a trimmed
                    # [system, user, draft] history caused false-negative
                    # "corrections" that discarded perfectly good, fully-
                    # grounded answers.
                    history = full_conversation + [
                        {"role": "assistant", "content": draft_answer}
                    ]
                    
                    reflection_result = reflect(history, draft_answer, MODEL_NAME)
                    
                    if reflection_result.get("ok"):
                        # Draft answer approved
                        final_answer = draft_answer
                    else:
                        # Draft answer corrected
                        final_answer = reflection_result.get("corrected_answer", draft_answer)
                        print("  ✓ Answer corrected", file=sys.stderr)
                    
                    # Save the turn to conversation state
                    conv_state.add_turn(user_message, final_answer)
                    
                    # Cache the answer
                    memory_service.set(user_id, cache_key, final_answer)
                    
                    # Print the final answer to stdout (clean output for scripting)
                    print(f"\n{final_answer}\n")
                    
                except RuntimeError as e:
                    # Max iterations reached or other loop failure
                    print(f"\nError: {e}", file=sys.stderr)
                
            except EOFError:
                # User pressed Ctrl-D (Unix) or Ctrl-Z (Windows)
                print("\nGoodbye!", file=sys.stderr)
                break
            except KeyboardInterrupt:
                # User pressed Ctrl-C
                print("\nInterrupted. Use 'exit' or Ctrl-D to quit.", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())