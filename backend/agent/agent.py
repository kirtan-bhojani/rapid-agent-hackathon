from google import genai
from dotenv import load_dotenv

from tools.time_tool import get_time
from tools.calculator_tool import add

import os
import re

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def decide_tool(query):

    prompt = f"""
You are an agent.

Available tools:

1. time
   Use when user asks current time.

2. calculator
   Use when user asks addition.

Return ONLY ONE WORD.

time
calculator
none

User query:
{query}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    return response.text.strip().lower()


def run_agent(query):

    tool = decide_tool(query)

    if tool == "time":
        return get_time()

    if tool == "calculator":

        nums = re.findall(r'\d+', query)

        if len(nums) >= 2:

            return str(
                add(
                    int(nums[0]),
                    int(nums[1])
                )
            )

        return "Need two numbers"

    return "No suitable tool found"