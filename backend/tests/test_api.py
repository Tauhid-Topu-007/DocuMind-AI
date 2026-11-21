import json

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from tests.conftest import fake_embed

UID = {"X-User-Id": "user_test_0001"}
OTHER = {"X-User-Id": "user_test_0002"}


def make_pdf(path, pages):
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=11)
    doc.save(str(path))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    pytest.importorskip("chromadb")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("CHROMA_PERSIST_DIRECTORY", str(tmp_path / "chroma"))
    monkeypatch.setenv("JSON_DB_PATH", str(tmp_path / "db.json"))
    monkeypatch.setenv("MONGODB_URI", "")
    monkeypatch.setenv("VECTOR_DB", "chroma")
    from app.core import config

    config.get_settings.cache_clear()
    import app.database.mongodb as mdb
    import app.services.vector_store as vs

    mdb._db = None
    vs._store = None
    from app.services import embedding_service, llm_service

    monkeypatch.setattr(embedding_service, "embed_texts", fake_embed)
    monkeypatch.setattr(embedding_service, "embed_query", lambda t: fake_embed([t])[0])

    async def fake_stream(messages, provider=None, model=None):
        assert "Retrieved context" in messages[0]["content"]
        for tok in ["The capital ", "is Paris ", "[Source 1]."]:
            yield tok

    monkeypatch.setattr(llm_service, "stream_chat", fake_stream)
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_requires_user_header(client):
    assert client.get("/api/v1/documents").status_code == 400
    assert client.get("/health").json() == {"status": "ok"}


def test_pdf_flow_and_isolation(client, tmp_path):
    pdf = tmp_path / "geo.pdf"
    make_pdf(pdf, ["Introduction to geography.", "The capital of France is Paris. Paris is on the Seine."])
    with open(pdf, "rb") as f:
        r = client.post("/api/v1/documents/upload", files={"file": ("geo.pdf", f, "application/pdf")}, headers=UID)
    assert r.status_code == 202, r.text
    doc_id = r.json()["id"]
    doc = client.get(f"/api/v1/documents/{doc_id}", headers=UID).json()
    assert doc["status"] == "processed", doc
    assert doc["page_count"] == 2 and "storage_path" not in doc

    r = client.post("/api/v1/chat", json={"question": "What is the capital of France?", "source_ids": [doc_id]}, headers=UID)
    body = r.json()
    assert r.status_code == 200, r.text
    assert "Paris" in body["answer"]
    top = body["sources"][0]
    assert top["filename"] == "geo.pdf" and top["page_number"] == 2

    # stream endpoint
    r = client.post("/api/v1/chat/stream", json={"question": "capital of France", "conversation_id": body["conversation_id"]}, headers=UID)
    assert "event: token" in r.text and "event: done" in r.text

    conv = client.get(f"/api/v1/conversations/{body['conversation_id']}", headers=UID).json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]

    # another user sees nothing and cannot read this document or conversation
    assert client.get("/api/v1/documents", headers=OTHER).json() == []
    assert client.get(f"/api/v1/documents/{doc_id}", headers=OTHER).status_code == 404
    r = client.post("/api/v1/chat", json={"question": "capital of France"}, headers=OTHER)
    assert r.json()["sources"] == []
    assert client.get(f"/api/v1/conversations/{body['conversation_id']}", headers=OTHER).status_code == 404

    assert client.delete(f"/api/v1/documents/{doc_id}", headers=UID).status_code == 200
    r = client.post("/api/v1/chat", json={"question": "capital of France"}, headers=UID)
    assert r.json()["sources"] == []
    assert client.delete(f"/api/v1/conversations/{body['conversation_id']}", headers=UID).status_code == 200


def test_upload_validation(client, tmp_path):
    r = client.post("/api/v1/documents/upload", files={"file": ("a.txt", b"hello", "text/plain")}, headers=UID)
    assert r.status_code == 400
    r = client.post("/api/v1/documents/upload", files={"file": ("a.pdf", b"not really a pdf", "application/pdf")}, headers=UID)
    assert r.status_code == 400


def test_website_ssrf_rejected(client):
    for url in ["http://127.0.0.1:8000", "http://169.254.169.254/", "ftp://x.com"]:
        r = client.post("/api/v1/websites/ingest", json={"url": url}, headers=UID)
        assert r.status_code == 400, url
