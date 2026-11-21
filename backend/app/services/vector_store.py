import threading

from app.core.config import get_settings
from app.services.embedding_service import collection_name


class VectorStoreError(Exception):
    pass


def _clean(p: dict) -> dict:
    return {k: v for k, v in p.items() if v is not None}


class ChromaStore:
    def __init__(self):
        try:
            import chromadb
        except ImportError:
            raise VectorStoreError("chromadb is not installed. Use: pip install -r requirements-local.txt")
        self.client = chromadb.PersistentClient(path=get_settings().chroma_persist_directory)

    def _col(self):
        return self.client.get_or_create_collection(
            collection_name(), metadata={"hnsw:space": "cosine"}
        )

    def add(self, ids, vectors, payloads):
        payloads = [_clean(p) for p in payloads]
        self._col().add(
            ids=ids,
            embeddings=vectors,
            documents=[p["content"] for p in payloads],
            metadatas=[{k: v for k, v in p.items() if k != "content"} for p in payloads],
        )

    def search(self, vector, top_k, user_id, source_ids):
        col = self._col()
        count = col.count()
        if count == 0:
            return []
        conds = [{"user_id": {"$eq": user_id}}]
        if source_ids:
            conds.append({"source_id": {"$in": list(source_ids)}})
        where = conds[0] if len(conds) == 1 else {"$and": conds}
        res = col.query(
            query_embeddings=[vector],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {**meta, "content": doc, "score": round(1 - dist, 4)}
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]

    def delete_source(self, source_id):
        self._col().delete(where={"source_id": {"$eq": source_id}})


class QdrantStore:
    def __init__(self):
        s = get_settings()
        if not s.qdrant_url:
            raise VectorStoreError("QDRANT_URL is not set.")
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise VectorStoreError("qdrant-client is not installed.")
        self.client = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None, timeout=30)
        self._ready: set[str] = set()

    def _ensure(self, dim: int) -> str:
        from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

        name = collection_name()
        if name in self._ready:
            return name
        if not self.client.collection_exists(name):
            self.client.create_collection(
                name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )
        for field in ("user_id", "source_id"):
            try:
                self.client.create_payload_index(name, field_name=field, field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass  # already exists
        self._ready.add(name)
        return name

    def add(self, ids, vectors, payloads):
        from qdrant_client.models import PointStruct

        try:
            name = self._ensure(len(vectors[0]))
            self.client.upsert(
                name,
                points=[PointStruct(id=i, vector=v, payload=_clean(p)) for i, v, p in zip(ids, vectors, payloads)],
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant error: {e}")

    def _filter(self, user_id=None, source_ids=None):
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        must = []
        if user_id:
            must.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
        if source_ids:
            must.append(FieldCondition(key="source_id", match=MatchAny(any=list(source_ids))))
        return Filter(must=must)

    def search(self, vector, top_k, user_id, source_ids):
        try:
            name = collection_name()
            if not self.client.collection_exists(name):
                return []
            res = self.client.query_points(
                collection_name=name,
                query=vector,
                limit=top_k,
                query_filter=self._filter(user_id, source_ids),
                with_payload=True,
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant error: {e}")
        return [{**(p.payload or {}), "score": round(p.score, 4)} for p in res.points]

    def delete_source(self, source_id):
        from qdrant_client.models import FilterSelector

        try:
            name = collection_name()
            if self.client.collection_exists(name):
                self.client.delete(name, points_selector=FilterSelector(filter=self._filter(source_ids=[source_id])))
        except Exception as e:
            raise VectorStoreError(f"Qdrant error: {e}")


_store = None
_lock = threading.Lock()


def get_store():
    global _store
    with _lock:
        if _store is None:
            kind = get_settings().vector_db.lower()
            if kind == "chroma":
                _store = ChromaStore()
            elif kind == "qdrant":
                _store = QdrantStore()
            else:
                raise VectorStoreError(f"Unsupported VECTOR_DB '{kind}'.")
        return _store
