import json
import logging
from typing import AsyncIterator

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

# Runtime default chosen via POST /models/select (per process; the frontend also sends its own choice per request).
runtime: dict = {"provider": None, "model": None}


class LLMError(Exception):
    def __init__(self, message: str, model_missing: bool = False):
        super().__init__(message)
        self.model_missing = model_missing


def resolve(provider: str | None, model: str | None) -> tuple[str, str]:
    s = get_settings()
    provider = (provider or runtime["provider"] or s.ai_provider).lower()
    if provider not in ("ollama", "groq"):
        raise LLMError(f"Unsupported AI provider '{provider}'.")
    if not model and runtime["provider"] == provider:
        model = runtime["model"]
    model = model or (s.ollama_chat_model if provider == "ollama" else s.groq_model)
    if provider == "groq" and (not s.groq_api_key or not model):
        raise LLMError("Groq is not configured. Set GROQ_API_KEY and GROQ_MODEL on the backend.")
    return provider, model


async def _stream_ollama(messages, model) -> AsyncIterator[str]:
    s = get_settings()
    url = f"{s.ollama_base_url.rstrip('/')}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True, "options": {"temperature": 0.2}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as c:
            async with c.stream("POST", url, json=payload) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode(errors="replace")[:300]
                    if r.status_code == 404:
                        raise LLMError(
                            f"Ollama model '{model}' not found. Run: ollama pull {model}", model_missing=True
                        )
                    raise LLMError(f"Ollama error {r.status_code}: {body}")
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise LLMError(f"Ollama: {data['error']}")
                    tok = (data.get("message") or {}).get("content", "")
                    if tok:
                        yield tok
                    if data.get("done"):
                        break
    except httpx.ConnectError:
        raise LLMError(f"Cannot connect to Ollama at {s.ollama_base_url}. Start it with `ollama serve`.")
    except httpx.HTTPError as e:
        raise LLMError(f"Ollama request failed ({type(e).__name__}).")


async def _stream_groq(messages, model) -> AsyncIterator[str]:
    s = get_settings()
    url = f"{s.groq_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {s.groq_api_key}"}
    payload = {"model": model, "messages": messages, "stream": True, "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as c:
            async with c.stream("POST", url, json=payload, headers=headers) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode(errors="replace")[:300]
                    if r.status_code in (401, 403):
                        raise LLMError("Groq authentication failed. Check GROQ_API_KEY.")
                    raise LLMError(f"Groq error {r.status_code}: {body}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    choices = json.loads(chunk).get("choices") or []
                    if choices:
                        tok = (choices[0].get("delta") or {}).get("content")
                        if tok:
                            yield tok
    except httpx.HTTPError as e:
        raise LLMError(f"Groq request failed ({type(e).__name__}).")


def _dispatch(provider, messages, model):
    return _stream_ollama(messages, model) if provider == "ollama" else _stream_groq(messages, model)


async def stream_chat(messages, provider: str | None = None, model: str | None = None) -> AsyncIterator[str]:
    s = get_settings()
    provider, model = resolve(provider, model)
    started = False
    try:
        async for tok in _dispatch(provider, messages, model):
            started = True
            yield tok
        return
    except LLMError as e:
        if started:
            raise
        err = e
    # Nothing was streamed yet: try the configured fallbacks.
    if provider == "ollama" and err.model_missing and s.ollama_fallback_model and model != s.ollama_fallback_model:
        log.warning("Ollama model missing, retrying with fallback model")
        async for tok in _stream_ollama(messages, s.ollama_fallback_model):
            yield tok
        return
    if s.fallback_enabled:
        other = "groq" if provider == "ollama" else "ollama"
        try:
            op, om = resolve(other, None)
        except LLMError:
            raise err
        log.warning("%s failed, falling back to %s", provider, op)
        async for tok in _dispatch(op, messages, om):
            yield tok
        return
    raise err


def list_ollama_models() -> tuple[bool, list[str]]:
    s = get_settings()
    try:
        r = httpx.get(f"{s.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
        r.raise_for_status()
        return True, sorted(m["name"] for m in r.json().get("models", []))
    except Exception:
        return False, []


def list_groq_models() -> list[str]:
    s = get_settings()
    if not s.groq_api_key:
        return []
    try:
        r = httpx.get(
            f"{s.groq_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {s.groq_api_key}"},
            timeout=5,
        )
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))
    except Exception:
        return []
