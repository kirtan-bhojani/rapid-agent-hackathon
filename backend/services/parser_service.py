from pypdf import PdfReader
from services.gemini_service import client
import json
from database import save_user_profile


def extract_pdf_text(pdf_path):

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += page_text + "\n"

    return text


def parse_resume_text(text):

    prompt = f"""
You are a resume parser.

Extract information from the resume.

Return ONLY valid JSON.

Format:

{{
    "name": "",
    "email": "",
    "phone": "",
    "education": [],
    "skills": [],
    "experience": []
}}

Rules:

- Return only JSON.
- Do not use markdown.
- Do not add explanations.
- If a field is missing, use an empty string or empty list.
- Extract as much information as possible.

Resume:

{text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    return response.text


def parse_resume(pdf_path):

    text = extract_pdf_text(pdf_path)

    result = parse_resume_text(text)

    try:

        cleaned_result = result.strip()

        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result.replace("```json", "")
            cleaned_result = cleaned_result.replace("```", "")
            cleaned_result = cleaned_result.strip()

        return json.loads(cleaned_result)

    except Exception as e:

        return {
            "error": str(e),
            "raw": result
        }
SENSITIVE_FIELDS = {
    "email",
    "phone",
    "address",
    "passport",
    "date_of_birth"
}


def split_profile_data(profile):

    public_data = {}
    sensitive_data = {}

    for key in profile:

        if key in SENSITIVE_FIELDS:

            sensitive_data[key] = profile[key]

        else:

            public_data[key] = profile[key]

    return public_data, sensitive_data
def process_resume(
    pdf_path,
    user_id
):

    profile = parse_resume(
        pdf_path
    )

    public_data, sensitive_data = split_profile_data(
        profile
    )

    save_user_profile(
        user_id,
        public_data,
        sensitive_data
    )

    return profile