"""Metadata store. MongoDB (Atlas) in production, JSON file for quick local dev."""
import json
import logging
import os
import threading
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger(__name__)


class JsonDB:
    kind = "json"

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.data: dict[str, dict[str, dict]] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text("utf-8"))
            except Exception:
                log.warning("Could not read %s, starting empty", self.path)

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data), "utf-8")
        os.replace(tmp, self.path)

    def insert(self, col, doc):
        with self.lock:
            self.data.setdefault(col, {})[doc["id"]] = dict(doc)
            self._save()
        return doc

    def get(self, col, id, user_id=None):
        with self.lock:
            d = self.data.get(col, {}).get(id)
            if d and (user_id is None or d.get("user_id") == user_id):
                return dict(d)
        return None

    def find(self, col, sort_key="created_at", desc=True, **flt):
        with self.lock:
            rows = [
                dict(d)
                for d in self.data.get(col, {}).values()
                if all(d.get(k) == v for k, v in flt.items())
            ]
        rows.sort(key=lambda r: r.get(sort_key) or "", reverse=desc)
        return rows

    def update(self, col, id, fields):
        with self.lock:
            d = self.data.get(col, {}).get(id)
            if d is None:
                return None
            d.update(fields)
            self._save()
            return dict(d)

    def delete(self, col, id):
        with self.lock:
            self.data.get(col, {}).pop(id, None)
            self._save()

    def delete_where(self, col, **flt):
        with self.lock:
            rows = self.data.get(col, {})
            for k in [k for k, d in rows.items() if all(d.get(a) == b for a, b in flt.items())]:
                rows.pop(k)
            self._save()


class MongoDB:
    kind = "mongodb"

    def __init__(self, uri: str, name: str):
        from pymongo import MongoClient

        self.client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        self.client.admin.command("ping")
        self.db = self.client[name]
        self.db.documents.create_index([("user_id", 1), ("created_at", -1)])
        self.db.websites.create_index([("user_id", 1), ("created_at", -1)])
        self.db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
        self.db.messages.create_index([("conversation_id", 1), ("created_at", 1)])

    @staticmethod
    def _out(d):
        if d is None:
            return None
        d = dict(d)
        d.pop("_id", None)
        return d

    def insert(self, col, doc):
        self.db[col].insert_one({**doc, "_id": doc["id"]})
        return doc

    def get(self, col, id, user_id=None):
        q = {"_id": id}
        if user_id is not None:
            q["user_id"] = user_id
        return self._out(self.db[col].find_one(q))

    def find(self, col, sort_key="created_at", desc=True, **flt):
        cur = self.db[col].find(flt).sort(sort_key, -1 if desc else 1)
        return [self._out(d) for d in cur]

    def update(self, col, id, fields):
        from pymongo import ReturnDocument

        d = self.db[col].find_one_and_update(
            {"_id": id}, {"$set": fields}, return_document=ReturnDocument.AFTER
        )
        return self._out(d)

    def delete(self, col, id):
        self.db[col].delete_one({"_id": id})

    def delete_where(self, col, **flt):
        self.db[col].delete_many(flt)


_db = None
_lock = threading.Lock()


def get_db():
    global _db
    with _lock:
        if _db is None:
            s = get_settings()
            if s.mongodb_uri:
                try:
                    _db = MongoDB(s.mongodb_uri, s.database_name)
                    log.info("Connected to MongoDB")
                except Exception as e:
                    if s.is_production:
                        raise RuntimeError(f"MongoDB connection failed: {e}") from e
                    log.warning("MongoDB unavailable (%s). Falling back to JSON file store.", e)
            if _db is None:
                if s.is_production:
                    raise RuntimeError("MONGODB_URI is required when APP_ENV=production")
                _db = JsonDB(s.json_db_path)
                log.info("Using local JSON metadata store at %s", s.json_db_path)
        return _db
