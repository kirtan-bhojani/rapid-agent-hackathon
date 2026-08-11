"""
mcp_helpers.py — shared helpers for reading MongoDB MCP tool-call results.

The MCP `find` tool returns its result as a text-content block rather than a
native JSON payload, so every caller needs to scrape the JSON out of it. This
was previously copy-pasted (nearly identically) across goal_analysis_agent.py,
gap_analysis_agent.py, career_pipeline.py, progress_agent.py, routes/career.py,
routes/dashboard.py, and routes/opportunities.py — this module is the single
shared implementation.
"""

from __future__ import annotations

import json
from typing import Any, Optional


async def parse_mcp_docs(result: Any) -> list[dict]:
    """Extract a list of documents from an MCP tool-call result's text content
    by scraping the first/last JSON bracket pair out of each text block."""
    docs: list[dict] = []
    for c in result.content:
        if c.type == "text":
            text = c.text.strip()
            start = next((i for i, ch in enumerate(text) if ch in "[{"), -1)
            end = next((i for i in range(len(text) - 1, -1, -1) if text[i] in "]}"), -1)
            if start != -1 and end != -1 and start < end:
                try:
                    parsed = json.loads(text[start : end + 1])
                    if isinstance(parsed, list):
                        docs.extend(parsed)
                    elif isinstance(parsed, dict):
                        docs.append(parsed)
                except Exception:
                    pass
    return docs


async def find_latest(
    mcp_client: Any,
    database: str,
    collection: str,
    filter: dict,
    sort_key: str = "created_at",
) -> Optional[dict]:
    """Common pattern: find() -> parse_mcp_docs() -> sort by sort_key desc ->
    return the newest doc, or None if nothing matched (or on any error)."""
    try:
        result = await mcp_client.session.call_tool("find", arguments={
            "database": database,
            "collection": collection,
            "filter": filter,
        })
        docs = await parse_mcp_docs(result)
        if docs:
            docs.sort(key=lambda x: x.get(sort_key, ""), reverse=True)
            return docs[0]
    except Exception as e:
        print(f"[mcp_helpers] find_latest error ({database}.{collection}): {e}")
    return None
