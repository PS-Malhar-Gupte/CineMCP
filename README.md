# 🎬 CineMCP

An AI agent that answers natural-language movie questions by genuinely reasoning about which tools to call — not hardcoded if/elif routing. Built on MCP (Model Context Protocol), backed by OMDb and TMDb, with real conversation memory, an answer cache, hallucination guardrails, LLM-as-judge evaluation, and structured observability.

Two interfaces share one identical agent core: a terminal CLI and a React + WebSocket web app.

---

## Why this project exists

Most "AI assistant" demos fake being agentic — they pattern-match keywords in the question to decide which function to call. That's an if-statement wearing a costume, not a model actually deciding anything.

CineMCP describes its tools to the LLM in plain text (no native `tools`/function-calling API parameter is used at all) and asks it to respond with a small JSON contract — `{"action": "call_tool", ...}` or `{"action": "final", ...}`. The model has to genuinely reason about which tool answers the question, including chaining multiple tool calls in one turn (e.g. resolving a title to an IMDb ID before it can fetch that movie's rating). Two tools, `movie_details` and `movie_ratings`, deliberately hit the *same* underlying OMDb endpoint but return disjoint fields — specifically so the agent can't get away with reaching for one mega-tool regardless of what was actually asked.

---

## Architecture

```
┌─────────────┐        ┌──────────────────┐
│  CLI (TTY)  │        │  React Web UI     │
│ agent/main  │        │  (Vite, port 5173)│
└──────┬──────┘        └────────┬──────────┘
       │                        │ WebSocket (+ REST for history)
       │                 ┌──────┴───────────┐
       │                 │  FastAPI backend  │
       │                 │  (port 8000)      │
       │                 └──────┬───────────┘
       └────────────┬───────────┘
                     │
              ┌──────▼───────┐        decide → act → observe
              │  Agent Loop   │◄──────────────────────────────┐
              │ (agent/loop)  │                                │
              └──────┬───────┘                                │
                     │ session.call_tool(name, args)           │
              ┌──────▼───────┐                          ┌──────┴──────┐
              │  MCP Client   │  stdio (JSON-RPC)        │  LLM Client │
              │ (subprocess)  │◄────────────────────────►│  (Groq /    │
              └──────┬───────┘                           │  Ollama /   │
                     │                                    │  any OpenAI-│
              ┌──────▼───────┐                            │  compatible)│
              │  MCP Server   │                            └─────────────┘
              │  (FastMCP)    │
              └──────┬───────┘
         ┌───────────┼────────────┐
    ┌────▼────┐  ┌───▼────┐
    │  OMDb   │  │  TMDb  │
    └─────────┘  └────────┘

  Cross-cutting: Redis-backed conversation history + answer cache,
  structured request-scoped observability spans, LLM-as-judge evaluation.
```

The CLI and the web backend call the exact same `agent/loop.run_loop()` — there is no duplicated decision logic between the two surfaces. The web backend is a WebSocket/REST wrapper around the identical agent core.

---

## What the agent can actually do

### MCP Tools (8 total, across two data sources)

| Tool | Source | Purpose |
|---|---|---|
| `search_movie` | OMDb | Resolve a title (+ optional year) to candidate IMDb IDs |
| `movie_details` | OMDb | Plot, director, writer, cast, genre, runtime, country, language, awards |
| `movie_ratings` | OMDb | IMDb score, vote count, Metascore, ratings-source breakdown |
| `now_playing_india` | TMDb | Currently playing in Indian theaters |
| `upcoming_releases_india` | TMDb | Upcoming Indian theatrical releases |
| `upcoming_releases_global` | TMDb | Upcoming releases worldwide; switches to `/discover/movie` with a `year` filter when given one |
| `recent_releases_global` | TMDb | Released in the last N days, worldwide |
| `recent_releases_india` | TMDb | Released in the last N days, in India — uses `/discover/movie` + `region=IN` rather than TMDb's less reliable curated `now_playing` endpoint |

All TMDb `discover`-backed tools (the last three) sort by `popularity.desc` within their date filter rather than raw date — sorting purely by date let obscure, low-budget titles that happened to share a release date rank ahead of the movie actually being asked about.

### Hallucination guardrails

Every final answer passes through two independent checks before it reaches the user:

- **Empty-result guardrail** — if a tool was called but returned no usable data, the answer is replaced with a fixed "I couldn't find verified information" response rather than letting the model guess.
- **Grounding validation** — a second LLM call checks the draft answer's factual claims against the actual tool results in the conversation (not just the question + draft in isolation), and rejects unsupported claims. The judge prompt is deliberately biased toward approving an answer unless a *specific, pointable* fabrication exists — an over-eager judge here previously produced false-positive rejections of correct, well-supported answers (e.g. rejecting a fully-grounded answer about *Inception*).

### Reflection pass

After the loop produces a draft answer, one more LLM call reviews it against the **full conversation, including every tool call and result** — not a trimmed stub — and can approve it or supply a corrected version. (Trimming that context was an earlier bug: reflection judging an answer with no evidence in front of it could reject correct answers and replace them with something worse.)

### Conversation memory & answer cache

- **Durable, session-scoped conversation history** (`agent/conversation_store.py`) — keyed by a `session_id` the web client generates once and persists in `localStorage`, sent on every connection as `?session_id=...`. A dropped/reconnected WebSocket gets a *new* connection object but rehydrates the *same* conversation from the store. The CLI uses the entered username as its `session_id` instead, so re-running `python -m agent.main` as the same user resumes where it left off.
- **Answer cache** (`agent/memory.py`), keyed by `(session_id, sha256(question))`. Two cache lifetimes: 7 days for answers built from stable facts, 1 hour for answers that used a date-sensitive tool (`VOLATILE_CACHE_TOOLS` in `config.py`). Fallback/error answers are never cached — caching a transient failure would permanently "poison" that question with a wrong answer.
- **Backend**: Redis by default (`MEMORY_BACKEND=redis`), shared across the CLI and every web worker/connection. Falls back automatically to an in-process/local-JSON-file store if Redis is unreachable or `MEMORY_BACKEND=local` — the app doesn't crash on startup if Redis isn't running, it just loses cross-restart persistence.

### Observability

Every request gets a UUID request ID (via `contextvars`, so it survives async boundaries without threading it through every function signature). `agent/observability.py`'s `MetricsLogger` wraps key operations (`agent_run_loop`, each `llm_call`, each `tool_execution`) in spans, logging structured JSON with duration on completion. The web backend forwards these spans to the frontend per-turn alongside evaluation results.

### Evaluation (LLM-as-judge)

After each answer, `agent/evaluation.py` scores it on four axes — Relevance, Confidence, Precision, Similarity — each via its own LLM call, run **sequentially** (not concurrently — these run in the background after the answer's already been sent, so there's no latency cost, and running them one at a time avoids bursting multiple simultaneous requests against the LLM provider's per-minute limits right after the main answer already used part of that budget). A metric that fails to evaluate (a parse error, a timeout, a rate limit) returns `None`, not `0.0` — a `0%` score is reserved for an actual judged "irrelevant/imprecise," not indistinguishable-from-failure.

### Resilient LLM client

`agent/llm_client.py` implements a provider-agnostic interface (`LLMProvider`) with three real implementations plus a mock for tests:

- `OpenAICompatibleProvider` — works with Groq, OpenRouter, or OpenAI's API unchanged (same request shape). Retries on `429` (honoring `Retry-After`, falling back to exponential backoff) and on `413` "request too large" (progressively halving `max_tokens` and retrying immediately, since that's a request-shape problem, not a cooldown situation).
- `OllamaProvider` — local, fully offline.
- `FallbackLLMProvider` — wraps a primary provider with a fallback (currently: Groq primary, local Ollama fallback). If you rely on this, make sure Ollama is actually running (`ollama serve` + `ollama pull llama3.1`) — an unconfigured fallback fails loudly rather than silently, which is correct, but worth knowing before you hit it mid-demo.

JSON responses from the model are parsed by a hand-rolled, **string-aware** extractor (`_extract_first_json`) — brace characters inside quoted text (e.g. a movie title) don't desync the parser, and it never loses track of where the real JSON object started, so truncated responses (e.g. from hitting a token limit mid-string) can still often be recovered via a repair pass instead of failing outright.

### MCP session management

`web/backend/mcp_manager.py` supports two modes via `MCP_MODE`:
- **`pool`** (default) — a fixed-size pool (`MCP_POOL_SIZE`, default 3) of long-lived MCP server subprocesses, checked out per-request via an `asyncio.Queue`.
- **`per_user`** — spawns a dedicated subprocess per request, cleaned up afterward.

A hard 180-second timeout wraps the whole agent turn in the web backend, and the WebSocket handler catches *any* exception (not just a specific type) and always sends a proper error message back — an earlier version only caught `RuntimeError`, so an uncaught exception type (e.g. a raw `requests` timeout) could crash a request silently, leaving the frontend's "thinking" indicator stuck forever with no recovery short of a page refresh.

---

## Frontend

React + Vite + Tailwind + Framer Motion. Dark/light theme (persisted, respects `prefers-color-scheme`). Real-time chat over WebSocket with live animated tool-call indicators, an inline Observability panel per message (latency, execution time, the four evaluation scores), suggested-prompt chips, and auto-growing input.

---

## Project structure

```
CineMCP/
├── agent/                     # the "brain"
│   ├── config.py               # model, prompts, storage/cache config
│   ├── llm_client.py           # provider abstraction, decide/reflect/grounding, JSON extraction
│   ├── loop.py                 # decide → act → observe loop + guardrails
│   ├── conversation.py         # in-process per-turn working history
│   ├── conversation_store.py   # durable, session_id-keyed history (Redis or local)
│   ├── memory.py                # answer cache (Redis or local)
│   ├── evaluation.py            # LLM-as-judge scoring
│   ├── observability.py         # request IDs + span tracing
│   ├── mcp_connection.py        # spawns + handshakes with the MCP server subprocess
│   └── main.py                  # CLI entrypoint
├── server/                    # the "hands" — MCP tools server
│   ├── mcp_instance.py          # shared FastMCP instance
│   ├── http_utils.py            # OMDb/TMDb request + error-normalization helpers
│   ├── movie_tools.py           # search_movie, movie_details, movie_ratings
│   ├── release_tools.py         # the 5 TMDb-backed release tools
│   └── app.py                   # server entrypoint (stdio transport)
├── web/
│   ├── backend/
│   │   ├── main.py               # FastAPI + WebSocket + REST history endpoints
│   │   └── mcp_manager.py        # pool / per_user MCP session management
│   └── frontend/                 # React + Vite + Tailwind chat UI
├── tests/
│   ├── test_phase1.py            # AgentConfig, provider factory, decide()/reflect() w/ mock LLM
│   └── test_memory_and_conversation.py  # cacheability, TTL selection, history truncation/reconnect
├── requirements.txt / web/backend/requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for the web frontend)
- Free API keys: [OMDb](https://www.omdbapi.com/apikey.aspx), [TMDb](https://www.themoviedb.org/settings/api)
- An LLM: either [Ollama](https://ollama.com/download) running locally, **or** an OpenAI-compatible API key (Groq, OpenRouter, or OpenAI)
- Optional but recommended for full functionality: [Redis](https://redis.io/) running locally (`MEMORY_BACKEND` defaults to `redis`) — the app runs fine without it via the automatic local fallback, but conversation continuity across a page refresh and the shared answer cache both need it to actually persist

### Install

```bash
git clone https://github.com/PS-Malhar-Gupte/CineMCP.git
cd CineMCP
pip install -r requirements.txt
cp .env.example .env
# edit .env: add OMDB_API_KEY, TMDB_API_KEY, and your LLM provider config
```

Then set `MODEL_NAME` in `agent/config.py` to match whichever LLM backend your `.env` is configured for (see the comments at the top of that file for the current recommendation and known compatibility issues per model).

### Run the CLI

```bash
python -m agent.main
```

### Run the web app

```bash
# terminal 1
cd web/backend
pip install -r requirements.txt
python main.py

# terminal 2
cd web/frontend
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

### Run the tests

```bash
python -m unittest tests.test_phase1 tests.test_memory_and_conversation -v
```

---

## Configuration reference

All in `agent/config.py` unless noted. Key environment variables (`.env`):

| Variable | Required | Purpose |
|---|---|---|
| `OMDB_API_KEY` | Yes | OMDb API key |
| `TMDB_API_KEY` | Yes | TMDb API key |
| `OPENAI_API_KEY` | For a cloud LLM | Switches the LLM client from local Ollama to an OpenAI-compatible HTTP call |
| `OPENAI_BASE_URL` | For Groq/OpenRouter | e.g. `https://api.groq.com/openai/v1` |
| `MEMORY_BACKEND` | No (default `redis`) | `redis` or `local` |
| `REDIS_URL` | If using Redis | Default `redis://localhost:6379/0` |
| `CONVERSATION_TTL_SECONDS` | No (default 24h) | Sliding idle-expiry for stored conversation history |
| `CACHE_TTL_STABLE_SECONDS` / `CACHE_TTL_VOLATILE_SECONDS` | No (default 7d / 1h) | Answer-cache lifetimes |
| `MCP_MODE` | No (default `pool`) | `pool` or `per_user` |
| `MCP_POOL_SIZE` | No (default 3) | Pool mode session count |

---

## Known limitations (honest, as of this doc)

- **No API-key/model-name validation at startup.** `MODEL_NAME` and the active `OPENAI_API_KEY`/`OPENAI_BASE_URL` pairing aren't cross-checked — a mismatch surfaces as a runtime call failure, not a clear config error.
- **The local Ollama fallback is only as good as your local Ollama setup.** If it isn't running or doesn't have the expected model pulled, the "fallback" fails loudly rather than silently — which is correct behavior, but means it isn't a real safety net until you've actually set it up.
- **Tool descriptions are hand-duplicated.** They live once as each tool's docstring (the real MCP schema) and again, by hand, in `SYSTEM_PROMPT` — nothing enforces the two stay in sync.
- **`MCP_MODE=pool` shares a fixed-size session pool across all concurrent web users** — adequate for a demo/single-user load, a real bottleneck under genuine concurrent traffic.
- **`PROJECT_HANDBOOK.md` and `QUICK_START_GUIDE.md` in this repo are stale** and describe an earlier, different version of this project (wrong tool names, a different LLM provider setup, no memory/reflection/evaluation/observability system). Don't treat them as current documentation — this README reflects the actual, current codebase; those two files need a rewrite or removal.

---

## Acknowledgements

- [Model Context Protocol](https://modelcontextprotocol.io/) and its [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OMDb API](https://www.omdbapi.com/) and [TMDb API](https://www.themoviedb.org/documentation/api)
- The agent core (loop, MCP connection handling, LLM client abstraction) originated in a prior project, Repo Pulse, and was carried over largely unchanged — only the tool set and prompts are movie-domain-specific.
