"""Official Government Source Retrieval: fetch the reviewed registry (cached), index it, return evidence."""
import asyncio
import threading
import time
from dataclasses import dataclass

import httpx

from app.civic.nim.provider import NemotronEmbeddingProvider
from app.civic.retrieval.fetch import FetchError, Page, fetch_page
from app.civic.retrieval.index import Evidence, EvidenceIndex
from app.civic.retrieval.sources import SeedSource, seed_sources
from app.core.logging import get_logger

log = get_logger("civic.retrieval")


@dataclass(frozen=True)
class RetrievalResult:
    evidence: list[Evidence]
    sources_checked: int
    sources_unavailable: dict[str, str]  # url -> safe reason
    available: bool  # False when no official page could be read at all


class OfficialSourceRetriever:
    def __init__(self, sources: tuple[SeedSource, ...], timeout: float = 12.0, ttl: int = 6 * 3600,
                 transport: httpx.AsyncBaseTransport | None = None, concurrency: int = 6):
        self._sources = sources
        self._timeout, self._ttl, self._transport, self._conc = timeout, ttl, transport, concurrency
        self._index = EvidenceIndex()
        self._failed: dict[str, str] = {}
        self._built_at = 0.0
        self._embedded = False
        self._lock = asyncio.Lock()

    async def _load(self, embedder: NemotronEmbeddingProvider | None) -> None:
        sem = asyncio.Semaphore(self._conc)
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            async def one(src: SeedSource) -> tuple[SeedSource, Page | str]:
                async with sem:
                    try:
                        return src, await fetch_page(src.url, client)
                    except FetchError as exc:
                        return src, exc.reason
            results = await asyncio.gather(*(one(s) for s in self._sources))
        pages = [(p, s.scheme_id) for s, p in results if isinstance(p, Page)]
        self._failed = {s.url: p for s, p in results if isinstance(p, str)}
        await self._index.build(pages, embedder)
        self._embedded = embedder is not None and any(c.vector for c in self._index.chunks)
        self._built_at = time.monotonic()
        log.info("official_sources_indexed", extra={"pages": len(pages), "failed": len(self._failed),
                                                    "chunks": len(self._index.chunks), "embedded": self._embedded})

    async def retrieve(self, query: str, embedder: NemotronEmbeddingProvider | None = None, k: int = 5,
                       scheme_id: str | None = None) -> RetrievalResult:
        async with self._lock:
            stale = time.monotonic() - self._built_at > self._ttl or not self._index.chunks
            if stale or (embedder is not None and not self._embedded):
                await self._load(embedder)
        evidence = await self._index.search(query, embedder, k=k, scheme_id=scheme_id)
        return RetrievalResult(evidence, len(self._sources), dict(self._failed), bool(self._index.chunks))


_retriever: OfficialSourceRetriever | None = None
_init_lock = threading.Lock()


def get_retriever() -> OfficialSourceRetriever:
    """Process-wide retriever (one page cache). Called from worker threads, hence the lock."""
    global _retriever
    if _retriever is None:
        with _init_lock:
            if _retriever is None:
                from app.civic.settings import get_civic_settings

                s = get_civic_settings()
                _retriever = OfficialSourceRetriever(seed_sources(), s.retrieval_timeout_seconds, s.retrieval_cache_seconds)
    return _retriever
