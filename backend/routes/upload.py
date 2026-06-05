import os
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_DOCUMENT_TYPES = [
    "resume",
    "transcript",
    "passport",
    "ielts",
    "sop",
    "lor",
]

BASE_UPLOAD_DIR = "uploads"

# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/upload", tags=["Upload"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_upload_dirs() -> None:
    """Create uploads/<doc_type>/ directories if they don't already exist."""
    for doc_type in SUPPORTED_DOCUMENT_TYPES:
        os.makedirs(os.path.join(BASE_UPLOAD_DIR, doc_type), exist_ok=True)


def _validate_pdf(file: UploadFile) -> None:
    """Raise HTTP 400 if the uploaded file is not a PDF."""
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are accepted. Received: '{file.content_type}'.",
        )


def _validate_document_type(document_type: str) -> None:
    """Raise HTTP 400 if document_type is not in SUPPORTED_DOCUMENT_TYPES."""
    if document_type not in SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported document type: '{document_type}'. "
                f"Allowed types: {SUPPORTED_DOCUMENT_TYPES}."
            ),
        )


def _build_filename(document_type: str) -> str:
    """Return a timestamped filename, e.g. '1749123456_resume.pdf'."""
    timestamp = int(time.time())
    return f"{timestamp}_{document_type}.pdf"


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/")
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload"),
    document_type: str = Form(..., description=f"One of: {SUPPORTED_DOCUMENT_TYPES}"),
):
    """
    Upload a PDF document and save it under uploads/<document_type>/.

    - **file**: must be a PDF (application/pdf)
    - **document_type**: one of resume | transcript | passport | ielts | sop | lor
    """

    # 1. Validate inputs
    _validate_pdf(file)
    _validate_document_type(document_type)

    # 2. Ensure directory tree exists
    _ensure_upload_dirs()

    # 3. Build save path
    filename = _build_filename(document_type)
    save_dir = os.path.join(BASE_UPLOAD_DIR, document_type)
    file_path = os.path.join(save_dir, filename)

    # 4. Stream file to disk
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {exc}",
        ) from exc
    finally:
        await file.close()

    # 5. Return structured response
    return {
        "status": "success",
        "file_path": file_path,
        "filename": filename,
        "document_type": document_type,
    }