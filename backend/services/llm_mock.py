"""
llm_mock.py — test double for LLMClient.

Agents take `llm_client` as an injected parameter specifically so tests can
pass a FakeLLMClient instead of hitting real OpenAI/Groq APIs. Per project
policy: real API calls are reserved for final verification, not routine
development/test runs.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient:
    """
    Configure canned responses either by schema class (`structured_responses`)
    or with a callable override for tests that need per-call logic:

        fake = FakeLLMClient(structured_responses={GapAnalysisOutput: my_fixture})
        fake = FakeLLMClient(text="mocked plain text")
        fake = FakeLLMClient(structured_fn=lambda prompt, schema, **kw: my_fixture)
    """

    def __init__(
        self,
        structured_responses: Optional[dict[Type[BaseModel], BaseModel]] = None,
        text: str = "",
        structured_fn: Optional[Callable[..., BaseModel]] = None,
        text_fn: Optional[Callable[..., str]] = None,
    ):
        self._structured_responses = structured_responses or {}
        self._text = text
        self._structured_fn = structured_fn
        self._text_fn = text_fn
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(self, prompt: str, schema: Type[T], **kwargs) -> T:
        self.calls.append({"method": "generate_structured", "prompt": prompt, "schema": schema, **kwargs})
        if self._structured_fn is not None:
            return self._structured_fn(prompt, schema, **kwargs)
        if schema in self._structured_responses:
            return self._structured_responses[schema]
        raise KeyError(f"FakeLLMClient has no canned response configured for schema {schema.__name__}")

    async def generate_text(self, prompt: str, **kwargs) -> str:
        self.calls.append({"method": "generate_text", "prompt": prompt, **kwargs})
        if self._text_fn is not None:
            return self._text_fn(prompt, **kwargs)
        return self._text

    async def health(self) -> dict:
        return {"openai": {"total": 0, "usable": 0}, "groq": {"total": 0, "usable": 0}}
