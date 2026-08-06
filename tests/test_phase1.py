"""
Phase 1 Architecture & Unit Tests.

Validates:
1. AgentConfig dataclass instantiation and environment overrides.
2. LLMProvider interface, factory, and MockLLMProvider behavior.
3. decide() and reflect() with MockLLMProvider.
"""

import os
import unittest
from agent.config import AgentConfig, MODEL_NAME, MAX_LOOP_ITERATIONS
from agent.llm_client import (
    LLMProvider,
    MockLLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
    decide,
    reflect
)


class TestPhase1Architecture(unittest.TestCase):

    def test_agent_config_defaults(self):
        config = AgentConfig()
        self.assertEqual(config.model_name, MODEL_NAME)
        self.assertEqual(config.max_loop_iterations, MAX_LOOP_ITERATIONS)
        self.assertIn("movie information assistant", config.system_prompt)

    def test_agent_config_from_env(self):
        os.environ["MODEL_NAME"] = "test-custom-model"
        os.environ["MAX_LOOP_ITERATIONS"] = "15"
        try:
            config = AgentConfig.from_env()
            self.assertEqual(config.model_name, "test-custom-model")
            self.assertEqual(config.max_loop_iterations, 15)
        finally:
            os.environ.pop("MODEL_NAME", None)
            os.environ.pop("MAX_LOOP_ITERATIONS", None)

    def test_provider_factory(self):
        provider_ollama = get_llm_provider("mistral:7b", api_key="", base_url="")
        self.assertIsInstance(provider_ollama, OllamaProvider)

        provider_openai = get_llm_provider("gpt-4o", api_key="sk-fake-key")
        self.assertIsInstance(provider_openai, OpenAICompatibleProvider)

    def test_decide_with_mock_provider(self):
        mock_response = '{"action": "final", "answer": "Inception was directed by Christopher Nolan."}'
        mock_provider = MockLLMProvider(responses=[mock_response])

        messages = [{"role": "user", "content": "Who directed Inception?"}]
        decision = decide(messages, "mock-model", provider=mock_provider)

        self.assertEqual(decision["action"], "final")
        self.assertEqual(decision["answer"], "Inception was directed by Christopher Nolan.")
        self.assertEqual(len(mock_provider.call_history), 1)

    def test_reflect_with_mock_provider(self):
        mock_response = '{"ok": true}'
        mock_provider = MockLLMProvider(responses=[mock_response])

        history = [{"role": "user", "content": "Who directed Inception?"}]
        draft = "Christopher Nolan"

        result = reflect(history, draft, "mock-model", provider=mock_provider)
        self.assertTrue(result.get("ok"))
        self.assertEqual(len(mock_provider.call_history), 1)


if __name__ == "__main__":
    unittest.main()
