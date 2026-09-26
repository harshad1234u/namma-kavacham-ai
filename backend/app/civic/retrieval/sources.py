"""The reviewed registry of official pages the retriever may fetch. Nothing outside it is ever fetched.

Registry = every source already cited by the curated scheme KB + the extra official pages listed in
data/civic/official_sources.json (each checked by a person to serve readable text over valid TLS).
Only https URLs on *.gov.in / *.nic.in are accepted; a page that redirects off those domains is dropped.
"""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.civic.schemes.kb import load_scheme_kb
from app.civic.schemes.schema import host_of, is_official_host

EXTRA_SOURCES_PATH = Path(__file__).resolve().parents[2] / "data" / "civic" / "official_sources.json"


class UnofficialUrlError(ValueError):
    pass


def validate_official_url(url: str) -> str:
    try:
        host = host_of(url)
    except ValueError as exc:
        raise UnofficialUrlError(str(exc)) from None
    if not is_official_host(host):
        raise UnofficialUrlError(f"not an official government domain: {host}")
    return url


@dataclass(frozen=True)
class SeedSource:
    url: str
    title: str
    publisher: str
    scheme_id: str | None


@lru_cache
def seed_sources() -> tuple[SeedSource, ...]:
    seen: dict[str, SeedSource] = {}
    for s in load_scheme_kb().schemes:
        for src in s.sources:
            seen.setdefault(src.url, SeedSource(src.url, src.title, src.publisher, s.id))
    for row in json.loads(EXTRA_SOURCES_PATH.read_text(encoding="utf-8"))["sources"]:
        url = validate_official_url(row["url"])
        seen.setdefault(url, SeedSource(url, row["title"], row["publisher"], row.get("scheme_id")))
    return tuple(seen.values())
