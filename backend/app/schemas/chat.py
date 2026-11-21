from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=50)
    provider: str | None = None
    model: str | None = None


class ModelSelect(BaseModel):
    provider: str
    model: str | None = None
