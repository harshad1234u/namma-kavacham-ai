"""Fetch an official page as plain text. TLS is always verified; off-domain redirects are rejected."""
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.civic.retrieval.sources import UnofficialUrlError, validate_official_url

UA = {"User-Agent": "Mozilla/5.0 (CivicInsight official-source retriever)"}
MAX_BYTES = 3 * 1024 * 1024


class FetchError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Page:
    url: str  # final URL after redirects (still official)
    title: str
    text: str
    retrieved_at: datetime


def html_to_text(body: str) -> tuple[str, str]:
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    title = re.sub(r"\s+", " ", html.unescape(title_m.group(1))).strip() if title_m else ""
    body = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", body)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    return title, re.sub(r"\s+", " ", html.unescape(body)).strip()


async def fetch_page(url: str, client: httpx.AsyncClient) -> Page:
    validate_official_url(url)
    try:
        r = await client.get(url, headers=UA, follow_redirects=True)
    except httpx.TimeoutException:
        raise FetchError("timeout") from None
    except httpx.HTTPError as exc:
        raise FetchError("tls_error" if "CERTIFICATE" in str(exc).upper() else "connection_error") from None
    try:
        validate_official_url(str(r.url))
    except UnofficialUrlError:
        raise FetchError("redirected_off_official_domain") from None
    if r.status_code != 200:
        raise FetchError(f"http_{r.status_code}")
    if "html" not in r.headers.get("content-type", "html"):
        raise FetchError("not_html")
    if len(r.content) > MAX_BYTES:
        raise FetchError("too_large")
    title, text = html_to_text(r.text)
    if len(text) < 200:
        raise FetchError("no_readable_text")  # JavaScript-only page or error shell
    return Page(str(r.url), title, text, datetime.now(timezone.utc))
