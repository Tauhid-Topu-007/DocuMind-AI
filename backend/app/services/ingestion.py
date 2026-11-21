import logging
import os
import uuid

from app.core.config import get_settings
from app.database.mongodb import get_db
from app.services import embedding_service, web_scraper
from app.services.pdf_processor import PDFError, extract_pages
from app.services.text_splitter import split_text
from app.services.vector_store import VectorStoreError, get_store

log = logging.getLogger(__name__)
BATCH = 32
KNOWN_ERRORS = (PDFError, web_scraper.ScrapeError, embedding_service.EmbeddingError, VectorStoreError)


def index_chunks(user_id: str, source_id: str, source_type: str, chunks: list[dict], base: dict) -> None:
    store = get_store()
    store.delete_source(source_id)  # makes reprocessing idempotent
    for i in range(0, len(chunks), BATCH):
        part = chunks[i : i + BATCH]
        vectors = embedding_service.embed_texts([c["content"] for c in part])
        payloads = [
            {**base, **c, "user_id": user_id, "source_id": source_id, "source_type": source_type}
            for c in part
        ]
        store.add([str(uuid.uuid4()) for _ in part], vectors, payloads)


def _fail(col: str, source_id: str, e: Exception) -> None:
    if isinstance(e, KNOWN_ERRORS):
        msg = str(e)
    else:
        log.exception("Processing failed for %s", source_id)
        msg = "Processing failed. Check the server logs."
    try:
        get_store().delete_source(source_id)
    except Exception:
        pass
    get_db().update(col, source_id, {"status": "failed", "error": msg[:400]})


def process_document(doc_id: str) -> None:
    db, s = get_db(), get_settings()
    doc = db.get("documents", doc_id)
    if not doc:
        return
    try:
        if not os.path.exists(doc["storage_path"]):
            raise PDFError("The original file is no longer on the server. Please upload it again.")
        pages, total = extract_pages(doc["storage_path"])
        chunks: list[dict] = []
        for page_no, text in pages:
            for piece in split_text(text, s.chunk_size, s.chunk_overlap):
                chunks.append({"content": piece, "page_number": page_no, "chunk_index": len(chunks)})
        index_chunks(doc["user_id"], doc_id, "pdf", chunks, {"filename": doc["filename"]})
        db.update(
            "documents",
            doc_id,
            {
                "status": "processed",
                "error": None,
                "page_count": total,
                "chunk_count": len(chunks),
                "vector_collection": embedding_service.collection_name(),
            },
        )
    except Exception as e:
        _fail("documents", doc_id, e)


def process_website(site_id: str) -> None:
    db, s = get_db(), get_settings()
    site = db.get("websites", site_id)
    if not site:
        return
    try:
        page = web_scraper.scrape(site["url"])
        chunks = [
            {"content": p, "chunk_index": i}
            for i, p in enumerate(split_text(page["text"], s.chunk_size, s.chunk_overlap))
        ]
        index_chunks(site["user_id"], site_id, "website", chunks, {"url": page["url"], "title": page["title"]})
        db.update(
            "websites",
            site_id,
            {
                "status": "processed",
                "error": None,
                "title": page["title"],
                "chunk_count": len(chunks),
                "vector_collection": embedding_service.collection_name(),
            },
        )
    except Exception as e:
        _fail("websites", site_id, e)
