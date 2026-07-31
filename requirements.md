# Requirements Document

## Introduction

CineMCP is an AI agent that answers natural-language questions about
movies — search, plot/cast/crew details, ratings, and current India
theatrical releases — by deciding, at run time, which of several MCP
tools to call. It follows the same architecture as a prior project
("Repo Pulse"): a Python MCP tools server exposing narrow, single-purpose
tools backed by free third-party APIs (OMDb, TMDb), and an agent client
that runs a decide → act → observe loop against a local LLM (via Ollama)
to pick the right tool(s) for a given question, rather than following a
fixed pipeline.

The tools are deliberately kept narrow and overlapping in what they could
plausibly answer, so the LLM has to genuinely reason about tool selection
and sequencing — this is a functional requirement of the project, not
just an implementation preference.

## Requirements

### Requirement 1: Movie search / resolution

**User Story:** As a user, I want to ask about a movie by title (possibly
ambiguous or shared with other titles), so that the agent can resolve it
to a specific, unambiguous movie before answering further questions
about it.

#### Acceptance Criteria

1. WHEN the user asks about a movie by title THEN the system SHALL call
   an MCP tool that searches OMDb by title and returns candidate matches
   including each match's IMDb ID, year, and type (movie/series/episode).
2. WHEN OMDb returns zero matches for a title THEN the tool SHALL return
   a structured result indicating no matches were found, without raising
   an unhandled exception.
3. WHEN multiple candidates share a title THEN the tool SHALL return all
   matches (up to OMDb's page size) so the agent or user can disambiguate
   by year or type.
4. IF the user's question already includes an unambiguous identifier
   (e.g., a specific year, or an IMDb ID) THEN the system SHALL prefer
   resolving directly to a single result over returning a broad search
   list.

### Requirement 2: Movie details

**User Story:** As a user, I want to ask about a movie's plot, cast,
crew, runtime, or other descriptive details, so that I get factual
information without the agent inventing or guessing any of it.

#### Acceptance Criteria

1. WHEN the user asks a question about a movie's plot, director, writer,
   cast, genre, runtime, country, language, or awards THEN the system
   SHALL call an MCP tool that fetches full details for that movie's
   IMDb ID from OMDb.
2. WHEN the requested IMDb ID does not exist or OMDb cannot find it THEN
   the tool SHALL return a structured error (not an HTTP-level exception),
   since OMDb signals failure via a `"Response": "False"` field in an
   HTTP 200 response rather than a non-200 status code.
3. WHEN the agent has not yet resolved a plain movie title to an IMDb ID
   THEN the system SHALL call the search/resolution tool (Requirement 1)
   before calling the details tool.

### Requirement 3: Movie ratings

**User Story:** As a user, I want to ask specifically about a movie's
ratings (IMDb score, Rotten Tomatoes, Metacritic), so that I get a
focused answer without unrelated plot/cast information cluttering it.

#### Acceptance Criteria

1. WHEN the user asks a question specifically about ratings, score, or
   critical reception THEN the system SHALL call an MCP tool that returns
   only the ratings-related fields (IMDb rating, IMDb vote count,
   Metascore, and the full Ratings source list) for a given IMDb ID.
2. THE ratings tool SHALL be a distinct MCP tool from the details tool
   (Requirement 2), even though both may be backed by the same OMDb
   endpoint, so that the agent must choose between them based on what
   the user actually asked.

### Requirement 4: Current India theatrical releases

**User Story:** As a user, I want to ask what's currently playing or
about to release in Indian theaters, so that I can get real, current
release information rather than the agent guessing from stale training
data.

#### Acceptance Criteria

1. WHEN the user asks about currently playing or upcoming movie releases
   in India THEN the system SHALL call an MCP tool that queries TMDb's
   now-playing/upcoming endpoints filtered to region `IN`.
2. THE system SHALL NOT use unofficial or scraped data sources (e.g.
   BookMyShow) for release data, since no legitimate public API exists
   for that source.
3. IF TMDb returns no results for the India region THEN the tool SHALL
   return a structured empty result rather than fabricating releases.

### Requirement 5: Genuine agent-driven tool selection

**User Story:** As the project owner, I want the LLM to genuinely decide
which tool(s) to call for a given question, so that the project
demonstrates real agentic behavior rather than a disguised fixed
pipeline.

#### Acceptance Criteria

1. THE agent client SHALL NOT contain any hardcoded routing logic
   (e.g. `if "rating" in user_text`) that determines which tool to call
   based on the raw user message.
2. THE agent SHALL discover available tools at runtime via the MCP
   protocol's tool-listing mechanism, not via direct imports of server
   code.
3. WHEN a question requires information from more than one tool (e.g.
   resolving a title AND fetching its ratings) THEN the agent SHALL be
   able to call multiple tools in sequence within a single user turn.
4. WHEN the agent's response to a tool result is ambiguous or ungrounded
   THEN the system SHALL prefer retrying or admitting uncertainty over
   fabricating plausible-sounding data.

### Requirement 6: Robust error handling

**User Story:** As a user, I want the agent to behave predictably when
an API call fails or a required credential is missing, so that one bad
call doesn't crash my whole session.

#### Acceptance Criteria

1. IF the `OMDB_API_KEY` or `TMDB_API_KEY` environment variable is not
   set WHEN a tool that needs it is called THEN the tool SHALL return a
   structured error explaining which key is missing, rather than raising
   an unhandled exception.
2. WHEN any tool encounters a network timeout or HTTP error THEN the
   tool SHALL return a structured `{"error": ...}` result rather than
   crashing the MCP server process.
3. WHEN the LLM's response cannot be parsed as valid JSON (including
   after one repair attempt) THEN the agent SHALL fall back to a safe
   response rather than crashing the conversation loop.

### Requirement 7: Local CLI interface

**User Story:** As the project owner, I want a terminal-based way to
interact with the agent, so that I can test and demo it without needing
a web frontend first.

#### Acceptance Criteria

1. THE system SHALL provide a command-line entrypoint that connects to
   the MCP tools server, accepts free-text user input in a loop, and
   prints the agent's final answer for each turn.
2. WHEN a tool is called THEN the CLI SHALL print which tool was called
   and with what arguments, so the underlying decision-making is visible
   during a demo.

### Requirement 8: One-shot reflection on final answers

**User Story:** As the project owner, I want a lightweight self-check on
the agent's final answers, so that obvious mistakes are caught before
being shown to the user.

#### Acceptance Criteria

1. WHEN the agent produces a draft final answer THEN the system SHALL
   run exactly one additional review pass checking that answer against
   the conversation so far.
2. IF the review pass finds the draft answer incomplete or incorrect
   THEN the system SHALL replace it with a corrected answer.
3. THE reflection pass SHALL NOT loop or repeat beyond one additional
   check, to keep response latency bounded on local hardware.
