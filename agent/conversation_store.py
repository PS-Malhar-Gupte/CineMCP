"""
Persistent conversation history, keyed by session_id.

This is distinct from agent.conversation.ConversationState, which is an
in-process, per-request working copy used to build the prompt for the
current turn. ConversationStore is the durable layer underneath it:

    on connect:  history = await store.get_history(session_id)
                 conv_state.load(history)
    each turn:   conv_state.add_turn(user_msg, answer)      # in-process
                 await store.append_turn(session_id, user_msg, answer)  # durable

Splitting them this way means a dropped/reconnected WebSocket (a new
ConnectionManager entry, hence a new ConversationState) can still recover
the same conversation by re-fetching from the store using the same
session_id - which is the whole point: session_id is the one thing that
survives a reconnect (it's generated client-side and stored in
localStorage), so it's the correct key for durable state, not the
WebSocket connection object.
"""

from abc import ABC, abstractmethod
from typing import Optional
import asyncio
import json

from agent.config import CONVERSATION_TTL_SECONDS, MEMORY_BACKEND, REDIS_URL


class ConversationStore(ABC):
    """Abstract base class for durable conversation history."""

    @abstractmethod
    async def get_history(self, session_id: str) -> list[dict]:
        """Return the stored turns for a session, oldest first."""
        raise NotImplementedError

    @abstractmethod
    async def append_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append one completed turn (user + assistant message pair)."""
        raise NotImplementedError

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """Delete all stored history for a session (used by 'new conversation')."""
        raise NotImplementedError


class LocalConversationStore(ConversationStore):
    """
    In-process fallback store. Not persisted across restarts, and not
    shared across workers - fine for offline/dev use with MEMORY_BACKEND=local,
    but doesn't survive a server restart the way RedisConversationStore does.
    """

    def __init__(self):
        self._store: dict[str, list[dict]] = {}
        self._lock = asyncio.Lock()

    async def get_history(self, session_id: str) -> list[dict]:
        return list(self._store.get(session_id, []))

    async def append_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        async with self._lock:
            self._store.setdefault(session_id, [])
            self._store[session_id].append({"role": "user", "content": user_msg})
            self._store[session_id].append({"role": "assistant", "content": assistant_msg})

    async def clear(self, session_id: str) -> None:
        async with self._lock:
            self._store.pop(session_id, None)


class RedisConversationStore(ConversationStore):
    """
    Redis-backed conversation history. Stores each session's turns as a
    single JSON-encoded list under `conv:{session_id}`, with a sliding TTL
    refreshed on every append so idle sessions expire naturally instead of
    accumulating forever.

    A JSON blob (rather than a Redis list of individually-appended items)
    is used so trimming to the most recent N turns is a single read-modify-
    write, matching the same truncation rule ConversationState already
    applies - one source of truth for "how much history do we keep."
    """

    def __init__(self, redis_url: str, max_turns: int):
        import redis.asyncio as redis  # local import: optional dependency

        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._max_turns = max_turns

    @staticmethod
    def _redis_key(session_id: str) -> str:
        return f"conv:{session_id}"

    async def get_history(self, session_id: str) -> list[dict]:
        try:
            raw = await self._redis.get(self._redis_key(session_id))
        except Exception as e:
            print(f"Warning: Redis conversation get_history() failed: {e}")
            return []
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    async def append_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        key = self._redis_key(session_id)
        try:
            history = await self.get_history(session_id)
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_msg})
            max_messages = self._max_turns * 2
            if len(history) > max_messages:
                history = history[-max_messages:]
            await self._redis.set(key, json.dumps(history), ex=CONVERSATION_TTL_SECONDS)
        except Exception as e:
            # A Redis blip here shouldn't crash the turn - the in-process
            # ConversationState still has this turn for the rest of *this*
            # connection's lifetime, we just lose reconnect-continuity for it.
            print(f"Warning: Redis conversation append_turn() failed: {e}")

    async def clear(self, session_id: str) -> None:
        try:
            await self._redis.delete(self._redis_key(session_id))
        except Exception as e:
            print(f"Warning: Redis conversation clear() failed: {e}")

    async def aclose(self) -> None:
        await self._redis.aclose()


def get_conversation_store(max_turns: int) -> ConversationStore:
    """
    Factory that picks the conversation-history backend based on
    MEMORY_BACKEND, mirroring agent.memory.get_memory_provider(). Falls
    back to the local in-process store if Redis can't be constructed,
    rather than crashing app startup.
    """
    if MEMORY_BACKEND == "redis":
        try:
            return RedisConversationStore(REDIS_URL, max_turns=max_turns)
        except Exception as e:
            print(
                f"Warning: Could not initialize Redis conversation store ({e}). "
                "Falling back to local in-process conversation store."
            )
    return LocalConversationStore()
