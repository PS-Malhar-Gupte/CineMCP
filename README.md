# CineMCP

An AI agent that answers natural-language questions about movies using MCP (Model Context Protocol) tools backed by OMDb and TMDb APIs.

## Features

- 🔍 **Movie Search** - Search for movies by title with optional year filtering
- 📊 **Movie Details** - Get plot, cast, crew, runtime, and awards information
- ⭐ **Movie Ratings** - Fetch IMDb ratings, Rotten Tomatoes, and Metacritic scores
- 🎬 **India Releases** - Get current and upcoming theatrical releases in India
- 🤖 **Agentic Behavior** - LLM-driven tool selection (not hardcoded routing)
- 💬 **Local CLI** - Terminal-based interface with visible tool calls

## Architecture

```
User (CLI)
    ↓
Agent (Ollama + LLM loop + reflection)
    ↓
MCP Client (stdio)
    ↓
MCP Tools Server
    ├── OMDb tools (search, details, ratings)
    └── TMDb tools (India releases)
```

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) running locally
- OMDb API key (free at [omdbapi.com](https://www.omdbapi.com/apikey.aspx))
- TMDb API key (free at [themoviedb.org](https://www.themoviedb.org/settings/api))

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/PS-Malhar-Gupte/CineMCP.git
   cd CineMCP
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Install and start Ollama**
   ```bash
   # Download from https://ollama.com/download
   ollama serve
   
   # In another terminal, download the model
   ollama pull mistral:7b
   ```

## Usage

### Start the Agent

```bash
python -m agent.main
```

### Example Questions

```
> What's Inception rated on IMDb?
> Who directed Oppenheimer?
> What movies are currently playing in India?
> Tell me about the movie Dune
> Search for movies called The Matrix
```

### Tool Calls are Visible

The agent prints each tool call before executing it:
```
→ Calling search_movie with {'title': 'Inception'}
← Result: {"results": [{"imdb_id": "tt1375666", ...}]}
→ Calling movie_ratings with {'imdb_id': 'tt1375666'}
← Result: {"imdb_rating": "8.8", ...}
```

## Project Structure

```
CineMCP/
├── agent/                  # Agent client (the "brain")
│   ├── config.py          # Model and prompts configuration
│   ├── llm_client.py      # Ollama integration
│   ├── mcp_connection.py  # MCP client setup
│   ├── loop.py            # Decide → act → observe loop
│   └── main.py            # CLI entrypoint
├── server/                 # MCP tools server (the "hands")
│   ├── mcp_instance.py    # Shared FastMCP instance
│   ├── http_utils.py      # API request helpers
│   ├── movie_tools.py     # OMDb-backed tools
│   ├── release_tools.py   # TMDb-backed tools
│   └── app.py             # Server entrypoint
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── design.md              # Architecture documentation
├── requirements.md        # Functional requirements
└── tasks.md               # Implementation plan
```

## Available Tools

| Tool | Description | API |
|------|-------------|-----|
| `search_movie` | Search movies by title | OMDb |
| `movie_details` | Get plot, cast, crew info | OMDb |
| `movie_ratings` | Get IMDb/RT/Metacritic scores | OMDb |
| `now_playing_india` | Movies in Indian theaters | TMDb |
| `upcoming_releases_india` | Upcoming Indian releases | TMDb |

## How It Works

1. **User asks a question** in natural language
2. **Agent (LLM) decides** which tool(s) to call based on the question
3. **MCP client** executes the tool via stdio transport
4. **MCP server** calls the appropriate API (OMDb or TMDb)
5. **Results** flow back to the agent
6. **Agent synthesizes** a final answer
7. **Reflection pass** reviews the answer for accuracy

## Requirements Satisfied

- ✅ **Req 1**: Movie search/resolution with IMDb IDs
- ✅ **Req 2**: Movie details (plot, cast, crew)
- ✅ **Req 3**: Movie ratings (separate tool for focused queries)
- ✅ **Req 4**: India theatrical releases (real-time TMDb data)
- ✅ **Req 5**: Genuine agent-driven tool selection (no hardcoded routing)
- ✅ **Req 6**: Robust error handling (structured error responses)
- ✅ **Req 7**: Local CLI interface with visible tool calls
- ✅ **Req 8**: One-shot reflection on final answers

## Development

### Running Tests

The implementation includes automated tests with stubbed LLM:
```bash
# Run agent loop tests
pytest agent/test_agent_loop.py -v
```

## License

MIT

## Acknowledgments

- Built following spec-driven development methodology
- Inspired by the Repo Pulse architecture
- Uses [MCP](https://modelcontextprotocol.io) for tool protocol
- Powered by [Ollama](https://ollama.com) for local LLM inference
