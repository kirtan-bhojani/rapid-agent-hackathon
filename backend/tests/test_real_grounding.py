import asyncio

from services.llm_client import LLMClient
from google.genai import types


async def main():
    llm = LLMClient()
    text = await llm.generate_text(
        """
Find machine learning scholarships in Germany
that are currently open.

Return:
- scholarship name
- deadline
- source URL
""",
        gemini_tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
