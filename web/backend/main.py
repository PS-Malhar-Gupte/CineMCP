"""
FastAPI backend for CineMCP web interface.

Provides WebSocket endpoint for real-time chat with the movie agent.
Integrates with the existing agent logic.
"""

import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Import agent components
import sys
sys.path.insert(0, str(project_root))

from agent.config import MODEL_NAME, MAX_LOOP_ITERATIONS, SYSTEM_PROMPT
from agent.mcp_connection import connect
from agent.llm_client import decide, reflect
from agent.loop import run_loop
from agent.evaluation import EvaluationEngine
from agent.observability import set_request_id, get_spans
from web.backend.mcp_manager import MCPSessionManager
from pydantic import BaseModel


class ConnectionManager:
    """Manages WebSocket connections and MCP session."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.mcp_manager = MCPSessionManager()
    
    async def connect_ws(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
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


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with the movie agent.
    
    Message format:
    - From client: {"type": "message", "content": "user message"}
    - To client: {"type": "thinking"} | {"type": "tool_call", "tool": "...", "args": {...}} | 
                 {"type": "tool_result", "result": "..."} | {"type": "response", "content": "..."}
    """
    await manager.connect_ws(websocket)
    
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
            
            # Send thinking indicator
            await manager.send_message(websocket, {"type": "thinking"})
            
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
                # Run the agent loop with checked out session
                async with manager.mcp_manager.get_session() as session:
                    draft_answer, full_conversation = await run_loop(
                        session=session,
                        user_message=user_message,
                        system_prompt=SYSTEM_PROMPT,
                        model_name=MODEL_NAME,
                        max_iterations=MAX_LOOP_ITERATIONS,
                        decide_fn=decide,
                        on_step=send_step
                    )
                
                # One-shot reflection pass
                history = full_conversation + [
                    {"role": "assistant", "content": draft_answer}
                ]
                
                reflection_result = await asyncio.to_thread(reflect, history, draft_answer, MODEL_NAME)
                
                if reflection_result.get("ok"):
                    final_answer = draft_answer
                else:
                    corrected = reflection_result.get("corrected_answer", draft_answer)
                    meta_keywords = ["please call", "original answer", "general knowledge", "should be based on", "tool call", "direct tool call"]
                    if any(kw in str(corrected).lower() for kw in meta_keywords):
                        final_answer = draft_answer
                    else:
                        final_answer = corrected
                
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

                
            except RuntimeError as e:
                # Max iterations or other error
                await manager.send_message(websocket, {
                    "type": "error",
                    "content": str(e)
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)