import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

print("Testing Gemini Grounding with JSON...")

prompt = "Find 2 real Machine Learning jobs. Return JSON array with title, organization, application_url, description."

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.2,
        ),
    )
    
    print("Response text:")
    print(response.text)
    print("\nGrounding metadata:")
    if hasattr(response.candidates[0], "grounding_metadata") and response.candidates[0].grounding_metadata:
        print("Grounding metadata found!")
    else:
        print("No grounding metadata.")
except Exception as e:
    print(f"Error: {e}")
