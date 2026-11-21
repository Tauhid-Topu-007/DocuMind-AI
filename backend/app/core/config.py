from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DocuMind AI"
    app_env: str = "development"
    port: int = 8000

    # LLM
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:latest"
    ollama_fallback_model: str = "llama3.2:3b"
    ollama_embed_model: str = "mxbai-embed-large:latest"
    groq_api_key: str = ""
    groq_model: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    fallback_enabled: bool = False  # try the other provider if the selected one is down

    # Embeddings
    embedding_provider: str = "ollama"  # ollama | fastembed
    fastembed_model: str = "BAAI/bge-small-en-v1.5"

    # Vector DB
    vector_db: str = "chroma"  # chroma | qdrant
    chroma_persist_directory: str = "./storage/chroma"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # Metadata DB (empty MONGODB_URI -> local JSON file, development only)
    mongodb_uri: str = ""
    database_name: str = "documind"
    json_db_path: str = "./storage/db.json"

    # Storage
    upload_dir: str = "./storage/uploads"
    max_upload_size_mb: int = 20

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    history_messages: int = 6

    # Security
    secret_key: str = "replace-with-a-strong-random-secret"  # reserved for future auth
    allowed_origins: str = "http://localhost:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
