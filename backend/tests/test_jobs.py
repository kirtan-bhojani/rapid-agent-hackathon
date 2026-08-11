import asyncio

from services.llm_client import LLMClient
from tools.search_tool import search_jobs


async def main():
    llm = LLMClient()
    result = await search_jobs("Machine Learning jobs Germany", llm)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
