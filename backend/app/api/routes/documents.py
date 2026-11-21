import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_user_id
from app.core.config import get_settings
from app.core.security import RateLimiter, safe_filename
from app.database.models import new_id, utcnow
from app.database.mongodb import get_db
from app.schemas.document import DocumentOut
from app.services.ingestion import process_document
from app.services.pdf_processor import is_pdf_header
from app.services.vector_store import get_store

router = APIRouter(prefix="/documents", tags=["documents"])
upload_limiter = RateLimiter(20, 60)


def _get_or_404(doc_id: str, user_id: str) -> dict:
    doc = get_db().get("documents", doc_id, user_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
    _: None = Depends(upload_limiter),
):
    s = get_settings()
    name = safe_filename(file.filename or "")
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are supported.")
    doc_id = new_id("doc_")
    os.makedirs(s.upload_dir, exist_ok=True)
    path = os.path.join(s.upload_dir, f"{doc_id}.pdf")  # never use the client's filename on disk
    limit = s.max_upload_size_mb * 1024 * 1024
    size = 0
    try:
        with open(path, "wb") as out:
            first = True
            while chunk := await file.read(1024 * 1024):
                if first:
                    if not is_pdf_header(chunk):
                        raise HTTPException(400, "The file is not a valid PDF.")
                    first = False
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"File too large (limit {s.max_upload_size_mb} MB).")
                out.write(chunk)
            if size == 0:
                raise HTTPException(400, "The file is empty.")
    except HTTPException:
        if os.path.exists(path):
            os.remove(path)
        raise
    doc = get_db().insert(
        "documents",
        {
            "id": doc_id,
            "user_id": user_id,
            "filename": name,
            "file_size": size,
            "file_type": "application/pdf",
            "status": "processing",
            "error": None,
            "storage_path": path,
            "created_at": utcnow(),
        },
    )
    background.add_task(process_document, doc_id)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(user_id: str = Depends(get_user_id)):
    return get_db().find("documents", user_id=user_id)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, user_id: str = Depends(get_user_id)):
    return _get_or_404(doc_id, user_id)


@router.delete("/{doc_id}")
def delete_document(doc_id: str, user_id: str = Depends(get_user_id)):
    doc = _get_or_404(doc_id, user_id)
    get_store().delete_source(doc_id)
    if os.path.exists(doc["storage_path"]):
        os.remove(doc["storage_path"])
    get_db().delete("documents", doc_id)
    return {"success": True}


@router.post("/{doc_id}/reprocess", response_model=DocumentOut, status_code=202)
def reprocess_document(doc_id: str, background: BackgroundTasks, user_id: str = Depends(get_user_id)):
    _get_or_404(doc_id, user_id)
    doc = get_db().update("documents", doc_id, {"status": "processing", "error": None})
    background.add_task(process_document, doc_id)
    return doc
