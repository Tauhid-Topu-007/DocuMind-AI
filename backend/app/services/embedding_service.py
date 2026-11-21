import re
import threading

import httpx

from app.core.config import get_settings


class EmbeddingError(Exception):
    pass


def collection_name() -> str:
    """One vector collection per embedding configuration (different models = different vector spaces)."""
    s = get_settings()
    model = s.ollama_embed_model if s.embedding_provider == "ollama" else s.fastembed_model
    slug = re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")
    return f"documind_{s.embedding_provider}_{slug}"[:60]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    provider = get_settings().embedding_provider
    if provider == "ollama":
        return _ollama(texts)
    if provider == "fastembed":
        return _fastembed(texts)
    raise EmbeddingError(f"Unsupported EMBEDDING_PROVIDER '{provider}'.")


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _ollama(texts):
    s = get_settings()
    try:
        r = httpx.post(
            f"{s.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": s.ollama_embed_model, "input": texts},
            timeout=120,
        )
    except httpx.ConnectError:
        raise EmbeddingError(
            f"Cannot connect to Ollama at {s.ollama_base_url}. Start it with `ollama serve`."
        )
    except httpx.HTTPError as e:
        raise EmbeddingError(f"Ollama embedding request failed ({type(e).__name__}).")
    if r.status_code == 404:
        raise EmbeddingError(
            f"Embedding model '{s.ollama_embed_model}' not found. Run: ollama pull {s.ollama_embed_model}"
        )
    if r.status_code != 200:
        raise EmbeddingError(f"Ollama embedding error {r.status_code}: {r.text[:200]}")
    emb = r.json().get("embeddings")
    if not emb or len(emb) != len(texts):
        raise EmbeddingError("Unexpected response from Ollama embeddings API.")
    return emb


_fe_model = None
_fe_lock = threading.Lock()


def _fastembed(texts):
    global _fe_model
    s = get_settings()
    try:
        with _fe_lock:
            if _fe_model is None:
                from fastembed import TextEmbedding

                _fe_model = TextEmbedding(model_name=s.fastembed_model)
            return [v.tolist() for v in _fe_model.embed(texts)]
    except ImportError:
        raise EmbeddingError("fastembed is not installed (pip install fastembed).")
    except Exception as e:
        raise EmbeddingError(f"FastEmbed failed: {e}")
