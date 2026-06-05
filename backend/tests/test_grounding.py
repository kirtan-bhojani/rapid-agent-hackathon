from services.gemini_service import client

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="""
Find machine learning scholarships in Germany announced recently.

Include:
- scholarship name
- source URL
- application deadline

Use web search if available.
"""
)

print(response.text)