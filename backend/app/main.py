import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, models, websites
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.mongodb import get_db

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    s = get_settings()
    Path(s.upload_dir).mkdir(parents=True, exist_ok=True)
    get_db()  # fail fast if the database is misconfigured
    if s.is_production and s.secret_key.startswith("replace-with"):
        log.warning("SECRET_KEY is still the default value.")
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

for r in (documents.router, websites.router, chat.router, models.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/health")  # used by Render's health check
def root_health():
    return {"status": "ok"}
