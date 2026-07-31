"""
Agent decide → act → observe loop.

Runs the core agentic loop: call the LLM to decide an action, execute tool
calls, feed results back, repeat until a final answer. Carries over from
Repo Pulse with no domain-specific changes.
"""

from typing import Callable, Any
from mcp import ClientSession


import asyncio
import inspect
import json
from agent.config import FALLBACK_EMPTY_RESULT, FALLBACK_UNGROUNDED
from agent.llm_client import validate_grounding
from agent.observability import MetricsLogger

async def _notify_step(on_step: Callable | None, step_type: str, data: dict[str, Any]) -> None:
    if on_step is None:
        return
    res = on_step(step_type, data)
    if inspect.isawaitable(res):
        await res


async def _run_loop_inner(
    session: ClientSession,
    user_message: str,
    system_prompt: str,
    model_name: str,
    max_iterations: int,
    decide_fn: Callable,
    on_step: Callable[[str, dict], None] | None = None,
    chat_history: list[dict] | None = None
) -> tuple[str, list[dict]]:
    """
    Run the agent's decide → act → observe loop.
    """
    if on_step is None:
        on_step = _default_step_handler
    
    conversation = [{"role": "system", "content": system_prompt}]
    
    if chat_history:
        conversation.extend(chat_history)
        
    conversation.append({"role": "user", "content": user_message})
    
    called_any_tools = False
    has_valid_data = False
    
    for iteration in range(max_iterations):
        # Decide: call LLM to get next action (in thread if sync to avoid blocking event loop)
        if inspect.iscoroutinefunction(decide_fn) or asyncio.iscoroutinefunction(decide_fn):
            decision = await decide_fn(conversation, model_name)
        else:
            decision = await asyncio.to_thread(decide_fn, conversation, model_name)
        
        action = decision.get("action")
        
        if action == "final":
            # Agent produced a final answer
            answer = decision.get("answer", "")
            
            # Guardrail 1: Empty results
            if called_any_tools and not has_valid_data:
                answer = FALLBACK_EMPTY_RESULT
            
            # Guardrail 2: Grounding validation
            elif has_valid_data:
                try:
                    is_grounded = await asyncio.to_thread(validate_grounding, conversation, answer, model_name)
                    if not is_grounded:
                        print("[Grounding] is_grounded returned False. Applying fallback.")
                        answer = FALLBACK_UNGROUNDED
                except Exception as e:
                    # If grounding validation fails, err on the side of caution
                    print(f"[Grounding Error] validate_grounding threw an exception: {str(e)}")
                    answer = FALLBACK_UNGROUNDED
            
            await _notify_step(on_step, "final", {"answer": answer})
            return answer, conversation
        
        elif action == "call_tool":
            # Agent wants to call a tool
            tool_name = decision.get("tool")
            tool_args = decision.get("arguments", {})
            
            await _notify_step(on_step, "tool_call", {"tool": tool_name, "arguments": tool_args})
            
            # Execute the tool call
            try:
                with MetricsLogger.start_span("tool_execution", {"tool": tool_name}):
                    result = await session.call_tool(tool_name, tool_args)
                
                # Extract the actual content from MCP's CallToolResult
                if hasattr(result, 'content') and result.content:
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        tool_result = content_item.text
                    else:
                        tool_result = str(content_item)
                else:
                    tool_result = str(result)
                
                called_any_tools = True
                
                # Check if it's empty
                try:
                    data = json.loads(tool_result)
                    if "error" not in data and not (isinstance(data.get("results"), list) and len(data["results"]) == 0):
                        has_valid_data = True
                except:
                    has_valid_data = True  # If it doesn't parse to JSON, treat it as some valid textual data
                
                await _notify_step(on_step, "tool_result", {"result": tool_result})
                
                # Feed result back into conversation
                conversation.append({
                    "role": "assistant",
                    "content": f"Called {tool_name} with {tool_args}"
                })
                conversation.append({
                    "role": "user",
                    "content": f"Tool result: {tool_result}"
                })
                
            except Exception as e:
                # Tool call failed (unknown tool, invalid args, etc.)
                error_msg = f"Error calling {tool_name}: {str(e)}"
                await _notify_step(on_step, "tool_error", {"error": error_msg})
                
                # Feed error back so agent can self-correct
                conversation.append({
                    "role": "assistant",
                    "content": f"Attempted to call {tool_name} with {tool_args}"
                })
                conversation.append({
                    "role": "user",
                    "content": f"Error: {error_msg}"
                })
        else:
            raise RuntimeError(f"Agent produced an invalid action type: {action}")
    
    # Max iterations reached without final answer
    raise RuntimeError(
        f"Agent did not produce a final answer within {max_iterations} iterations"
    )


def _default_step_handler(step_type: str, data: dict[str, Any]) -> None:
    """
    Default step callback that prints each step to console.
    
    Provides visibility into the agent's decision-making during execution.
    """
    if step_type == "tool_call":
        print(f"→ Calling {data['tool']} with {data['arguments']}")
    elif step_type == "tool_result":
        result_preview = str(data['result'])[:200]
        if len(str(data['result'])) > 200:
            result_preview += "..."
        print(f"← Result: {result_preview}")
    elif step_type == "tool_error":
        print(f"✗ {data['error']}")
    elif step_type == "final":
        print(f"✓ Final answer: {data['answer']}")
    elif step_type == "unknown_action":
        print(f"? Unknown action: {data['decision']}")


async def run_loop(*args, **kwargs):
    """
    Run the agent's decide → act → observe loop with observability tracing.
    """
    with MetricsLogger.start_span("agent_run_loop"):
        return await _run_loop_inner(*args, **kwargs)