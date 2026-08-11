"""
llm_client.py — unified async, multi-key, multi-provider LLM client.

Every agent service should receive an `LLMClient` instance (dependency-injected
via backend/dependencies.py::get_llm_client) rather than instantiating its own
`AsyncOpenAI` client. This is what makes many OpenAI keys + many Groq keys
behave as one resilient pool with automatic rate-limit fallback, and what
makes tests able to swap in `llm_mock.FakeLLMClient` instead of hitting real
APIs.

Design
──────
- OpenAI is the primary path for both plain text and structured output, and
  the only path for web-search-grounded generation.
- Groq is the fallback path, used only once every OpenAI key is cooling down
  (rate-limited) or erroring. Groq hosts many different model families with
  inconsistent tool-calling/schema support, so instead of trying to map each
  model's native structured-output quirks, we use one uniform strategy:
  prompt-injected JSON schema + response_format=json_object +
  reasoning_format="hidden" (strips <think> blocks from reasoning models) +
  pydantic validation with one repair-retry. This behaves predictably across
  every Groq model and keeps the fallback path simple.
- Web-search-grounded generation (used by tools/search_tool.py) goes through
  OpenAI's Responses API `web_search` tool. Groq has no equivalent, so calls
  that pass `web_search=True` never fall over to Groq — they raise
  LLMAllProvidersExhaustedError instead of silently degrading to a
  non-grounded (and therefore less trustworthy) answer.
- Key selection (KeyPool.acquire) is guarded by an asyncio.Lock, but the
  network call itself is not — concurrent asyncio.gather'd agents only briefly
  serialize on "which key do I use next," not on I/O.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from config import settings

logger = logging.getLogger("llm_client")

T = TypeVar("T", bound=BaseModel)


class LLMAllProvidersExhaustedError(Exception):
    """Raised when every configured key across every eligible provider has
    failed or is cooling down for a given call."""


class KeyPool:
    """Round-robins a list of API keys, skipping keys that are cooling down
    after a rate-limit/error hit."""

    def __init__(self, keys: list[str], cooldown_seconds: float):
        self._keys = list(keys)
        self._cooldown_seconds = cooldown_seconds
        self._cursor = 0
        self._cooldown_until: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    async def acquire(self) -> Optional[str]:
        """Return the next usable key, or None if all keys are cooling down."""
        if not self._keys:
            return None
        async with self._lock:
            now = time.time()
            for _ in range(len(self._keys)):
                key = self._keys[self._cursor]
                self._cursor = (self._cursor + 1) % len(self._keys)
                if self._cooldown_until.get(key, 0.0) <= now:
                    return key
            return None

    def mark_cooldown(self, key: str, seconds: Optional[float] = None) -> None:
        self._cooldown_until[key] = time.time() + (seconds if seconds is not None else self._cooldown_seconds)

    def usable_count(self) -> int:
        now = time.time()
        return sum(1 for k in self._keys if self._cooldown_until.get(k, 0.0) <= now)


def _is_retryable_groq(exc: Exception) -> bool:
    import groq

    if isinstance(exc, groq.APIStatusError):
        return exc.status_code in (401, 403, 408, 429, 500, 502, 503, 504)
    if isinstance(exc, (groq.APIConnectionError, groq.APITimeoutError)):
        return True
    return True


def _is_retryable_openai(exc: Exception) -> bool:
    import openai

    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in (401, 403, 408, 429, 500, 502, 503, 504)
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return True
    return True


class LLMClient:
    def __init__(self, settings_obj=None):
        self._settings = settings_obj or settings
        self._openai_pool = KeyPool(self._settings.OPENAI_API_KEYS, self._settings.LLM_KEY_COOLDOWN_SECONDS)
        self._groq_pool = KeyPool(self._settings.GROQ_API_KEYS, self._settings.LLM_KEY_COOLDOWN_SECONDS)
        self._openai_clients: dict[str, Any] = {}
        self._groq_clients: dict[str, Any] = {}

    # ── client caching ───────────────────────────────────────────────────

    def _openai_client_for(self, key: str):
        from openai import AsyncOpenAI

        client = self._openai_clients.get(key)
        if client is None:
            client = AsyncOpenAI(api_key=key)
            self._openai_clients[key] = client
        return client

    def _groq_client_for(self, key: str):
        from groq import AsyncGroq

        client = self._groq_clients.get(key)
        if client is None:
            client = AsyncGroq(api_key=key)
            self._groq_clients[key] = client
        return client

    # ── public API ───────────────────────────────────────────────────────

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        model_openai: Optional[str] = None,
        model_groq: Optional[str] = None,
    ) -> T:
        result = await self._try_openai_structured(
            prompt, schema, system_instruction=system_instruction, temperature=temperature,
            model=model_openai or self._settings.OPENAI_MODEL_DEFAULT,
        )
        if result is not None:
            return result

        result = await self._try_groq_structured(
            prompt, schema, system_instruction=system_instruction, temperature=temperature,
            model=model_groq or self._settings.GROQ_MODEL_DEFAULT,
        )
        if result is not None:
            return result

        raise LLMAllProvidersExhaustedError(
            f"All OpenAI ({len(self._openai_pool)}) and Groq ({len(self._groq_pool)}) keys "
            f"exhausted or failed for generate_structured({schema.__name__})."
        )

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        web_search: bool = False,
        model_openai: Optional[str] = None,
        model_groq: Optional[str] = None,
    ) -> str:
        if web_search:
            # Grounded (web search) generation goes through OpenAI's Responses
            # API web_search tool. Groq has no equivalent, so this never falls
            # over to another provider.
            text = await self._try_openai_grounded_text(
                prompt, system_instruction=system_instruction,
                model=model_openai or self._settings.OPENAI_MODEL_DEFAULT,
            )
            if text is not None:
                return text
            raise LLMAllProvidersExhaustedError(
                f"All OpenAI keys ({len(self._openai_pool)}) exhausted for a grounded "
                f"(web_search) call. This call cannot fail over to Groq."
            )

        text = await self._try_openai_text(
            prompt, system_instruction=system_instruction, temperature=temperature,
            model=model_openai or self._settings.OPENAI_MODEL_DEFAULT,
        )
        if text is not None:
            return text

        text = await self._try_groq_text(
            prompt, system_instruction=system_instruction, temperature=temperature,
            model=model_groq or self._settings.GROQ_MODEL_DEFAULT,
        )
        if text is not None:
            return text

        raise LLMAllProvidersExhaustedError(
            f"All OpenAI ({len(self._openai_pool)}) and Groq ({len(self._groq_pool)}) keys "
            f"exhausted or failed for generate_text()."
        )

    async def health(self) -> dict:
        return {
            "openai": {"total": len(self._openai_pool), "usable": self._openai_pool.usable_count()},
            "groq": {"total": len(self._groq_pool), "usable": self._groq_pool.usable_count()},
        }

    # ── OpenAI paths ─────────────────────────────────────────────────────

    async def _try_openai_grounded_text(self, prompt, *, system_instruction, model):
        attempts = max(len(self._openai_pool), 1)
        for _ in range(attempts):
            key = await self._openai_pool.acquire()
            if key is None:
                return None
            try:
                client = self._openai_client_for(key)
                full_input = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                response = await client.responses.create(
                    model=model,
                    input=full_input,
                    tools=[{"type": "web_search"}],
                )
                return response.output_text
            except Exception as e:
                retryable = _is_retryable_openai(e)
                logger.warning("OpenAI grounded call failed (retryable=%s): %s", retryable, e)
                self._openai_pool.mark_cooldown(key, None if retryable else 5.0)
        return None

    def _openai_schema_prompt(self, prompt: str, schema: Type[BaseModel]) -> str:
        return (
            f"{prompt}\n\n"
            "Respond with ONLY a single valid JSON object (no markdown fences, no commentary) "
            "matching exactly this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )

    async def _try_openai_structured(self, prompt, schema, *, system_instruction, temperature, model):
        base_prompt = self._openai_schema_prompt(prompt, schema)
        attempts = max(len(self._openai_pool), 1)
        for _ in range(attempts):
            key = await self._openai_pool.acquire()
            if key is None:
                return None
            client = self._openai_client_for(key)
            current_prompt = base_prompt
            for repair_attempt in range(self._settings.LLM_MAX_REPAIR_RETRIES + 1):
                try:
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": current_prompt})
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        response_format={"type": "json_object"},
                    )
                    content = response.choices[0].message.content
                    return schema.model_validate_json(content)
                except ValidationError as e:
                    if repair_attempt >= self._settings.LLM_MAX_REPAIR_RETRIES:
                        logger.warning("OpenAI structured output failed schema validation, out of repair retries: %s", e)
                        break
                    logger.info("OpenAI structured output failed validation, retrying with repair prompt: %s", e)
                    current_prompt = (
                        f"{base_prompt}\n\nYour previous response was invalid: {e}\n"
                        "Return corrected JSON that strictly matches the schema."
                    )
                    continue
                except Exception as e:
                    retryable = _is_retryable_openai(e)
                    logger.warning("OpenAI structured call failed (retryable=%s): %s", retryable, e)
                    self._openai_pool.mark_cooldown(key, None if retryable else 5.0)
                    break
        return None

    async def _try_openai_text(self, prompt, *, system_instruction, temperature, model):
        attempts = max(len(self._openai_pool), 1)
        for _ in range(attempts):
            key = await self._openai_pool.acquire()
            if key is None:
                return None
            try:
                client = self._openai_client_for(key)
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model=model, messages=messages,
                )
                return response.choices[0].message.content
            except Exception as e:
                retryable = _is_retryable_openai(e)
                logger.warning("OpenAI text call failed (retryable=%s): %s", retryable, e)
                self._openai_pool.mark_cooldown(key, None if retryable else 5.0)
        return None

    # ── Groq paths ───────────────────────────────────────────────────────

    def _groq_schema_prompt(self, prompt: str, schema: Type[BaseModel]) -> str:
        return (
            f"{prompt}\n\n"
            "Respond with ONLY a single valid JSON object (no markdown fences, no commentary) "
            "matching exactly this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )

    async def _try_groq_structured(self, prompt, schema, *, system_instruction, temperature, model):
        base_prompt = self._groq_schema_prompt(prompt, schema)
        attempts = max(len(self._groq_pool), 1)
        for _ in range(attempts):
            key = await self._groq_pool.acquire()
            if key is None:
                return None
            client = self._groq_client_for(key)
            current_prompt = base_prompt
            for repair_attempt in range(self._settings.LLM_MAX_REPAIR_RETRIES + 1):
                try:
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": current_prompt})
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                        reasoning_format="hidden",
                    )
                    content = response.choices[0].message.content
                    return schema.model_validate_json(content)
                except ValidationError as e:
                    if repair_attempt >= self._settings.LLM_MAX_REPAIR_RETRIES:
                        logger.warning("Groq structured output failed schema validation, out of repair retries: %s", e)
                        break
                    logger.info("Groq structured output failed validation, retrying with repair prompt: %s", e)
                    current_prompt = (
                        f"{base_prompt}\n\nYour previous response was invalid: {e}\n"
                        "Return corrected JSON that strictly matches the schema."
                    )
                    continue
                except Exception as e:
                    retryable = _is_retryable_groq(e)
                    logger.warning("Groq structured call failed (retryable=%s): %s", retryable, e)
                    self._groq_pool.mark_cooldown(key, None if retryable else 5.0)
                    break
        return None

    async def _try_groq_text(self, prompt, *, system_instruction, temperature, model):
        attempts = max(len(self._groq_pool), 1)
        for _ in range(attempts):
            key = await self._groq_pool.acquire()
            if key is None:
                return None
            try:
                client = self._groq_client_for(key)
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model=model, messages=messages, temperature=temperature, reasoning_format="hidden",
                )
                return response.choices[0].message.content
            except Exception as e:
                retryable = _is_retryable_groq(e)
                logger.warning("Groq text call failed (retryable=%s): %s", retryable, e)
                self._groq_pool.mark_cooldown(key, None if retryable else 5.0)
        return None
