import sys
import os
import asyncio

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import process_resume
from services.llm_client import LLMClient


async def main():
    llm = LLMClient()
    profile = await process_resume("uploads/sample_resume.pdf", "kirtan_test", llm)
    print(profile)


if __name__ == "__main__":
    asyncio.run(main())
