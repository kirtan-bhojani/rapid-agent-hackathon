import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import process_resume

profile = process_resume(
    "uploads/sample_resume.pdf",
    "kirtan_test"
)

print(profile)