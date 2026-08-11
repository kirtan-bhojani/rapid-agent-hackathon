"""
config.py — single source of truth for environment configuration.

Replaces the scattered per-file `load_dotenv()` + `os.getenv(...)` calls that
used to live in database.py, mcp_service.py, and every agent service file.
Import `settings` from here instead of reading env vars directly.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def _split_keys(env_name: str) -> list[str]:
    raw = os.getenv(env_name, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


class Settings:
    # ── LLM providers ────────────────────────────────────────────────────
    OPENAI_API_KEYS: list[str] = _split_keys("OPENAI_API_KEYS")
    GROQ_API_KEYS: list[str] = _split_keys("GROQ_API_KEYS")

    OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL_DEFAULT", "gpt-5.6-terra")
    GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL_DEFAULT", "llama-3.3-70b-versatile")
    GROQ_MODEL_REASONING = os.getenv("GROQ_MODEL_REASONING", "qwen/qwen3-32b")

    LLM_KEY_COOLDOWN_SECONDS = float(os.getenv("LLM_KEY_COOLDOWN_SECONDS", "30"))
    LLM_MAX_REPAIR_RETRIES = int(os.getenv("LLM_MAX_REPAIR_RETRIES", "1"))

    # ── MongoDB ──────────────────────────────────────────────────────────
    MONGO_URI = os.getenv("MONGO_URI")
    MDB_MCP_CONNECTION_STRING = os.getenv("MDB_MCP_CONNECTION_STRING") or MONGO_URI


settings = Settings()
