from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.dependencies import get_user_id
from app.core.security import RateLimiter
from app.database.models import new_id, utcnow
from app.database.mongodb import get_db
from app.schemas.website import WebsiteIngest, WebsiteOut
from app.services.ingestion import process_website
from app.services.vector_store import get_store
from app.services.web_scraper import ScrapeError, assert_public_url

router = APIRouter(prefix="/websites", tags=["websites"])
ingest_limiter = RateLimiter(20, 60)


def _get_or_404(site_id: str, user_id: str) -> dict:
    site = get_db().get("websites", site_id, user_id)
    if not site:
        raise HTTPException(404, "Website not found")
    return site


@router.post("/ingest", response_model=WebsiteOut, status_code=202)
def ingest(
    body: WebsiteIngest,
    background: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    _: None = Depends(ingest_limiter),
):
    url = body.url.strip()
    if "://" not in url:
        url = "https://" + url
    try:
        assert_public_url(url)  # fail fast (SSRF check runs again on every redirect while fetching)
    except ScrapeError as e:
        raise HTTPException(400, str(e))
    if any(w["url"] == url for w in get_db().find("websites", user_id=user_id)):
        raise HTTPException(409, "This website was already added.")
    site = get_db().insert(
        "websites",
        {
            "id": new_id("web_"),
            "user_id": user_id,
            "url": url,
            "title": url,
            "status": "processing",
            "error": None,
            "created_at": utcnow(),
        },
    )
    background.add_task(process_website, site["id"])
    return site


@router.get("", response_model=list[WebsiteOut])
def list_websites(user_id: str = Depends(get_user_id)):
    return get_db().find("websites", user_id=user_id)


@router.get("/{site_id}", response_model=WebsiteOut)
def get_website(site_id: str, user_id: str = Depends(get_user_id)):
    return _get_or_404(site_id, user_id)


@router.delete("/{site_id}")
def delete_website(site_id: str, user_id: str = Depends(get_user_id)):
    _get_or_404(site_id, user_id)
    get_store().delete_source(site_id)
    get_db().delete("websites", site_id)
    return {"success": True}
