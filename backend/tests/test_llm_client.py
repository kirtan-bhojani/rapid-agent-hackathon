"""
Unit tests for services/llm_client.py — KeyPool rotation/cooldown, and the
OpenAI→Groq fallback / exhaustion orchestration logic (grounded web search
has no fallback, OpenAI-only). No real API calls: the OpenAI/Groq call
methods are monkeypatched at the instance level so the fallback logic itself
is exercised deterministically.
"""

import pytest
from pydantic import BaseModel

from services.llm_client import LLMClient, KeyPool, LLMAllProvidersExhaustedError


class DummySchema(BaseModel):
    value: str


# ── KeyPool ──────────────────────────────────────────────────────────────

async def test_keypool_round_robins():
    pool = KeyPool(["a", "b", "c"], cooldown_seconds=30)
    seen = [await pool.acquire() for _ in range(4)]
    assert seen == ["a", "b", "c", "a"]


async def test_keypool_skips_cooling_down_keys():
    pool = KeyPool(["a", "b"], cooldown_seconds=100)
    key = await pool.acquire()
    pool.mark_cooldown(key, 100)
    remaining = [await pool.acquire() for _ in range(3)]
    assert key not in remaining


async def test_keypool_returns_none_when_all_cooling_down():
    pool = KeyPool(["a", "b"], cooldown_seconds=100)
    pool.mark_cooldown("a", 100)
    pool.mark_cooldown("b", 100)
    assert await pool.acquire() is None


async def test_keypool_empty_returns_none():
    pool = KeyPool([], cooldown_seconds=30)
    assert await pool.acquire() is None


# ── LLMClient fallback orchestration ────────────────────────────────────

def _client_with_pools(openai_keys, groq_keys):
    from config import Settings
    s = Settings()
    s.OPENAI_API_KEYS = openai_keys
    s.GROQ_API_KEYS = groq_keys
    return LLMClient(settings_obj=s)


async def test_generate_structured_uses_openai_when_available(monkeypatch):
    llm = _client_with_pools(["o1"], ["q1"])
    expected = DummySchema(value="from-openai")

    async def fake_openai(*a, **kw):
        return expected

    async def fake_groq(*a, **kw):
        raise AssertionError("Groq should not be called when OpenAI succeeds")

    monkeypatch.setattr(llm, "_try_openai_structured", fake_openai)
    monkeypatch.setattr(llm, "_try_groq_structured", fake_groq)

    result = await llm.generate_structured("prompt", DummySchema)
    assert result is expected


async def test_generate_structured_falls_back_to_groq_when_openai_exhausted(monkeypatch):
    llm = _client_with_pools(["o1"], ["q1"])
    expected = DummySchema(value="from-groq")

    async def fake_openai(*a, **kw):
        return None  # simulates every OpenAI key exhausted/failed

    async def fake_groq(*a, **kw):
        return expected

    monkeypatch.setattr(llm, "_try_openai_structured", fake_openai)
    monkeypatch.setattr(llm, "_try_groq_structured", fake_groq)

    result = await llm.generate_structured("prompt", DummySchema)
    assert result is expected


async def test_generate_structured_raises_when_both_providers_exhausted(monkeypatch):
    llm = _client_with_pools(["o1"], ["q1"])

    async def fake_none(*a, **kw):
        return None

    monkeypatch.setattr(llm, "_try_openai_structured", fake_none)
    monkeypatch.setattr(llm, "_try_groq_structured", fake_none)

    with pytest.raises(LLMAllProvidersExhaustedError):
        await llm.generate_structured("prompt", DummySchema)


async def test_grounded_text_never_falls_back_to_groq(monkeypatch):
    """Search grounding (web_search=True) has no Groq equivalent — must raise
    rather than silently degrade to an ungrounded answer."""
    llm = _client_with_pools(["o1"], ["q1"])

    async def fake_openai_grounded_text(*a, **kw):
        return None  # OpenAI exhausted

    async def fake_openai_text(*a, **kw):
        raise AssertionError("Ungrounded OpenAI path must never be used for a grounded call")

    async def fake_groq_text(*a, **kw):
        raise AssertionError("Groq must never be used for a grounded call")

    monkeypatch.setattr(llm, "_try_openai_grounded_text", fake_openai_grounded_text)
    monkeypatch.setattr(llm, "_try_openai_text", fake_openai_text)
    monkeypatch.setattr(llm, "_try_groq_text", fake_groq_text)

    with pytest.raises(LLMAllProvidersExhaustedError):
        await llm.generate_text("prompt", web_search=True)


async def test_ungrounded_text_falls_back_to_groq(monkeypatch):
    llm = _client_with_pools(["o1"], ["q1"])

    async def fake_openai_text(*a, **kw):
        return None

    async def fake_groq_text(*a, **kw):
        return "groq answer"

    monkeypatch.setattr(llm, "_try_openai_text", fake_openai_text)
    monkeypatch.setattr(llm, "_try_groq_text", fake_groq_text)

    result = await llm.generate_text("prompt")
    assert result == "groq answer"
