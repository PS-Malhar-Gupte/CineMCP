"""
Memory module for the agent.

Provides abstractions for caching agent answers so repeated questions are
fast and don't re-hit the LLM/tool chain. Two backends:

- LocalMemoryService: an in-process dict, optionally persisted to a JSON
  file. Ephemeral-ish, single-process, fine for CLI/offline dev.
- RedisMemoryProvider: shared, persistent, TTL-aware cache. Used by the web
  backend so the cache (and, via conversation_store.py, conversation
  history) survive process restarts and are shared across concurrent
  connections/workers.

Both are keyed by (session_id, query_hash) rather than a free-form user_id,
so the web backend and CLI can each pick whatever session-scoping makes
sense for their surface without changing this module.

Important: NOT every produced answer should be cached. A grounding-fallback
or empty-result answer is a symptom of a transient tool/API failure, not a
fact about the question - caching it would permanently "poison" that
question with a wrong answer. is_cacheable() encodes that rule; callers
should check it before calling set().
"""

from abc import ABC, abstractmethod
from typing import Optional, Iterable
import asyncio
import json
import os
import hashlib

from agent.config import (
    FALLBACK_EMPTY_RESULT,
    FALLBACK_UNGROUNDED,
    CACHE_TTL_STABLE_SECONDS,
    CACHE_TTL_VOLATILE_SECONDS,
    VOLATILE_CACHE_TOOLS,
    MEMORY_BACKEND,
    REDIS_URL,
)

# Answers matching one of these should never be persisted to the cache -
# they represent "we couldn't verify this," not "this is the answer."
_UNCACHEABLE_ANSWERS = {FALLBACK_EMPTY_RESULT, FALLBACK_UNGROUNDED}


def is_cacheable(answer: str) -> bool:
    """
    Returns False for fallback/error answers that should never be cached,
    since caching them would permanently serve a transient failure as if
    it were the real answer to the question.
    """
    return answer not in _UNCACHEABLE_ANSWERS


def cache_ttl_for_tools(tools_used: Optional[Iterable[str]]) -> int:
    """
    Picks a cache TTL based on which tools produced the answer. Answers
    built from date-sensitive tools (now playing / upcoming / recent
    releases) expire quickly; everything else (fixed movie facts) is
    treated as stable and cached longer.
    """
    if tools_used and any(t in VOLATILE_CACHE_TOOLS for t in tools_used):
        return CACHE_TTL_VOLATILE_SECONDS
    return CACHE_TTL_STABLE_SECONDS


class MemoryProvider(ABC):
    """
    Abstract base class for memory services.

    Any memory implementation (Local, Redis, etc.) must implement these
    methods to store and retrieve data. All methods are async so the same
    interface can be backed by a network call (Redis) or in-process state
    (local dict) interchangeably.
    """

    @abstractmethod
    async def get(self, session_id: str, key: str) -> Optional[str]:
        """Retrieve a cached value for a specific session."""
        raise NotImplementedError

    @abstractmethod
    async def set(
        self,
        session_id: str,
        key: str,
        value: str,
        tools_used: Optional[Iterable[str]] = None,
    ) -> None:
        """
        Store a value for a specific session. Implementations should skip
        the write (or otherwise avoid it) when `is_cacheable(value)` is
        False, and should apply `cache_ttl_for_tools(tools_used)` where the
        backend supports expiry.
        """
        raise NotImplementedError

    def generate_key(self, query: str) -> str:
        """
        Helper method to generate a consistent key for a query.
        Uses SHA-256 to hash the query string.
        """
        # Normalize the query by converting to lowercase and stripping whitespace
        normalized_query = query.strip().lower()
        return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()


class LocalMemoryService(MemoryProvider):
    """
    Local implementation of MemoryProvider using a Python dictionary.
    Optionally persists to a local JSON file. No TTL support - entries live
    until the process restarts (or forever, if persisted).
    """

    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize the local memory service.

        Args:
            persist_path: Optional file path to load/save memory data.
                          If None, memory is entirely ephemeral.
        """
        self.persist_path = persist_path
        self._store: dict[str, dict[str, str]] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self._store = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load local memory from {self.persist_path}: {e}")
                self._store = {}

    def _save_sync(self) -> None:
        if self.persist_path:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(self.persist_path)), exist_ok=True)
                with open(self.persist_path, "w", encoding="utf-8") as f:
                    json.dump(self._store, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save local memory to {self.persist_path}: {e}")

    async def get(self, session_id: str, key: str) -> Optional[str]:
        """Retrieve a cached value for a specific session."""
        session_store = self._store.get(session_id, {})
        return session_store.get(key)

    async def set(
        self,
        session_id: str,
        key: str,
        value: str,
        tools_used: Optional[Iterable[str]] = None,
    ) -> None:
        """Store a value for a specific session and persist to disk."""
        if not is_cacheable(value):
            return
        # Guard against concurrent writers (CLI + multiple web connections
        # sharing the same JSON file) clobbering each other's in-memory
        # dict update before it's flushed to disk.
        async with self._lock:
            if session_id not in self._store:
                self._store[session_id] = {}
            self._store[session_id][key] = value
            # File I/O is blocking; keep it off the event loop.
            await asyncio.to_thread(self._save_sync)


class RedisMemoryProvider(MemoryProvider):
    """
    Redis-backed answer cache. Shared across processes (CLI + all web
    workers/connections), TTL-aware, and safe under concurrent writers
    since Redis handles that natively (no local locking needed).

    Each session's cache lives in a single Redis hash (`cache:{session_id}`)
    so it can be inspected/cleared as a unit; per-entry TTL isn't natively
    supported on individual hash fields in older Redis versions, so instead
    we key each cached answer as its own string (`cache:{session_id}:{key}`)
    to get real per-entry expiry.
    """

    def __init__(self, redis_url: str):
        import redis.asyncio as redis  # local import: optional dependency

        self._redis = redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _redis_key(session_id: str, key: str) -> str:
        return f"cache:{session_id}:{key}"

    async def get(self, session_id: str, key: str) -> Optional[str]:
        try:
            return await self._redis.get(self._redis_key(session_id, key))
        except Exception as e:
            # A Redis blip shouldn't take down the request - just miss the
            # cache and let the agent loop run normally.
            print(f"Warning: Redis cache get() failed: {e}")
            return None

    async def set(
        self,
        session_id: str,
        key: str,
        value: str,
        tools_used: Optional[Iterable[str]] = None,
    ) -> None:
        if not is_cacheable(value):
            return
        ttl = cache_ttl_for_tools(tools_used)
        try:
            await self._redis.set(self._redis_key(session_id, key), value, ex=ttl)
        except Exception as e:
            print(f"Warning: Redis cache set() failed: {e}")

    async def aclose(self) -> None:
        await self._redis.aclose()


def get_memory_provider(local_persist_path: Optional[str] = None) -> MemoryProvider:
    """
    Factory that picks the memory backend based on MEMORY_BACKEND
    ("redis" by default, "local" as an offline/dev fallback). Callers pass
    `local_persist_path` for the local-backend case; it's ignored for Redis.

    If Redis is selected but can't be constructed (bad URL, missing
    `redis` package), falls back to the local backend with a warning
    rather than crashing the whole app on startup.
    """
    if MEMORY_BACKEND == "redis":
        try:
            return RedisMemoryProvider(REDIS_URL)
        except Exception as e:
            print(
                f"Warning: Could not initialize Redis memory backend ({e}). "
                "Falling back to local in-process memory."
            )
    return LocalMemoryService(persist_path=local_persist_path)
