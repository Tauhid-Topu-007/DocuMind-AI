from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    error: str | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    vector_collection: str | None = None
    created_at: str
