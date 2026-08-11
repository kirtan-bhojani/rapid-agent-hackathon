# test_search.py

import asyncio

from services.llm_client import LLMClient
from tools.search_tool import search_universities


async def main():
    llm = LLMClient()
    results = await search_universities("MS Artificial Intelligence Germany", llm)
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
