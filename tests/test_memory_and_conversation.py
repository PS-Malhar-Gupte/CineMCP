"""
Tests for the Redis-backed conversation history + answer cache (Phase:
conversation state & memory management).

Uses the local in-process fallbacks (LocalMemoryService,
LocalConversationStore) rather than a real Redis instance, so these run
without any external dependency - they validate the same contract
(is_cacheable filtering, TTL selection logic, append/trim/load behavior)
that the Redis-backed classes must also satisfy.
"""

import asyncio
import unittest

from agent.config import FALLBACK_EMPTY_RESULT, FALLBACK_UNGROUNDED
from agent.memory import LocalMemoryService, is_cacheable, cache_ttl_for_tools
from agent.conversation import ConversationState
from agent.conversation_store import LocalConversationStore


class TestCacheability(unittest.TestCase):

    def test_fallback_answers_are_not_cacheable(self):
        self.assertFalse(is_cacheable(FALLBACK_EMPTY_RESULT))
        self.assertFalse(is_cacheable(FALLBACK_UNGROUNDED))

    def test_normal_answers_are_cacheable(self):
        self.assertTrue(is_cacheable("Inception was directed by Christopher Nolan."))

    def test_volatile_tool_gets_short_ttl(self):
        short = cache_ttl_for_tools(["now_playing_india"])
        long = cache_ttl_for_tools(["search_movie", "movie_details"])
        self.assertLess(short, long)

    def test_no_tools_used_gets_stable_ttl(self):
        self.assertEqual(cache_ttl_for_tools(None), cache_ttl_for_tools([]))


class TestLocalMemoryService(unittest.TestCase):

    def test_set_then_get_round_trip(self):
        async def _run():
            svc = LocalMemoryService(persist_path=None)
            key = svc.generate_key("Who directed Inception?")
            await svc.set("session-a", key, "Christopher Nolan")
            return await svc.get("session-a", key)
        result = asyncio.run(_run())
        self.assertEqual(result, "Christopher Nolan")

    def test_fallback_answer_is_never_stored(self):
        async def _run():
            svc = LocalMemoryService(persist_path=None)
            key = svc.generate_key("Some question")
            await svc.set("session-a", key, FALLBACK_UNGROUNDED)
            return await svc.get("session-a", key)
        result = asyncio.run(_run())
        self.assertIsNone(result)

    def test_sessions_are_isolated(self):
        async def _run():
            svc = LocalMemoryService(persist_path=None)
            key = svc.generate_key("same question")
            await svc.set("session-a", key, "Answer A")
            await svc.set("session-b", key, "Answer B")
            return await svc.get("session-a", key), await svc.get("session-b", key)
        a, b = asyncio.run(_run())
        self.assertEqual(a, "Answer A")
        self.assertEqual(b, "Answer B")


class TestConversationStateAndStore(unittest.TestCase):

    def test_add_turn_truncates_to_max_turns(self):
        state = ConversationState(max_turns=2)
        for i in range(5):
            state.add_turn(f"q{i}", f"a{i}")
        history = state.get_history()
        # 2 turns = 4 messages max
        self.assertEqual(len(history), 4)
        # Should be the two most recent turns
        self.assertEqual(history[0]["content"], "q3")
        self.assertEqual(history[-1]["content"], "a4")

    def test_load_applies_same_truncation_as_add_turn(self):
        state = ConversationState(max_turns=1)
        long_history = []
        for i in range(5):
            long_history.append({"role": "user", "content": f"q{i}"})
            long_history.append({"role": "assistant", "content": f"a{i}"})
        state.load(long_history)
        history = state.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "q4")

    def test_conversation_store_round_trip_and_reconnect_scenario(self):
        async def _run():
            store = LocalConversationStore()
            session_id = "session-xyz"

            # Simulate connection #1: a couple of turns happen.
            await store.append_turn(session_id, "What's Inception about?", "A heist in dreams.")
            await store.append_turn(session_id, "Who directed it?", "Christopher Nolan.")

            # Simulate a dropped connection: a brand new ConversationState
            # (as ConnectionManager.connect_ws creates on every accept)
            # should still recover full history via the same session_id.
            new_conv_state = ConversationState(max_turns=5)
            stored = await store.get_history(session_id)
            new_conv_state.load(stored)

            return new_conv_state.get_history()

        history = asyncio.run(_run())
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["content"], "What's Inception about?")
        self.assertEqual(history[-1]["content"], "Christopher Nolan.")

    def test_clear_removes_session_history(self):
        async def _run():
            store = LocalConversationStore()
            await store.append_turn("s1", "q", "a")
            await store.clear("s1")
            return await store.get_history("s1")
        history = asyncio.run(_run())
        self.assertEqual(history, [])


if __name__ == "__main__":
    unittest.main()
