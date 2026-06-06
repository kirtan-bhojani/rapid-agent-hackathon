"""
Test script for the orchestrator.

Runs three representative queries through ``handle_request`` and prints
the structured results:

    1. "What time is it?"           → time tool
    2. "Add 5 and 10"              → calculator tool
    3. "Find scholarships …"       → search_scholarships tool

Usage:
    cd backend
    python -m pytest tests/test_orchestrator.py -v -s
        — or —
    python tests/test_orchestrator.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# Ensure the backend directory is on sys.path so tool imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.orchestrator import handle_request


# ── Test cases ───────────────────────────────────────────────────────

TEST_QUERIES = [
    "What time is it?",
    "Add 5 and 10",
    "Find scholarships for Indian students in Germany",
]


async def run_tests() -> None:
    """Execute each test query and pretty-print the result."""

    print("=" * 60)
    print("  ORCHESTRATOR TEST SUITE")
    print("=" * 60)

    for i, query in enumerate(TEST_QUERIES, start=1):
        print(f"\n{'─' * 60}")
        print(f"  Test {i}: \"{query}\"")
        print(f"{'─' * 60}")

        result = await handle_request(query)

        print(f"\n  Tool used : {result['tool_used']}")
        print(f"  Reason    : {result['reason']}")
        print(f"  Result    : {json.dumps(result['result'], indent=2, default=str)}")

    print(f"\n{'=' * 60}")
    print("  ALL TESTS COMPLETE")
    print(f"{'=' * 60}\n")


# ── Pytest-compatible async tests ────────────────────────────────────

import pytest


@pytest.mark.asyncio
async def test_time_query():
    """The 'time' tool should be selected for time-related queries."""
    result = await handle_request("What time is it?")
    assert result["tool_used"] == "time", f"Expected 'time', got '{result['tool_used']}'"
    assert result["result"] is not None


@pytest.mark.asyncio
async def test_calculator_query():
    """The 'calculator' tool should be selected and return 15."""
    result = await handle_request("Add 5 and 10")
    assert result["tool_used"] == "calculator", f"Expected 'calculator', got '{result['tool_used']}'"
    assert result["result"] == 15, f"Expected 15, got {result['result']}"


@pytest.mark.asyncio
async def test_scholarship_search_query():
    """The 'search_scholarships' tool should be selected for scholarship queries."""
    result = await handle_request("Find scholarships for Indian students in Germany")
    assert result["tool_used"] == "search_scholarships", (
        f"Expected 'search_scholarships', got '{result['tool_used']}'"
    )
    assert result["result"] is not None


# ── CLI runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_tests())
