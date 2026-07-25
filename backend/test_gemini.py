import os, json
from google import genai
from google.genai import types
from pydantic import BaseModel
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
class Out(BaseModel):
    x: str
try:
    response = client.models.generate_content(model='gemini-2.5-flash-lite', contents='say hi', config=types.GenerateContentConfig(response_mime_type='application/json', response_schema=Out))
    print(response.text)
except Exception as e:
    print(f'ERROR: {e}')
