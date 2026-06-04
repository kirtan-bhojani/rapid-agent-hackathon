from services.gemini_service import client
from google.genai import types
import json


def _search(query):

    prompt = f"""
Search the web for:

{query}

Return ONLY valid JSON.

Format:

[
  {{
    "name": "",
    "description": "",
    "deadline": "",
    "link": ""
  }}
]

Rules:

- Use current web information.
- Prefer official sources.
- Do not invent deadlines.
- If a deadline is unavailable, use "Unknown".
- If a link is unavailable, use "Unknown".
- Return only JSON.
- Do not wrap the JSON in markdown.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )
    )

    try:

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)

    except Exception as e:

        return {
            "error": str(e),
            "raw": response.text
        }


def search_scholarships(query):

    return _search(query)


def search_universities(query):

    return _search(query)


def search_jobs(query):

    return _search(query)


def search_internships(query):

    return _search(query)