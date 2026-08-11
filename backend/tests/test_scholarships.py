import asyncio

from services.llm_client import LLMClient
from tools.search_tool import search_scholarships


async def main():
    llm = LLMClient()
    result = await search_scholarships("Machine Learning scholarships Germany currently open", llm)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
