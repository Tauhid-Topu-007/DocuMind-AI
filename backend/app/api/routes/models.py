from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.database.mongodb import get_db
from app.schemas.chat import ModelSelect
from app.services import llm_service

router = APIRouter(tags=["models"])


def health_payload() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "env": s.app_env,
        "ai_provider": s.ai_provider,
        "embedding_provider": s.embedding_provider,
        "vector_db": s.vector_db,
        "database": get_db().kind,
    }


@router.get("/health")
def health():
    return health_payload()


@router.get("/models")
def list_models():
    s = get_settings()
    ok, ollama_models = llm_service.list_ollama_models()
    chat_models = [m for m in ollama_models if "embed" not in m.lower()]
    groq_models = llm_service.list_groq_models()
    return {
        "ollama": {"available": ok, "models": chat_models, "default": s.ollama_chat_model},
        "groq": {"configured": bool(s.groq_api_key), "models": groq_models, "default": s.groq_model},
        "selected": llm_service.runtime,
        "default_provider": s.ai_provider,
    }


@router.get("/models/providers")
def providers():
    s = get_settings()
    ok, _ = llm_service.list_ollama_models()
    return [
        {"id": "ollama", "name": "Ollama (local)", "available": ok, "default_model": s.ollama_chat_model},
        {"id": "groq", "name": "Groq (cloud)", "available": bool(s.groq_api_key and s.groq_model), "default_model": s.groq_model},
    ]


@router.post("/models/select")
def select_model(body: ModelSelect):
    if body.provider not in ("ollama", "groq"):
        raise HTTPException(400, "Unsupported provider")
    llm_service.runtime.update({"provider": body.provider, "model": body.model or None})
    return {"success": True, "selected": llm_service.runtime}
