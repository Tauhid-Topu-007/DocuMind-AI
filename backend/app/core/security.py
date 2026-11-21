import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from app.api.dependencies import get_user_id


class RateLimiter:
    """Tiny in-memory sliding-window limiter (per user, per process)."""

    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def __call__(self, user_id: str = Depends(get_user_id)) -> None:
        now = time.monotonic()
        with self.lock:
            q = self.hits[user_id]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_calls:
                raise HTTPException(429, "Too many requests. Please slow down.")
            q.append(now)


def safe_filename(name: str) -> str:
    name = (name or "document.pdf").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\- ()]", "_", name).strip() or "document.pdf"
    return name[:120]
