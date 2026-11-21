import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_user_id
from app.core.config import get_settings
from app.core.security import RateLimiter
from app.database.models import new_id, utcnow
from app.database.mongodb import get_db
from app.schemas.chat import ChatRequest
from app.services import llm_service, rag_service
from app.services.embedding_service import EmbeddingError
from app.services.llm_service import LLMError
from app.services.vector_store import VectorStoreError

router = APIRouter(tags=["chat"])
chat_limiter = RateLimiter(30, 60)


async def _prepare(req: ChatRequest, user_id: str) -> dict:
    s, db = get_settings(), get_db()
    question = req.question.strip()
    if not question:
        raise HTTPException(422, "Question is empty.")
    try:
        provider, model = llm_service.resolve(req.provider, req.model)
    except LLMError as e:
        raise HTTPException(400, str(e))

    conv = None
    history: list[dict] = []
    if req.conversation_id:
        conv = await run_in_threadpool(db.get, "conversations", req.conversation_id, user_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        rows = await run_in_threadpool(
            lambda: db.find("messages", sort_key="created_at", desc=False, conversation_id=conv["id"])
        )
        history = [{"role": m["role"], "content": m["content"]} for m in rows][-s.history_messages :]

    try:
        hits = await run_in_threadpool(rag_service.retrieve, question, user_id, req.source_ids, s.top_k)
    except (EmbeddingError, VectorStoreError) as e:
        raise HTTPException(502, str(e))

    now = utcnow()
    if not conv:
        conv = await run_in_threadpool(
            db.insert,
            "conversations",
            {"id": new_id("conv_"), "user_id": user_id, "title": question[:60], "created_at": now, "updated_at": now},
        )
    await run_in_threadpool(
        db.insert,
        "messages",
        {
            "id": new_id("msg_"),
            "conversation_id": conv["id"],
            "user_id": user_id,
            "role": "user",
            "content": question,
            "sources": [],
            "created_at": now,
        },
    )
    return {
        "conv_id": conv["id"],
        "hits": hits,
        "sources": rag_service.sources_from_hits(hits),
        "messages": rag_service.build_messages(question, hits, history) if hits else None,
        "provider": provider,
        "model": model,
    }


def _save_answer(conv_id: str, user_id: str, answer: str, sources: list, model: str) -> None:
    db = get_db()
    now = utcnow()
    db.insert(
        "messages",
        {
            "id": new_id("msg_"),
            "conversation_id": conv_id,
            "user_id": user_id,
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "model": model,
            "created_at": now,
        },
    )
    db.update("conversations", conv_id, {"updated_at": now})


@router.post("/chat")
async def chat(req: ChatRequest, user_id: str = Depends(get_user_id), _: None = Depends(chat_limiter)):
    p = await _prepare(req, user_id)
    if p["messages"] is None:
        answer = rag_service.NO_CONTEXT_MESSAGE
    else:
        try:
            answer = "".join([t async for t in llm_service.stream_chat(p["messages"], p["provider"], p["model"])])
        except LLMError as e:
            raise HTTPException(502, str(e))
    await run_in_threadpool(_save_answer, p["conv_id"], user_id, answer, p["sources"], p["model"])
    return {
        "success": True,
        "answer": answer,
        "conversation_id": p["conv_id"],
        "provider": p["provider"],
        "model": p["model"],
        "sources": p["sources"],
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, user_id: str = Depends(get_user_id), _: None = Depends(chat_limiter)):
    p = await _prepare(req, user_id)

    async def gen():
        yield _sse("meta", {"conversation_id": p["conv_id"], "provider": p["provider"], "model": p["model"]})
        yield _sse("sources", {"sources": p["sources"]})
        parts: list[str] = []
        if p["messages"] is None:
            parts.append(rag_service.NO_CONTEXT_MESSAGE)
            yield _sse("token", {"text": parts[0]})
        else:
            try:
                async for tok in llm_service.stream_chat(p["messages"], p["provider"], p["model"]):
                    parts.append(tok)
                    yield _sse("token", {"text": tok})
            except LLMError as e:
                yield _sse("error", {"message": str(e)})
                return
            except asyncio.CancelledError:
                raise
        await run_in_threadpool(_save_answer, p["conv_id"], user_id, "".join(parts), p["sources"], p["model"])
        yield _sse("done", {"conversation_id": p["conv_id"]})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
def list_conversations(user_id: str = Depends(get_user_id)):
    return get_db().find("conversations", sort_key="updated_at", user_id=user_id)


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: str, user_id: str = Depends(get_user_id)):
    db = get_db()
    conv = db.get("conversations", conv_id, user_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    msgs = db.find("messages", sort_key="created_at", desc=False, conversation_id=conv_id)
    return {**conv, "messages": msgs}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str, user_id: str = Depends(get_user_id)):
    db = get_db()
    if not db.get("conversations", conv_id, user_id):
        raise HTTPException(404, "Conversation not found")
    db.delete_where("messages", conversation_id=conv_id)
    db.delete("conversations", conv_id)
    return {"success": True}
