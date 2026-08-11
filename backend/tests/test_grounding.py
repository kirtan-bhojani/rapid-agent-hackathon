import asyncio

from services.llm_client import LLMClient
from google.genai import types


async def main():
    llm = LLMClient()
    text = await llm.generate_text(
        """
Find machine learning scholarships in Germany announced recently.

Include:
- scholarship name
- source URL
- application deadline

Use web search if available.
""",
        gemini_tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
