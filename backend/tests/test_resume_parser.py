import sys
import os
import asyncio

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import parse_resume
from services.llm_client import LLMClient


async def main():
    llm = LLMClient()
    result = await parse_resume("uploads/sample_resume.pdf", llm)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
