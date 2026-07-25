import os, sys
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
for m in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.5-flash-lite']:
    try:
        r = client.models.generate_content(model=m, contents='say hi')
        print(f'{m}: SUCCESS')
    except Exception as e:
        print(f'{m}: ERROR {e}')
