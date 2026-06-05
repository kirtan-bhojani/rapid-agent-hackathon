import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import extract_pdf_text
text = extract_pdf_text(
    "uploads/sample_resume.pdf"
)

print(text)