import os, sys
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
try:
    r = client.models.generate_content(model='gemini-2.5-flash-lite', contents='what is the weather today?', config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
