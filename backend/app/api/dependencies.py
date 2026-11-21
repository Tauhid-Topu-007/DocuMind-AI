import re

from fastapi import Header, HTTPException

_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Identify the caller. The frontend generates an anonymous id and sends it in
    `X-User-Id`. Every query is scoped by it. Replace with real auth (JWT/OAuth)
    before opening the app to the public with sensitive documents."""
    if not x_user_id or not _ID.match(x_user_id):
        raise HTTPException(400, "Missing or invalid X-User-Id header")
    return x_user_id
