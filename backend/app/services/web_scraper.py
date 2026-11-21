import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import httpx

log = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_PORTS = {80, 443, 8080, 8443}
MIN_TEXT_CHARS = 100


class ScrapeError(Exception):
    pass


def assert_public_url(url: str) -> None:
    """SSRF guard: http(s) only, no credentials, and every resolved IP must be public."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ScrapeError("Only http:// and https:// URLs are allowed.")
    if not p.hostname:
        raise ScrapeError("Invalid URL.")
    if p.username or p.password:
        raise ScrapeError("URLs with credentials are not allowed.")
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
    except ValueError:
        raise ScrapeError("Invalid port in URL.")
    if port not in ALLOWED_PORTS:
        raise ScrapeError("This port is not allowed.")
    try:
        infos = socket.getaddrinfo(p.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ScrapeError("Could not resolve the website's hostname.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise ScrapeError("Private, local and internal addresses are blocked.")


def fetch_html(url: str) -> tuple[str, str]:
    """Fetch a page, validating every redirect hop. Returns (final_url, html)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DocuMindBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    current = url
    try:
        with httpx.Client(timeout=15, follow_redirects=False, headers=headers) as client:
            for _ in range(MAX_REDIRECTS + 1):
                assert_public_url(current)
                with client.stream("GET", current) as r:
                    if r.is_redirect:
                        loc = r.headers.get("location")
                        if not loc:
                            raise ScrapeError("Bad redirect from website.")
                        current = urljoin(current, loc)
                        continue
                    if r.status_code >= 400:
                        raise ScrapeError(f"The website returned HTTP {r.status_code}.")
                    ctype = r.headers.get("content-type", "").lower()
                    if not any(t in ctype for t in ("html", "xml", "text/plain")):
                        raise ScrapeError("The URL does not point to an HTML page.")
                    buf = bytearray()
                    for chunk in r.iter_bytes():
                        buf += chunk
                        if len(buf) > MAX_BYTES:
                            raise ScrapeError("The page is too large (limit 5 MB).")
                    return current, bytes(buf).decode(r.encoding or "utf-8", errors="replace")
    except httpx.HTTPError as e:
        raise ScrapeError(f"Could not fetch the website ({type(e).__name__}).") from e
    raise ScrapeError("Too many redirects.")


def scrape(url: str) -> dict:
    final_url, html = fetch_html(url)
    text, title = None, None
    try:
        import trafilatura

        text = trafilatura.extract(
            html, url=final_url, include_comments=False, include_tables=True, favor_recall=True
        )
        meta = trafilatura.extract_metadata(html)
        title = getattr(meta, "title", None) if meta else None
    except Exception:
        log.warning("trafilatura failed, using BeautifulSoup fallback")

    if not text or len(text) < MIN_TEXT_CHARS or not title:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not text or len(text) < MIN_TEXT_CHARS:
            for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()
            text = "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())

    if not text or len(text) < MIN_TEXT_CHARS:
        raise ScrapeError(
            "Not enough readable text found. The page may be JavaScript-rendered, login-protected or blocking bots."
        )
    return {"url": final_url, "title": (title or final_url)[:200], "text": text}
