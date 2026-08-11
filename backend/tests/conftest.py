"""
conftest.py — shared fixtures for the new pytest suite.

These tests exercise agent business logic against FakeLLMClient and a fake
MCP session — no real Gemini/Groq/MongoDB calls, per the project's policy
of reserving real API calls for final verification, not routine test runs.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeMCPResult:
    def __init__(self, content):
        self.content = content


def _docs_to_result(docs):
    """Wrap a list of dicts the way the MCP server's text-content response
    shape looks, so parse_mcp_docs() can scrape it back out."""
    return _FakeMCPResult(content=[_FakeTextBlock(json.dumps(docs))])


class FakeMCPSession:
    """Configurable fake for mcp_client.session. `find_docs` is returned for
    every `find` call (tests needing per-call variation can swap it mid-test);
    insert-many / update-many calls are recorded in `inserted` / `updated`."""

    def __init__(self, find_docs=None):
        self.find_docs = find_docs or []
        self.inserted = []
        self.updated = []

    async def call_tool(self, name, arguments):
        if name == "find":
            return _docs_to_result(self.find_docs)
        if name == "insert-many":
            self.inserted.append(arguments)
            return _FakeMCPResult(content=[])
        if name == "update-many":
            self.updated.append(arguments)
            return _FakeMCPResult(content=[])
        return _FakeMCPResult(content=[])


class FakeMCPClient:
    def __init__(self, find_docs=None):
        self.session = FakeMCPSession(find_docs=find_docs)


@pytest.fixture
def fake_mcp_client():
    return FakeMCPClient()
