# Design Document

## Overview

CineMCP follows the same two-package architecture proven in the prior
Repo Pulse project: a `server` package (the "hands" — MCP tools that call
real APIs) and an `agent` package (the "brain" — the LLM-driven decide →
act → observe loop). The `agent` package is designed to carry over
almost unchanged from Repo Pulse, since it contains no domain-specific
logic; only tool descriptions and the system prompt change.

Two external data sources are used, each requiring its own free API key:
- **OMDb** (omdbapi.com) — search, plot/cast/crew details, ratings
- **TMDb** (themoviedb.org) — current/upcoming India theatrical releases

## Architecture

```
User (CLI)
    |
    v
Agent (Ollama + decide/act/observe loop + reflection)
    |
    v
MCP Client (stdio)
    |
    v
MCP Tools Server
    |
    +-- OMDb tools (search_movie, movie_details, movie_ratings)
    |
    +-- TMDb tools (now_playing_india, upcoming_releases_india)
```

Transport is stdio (matching Repo Pulse): the agent spawns the tools
server as a subprocess and communicates over its stdin/stdout, which is
sufficient for a single-user local CLI and avoids any network/port
configuration.

## Components and Interfaces

### `server/mcp_instance.py`
Holds the single shared `FastMCP` instance every tool module registers
against. Exists as its own file solely to avoid a circular import
between `app.py` (which must import the tool modules to trigger their
`@mcp.tool()` registration) and the tool modules (which need the shared
`mcp` object to register against).

### `server/http_utils.py`
Shared request helpers, split by data source concern:
- `omdb_get(params)` — attaches `OMDB_API_KEY` from the environment,
  and normalizes OMDb's unusual failure signaling (`HTTP 200` with
  `{"Response": "False", "Error": "..."}`) into a plain
  `{"error": "..."}` dict, matching the error shape used elsewhere.
- `tmdb_get(path, params)` — attaches `TMDB_API_KEY`, handles standard
  HTTP error codes (TMDb, unlike OMDb, uses real HTTP status codes for
  failures).
- Both raise a typed exception (`OmdbKeyMissing` / `TmdbKeyMissing`) when
  the relevant environment variable isn't set, caught at the tool level
  to produce an actionable error message (satisfies Requirement 6.1).

### `server/movie_tools.py` (OMDb-backed)
- `search_movie(title: str, year: str = "") -> dict` — Requirement 1.
  Calls OMDb's `s=` search parameter. Returns a list of candidates
  (`imdb_id`, `title`, `year`, `type`). Deliberately does NOT return full
  details — that requires a second, separate tool call, forcing the
  agent to chain tools rather than get everything from one call.
- `movie_details(imdb_id: str) -> dict` — Requirement 2. Calls OMDb's
  `i=` lookup. Returns plot, director, writer, actors, genre, runtime,
  country, language, awards. Excludes the ratings breakdown (kept in a
  separate tool below).
- `movie_ratings(imdb_id: str) -> dict` — Requirement 3. Calls the same
  OMDb `i=` lookup as `movie_details`, but returns only the
  ratings-relevant fields (`imdb_rating`, `imdb_votes`, `metascore`,
  `ratings` source list). Kept as a distinct tool from `movie_details`
  specifically so the agent must choose based on what was asked, per
  Requirement 3.2 — even though both tools share an underlying endpoint.

### `server/release_tools.py` (TMDb-backed)
- `now_playing_india(page: int = 1) -> dict` — Requirement 4. Calls
  TMDb's now-playing endpoint with `region=IN`.
- `upcoming_releases_india(page: int = 1) -> dict` — Requirement 4.
  Calls TMDb's upcoming endpoint with `region=IN`.
  Kept separate from `now_playing_india` (rather than one
  `releases_india(mode)` tool) for the same reason `movie_details` and
  `movie_ratings` are separate — real tool-selection signal for the
  agent, per the project's overlap-by-design principle (Requirement 5).

### `server/app.py`
Entrypoint. Imports `mcp_instance`, `movie_tools`, and `release_tools`
(triggering their tool registration as a side effect), then calls
`mcp.run()` on stdio. Mirrors Repo Pulse's `app.py` exactly.

### `agent/config.py`
Carries over Repo Pulse's structure unchanged; only content changes:
- `MODEL_NAME` — `mistral:7b` (same rationale as Repo Pulse: small
  enough for local CPU inference, adequate JSON-following for this task).
- `MAX_LOOP_ITERATIONS` — safety cap on tool-call chaining per turn.
- `SYSTEM_PROMPT` — describes the movie domain instead of OSS repos;
  explicitly instructs the agent to resolve a title to an IMDb ID via
  `search_movie` before calling `movie_details`/`movie_ratings`
  (Requirement 2.3), and to prefer admitting uncertainty over fabricating
  data when a tool result contains an `error` field (Requirement 5.4).
- `REFLECTION_PROMPT` — unchanged in structure from Repo Pulse; requests
  a structured `{"ok": true}` / `{"ok": false, "corrected_answer": ...}`
  JSON response rather than a free-form string, since free-form
  "reply with exactly these words" checks proved fragile in the prior
  project.

### `agent/llm_client.py`
Carried over from Repo Pulse with no domain-specific changes:
- `decide(messages)` — calls Ollama, tolerantly extracts the first valid
  JSON object from the response (handling prose-wrapped JSON, markdown
  fences, or the model emitting multiple JSON objects in one response),
  with one repair-call fallback before giving up (Requirement 6.3).
- `reflect(history, draft_answer)` — the one-shot reflection pass
  (Requirement 8), parsed the same tolerant way.

### `agent/mcp_connection.py`
Carried over unchanged: spawns the server subprocess (passing the full
parent environment, including `OMDB_API_KEY`/`TMDB_API_KEY`, since MCP's
`StdioServerParameters` does not inherit the parent environment by
default), completes the MCP handshake, and discovers available tools via
`session.list_tools()` (Requirement 5.2).

### `agent/loop.py`
Carried over unchanged: the decide → act → observe loop, with an
optional `on_step` callback (defaults to printing, satisfying
Requirement 7.2) so the exact same loop can later be reused by a
non-CLI surface without modification.

### `agent/main.py`
Carried over unchanged in structure: CLI entrypoint (Requirement 7.1)
that connects, prints available tools, and loops on `input()`.

## Data Models

Tool return shapes (all JSON-serializable dicts, matching the MCP tool
result convention used throughout):

```
search_movie ->
  { "results": [ { "imdb_id": str, "title": str, "year": str, "type": str }, ... ] }
  | { "results": [], "summary": str }   # no matches (Req 1.2)

movie_details ->
  { "title": str, "year": str, "director": str, "writer": str,
    "actors": str, "genre": str, "runtime": str, "country": str,
    "language": str, "awards": str, "plot": str }
  | { "error": str }

movie_ratings ->
  { "imdb_rating": str, "imdb_votes": str, "metascore": str,
    "ratings": [ { "source": str, "value": str }, ... ] }
  | { "error": str }

now_playing_india / upcoming_releases_india ->
  { "results": [ { "title": str, "release_date": str, "overview": str }, ... ] }
  | { "results": [], "summary": str }
```

Every tool that can fail returns `{"error": "<message>"}` rather than
raising — consistent with Repo Pulse's convention and required by
Requirement 6.2.

## Error Handling

| Failure case | Handling |
|---|---|
| Missing `OMDB_API_KEY` / `TMDB_API_KEY` | Typed exception raised in `http_utils`, caught in the tool, returned as `{"error": "..."}` naming the missing variable (Req 6.1) |
| OMDb "not found" (`Response: False`) | Normalized in `omdb_get()` to `{"error": ...}` before it reaches tool logic (Req 2.2) |
| TMDb HTTP error (4xx/5xx) | Caught via `requests`' `raise_for_status()`, returned as `{"error": ...}` |
| Network timeout | 15s timeout on all requests; caught and returned as `{"error": ...}` rather than hanging the MCP server |
| LLM produces invalid JSON | `decide()`/`reflect()` attempt a tolerant "first JSON object" extraction, then one repair call, then fall back to using the raw text as the answer rather than crashing (Req 6.3) |
| Agent references an unknown tool name (hallucinated) | Loop catches this in `agent/loop.py`, feeds the error back into conversation history so the model can self-correct next iteration, rather than crashing |

## Testing Strategy

- **Unit-level smoke tests**: call each tool function directly (bypassing
  MCP) against the live OMDb/TMDb APIs with known-good inputs (e.g.
  `search_movie("Inception")`) to confirm response parsing matches the
  documented API schema.
- **Error-path tests**: call tools with a deliberately invalid IMDb ID,
  and with the relevant API key env var unset, to confirm the structured
  `{"error": ...}` shape is returned in both cases rather than an
  exception.
- **MCP transport test**: spawn `server/app.py` as a subprocess via
  `agent/mcp_connection.py.connect()` and confirm tool discovery lists
  all five tools, then make one real `session.call_tool(...)` to confirm
  the full client-server round trip works end to end.
- **Agent loop test with a stubbed LLM**: monkeypatch `decide`/`reflect`
  to return scripted decisions (no real Ollama call needed), to verify
  the loop correctly dispatches tool calls, handles unknown-tool
  responses, and terminates on a `final` action — this isolates loop
  correctness from LLM behavior, which is useful given small local
  models are non-deterministic.
- **Manual multi-tool chaining test**: with a real Ollama model running,
  ask a question that requires resolving a title AND fetching ratings
  (e.g. "what's the IMDb rating of Inception?") and confirm the agent
  calls `search_movie` then `movie_ratings` in sequence (Requirement
  5.3), not just one or the other.
