"""
FastAPI backend for CineMCP web interface.

Provides WebSocket endpoint for real-time chat with the movie agent.
Integrates with the existing agent logic.
"""

import asyncio
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Import agent components
import sys
sys.path.insert(0, str(project_root))

from agent.config import MODEL_NAME, MAX_LOOP_ITERATIONS, SYSTEM_PROMPT, MAX_HISTORY_TURNS
from agent.mcp_connection import connect
from agent.llm_client import decide, reflect
from agent.loop import run_loop
from agent.evaluation import EvaluationEngine
from agent.observability import set_request_id, get_spans
from agent.conversation import ConversationState
from agent.conversation_store import get_conversation_store
from agent.memory import get_memory_provider
from web.backend.mcp_manager import MCPSessionManager
from pydantic import BaseModel


class ConnectionManager:
    """Manages WebSocket connections, per-connection conversation state, and the MCP session."""
    
    def __init__(self):
        # Per-connection ConversationState is still used as the in-process
        # working copy for building each turn's prompt, but the durable
        # identity that survives a reconnect is session_id, not the
        # WebSocket object - a dropped connection gets a *new*
        # ConversationState here, but re-hydrates it from conversation_store
        # using the client-supplied session_id (see connect_ws below), so
        # multi-turn context survives the reconnect-with-backoff behavior
        # the frontend already does.
        self.connections: dict[WebSocket, dict] = {}
        self.mcp_manager = MCPSessionManager()
        # Durable, TTL-aware, shared across CLI + all web connections/workers
        # (Redis by default; falls back to the local JSON file if
        # MEMORY_BACKEND=local or Redis is unreachable - see agent/memory.py
        # and agent/conversation_store.py for the fallback logic).
        memory_file = project_root / ".cine_memory.json"
        self.memory_service = get_memory_provider(local_persist_path=str(memory_file))
        self.conversation_store = get_conversation_store(max_turns=MAX_HISTORY_TURNS)
    
    async def connect_ws(self, websocket: WebSocket) -> str:
        """
        Accept the connection, resolve its session_id, and rehydrate
        conversation history for that session. Returns the resolved
        session_id so the caller can send it back to the client (important
        when the server had to generate one - the client must persist it
        to get continuity on the *next* connection).
        """
        await websocket.accept()
        # The frontend generates a session_id client-side (localStorage) and
        # sends it as ?session_id=... so reconnects/refreshes resolve back
        # to the same durable history. If it's ever missing (older client,
        # direct API use, etc.) we mint one so the connection still works,
        # just without continuity until the client starts sending it back.
        session_id = websocket.query_params.get("session_id") or str(uuid.uuid4())
        
        conv_state = ConversationState(max_turns=MAX_HISTORY_TURNS)
        stored_history = await self.conversation_store.get_history(session_id)
        if stored_history:
            conv_state.load(stored_history)
        
        self.connections[websocket] = {
            "conv_state": conv_state,
            "session_id": session_id
        }
        return session_id
    
    def disconnect(self, websocket: WebSocket):
        self.connections.pop(websocket, None)
    
    def get_conv_state(self, websocket: WebSocket) -> ConversationState:
        return self.connections[websocket]["conv_state"]
    
    def get_session_id(self, websocket: WebSocket) -> str:
        return self.connections[websocket]["session_id"]
    
    async def initialize_mcp(self):
        """Initialize MCP connection if not already connected."""
        await self.mcp_manager.initialize()
    
    async def cleanup_mcp(self):
        """Cleanup MCP connection."""
        await self.mcp_manager.cleanup()
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Send a JSON message to a specific WebSocket client."""
        await websocket.send_json(message)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    try:
        await manager.initialize_mcp()
        print(f"✅ MCP session initialized with {len(manager.mcp_manager.tools)} tools")
    except Exception as e:
        print(f"❌ Failed to initialize MCP: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    # Shutdown
    await manager.cleanup_mcp()
    print("MCP session cleaned up")


app = FastAPI(title="CineMCP API", lifespan=lifespan)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "tools": len(manager.mcp_manager.tools),
        "model": MODEL_NAME
    }

class EvaluateRequest(BaseModel):
    query: str
    response: str
    context: str = None

# Instantiate global evaluation engine
eval_engine = EvaluationEngine()

@app.post("/evaluate")
async def evaluate_response(req: EvaluateRequest):
    """Evaluate an agent response against a query."""
    set_request_id()
    metrics = await eval_engine.evaluate_all(req.query, req.response, req.context)
    return {"metrics": metrics}


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """
    Return stored conversation turns for a session so the frontend can
    hydrate the chat UI on page load, without waiting for the WebSocket
    handshake and a first message round-trip.
    """
    history = await manager.conversation_store.get_history(session_id)
    return {"session_id": session_id, "history": history}


@app.delete("/api/history/{session_id}")
async def clear_history(session_id: str):
    """Clear stored history for a session (backs the frontend's 'New conversation' action)."""
    await manager.conversation_store.clear(session_id)
    return {"session_id": session_id, "cleared": True}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with the movie agent.
    
    Message format:
    - From client: {"type": "message", "content": "user message"}
    - To client: {"type": "thinking"} | {"type": "tool_call", "tool": "...", "args": {...}} | 
                 {"type": "tool_result", "result": "..."} | {"type": "response", "content": "..."}
    """
    session_id = await manager.connect_ws(websocket)
    # Tell the client which session_id this connection resolved to - it
    # must persist this (localStorage) so a future reconnect/refresh sends
    # it back and gets the same conversation history. Doing this before
    # the first message means even a client that had no session_id yet
    # (first-ever visit) is covered from the very first turn.
    await manager.send_message(websocket, {"type": "session", "session_id": session_id})
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") != "message":
                continue
            
            user_message = data.get("content", "").strip()
            if not user_message:
                continue
            
            # Set request ID for tracing
            set_request_id()
            
            conv_state = manager.get_conv_state(websocket)
            session_id = manager.get_session_id(websocket)
            
            # Send thinking indicator
            await manager.send_message(websocket, {"type": "thinking"})
            
            # Check memory cache for an exact repeat of this question before
            # running the full agent loop - mirrors agent/main.py's CLI
            # behavior, and shares the same underlying Redis/local cache.
            cache_key = manager.memory_service.generate_key(user_message)
            cached_answer = await manager.memory_service.get(session_id, cache_key)
            if cached_answer:
                conv_state.add_turn(user_message, cached_answer)
                await manager.conversation_store.append_turn(session_id, user_message, cached_answer)
                await manager.send_message(websocket, {
                    "type": "response",
                    "content": cached_answer,
                    "cached": True
                })
                continue
            
            # Define step callback to send real-time updates
            async def send_step(step_type: str, step_data: dict):
                if step_type == "tool_call":
                    await manager.send_message(websocket, {
                        "type": "tool_call",
                        "tool": step_data["tool"],
                        "args": step_data["arguments"]
                    })
                elif step_type == "tool_result":
                    await manager.send_message(websocket, {
                        "type": "tool_result",
                        "result": step_data["result"][:500]  # Truncate for UI
                    })
                elif step_type == "tool_error":
                    await manager.send_message(websocket, {
                        "type": "tool_error",
                        "error": step_data["error"]
                    })
            
            try:
                # Wrapped in a hard timeout as defense-in-depth: without this,
                # a hung MCP session checkout (e.g. pool exhaustion - a prior
                # request's session never returned to the queue) or a runaway
                # chain of LLM retries could block this request indefinitely
                # with no way to recover except a page refresh, since nothing
                # else in this handler would ever time out on its own.
                async def _run_agent_turn():
                    # Run the agent loop with checked out session
                    async with manager.mcp_manager.get_session() as session:
                        draft_answer, full_conversation, tools_used = await run_loop(
                            session=session,
                            user_message=user_message,
                            system_prompt=SYSTEM_PROMPT,
                            model_name=MODEL_NAME,
                            max_iterations=MAX_LOOP_ITERATIONS,
                            decide_fn=decide,
                            on_step=send_step,
                            chat_history=conv_state.get_history()
                        )

                    # One-shot reflection pass
                    history = full_conversation + [
                        {"role": "assistant", "content": draft_answer}
                    ]

                    reflection_result = await asyncio.to_thread(reflect, history, draft_answer, MODEL_NAME)

                    if reflection_result.get("ok"):
                        resolved_answer = draft_answer
                    else:
                        corrected = reflection_result.get("corrected_answer", draft_answer)
                        meta_keywords = ["please call", "original answer", "general knowledge", "should be based on", "tool call", "direct tool call"]
                        if any(kw in str(corrected).lower() for kw in meta_keywords):
                            resolved_answer = draft_answer
                        else:
                            resolved_answer = corrected

                    return resolved_answer, tools_used

                final_answer, tools_used = await asyncio.wait_for(_run_agent_turn(), timeout=180)

                # Save the turn to this connection's conversation history
                # (in-process, for the next prompt on *this* connection) and
                # to the durable conversation store (so a reconnect under
                # the same session_id picks it up even on a fresh
                # ConnectionManager entry). Cache write is skipped
                # internally for fallback/error answers - see
                # agent/memory.py.is_cacheable - and TTL is picked based on
                # whether a date-sensitive tool contributed to the answer.
                conv_state.add_turn(user_message, final_answer)
                await manager.conversation_store.append_turn(session_id, user_message, final_answer)
                await manager.memory_service.set(session_id, cache_key, final_answer, tools_used=tools_used)

                # capture spans NOW while still in the main request context
                current_spans = get_spans()
                
                # Send final response
                await manager.send_message(websocket, {
                    "type": "response",
                    "content": final_answer
                })
                
                # Emit evaluation metrics asynchronously so it doesn't block
                async def emit_eval(spans_to_emit):
                    try:
                        metrics = await eval_engine.evaluate_all(user_message, final_answer)
                        await manager.send_message(websocket, {
                            "type": "evaluation",
                            "metrics": metrics,
                            "observability": spans_to_emit
                        })
                    except Exception as e:
                        print(f"Error emitting evaluation metrics: {e}")
                        
                asyncio.create_task(emit_eval(current_spans))

                
            except Exception as e:
                # Previously this only caught RuntimeError - anything else
                # (a requests.exceptions.Timeout/ConnectionError from a slow
                # or dropped Groq call, an MCP session error, etc.) propagated
                # straight out of this handler uncaught. That crashed the
                # request silently: no "error" message ever reached the
                # frontend, so isThinking/currentToolCall in ChatContainer
                # never got cleared and the UI was stuck on the typing
                # indicator with no way to recover short of a page refresh.
                # Catching Exception broadly here guarantees the frontend
                # always gets a message back, whatever actually went wrong.
                print(f"[WebSocket] Unhandled error while processing message: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await manager.send_message(websocket, {
                        "type": "error",
                        "content": f"Something went wrong processing that request ({type(e).__name__}). Please try again."
                    })
                except Exception:
                    # If we can't even send on this socket, it's already dead -
                    # nothing more to do for this iteration.
                    pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)