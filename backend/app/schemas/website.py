from pydantic import BaseModel, Field


class WebsiteIngest(BaseModel):
    url: str = Field(min_length=4, max_length=2000)


class WebsiteOut(BaseModel):
    id: str
    url: str
    title: str
    status: str
    error: str | None = None
    chunk_count: int | None = None
    vector_collection: str | None = None
    created_at: str
