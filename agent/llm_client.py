"""
LLM client for agent decision-making and reflection.

Handles communication with Ollama (local) or OpenAI-compatible APIs (OpenRouter, OpenAI, etc.)
and provides tolerant JSON parsing with repair fallback.
Follows SOLID principles with an extensible LLMProvider interface.
"""

from abc import ABC, abstractmethod
import json
import os
import re
import time
from typing import Any, Callable, List, Dict, Optional, Literal
import requests
from pydantic import BaseModel, Field, ValidationError
from agent.observability import MetricsLogger

class DecisionModel(BaseModel):
    action: Literal["call_tool", "final"]
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None

class ReflectionModel(BaseModel):
    ok: bool
    corrected_answer: Optional[str] = None

class GroundingValidationModel(BaseModel):
    is_grounded: bool
    unsupported_claims: list[str] = Field(default_factory=list)


class LLMProvider(ABC):
    """Abstract base class defining the contract for LLM providers."""
    
    @abstractmethod
    def call(self, messages: List[Dict[str, str]]) -> str:
        """Send messages to the LLM provider and return the string response."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """Provider implementation for OpenAI-compatible APIs (OpenRouter, OpenAI, Groq, etc.)."""
    
    def __init__(self, model_name: str, api_key: str, base_url: str = "https://api.openai.com/v1", max_retries: int = 4):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
    
    def call(self, messages: List[Dict[str, str]]) -> str:
        # Start at the configured max_tokens; on a 413 "request too large"
        # (a TPM ceiling counting prompt + reserved completion tokens, not
        # a retryable rate limit), progressively ask for less completion
        # budget instead of immediately giving up to the fallback provider.
        current_max_tokens = 1024
        min_max_tokens = 200

        for attempt in range(self.max_retries):
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": current_max_tokens
                },
                timeout=120
            )

            if response.status_code == 429 and attempt < self.max_retries - 1:
                retry_after = response.headers.get("Retry-After")
                wait_seconds = float(retry_after) if retry_after else (2 ** (attempt + 1))
                time.sleep(wait_seconds)
                continue

            if response.status_code == 413 and current_max_tokens > min_max_tokens and attempt < self.max_retries - 1:
                # Groq's free tier counts (prompt tokens + max_tokens
                # reserved) toward its TPM ceiling. A long system prompt or
                # a conversation that's grown across several tool-call
                # iterations can tip a request over that limit even with a
                # modest max_tokens. Halving it and retrying immediately
                # (no sleep needed - this isn't a rate-limit cooldown, it's
                # a request-shape problem) recovers most of these without
                # ever falling through to the (possibly unconfigured) local
                # Ollama fallback.
                current_max_tokens = max(min_max_tokens, current_max_tokens // 2)
                print(f"[LLM Retry] 413 too-large - retrying with max_tokens={current_max_tokens}")
                continue

            if response.status_code >= 400:
                try:
                    error_detail = response.json()
                except ValueError:
                    error_detail = response.text
                raise RuntimeError(
                    f"{self.base_url} returned HTTP {response.status_code}: {error_detail}"
                )

            result = response.json()
            return result["choices"][0]["message"]["content"]

        raise RuntimeError(
            f"Rate limited by {self.base_url} after {self.max_retries} attempts."
        )


class OllamaProvider(LLMProvider):
    """Provider implementation for local Ollama instances."""
    
    def __init__(self, model_name: str, host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
    
    def call(self, messages: List[Dict[str, str]]) -> str:
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "")


class MockLLMProvider(LLMProvider):
    """Mock provider for unit testing without external API calls."""
    
    def __init__(self, responses: Optional[List[str]] = None, handler: Optional[Callable[[List[Dict[str, str]]], str]] = None):
        self.responses = responses or []
        self.handler = handler
        self.call_history: List[List[Dict[str, str]]] = []
    
    def call(self, messages: List[Dict[str, str]]) -> str:
        self.call_history.append(messages)
        if self.handler:
            return self.handler(messages)
        if self.responses:
            return self.responses.pop(0)
        return '{"action": "final", "answer": "Mocked default answer"}'


class FallbackLLMProvider(LLMProvider):
    """
    Provider wrapper that attempts a primary provider and falls back to a secondary
    provider if the primary raises an exception (e.g., API downtime, rate limits).
    """
    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary = primary
        self.fallback = fallback
        
    def call(self, messages: List[Dict[str, str]]) -> str:
        try:
            return self.primary.call(messages)
        except Exception as e:
            print(f"[LLM Fallback] Primary provider failed: {str(e)[:100]}... Switching to local fallback.")
            with MetricsLogger.start_span("llm_call_fallback", {"error": str(e)[:100]}):
                return self.fallback.call(messages)


def get_llm_provider(model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> LLMProvider:
    """
    Factory function to obtain an LLMProvider instance based on environment/config.
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    if api_key:
        primary = OpenAICompatibleProvider(model_name=model_name, api_key=api_key, base_url=base_url)
        # We assume the user has 'llama3.1' available on their local Ollama instance
        fallback = OllamaProvider(model_name="llama3.1")
        return FallbackLLMProvider(primary=primary, fallback=fallback)
    else:
        return OllamaProvider(model_name=model_name)


def decide(messages: list[dict[str, str]], model_name: str, provider: Optional[LLMProvider] = None) -> dict[str, Any]:
    """
    Call the LLM to make a decision (tool call or final answer).
    
    Returns a parsed JSON object from the LLM response.
    """
    if provider is None:
        provider = get_llm_provider(model_name)
        
    with MetricsLogger.start_span("llm_call", {"operation": "decide", "model": model_name}):
        response = provider.call(messages)
    
    try:
        parsed = _extract_first_json(response)
        decision = DecisionModel.model_validate(parsed)
        return decision.model_dump(exclude_none=True)
    except (ValueError, ValidationError) as e:
        raise RuntimeError(f"LLM decision validation failed: {str(e)}\nRaw response: {response}") from e


def reflect(history: list[dict[str, str]], draft_answer: str, model_name: str, provider: Optional[LLMProvider] = None) -> dict[str, Any]:
    """
    One-shot reflection pass to review a draft final answer.
    """
    reflection_prompt = {
        "role": "user",
        "content": (
            f"Review this draft answer against the conversation history:\n\n"
            f"Draft: {draft_answer}\n\n"
            f"CRITICAL: Respond with exactly ONE valid JSON object and absolutely nothing else. No conversational text before or after the JSON.\n"
            f'{{"ok": true}} if the draft answer is accurate and directly answers the user.\n'
            f'{{"ok": false, "corrected_answer": "..."}} ONLY if you can write a complete, polished user-facing response.\n\n'
            f"CRITICAL RULE: 'corrected_answer' MUST be a clean response written directly for the user. "
            f"NEVER include developer notes, meta-commentary, or instructions to call tools (such as 'Please call movie_details' or 'The original answer was...'). "
            f"If the draft answer is acceptable or if you cannot provide a full user answer, return {{\"ok\": true}}."
        )
    }
    
    messages = history + [reflection_prompt]
    if provider is None:
        provider = get_llm_provider(model_name)
        
    with MetricsLogger.start_span("llm_call", {"operation": "reflect", "model": model_name}):
        response = provider.call(messages)
    
    try:
        parsed = _extract_first_json(response)
        reflection = ReflectionModel.model_validate(parsed)
        
        # Meta keywords check for correction quality
        if not reflection.ok and reflection.corrected_answer:
            corr = reflection.corrected_answer.lower()
            meta_keywords = ["please call", "original answer", "general knowledge", "should be based on", "tool call", "direct tool call"]
            if any(kw in corr for kw in meta_keywords):
                return {"ok": True}
                
        return reflection.model_dump(exclude_none=True)
    except (ValueError, ValidationError) as e:
        raise RuntimeError(f"LLM reflection validation failed: {str(e)}\nRaw response: {response}") from e


def validate_grounding(history: list[dict[str, str]], draft_answer: str, model_name: str, provider: Optional[LLMProvider] = None) -> bool:
    """
    Validates that any factual claims in the draft answer are explicitly supported by the tool results in the history.
    """
    grounding_prompt = {
        "role": "user",
        "content": (
            f"Review this conversation history and the draft answer.\n\n"
            f"Draft: {draft_answer}\n\n"
            f"CRITICAL: Respond with exactly ONE valid JSON object and absolutely nothing else. No conversational text before or after the JSON.\n"
            f"Check if the draft answer makes ANY major factual claims about movies (titles, release dates, plot specifics, ratings).\n"
            f"Verify that these claims are generally supported by the 'Tool result' blocks in the history.\n"
            f"It is OK if the draft answer paraphrases the plot or uses common sense formatting, as long as it doesn't invent entirely new, unsupported facts (like fake sequels or wrong actors).\n"
            f"If the answer contains major fabrications not supported by the Tool Results, it is NOT grounded.\n"
            f"If the answer is a general greeting, clarifying question, or accurately reflects the tool data, it IS grounded.\n"
            f"IMPORTANT: default to is_grounded=true unless you can point to a SPECIFIC sentence that states a concrete fact "
            f"(a title, date, name, or number) with no matching support anywhere in the tool results. Minor rewording, "
            f"summarizing, or well-known general context about a famous film is NOT a fabrication - do not reject an answer "
            f"just because it adds reasonable framing on top of the tool data. When genuinely unsure, prefer true over false: "
            f"a wrongly-approved answer is far less harmful to the user than wrongly discarding a correct, well-supported one.\n"
            f"Return {{\"is_grounded\": true, \"unsupported_claims\": []}} if it passes, or {{\"is_grounded\": false, \"unsupported_claims\": [\"claim 1\", ...]}} if it fails."
        )
    }
    
    messages = history + [grounding_prompt]
    if provider is None:
        provider = get_llm_provider(model_name)
        
    with MetricsLogger.start_span("llm_call", {"operation": "validate_grounding", "model": model_name}):
        response = provider.call(messages)
    
    try:
        parsed = _extract_first_json(response)
        validation = GroundingValidationModel.model_validate(parsed)
        if not validation.is_grounded:
            # Previously this reason was computed and then discarded, making
            # every FALLBACK_UNGROUNDED response undebuggable - there was no
            # way to tell whether the judge caught a real fabrication or
            # just misjudged a well-supported answer (e.g. a false positive
            # on a well-known movie). Surface it so it's visible in logs.
            print(f"[Grounding] Rejected as ungrounded. Unsupported claims: {validation.unsupported_claims}")
        return validation.is_grounded
    except (ValueError, ValidationError) as e:
        raise RuntimeError(f"LLM grounding validation failed: {str(e)}\nRaw response: {response}") from e


def _extract_first_json(text: str) -> dict[str, Any]:
    """
    Tolerantly extract the first valid JSON object from text.
    Raises ValueError if a valid JSON object cannot be found.

    This is string-aware: brace characters that appear INSIDE a JSON string
    value (e.g. a movie title quoted mid-sentence, or any '{'/'}' in prose)
    no longer affect the depth count. The previous version tracked braces
    naively across the whole text, so a stray/unescaped quote inside the
    model's answer could desync the counter and produce a false 'unbalanced'
    result even when the real JSON object was well-formed.

    It also never discards the position of the first '{' once found - the
    previous version reset start_idx to None the moment ANY candidate slice
    failed to parse, which silently disabled the truncation-repair fallback
    below it (the repair path only runs `if start_idx is not None`).
    """
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = text.strip()

    # Fast path: well-formed responses parse immediately, no scanning needed.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_open = None
    balanced_candidate = None
    depth = 0
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '{':
            if depth == 0:
                first_open = i if first_open is None else first_open
                candidate_start = i
            depth += 1
        elif char == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and balanced_candidate is None:
                    balanced_candidate = text[candidate_start:i + 1]

    if balanced_candidate is not None:
        try:
            return json.loads(balanced_candidate)
        except json.JSONDecodeError:
            pass  # fall through to truncation repair below

    # Truncation repair: the response likely got cut off (e.g. hit max_tokens
    # mid-string) before ever closing its braces. Try trimming any trailing
    # partial token and appending plausible closing punctuation.
    if first_open is not None:
        tail = text[first_open:]
        for repair in ['"}', '"]}', '}', ']}']:
            try:
                return json.loads(tail + repair)
            except json.JSONDecodeError:
                continue
        # Last resort: drop back to the last comma (likely the last complete
        # key/value pair) before appending closing punctuation.
        last_comma = tail.rfind(',')
        if last_comma > 0:
            trimmed = tail[:last_comma]
            for repair in ['}', ']}']:
                try:
                    return json.loads(trimmed + repair)
                except json.JSONDecodeError:
                    continue

    raise ValueError(f"Could not extract valid JSON from response: {text}")