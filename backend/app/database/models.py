import uuid
from datetime import datetime, timezone


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
