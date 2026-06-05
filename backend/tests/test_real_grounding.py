from google.genai import types
from services.gemini_service import client

response = client.models.generate_content(
    model="gemini-2.5-flash",

    contents="""
Find machine learning scholarships in Germany
that are currently open.

Return:
- scholarship name
- deadline
- source URL
""",

    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ]
    )
)

print(response)