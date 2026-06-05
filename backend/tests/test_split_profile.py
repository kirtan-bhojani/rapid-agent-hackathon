import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from services.parser_service import (
    parse_resume,
    split_profile_data
)

profile = parse_resume(
    "uploads/sample_resume.pdf"
)

public_data, sensitive_data = split_profile_data(
    profile
)

print("PUBLIC")
print(public_data)

print("\nSENSITIVE")
print(sensitive_data)