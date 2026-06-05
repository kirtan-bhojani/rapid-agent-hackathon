import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import parse_resume

result = parse_resume(
    "uploads/sample_resume.pdf"
)

print(result)