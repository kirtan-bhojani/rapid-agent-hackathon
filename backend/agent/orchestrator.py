"""
Orchestrator — scalable tool-routing layer.

Instead of hard-coded if/else chains, every tool is registered in
TOOL_REGISTRY.  A Gemini-powered classifier picks the right tool,
arguments are resolved dynamically, and the tool is executed — all
without touching existing tool modules.

To add a new tool:
    1. Implement it in backend/tools/
    2. Add an entry to TOOL_REGISTRY below.
    That's it.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, Optional
from agent.goal_agent import extract_goal
from google import genai
from dotenv import load_dotenv
import os

# ── Tool imports ─────────────────────────────────────────────────────
from tools.time_tool import get_time
from tools.calculator_tool import add
from tools.search_tool import (
    search_scholarships,
    search_universities,
    search_jobs,
    search_internships,
)

# ── Environment & Gemini client ──────────────────────────────────────
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Logging ──────────────────────────────────────────────────────────
logger = logging.getLogger("orchestrator")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(_handler)

# =====================================================================
#  TOOL REGISTRY
# =====================================================================
# Each entry maps a tool name → its callable, description, and optional
# metadata.  The classifier prompt is built dynamically from this dict,
# so adding a tool here is the *only* step needed to wire it up.
# =====================================================================

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "time": {
        "fn": get_time,
        "description": "Get the current date and time.",
        "args": None,  # takes no arguments
    },
    "calculator": {
        "fn": add,
        "description": "Perform addition of two numbers.",
        "args": ["a", "b"],
    },
    "search_scholarships": {
        "fn": search_scholarships,
        "description": "Search for scholarships on the web.",
        "args": ["query"],
    },
    "search_universities": {
        "fn": search_universities,
        "description": "Search for universities on the web.",
        "args": ["query"],
    },
    "search_jobs": {
        "fn": search_jobs,
        "description": "Search for jobs on the web.",
        "args": ["query"],
    },
    "search_internships": {
        "fn": search_internships,
        "description": "Search for internships on the web.",
        "args": ["query"],
    },
    "goal": {
    "fn": extract_goal,
    "description": "Understand student career or study goals.",
    "args": ["query"]
}
}


# =====================================================================
#  1. INTENT CLASSIFICATION
# =====================================================================

def _classify_intent(user_query: str) -> Dict[str, str]:
    """Use Gemini to select the most appropriate tool from TOOL_REGISTRY.

    Returns ``{"tool": "<name>", "reason": "<why>"}`` parsed from JSON.
    Never hard-codes tool names — the prompt is built from TOOL_REGISTRY.
    """

    # Build the tool list dynamically
    tool_descriptions = "\n".join(
        f"- {name}: {entry['description']}"
        for name, entry in TOOL_REGISTRY.items()
    )

    prompt = f"""\
You are an intelligent intent-classification agent.

Available tools:

{tool_descriptions}
Examples:

"I want to pursue MS in Germany."
→ {{"tool":"goal","reason":"User is expressing a future study goal."}}

"I want to become a Machine Learning Engineer."
→ {{"tool":"goal","reason":"User is expressing a future career goal."}}

"I want to switch from Electronics to Data Science."
→ {{"tool":"goal","reason":"User wants a career transition."}}

"Find scholarships for MS in Canada."
→ {{"tool":"search_scholarships","reason":"User wants scholarship opportunities."}}

"Show software internships in Bangalore."
→ {{"tool":"search_internships","reason":"User wants internship opportunities."}}

"Find universities in Germany."
→ {{"tool":"search_universities","reason":"User wants university information."}}

"What is 5 + 10?"
→ {{"tool":"calculator","reason":"Arithmetic calculation."}}

"What time is it?"
→ {{"tool":"time","reason":"Current time request."}}
User query:
\"{user_query}\"

Choose the single best tool for the query above.
If no tool fits, use tool name "none".

Respond with ONLY valid JSON (no markdown, no explanation):

{{"tool": "<tool_name>", "reason": "<short reason>"}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    raw = response.text.strip()

    # Strip markdown fences if the model wraps its answer
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw)
        raw = re.sub(r"```$", "", raw)
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Classifier returned non-JSON: %s", raw)
        result = {"tool": "none", "reason": "classifier response was not valid JSON"}

    logger.info("Intent classified → tool=%s | reason=%s", result.get("tool"), result.get("reason"))
    return result


# =====================================================================
#  2. ARGUMENT RESOLUTION
# =====================================================================

def _resolve_tool_args(tool_name: str, user_query: str) -> Dict[str, Any]:
    """Extract the arguments required by *tool_name* from *user_query*.

    Strategy per tool type:
      • No args declared     → return empty dict.
      • Args == ["a", "b"]   → extract the first two numbers from the query.
      • Args == ["query"]    → pass the user query through as-is.
      • Otherwise            → pass the raw query under each arg key.
    """

    entry = TOOL_REGISTRY.get(tool_name)
    if entry is None:
        return {}

    declared_args = entry.get("args")

    # Tool takes no arguments (e.g. time)
    if not declared_args:
        return {}

    # Calculator-style: extract numbers
    if set(declared_args) == {"a", "b"}:
        nums = [int(n) for n in re.findall(r"\d+", user_query)]
        if len(nums) >= 2:
            args = {"a": nums[0], "b": nums[1]}
        else:
            args = {"a": nums[0] if nums else 0, "b": 0}
        logger.info("Resolved args for '%s' → %s", tool_name, args)
        return args

    # Search-style: pass query as-is
    if "query" in declared_args:
        args = {"query": user_query}
        logger.info("Resolved args for '%s' → %s", tool_name, args)
        return args

    # Fallback: map every declared arg to the raw query
    args = {arg: user_query for arg in declared_args}
    logger.info("Resolved args for '%s' (fallback) → %s", tool_name, args)
    return args


# =====================================================================
#  3. TOOL EXECUTION
# =====================================================================

def _execute_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """Look up *tool_name* in TOOL_REGISTRY and call it with *args*.

    Raises ``ValueError`` if the tool is unknown.
    """

    entry = TOOL_REGISTRY.get(tool_name)
    if entry is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    fn: Callable = entry["fn"]

    logger.info("Executing tool '%s' with args %s …", tool_name, args)

    try:
        result = fn(**args)
        logger.info("Tool '%s' executed successfully.", tool_name)
        return result
    except Exception as exc:
        logger.error("Tool '%s' raised an error: %s", tool_name, exc)
        raise


# =====================================================================
#  4. PUBLIC ENTRY POINT
# =====================================================================

async def handle_request(user_query: str) -> Dict[str, Any]:
    """Full orchestration pipeline.

    Flow:
        classify intent → resolve arguments → execute tool → return result.

    Returns a structured dict:
        {"tool_used": "…", "reason": "…", "result": …}
    """

    logger.info("─── New request: %s", user_query)

    # Step 1 — classify
    classification = _classify_intent(user_query)
    tool_name = classification.get("tool", "none")
    reason = classification.get("reason", "")

    if tool_name == "none" or tool_name not in TOOL_REGISTRY:
        logger.warning("No suitable tool for query.")
        return {
            "tool_used": "none",
            "reason": reason or "No suitable tool found.",
            "result": None,
        }

    # Step 2 — resolve args
    args = _resolve_tool_args(tool_name, user_query)

    # Step 3 — execute
    try:
        result = _execute_tool(tool_name, args)
    except Exception as exc:
        return {
            "tool_used": tool_name,
            "reason": reason,
            "result": f"Error: {exc}",
        }

    # Step 4 — return structured response
    return {
        "tool_used": tool_name,
        "reason": reason,
        "result": result,
    }
