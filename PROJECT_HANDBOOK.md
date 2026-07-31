# CineMCP Project Handbook

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Directory Structure](#directory-structure)
5. [Setup Instructions](#setup-instructions)
6. [Configuration](#configuration)
7. [Agent System](#agent-system)
8. [MCP Server & Tools](#mcp-server--tools)
9. [Web Interface](#web-interface)
10. [API Reference](#api-reference)
11. [Development Workflow](#development-workflow)
12. [Troubleshooting](#troubleshooting)
13. [Deployment](#deployment)

---

## Project Overview

**CineMCP** is an AI-powered movie information agent with dual interfaces:
- **CLI Mode**: Terminal-based conversational agent
- **Web UI**: Modern React-based chat interface with real-time WebSocket communication

The agent uses MCP (Model Context Protocol) to access movie databases (OMDb, TMDb) and provides:
- Movie search and details
- Latest releases (including India-specific releases)
- Movie recommendations
- Streaming availability information
- Box office data

**Key Features:**
- Multi-source movie data (OMDb + TMDb)
- Cloud LLM support (OpenRouter, OpenAI-compatible APIs)
- Real-time chat with streaming responses
- Clean, modern React UI
- Async Python backend with FastAPI

**Repository:** https://github.com/PS-Malhar-Gupte/CineMCP

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
        CLI Interface              Web Interface
               │                          │
               │                   ┌──────▼──────┐
               │                   │   React UI   │
               │                   │  (Port 5173) │
               │                   └──────┬──────┘
               │                          │ WebSocket
               │                   ┌──────▼──────────┐
               │                   │  FastAPI Backend │
               │                   │   (Port 8000)    │
               │                   └──────┬──────────┘
               │                          │
               └──────────┬───────────────┘
                          │
                   ┌──────▼──────┐
                   │ Agent Loop   │
                   │ (LLM Client) │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ MCP Session  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  MCP Server  │
                   │  (FastMCP)   │
                   └──────┬──────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
    │  OMDb   │     │  TMDb   │     │  HTTP   │
    │   API   │     │   API   │     │ Request │
    └─────────┘     └─────────┘     └─────────┘
```


### Component Interactions

1. **User Interface Layer**
   - CLI: Direct Python script execution (`agent/main.py`)
   - Web: React frontend → FastAPI backend via HTTP/WebSocket

2. **Agent Layer**
   - LLM Client: Manages API calls to cloud LLM providers
   - Agent Loop: Orchestrates conversation flow and tool execution
   - Config: System prompts, model selection, behavior tuning

3. **MCP Layer**
   - MCP Connection: Establishes subprocess connection to server
   - MCP Session: Manages tool discovery and execution
   - MCP Server: FastMCP-based server exposing movie tools

4. **Data Layer**
   - OMDb API: Primary movie database (older movies, detailed info)
   - TMDb API: Secondary database (new releases 2024-2026, India releases)
   - HTTP Utils: Generic web requests for streaming availability

---

## Technology Stack

### Backend (Agent + Server)
- **Python 3.13**
- **FastMCP**: MCP server implementation
- **OpenAI SDK**: LLM API client (OpenRouter/OpenAI-compatible)
- **python-dotenv**: Environment variable management
- **httpx**: Async HTTP client

### Web Backend
- **FastAPI**: Modern async web framework
- **WebSockets**: Real-time bidirectional communication
- **Uvicorn**: ASGI server
- **MCP Client SDK**: Python MCP client library


### Web Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Icon library
- **Native WebSocket API**: Real-time communication

### External APIs
- **OMDb API**: Movie database (requires API key)
- **TMDb API**: The Movie Database (requires API key)
- **OpenRouter / OpenAI**: LLM providers (requires API key)

---

## Directory Structure

```
CineMCP/
├── agent/                      # Core agent implementation
│   ├── __init__.py
│   ├── main.py                 # CLI entry point
│   ├── loop.py                 # Agent conversation loop
│   ├── llm_client.py           # LLM API client
│   ├── config.py               # Configuration & system prompt
│   └── mcp_connection.py       # MCP server connection manager
│
├── server/                     # MCP server implementation
│   ├── __init__.py
│   ├── app.py                  # FastMCP server entry point
│   ├── movie_tools.py          # OMDb/TMDb search tools
│   ├── release_tools.py        # India-specific release tools
│   └── http_utils.py           # HTTP request utilities
│
├── web/                        # Web interface
│   ├── backend/
│   │   ├── main.py             # FastAPI + WebSocket server
│   │   └── requirements.txt    # Python dependencies
│   │
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx         # Main React component
│       │   ├── main.jsx        # React entry point
│       │   └── index.css       # Global styles
│       ├── index.html
│       ├── package.json
│       └── vite.config.js
│
├── .env                        # Environment variables (NOT in git)
├── .env.example                # Template for .env
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies (agent)
├── README.md                   # Quick start guide
└── PROJECT_HANDBOOK.md         # This file
```


---

## Setup Instructions

### Prerequisites
- Python 3.13+ installed
- Node.js 18+ and npm (for web UI)
- API keys for:
  - OMDb API (http://www.omdbapi.com/apikey.aspx)
  - TMDb API (https://www.themoviedb.org/settings/api)
  - OpenRouter or OpenAI (https://openrouter.ai/)

### Initial Setup

#### 1. Clone Repository
```bash
git clone https://github.com/PS-Malhar-Gupte/CineMCP.git
cd CineMCP
```

#### 2. Configure Environment Variables
```bash
# Copy example file
copy .env.example .env

# Edit .env with your API keys
notepad .env
```

Required variables:
```
OMDB_API_KEY=your_omdb_key_here
TMDB_API_KEY=your_tmdb_key_here
OPENAI_API_KEY=your_openrouter_or_openai_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

#### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Test CLI Agent
```bash
python -m agent.main
```

### Web Interface Setup

#### 1. Install Backend Dependencies
```bash
cd web/backend
pip install -r requirements.txt
```

#### 2. Install Frontend Dependencies
```bash
cd ../frontend
npm install
```

#### 3. Start Development Servers

Terminal 1 - Backend:
```bash
cd web/backend
uvicorn main:app --reload
```

Terminal 2 - Frontend:
```bash
cd web/frontend
npm run dev
```

#### 4. Access Web UI
Open browser to: http://localhost:5173

---

## Configuration


### Environment Variables (.env)

| Variable | Purpose | Example |
|----------|---------|---------|
| `OMDB_API_KEY` | OMDb API authentication | `abc12345` |
| `TMDB_API_KEY` | TMDb API authentication | `xyz67890abcdef...` |
| `OPENAI_API_KEY` | LLM provider authentication | `sk-or-v1-...` (OpenRouter) |
| `OPENAI_BASE_URL` | LLM API endpoint | `https://openrouter.ai/api/v1` |

### Agent Configuration (agent/config.py)

#### Model Selection
```python
MODEL_NAME = "deepseek/deepseek-chat"  # Fast, affordable
# Alternatives:
# "openai/gpt-4o"           # More capable, expensive
# "anthropic/claude-3.5"     # High quality
# "meta-llama/llama-3.1-70b" # Open source
```

#### System Prompt

**Current Version (v3)** - Optimized for global search with India fallback:

```python
SYSTEM_PROMPT = """You are a helpful movie information assistant with access to...

CRITICAL TOOL SELECTION RULES:
1. For questions about NEW movies (2024-2026):
   - FIRST check now_playing_india() - it has the latest releases
   - If not found, then use search_movie()

2. For questions about older movies or specific titles:
   - Use search_movie() directly

3. For "latest releases" or "recent movies" questions:
   - ALWAYS start with now_playing_india()
   - It contains 2024-2026 releases that OMDb doesn't have

4. For movie recommendations:
   - If user asks for "latest" or "recent" → now_playing_india()
   - If user asks by genre/director → search_movie() first, then filter
   - For India-specific: now_playing_india()

Always provide complete information with proper formatting.
"""
```

**Why This Version Works:**
- Prioritizes `now_playing_india()` for 2024-2026 movies
- OMDb (via `search_movie()`) lacks recent releases
- TMDb (via `now_playing_india()`) has up-to-date data
- Prevents agent from missing new Christopher Nolan, Denis Villeneuve releases


#### System Prompt Evolution

**Version 1 (Initial)** - Problem: Always used India-specific tool
```python
# Issue: Agent called now_playing_india() for EVERYTHING
# Even for "Christopher Nolan movies" or "best sci-fi films"
```

**Version 2 (First Fix)** - Problem: Stopped calling tools
```python
# Issue: Agent said "I'll check for you..." but never actually called tools
# Needed explicit instructions to USE the tools
```

**Version 3 (Current)** - Solution: Explicit decision tree
```python
# Fix: Clear rules for WHEN to use each tool
# Result: Proper tool selection based on query type
```

### LLM Provider Configuration

#### OpenRouter (Recommended)
```python
# agent/llm_client.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = "deepseek/deepseek-chat"  # 3-5s response time
```

**Why OpenRouter:**
- Fast responses (3-5s vs 120s+ with local Ollama)
- Multiple model options
- Pay-per-use pricing
- Good for development and production

#### Local Ollama (Not Recommended)
```python
# Previous setup - SLOW
OPENAI_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME = "llama3.2"  # 120+ second responses
```

**Why Not Ollama:**
- 120+ second response times
- Frequent timeouts
- Resource intensive
- Poor user experience

---

## Agent System

### Core Components

#### 1. Main Entry Point (agent/main.py)
```python
# Loads .env variables
# Initializes MCP connection
# Starts conversation loop
```

**Key Features:**
- Environment variable loading via `python-dotenv`
- Async MCP session management
- Clean error handling


#### 2. Agent Loop (agent/loop.py)
```python
async def run_agent_loop(mcp_session: ClientSession)
```

**Responsibilities:**
- Manages conversation state (message history)
- Handles tool execution requests from LLM
- Formats tool results for LLM
- Implements streaming response display
- Maintains conversation context

**Flow:**
1. Accept user input
2. Send messages + available tools to LLM
3. Process LLM response:
   - If text: Display and continue
   - If tool call: Execute via MCP → feed result back to LLM
4. Loop until complete response

#### 3. LLM Client (agent/llm_client.py)
```python
async def call_llm(messages, tools=None) -> dict
async def call_llm_stream(messages, tools=None)
```

**Features:**
- OpenAI-compatible API client
- Streaming support for real-time responses
- Tool/function calling support
- Configurable via environment variables

**Usage:**
```python
response = await call_llm(
    messages=[{"role": "user", "content": "Latest Nolan films?"}],
    tools=mcp_tools
)
```

#### 4. Configuration (agent/config.py)
```python
MODEL_NAME = "deepseek/deepseek-chat"
SYSTEM_PROMPT = "..."  # Behavior instructions
```

**Tuning Points:**
- Model selection (speed vs quality vs cost)
- System prompt (tool selection logic)
- Temperature (creativity vs consistency)
- Max tokens (response length)

#### 5. MCP Connection (agent/mcp_connection.py)
```python
@asynccontextmanager
async def connect_to_server()
```

**Critical Fix:**
```python
# ❌ Old (broken): ImportError
command="python", args=["server/app.py"]

# ✅ New (working): Module execution
command="python", args=["-m", "server.app"], cwd=str(project_root)
```

**Why This Works:**
- Runs server as module: `python -m server.app`
- Sets working directory to project root
- Python can resolve `from server.movie_tools import ...`


---

## MCP Server & Tools

### Server Implementation (server/app.py)

```python
from fastmcp import FastMCP

mcp = FastMCP("CineMCP Movie Server")

# Tool imports
from server.movie_tools import search_movie, get_movie_details
from server.release_tools import now_playing_india

# Automatic tool registration via FastMCP decorators
```

**FastMCP Benefits:**
- Automatic tool registration from decorated functions
- Built-in stdio transport
- Type hints → JSON schemas
- Simple async support

### Available Tools

#### 1. search_movie
**Purpose:** Search for movies in OMDb database

**Parameters:**
- `title` (string, required): Movie title to search
- `year` (string, optional): Release year filter

**Returns:**
```json
{
  "Title": "Inception",
  "Year": "2010",
  "imdbID": "tt1375666",
  "Type": "movie",
  "Poster": "https://..."
}
```

**Use Cases:**
- Finding specific movies by title
- Getting OMDb IDs for detailed lookups
- Searching older movies (pre-2024)

**Example:**
```python
result = await mcp_session.call_tool("search_movie", {"title": "Inception"})
```

#### 2. get_movie_details
**Purpose:** Get comprehensive movie information from OMDb

**Parameters:**
- `imdb_id` (string, required): IMDb ID (e.g., "tt1375666")

**Returns:**
```json
{
  "Title": "Inception",
  "Year": "2010",
  "Director": "Christopher Nolan",
  "Actors": "Leonardo DiCaprio, ...",
  "Plot": "A thief who steals...",
  "imdbRating": "8.8",
  "BoxOffice": "$292,576,195",
  "Runtime": "148 min",
  "Genre": "Action, Sci-Fi, Thriller"
}
```


**Use Cases:**
- Getting full movie details
- Ratings and reviews
- Cast and crew information
- Box office numbers

**Example:**
```python
result = await mcp_session.call_tool("get_movie_details", {"imdb_id": "tt1375666"})
```

#### 3. now_playing_india
**Purpose:** Get current and recent theatrical releases in India from TMDb

**Parameters:** None

**Returns:**
```json
[
  {
    "title": "Oppenheimer",
    "release_date": "2023-07-21",
    "overview": "The story of J. Robert Oppenheimer...",
    "vote_average": 8.2,
    "id": 872585
  },
  ...
]
```

**Use Cases:**
- Finding 2024-2026 releases (OMDb doesn't have these)
- India-specific theatrical releases
- Latest Christopher Nolan, Denis Villeneuve films
- Current trending movies

**Why Critical:**
- OMDb API lags behind by months/years
- TMDb has real-time release data
- Essential for "what's new" queries

**Example:**
```python
result = await mcp_session.call_tool("now_playing_india", {})
```

#### 4. get_streaming_info
**Purpose:** Check where a movie is available for streaming

**Parameters:**
- `title` (string, required): Movie title

**Returns:**
```json
{
  "available_on": ["Netflix", "Amazon Prime"],
  "rent_options": ["YouTube", "Google Play"],
  "free_options": []
}
```

**Note:** Requires external API or web scraping (implementation varies)

#### 5. get_movie_recommendations
**Purpose:** Get similar movie recommendations

**Parameters:**
- `movie_id` (string, required): TMDb movie ID
- `count` (integer, optional): Number of recommendations

**Returns:** Array of similar movies with scores


### Tool Implementation Details

#### movie_tools.py
```python
@mcp.tool()
async def search_movie(title: str, year: str = None) -> dict:
    """Search for movies using OMDb API"""
    params = {"apikey": OMDB_API_KEY, "s": title}
    if year:
        params["y"] = year
    
    response = httpx.get("http://www.omdbapi.com/", params=params)
    return response.json()
```

**Key Points:**
- Uses `@mcp.tool()` decorator for auto-registration
- Type hints generate JSON schema automatically
- Async for non-blocking I/O
- Error handling for API failures

#### release_tools.py
```python
@mcp.tool()
async def now_playing_india() -> list:
    """Get movies currently in theaters in India"""
    url = "https://api.themoviedb.org/3/movie/now_playing"
    params = {
        "api_key": TMDB_API_KEY,
        "region": "IN",
        "language": "en-US"
    }
    
    response = httpx.get(url, params=params)
    return response.json()["results"]
```

**Key Points:**
- Region filter: `IN` for India
- Returns 20 movies per request
- Includes vote averages and release dates
- Updated daily by TMDb

---

## Web Interface

### Architecture Overview

```
React Frontend (Port 5173)
        ↕ WebSocket
FastAPI Backend (Port 8000)
        ↕ Async
  Agent Loop + MCP
```

### Backend (web/backend/main.py)

#### FastAPI Application
```python
app = FastAPI(title="CineMCP Chat API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```


#### Lifespan Management
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP connection on startup"""
    await manager.initialize_mcp()
    yield
    # Cleanup on shutdown

app = FastAPI(lifespan=lifespan)
```

**Critical Fix:** Using `lifespan` instead of deprecated `@app.on_event("startup")`

**Why This Matters:**
- Proper async context management
- MCP session lives for entire app lifetime
- Clean shutdown handling
- Avoids `RuntimeError: Attempted to exit cancel scope in different task`

#### WebSocket Endpoint
```python
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        # Receive user message
        data = await websocket.receive_json()
        user_message = data["message"]
        
        # Run agent loop
        response = await run_agent_with_message(user_message)
        
        # Stream response chunks
        for chunk in response:
            await websocket.send_json({"type": "chunk", "content": chunk})
        
        # Send completion signal
        await websocket.send_json({"type": "done"})
```

**Features:**
- Real-time bidirectional communication
- Streaming response support
- Error handling and reconnection
- JSON message format

#### Connection Manager
```python
class ConnectionManager:
    def __init__(self):
        self.mcp_session = None
        self.mcp_context = None
    
    async def initialize_mcp(self):
        """Start MCP server connection"""
        self.mcp_context = connect_to_server()
        self.mcp_session = await self.mcp_context.__aenter__()
    
    async def get_tools(self):
        """Fetch available MCP tools"""
        return await self.mcp_session.list_tools()
```

**Responsibilities:**
- MCP session lifecycle management
- Tool discovery and caching
- Connection state tracking


### Frontend (web/frontend/src/App.jsx)

#### Component Structure
```jsx
function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [ws, setWs] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  
  // WebSocket connection management
  // Message sending/receiving
  // UI rendering
}
```

#### WebSocket Connection
```jsx
useEffect(() => {
  const websocket = new WebSocket("ws://localhost:8000/ws/chat")
  
  websocket.onopen = () => {
    setIsConnected(true)
  }
  
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === "chunk") {
      // Append to current streaming message
      appendToLastMessage(data.content)
    } else if (data.type === "done") {
      // Mark message as complete
      setIsStreaming(false)
    }
  }
  
  websocket.onerror = () => {
    setIsConnected(false)
  }
  
  return () => websocket.close()
}, [])
```

#### Message Sending
```jsx
const sendMessage = async () => {
  if (!input.trim() || !ws || !isConnected) return
  
  // Add user message to UI
  const userMsg = { role: "user", content: input }
  setMessages(prev => [...prev, userMsg])
  
  // Send to backend
  ws.send(JSON.stringify({ message: input }))
  
  // Prepare for assistant response
  setMessages(prev => [...prev, { role: "assistant", content: "" }])
  setIsStreaming(true)
  setInput("")
}
```

#### UI Components

**Chat Container:**
```jsx
<div className="flex flex-col h-screen bg-gray-900 text-white">
  <Header />
  <MessageList messages={messages} />
  <InputArea onSend={sendMessage} />
</div>
```

**Message Rendering:**
```jsx
{messages.map((msg, idx) => (
  <div key={idx} className={msg.role === "user" ? "user-msg" : "assistant-msg"}>
    <div className="avatar">
      {msg.role === "user" ? <User /> : <Bot />}
    </div>
    <div className="content">
      {msg.content}
    </div>
  </div>
))}
```


**Styling (Tailwind CSS):**
```css
/* index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

.user-msg {
  @apply bg-blue-600 rounded-lg p-4 ml-auto max-w-2xl;
}

.assistant-msg {
  @apply bg-gray-800 rounded-lg p-4 mr-auto max-w-2xl;
}
```

#### Key Features

1. **Real-time Streaming**
   - Messages appear character-by-character
   - Smooth user experience
   - No loading spinners needed

2. **Connection Status**
   - Visual indicator for WebSocket state
   - Auto-reconnection attempts
   - Error messages on disconnect

3. **Responsive Design**
   - Mobile-friendly layout
   - Flexbox-based structure
   - Scrollable message area

4. **Message History**
   - Persistent during session
   - Auto-scroll to latest message
   - Clear visual distinction between roles

---

## API Reference

### WebSocket API

#### Connection
```
ws://localhost:8000/ws/chat
```

#### Message Format - Client to Server
```json
{
  "message": "What are the latest Christopher Nolan movies?"
}
```

#### Message Format - Server to Client

**Streaming Chunk:**
```json
{
  "type": "chunk",
  "content": "Based on the latest releases..."
}
```

**Completion Signal:**
```json
{
  "type": "done"
}
```

**Error:**
```json
{
  "type": "error",
  "message": "Connection to MCP server failed"
}
```

### REST API (Future)

Currently not implemented, but planned:

```
GET  /api/health          - Health check
GET  /api/tools           - List available tools
POST /api/chat            - Single message (non-streaming)
GET  /api/history         - Get conversation history
```


---

## Development Workflow

### Running the Project

#### CLI Mode (Quick Testing)
```bash
# From project root
python -m agent.main

# Start chatting
> What's the latest from Christopher Nolan?
> Tell me about Inception
> Recommend sci-fi movies
```

#### Web Mode (Full Development)

**Terminal 1 - Backend:**
```bash
cd web/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd web/frontend
npm run dev
```

**Browser:**
- Open http://localhost:5173
- Chat interface should appear
- Check browser console for WebSocket connection

### Making Changes

#### Modifying Agent Behavior

**File:** `agent/config.py`

```python
# Change system prompt for different behavior
SYSTEM_PROMPT = """
Your custom instructions here...
"""

# Switch models
MODEL_NAME = "openai/gpt-4o"  # More powerful
MODEL_NAME = "anthropic/claude-3.5-sonnet"  # Alternative
```

**Testing:**
```bash
python -m agent.main
```

#### Adding New Tools

**1. Create tool function in server/**
```python
# server/new_tools.py
from fastmcp import mcp

@mcp.tool()
async def get_actor_filmography(actor_name: str) -> list:
    """Get all movies for an actor"""
    # Implementation here
    return results
```

**2. Import in server/app.py**
```python
from server.new_tools import get_actor_filmography
```

**3. Restart and test**
```bash
python -m agent.main
> Show me Tom Hanks movies
```

#### Modifying Frontend UI

**File:** `web/frontend/src/App.jsx`

```jsx
// Change colors
<div className="bg-gray-900">  // → bg-slate-900

// Add new features
const [theme, setTheme] = useState("dark")

// Modify message styling
<div className="user-msg text-lg font-medium">
```

**Hot Reload:**
- Vite automatically reloads on save
- Check browser for changes
- Console logs for debugging


### Git Workflow

#### Committing Changes
```bash
# Check status
git status

# Stage specific files
git add agent/config.py
git add web/frontend/src/App.jsx

# Commit with descriptive message
git commit -m "Update system prompt for better tool selection"

# Push to GitHub
git push origin main
```

#### What NOT to Commit
```
# .gitignore ensures these are excluded:
.env                    # API keys - NEVER commit
__pycache__/           # Python cache
node_modules/          # Node dependencies
dist/                  # Build output
*.pyc                  # Compiled Python
.DS_Store              # Mac files
```

#### Branch Strategy (Recommended)
```bash
# Feature development
git checkout -b feature/actor-search
# ... make changes ...
git commit -m "Add actor filmography tool"
git push origin feature/actor-search

# Create pull request on GitHub
# Merge after review
```

### Testing Checklist

Before committing:

**CLI Agent:**
- [ ] `python -m agent.main` starts without errors
- [ ] Can search for movies
- [ ] Can get movie details
- [ ] Latest releases work (2024-2026 movies)
- [ ] Tool selection is correct

**Web Interface:**
- [ ] Backend starts: `uvicorn main:app --reload`
- [ ] Frontend starts: `npm run dev`
- [ ] WebSocket connects (check browser console)
- [ ] Can send messages
- [ ] Receives streaming responses
- [ ] No console errors

**Environment:**
- [ ] `.env` file has all required keys
- [ ] `.env` is NOT committed to git
- [ ] `.env.example` is up to date

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'server'"

**Cause:** MCP server not running as module

**Solution:**
```python
# agent/mcp_connection.py
StdioServerParameters(
    command="python",
    args=["-m", "server.app"],  # ✅ Run as module
    cwd=str(project_root),      # ✅ Set working directory
    env=None
)
```

**Verify:**
```bash
cd c:\Users\MalharGupte\Downloads\CineMCP
python -m server.app  # Should start MCP server
```


#### 2. "RuntimeError: Attempted to exit cancel scope in different task"

**Cause:** Deprecated `@app.on_event("startup")` usage

**Solution:**
```python
# web/backend/main.py - OLD (broken)
@app.on_event("startup")
async def startup_event():
    await manager.initialize_mcp()

# NEW (working)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.initialize_mcp()
    yield
    # cleanup here

app = FastAPI(lifespan=lifespan)
```

#### 3. Agent uses wrong tool (always now_playing_india)

**Cause:** System prompt doesn't guide tool selection

**Solution:** Update `agent/config.py`:
```python
SYSTEM_PROMPT = """
CRITICAL TOOL SELECTION RULES:
1. For NEW movies (2024-2026): Check now_playing_india() FIRST
2. For older movies: Use search_movie() directly
3. For "latest releases": ALWAYS start with now_playing_india()
"""
```

#### 4. LLM responses too slow (120+ seconds)

**Cause:** Using local Ollama

**Solution:** Switch to OpenRouter:
```python
# agent/config.py
MODEL_NAME = "deepseek/deepseek-chat"

# .env
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-your-key-here
```

**Result:** 3-5 second responses

#### 5. "WebSocket connection failed"

**Symptoms:**
- Frontend shows "Disconnected"
- Browser console: `WebSocket connection to 'ws://localhost:8000/ws/chat' failed`

**Checks:**
```bash
# Is backend running?
curl http://localhost:8000/

# Check backend logs
# Should see: "INFO: Application startup complete"
```

**Solution:**
```bash
# Restart backend
cd web/backend
uvicorn main:app --reload
```

#### 6. "npm: The term 'npm' is not recognized"

**Cause:** Node.js not installed

**Solution:**
1. Download from https://nodejs.org/
2. Install LTS version (18+)
3. Restart terminal
4. Verify: `npm --version`


#### 7. "401 Unauthorized" from APIs

**Cause:** Missing or invalid API keys

**Check .env file:**
```bash
# Should have all three
OMDB_API_KEY=your_key_here
TMDB_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

**Verify keys work:**
```bash
# Test OMDb
curl "http://www.omdbapi.com/?apikey=YOUR_KEY&s=Inception"

# Test TMDb
curl "https://api.themoviedb.org/3/movie/now_playing?api_key=YOUR_KEY&region=IN"

# Test OpenRouter
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer YOUR_KEY"
```

#### 8. Frontend shows blank page

**Checks:**
```bash
# Is Vite dev server running?
cd web/frontend
npm run dev

# Check browser console for errors
# F12 → Console tab

# Check if React is loaded
# Should see "Vite + React" in page title
```

**Common fixes:**
```bash
# Clear cache and reinstall
rm -rf node_modules
npm install

# Check for port conflicts
# Vite uses port 5173 by default
```

#### 9. Agent doesn't call tools

**Symptoms:**
- Agent says "I'll check..." but doesn't actually search
- No tool execution logs

**Cause:** System prompt doesn't emphasize tool usage

**Solution:**
```python
SYSTEM_PROMPT = """
You MUST use the available tools to answer questions.
NEVER say you'll check - ACTUALLY call the tools immediately.

Available tools:
- search_movie: Search OMDb
- get_movie_details: Get full info
- now_playing_india: Latest releases
"""
```

#### 10. Git push fails with "Permission denied"

**Windows PowerShell execution policy:**
```powershell
# Error: "cannot be loaded because running scripts is disabled"

# Solution:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Or use git commands directly:
git add .
git commit -m "Your message"
git push origin main
```


---

## Deployment

### Production Considerations

#### Backend Deployment

**Recommended Stack:**
- **Platform:** Railway, Render, or AWS EC2
- **Server:** Uvicorn with Gunicorn (multi-worker)
- **Environment:** Python 3.13+
- **Configuration:** Environment variables via platform UI

**Production Command:**
```bash
gunicorn web.backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

**Environment Variables:**
```
OMDB_API_KEY=prod_key_here
TMDB_API_KEY=prod_key_here
OPENAI_API_KEY=prod_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

#### Frontend Deployment

**Build for Production:**
```bash
cd web/frontend
npm run build
```

**Output:** `dist/` folder with static files

**Hosting Options:**

1. **Vercel (Recommended)**
   ```bash
   npm install -g vercel
   vercel --prod
   ```

2. **Netlify**
   ```bash
   netlify deploy --prod --dir=dist
   ```

3. **Static Server**
   ```bash
   npm install -g serve
   serve -s dist -p 5173
   ```

**Update WebSocket URL:**
```jsx
// src/App.jsx
const WS_URL = import.meta.env.PROD 
  ? "wss://your-backend.com/ws/chat"
  : "ws://localhost:8000/ws/chat"
```

#### Docker Deployment (Future)

**Dockerfile (Backend):**
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile (Frontend):**
```dockerfile
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
  
  frontend:
    build: ./web/frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```


### Security Checklist

**Before Production:**
- [ ] Remove all hardcoded API keys
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS (WSS for WebSocket)
- [ ] Set proper CORS origins (not `*`)
- [ ] Add rate limiting
- [ ] Implement authentication (if multi-user)
- [ ] Enable logging and monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Regular dependency updates
- [ ] Secure WebSocket connections

**CORS Configuration (Production):**
```python
# web/backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Monitoring

**Backend Health Check:**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mcp_connected": manager.mcp_session is not None,
        "timestamp": datetime.now().isoformat()
    }
```

**Metrics to Track:**
- WebSocket connection count
- Average response time
- Tool execution success rate
- API error rates
- LLM token usage

---

## Key Learning Points

### What Went Right

1. **FastMCP Integration**
   - Easy tool registration via decorators
   - Clean async support
   - Automatic JSON schema generation

2. **OpenRouter Switch**
   - 40x speed improvement (120s → 3s)
   - Multiple model options
   - Cost-effective for development

3. **React + WebSocket**
   - Real-time streaming responses
   - Modern, responsive UI
   - Good developer experience

4. **Module Execution Fix**
   - `python -m server.app` solved import issues
   - Proper working directory handling
   - Reliable subprocess management

### What Was Challenging

1. **System Prompt Tuning (3 iterations)**
   - V1: Too India-specific
   - V2: Didn't call tools
   - V3: Finally got tool selection right

2. **Async Context Management**
   - `@app.on_event` deprecation
   - Cancel scope errors
   - Required lifespan context manager

3. **Tool Selection Logic**
   - OMDb doesn't have 2024-2026 movies
   - TMDb required for recent releases
   - Needed explicit prioritization rules


### Design Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| FastMCP for server | Simple decorator-based API, good async support | MCP official SDK (more complex) |
| OpenRouter for LLM | Fast, multiple models, cost-effective | Local Ollama (too slow), OpenAI direct (expensive) |
| React + Vite | Modern, fast dev experience, hot reload | Plain HTML (not interactive), Next.js (overkill) |
| WebSocket for chat | Real-time streaming, bidirectional | SSE (one-way), Polling (inefficient) |
| Lifespan context | Modern FastAPI pattern, proper async | on_event (deprecated), global variables (messy) |
| Module execution | Fixes import resolution | Script path (doesn't work), sys.path hacks (fragile) |

---

## Future Enhancements

### Planned Features

1. **Conversation History**
   - Store chat history in database
   - Resume previous conversations
   - Export chat transcripts

2. **Multi-User Support**
   - User authentication
   - Per-user conversation storage
   - API rate limiting per user

3. **Advanced Search**
   - Filter by genre, year, rating
   - Sort by various criteria
   - Watchlist management

4. **Streaming Platform Integration**
   - Check Netflix, Prime, Disney+ availability
   - Direct links to streaming platforms
   - Price comparison for rentals

5. **Recommendation Engine**
   - Personalized suggestions
   - Based on watch history
   - Collaborative filtering

6. **Voice Interface**
   - Speech-to-text input
   - Text-to-speech responses
   - Hands-free operation

7. **Mobile App**
   - React Native version
   - Push notifications for new releases
   - Offline mode

8. **Analytics Dashboard**
   - Popular queries
   - Tool usage statistics
   - Performance metrics

### Technical Improvements

1. **Caching Layer**
   - Redis for API responses
   - Reduce external API calls
   - Faster response times

2. **Database Integration**
   - PostgreSQL for persistence
   - User preferences
   - Search history

3. **Background Tasks**
   - Celery for async jobs
   - Scheduled data updates
   - Email notifications

4. **Testing**
   - Unit tests (pytest)
   - Integration tests
   - E2E tests (Playwright)

5. **CI/CD Pipeline**
   - GitHub Actions
   - Automated testing
   - Deployment automation


---

## Appendix

### A. Complete File Listings

#### agent/config.py (Current Version)
```python
import os

MODEL_NAME = "deepseek/deepseek-chat"

SYSTEM_PROMPT = """You are a helpful movie information assistant with access to movie databases.

You have access to these tools:
1. search_movie - Search for movies in OMDb (good for older movies, detailed info)
2. get_movie_details - Get full details for a specific movie from OMDb
3. now_playing_india - Get current theatrical releases in India from TMDb (has 2024-2026 movies!)
4. get_streaming_info - Check where movies are available to watch
5. get_movie_recommendations - Get similar movie suggestions

CRITICAL TOOL SELECTION RULES:

1. For questions about NEW movies (2024-2026 releases):
   - FIRST check now_playing_india() - it has the latest releases that OMDb doesn't
   - If not found there, then use search_movie()
   - Examples: "latest Christopher Nolan", "new releases", "what's in theaters"

2. For questions about older movies or specific titles:
   - Use search_movie() directly
   - Examples: "tell me about Inception", "Godfather details"

3. For "latest releases" or "recent movies" questions:
   - ALWAYS start with now_playing_india()
   - It contains 2024-2026 releases that OMDb doesn't have yet

4. For movie recommendations:
   - If user asks for "latest" or "recent" → use now_playing_india()
   - If user asks by genre/director → search_movie() first, then filter results
   - For India-specific recommendations → use now_playing_india()

Always provide complete information including:
- Title, year, director, cast
- Plot summary
- Ratings (IMDb, Rotten Tomatoes if available)
- Where to watch (if asked)

Format your responses clearly with proper sections and bullet points.
"""
```

#### agent/mcp_connection.py (Working Version)
```python
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path

@asynccontextmanager
async def connect_to_server():
    """Connect to the MCP movie server."""
    project_root = Path(__file__).parent.parent
    
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "server.app"],  # Run as module
        cwd=str(project_root),      # Set working directory
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
```


#### web/backend/main.py (Working Version)
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.mcp_connection import connect_to_server
from agent.loop import run_agent_loop

class ConnectionManager:
    def __init__(self):
        self.mcp_session = None
        self.mcp_context = None
    
    async def initialize_mcp(self):
        """Initialize MCP connection"""
        self.mcp_context = connect_to_server()
        self.mcp_session = await self.mcp_context.__aenter__()

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    await manager.initialize_mcp()
    yield
    if manager.mcp_context:
        await manager.mcp_context.__aexit__(None, None, None)

app = FastAPI(title="CineMCP Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            
            # Stream response
            async for chunk in run_agent_loop(manager.mcp_session, user_message):
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk
                })
            
            await websocket.send_json({"type": "done"})
    
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mcp_connected": manager.mcp_session is not None
    }
```

### B. Environment Setup Commands

**Windows (PowerShell):**
```powershell
# Install Python 3.13
winget install Python.Python.3.13

# Install Node.js
winget install OpenJS.NodeJS.LTS

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
cd web\frontend
npm install
```

**macOS/Linux:**
```bash
# Install Python 3.13
brew install python@3.13

# Install Node.js
brew install node

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
cd web/frontend
npm install
```


### C. API Key Setup Guides

#### OMDb API Key
1. Visit http://www.omdbapi.com/apikey.aspx
2. Enter your email
3. Select free tier (1,000 requests/day)
4. Check email for activation link
5. Copy API key to `.env`

#### TMDb API Key
1. Visit https://www.themoviedb.org/signup
2. Create account and verify email
3. Go to Settings → API
4. Request API key (select Developer)
5. Fill out form (personal/educational use)
6. Copy API key (v3 auth) to `.env`

#### OpenRouter API Key
1. Visit https://openrouter.ai/
2. Sign in with Google/GitHub
3. Go to Keys tab
4. Click "Create Key"
5. Copy key to `.env`
6. Add credits (starts at $0, pay-as-you-go)

**Cost Estimate (OpenRouter):**
- deepseek/deepseek-chat: ~$0.14 per 1M tokens
- Typical query: 500-2000 tokens
- **100 queries ≈ $0.01-0.03**

### D. Useful Commands Reference

**Python:**
```bash
# Run CLI agent
python -m agent.main

# Run MCP server standalone
python -m server.app

# Check Python version
python --version

# Install specific package
pip install fastmcp

# List installed packages
pip list
```

**Node/npm:**
```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Check for outdated packages
npm outdated

# Update all packages
npm update
```

**Git:**
```bash
# Check status
git status

# Stage changes
git add agent/config.py

# Commit
git commit -m "Update system prompt"

# Push to GitHub
git push origin main

# Create new branch
git checkout -b feature/new-tool

# View commit history
git log --oneline

# Discard local changes
git checkout -- filename
```

**Process Management:**
```bash
# Find process on port
netstat -ano | findstr :8000

# Kill process (Windows)
taskkill /PID <pid> /F

# Kill process (Mac/Linux)
kill -9 <pid>
```


### E. Debugging Tips

**Enable Verbose Logging:**
```python
# agent/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check MCP Communication:**
```python
# agent/loop.py
print(f"Available tools: {tools}")
print(f"Tool call result: {result}")
```

**WebSocket Debugging:**
```javascript
// web/frontend/src/App.jsx
websocket.onmessage = (event) => {
  console.log("Received:", event.data)
  // ... rest of handler
}
```

**Test Tools Directly:**
```python
# test_tools.py
import asyncio
from agent.mcp_connection import connect_to_server

async def test():
    async with connect_to_server() as session:
        result = await session.call_tool("search_movie", {"title": "Inception"})
        print(result)

asyncio.run(test())
```

**Check API Responses:**
```bash
# Test OMDb directly
curl "http://www.omdbapi.com/?apikey=YOUR_KEY&s=Inception"

# Test TMDb directly
curl "https://api.themoviedb.org/3/movie/now_playing?api_key=YOUR_KEY&region=IN"
```

### F. Performance Optimization

**Backend:**
```python
# Cache API responses
from functools import lru_cache

@lru_cache(maxsize=100)
async def get_cached_movie(title: str):
    return await search_movie(title)
```

**Frontend:**
```jsx
// Debounce input
import { useState, useEffect } from 'react'

const [input, setInput] = useState("")
const [debouncedInput, setDebouncedInput] = useState("")

useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedInput(input)
  }, 500)
  return () => clearTimeout(timer)
}, [input])
```

**Database Queries:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_movie_title ON movies(title);
CREATE INDEX idx_movie_year ON movies(year);
```

### G. Resources

**Documentation:**
- FastMCP: https://github.com/jlowin/fastmcp
- MCP Protocol: https://modelcontextprotocol.io/
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Tailwind CSS: https://tailwindcss.com/

**APIs:**
- OMDb: http://www.omdbapi.com/
- TMDb: https://developers.themoviedb.org/3
- OpenRouter: https://openrouter.ai/docs

**Community:**
- GitHub Issues: https://github.com/PS-Malhar-Gupte/CineMCP/issues
- MCP Discord: (link if available)
- FastAPI Discord: https://discord.gg/VQjSZaeJmf

---

## Conclusion

CineMCP demonstrates a modern approach to building AI-powered applications:

**Key Achievements:**
✅ Functional CLI and web interfaces
✅ Real-time streaming responses
✅ Multi-source data integration (OMDb + TMDb)
✅ Production-ready architecture
✅ Proper error handling and logging
✅ Clean, maintainable codebase

**Technical Highlights:**
- MCP for tool orchestration
- FastAPI for async backend
- React for modern UI
- WebSocket for real-time communication
- Cloud LLM integration

**Lessons Learned:**
- System prompt engineering is critical
- Tool selection logic needs explicit rules
- Async context management requires care
- Module execution solves import issues
- Cloud LLMs vastly superior to local for production

This handbook provides everything needed to understand, modify, deploy, and extend CineMCP. Happy coding! 🎬🤖

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Project:** CineMCP  
**Repository:** https://github.com/PS-Malhar-Gupte/CineMCP  
**Maintainer:** Malhar Gupte
