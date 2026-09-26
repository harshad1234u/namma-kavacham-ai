"""Chunk official pages and rank passages for a query: Nemotron embeddings when available, keywords otherwise."""
import math
import re
from dataclasses import dataclass, field
from datetime import datetime

from app.civic.nim.provider import NemotronEmbeddingProvider, NIMError
from app.civic.retrieval.fetch import Page
from app.civic.schemes.schema import host_of, norm

_SENTENCE = re.compile(r"(?<=[.!?।॥])\s+|\s+(?=\d+\.\s)|;\s+")
# Split on spaces/punctuation, not \w: \w drops Indic vowel signs and would cut words apart.
_SPLIT = re.compile(r"[\s.,;:!?()\[\]{}\"'/\|\-–—।॥₹*#@<>=+]+")
_STOP = frozenset("the a an of to in for and or is are be on by with as at from this that it its under scheme yojana".split())


def tokens(text: str) -> list[str]:
    text = re.sub(r"(?<=\d),(?=\d)", "", norm(text))  # 6,000 == 6000
    return [t for t in _SPLIT.split(text) if len(t) > 1 and t not in _STOP]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(text) if len(s.strip()) > 20]


def chunk(text: str, size: int = 700, overlap: int = 1) -> list[str]:
    """Group sentences into ~size-character passages, repeating `overlap` sentences between neighbours."""
    sents, out, cur = sentences(text), [], []
    for s in sents:
        if cur and sum(map(len, cur)) + len(s) > size:
            out.append(" ".join(cur))
            cur = cur[-overlap:] if overlap else []
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return out


@dataclass
class Chunk:
    page: Page
    scheme_id: str | None
    text: str
    vector: list[float] | None = None
    tokens: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Evidence:
    url: str
    title: str
    domain: str
    retrieved_at: datetime
    passage: str
    quote: str  # exact substring of the official page text
    scheme_id: str | None
    score: float
    method: str  # "embedding" | "keyword"


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def best_quote(passage: str, query_tokens: set[str], max_len: int = 300) -> str:
    """The passage sentence sharing most words with the query, verbatim; long ones are cut to an exact window."""
    sents = sentences(passage) or [passage]
    best = max(sents, key=lambda s: (len(query_tokens & set(tokens(s))), -len(s)))
    if len(best) <= max_len:
        return best
    low = best.lower()
    hits = [low.find(t) for t in query_tokens if low.find(t) >= 0]
    start = max(0, min(hits, default=0) - max_len // 3)
    return best[start:start + max_len]


class EvidenceIndex:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []

    async def build(self, pages: list[tuple[Page, str | None]], embedder: NemotronEmbeddingProvider | None) -> None:
        chunks = [Chunk(p, sid, c, tokens=tokens(c)) for p, sid in pages for c in chunk(p.text)]
        if embedder is not None and chunks:
            try:
                for i in range(0, len(chunks), 32):
                    batch = chunks[i:i + 32]
                    for c, v in zip(batch, await embedder.embed([c.text for c in batch], "passage")):
                        c.vector = v
            except NIMError:
                for c in chunks:
                    c.vector = None  # partial vectors are useless; rank by keywords instead
        self.chunks = chunks

    def _keyword_scores(self, q: list[str]) -> list[float]:
        n = len(self.chunks) or 1
        df = {t: sum(1 for c in self.chunks if t in c.tokens) for t in set(q)}
        idf = {t: math.log(1 + n / (1 + d)) for t, d in df.items()}
        return [sum(idf[t] for t in set(q) if t in c.tokens) / math.sqrt(1 + len(c.tokens) / 60) for c in self.chunks]

    async def search(self, query: str, embedder: NemotronEmbeddingProvider | None, k: int = 5,
                     scheme_id: str | None = None) -> list[Evidence]:
        pool = [i for i, c in enumerate(self.chunks) if scheme_id is None or c.scheme_id in (scheme_id, None)]
        if not pool:
            return []
        q_tokens = tokens(query)
        method, scores = "keyword", self._keyword_scores(q_tokens)
        if embedder is not None and all(self.chunks[i].vector for i in pool):
            try:
                qv = (await embedder.embed([query], "query"))[0]
                scores = [_cos(qv, c.vector) if c.vector else 0.0 for c in self.chunks]
                method = "embedding"
            except NIMError:
                pass
        ranked = sorted(pool, key=lambda i: scores[i], reverse=True)[:k]
        out = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            c = self.chunks[i]
            out.append(Evidence(c.page.url, c.page.title, host_of(c.page.url), c.page.retrieved_at, c.text,
                                best_quote(c.text, set(q_tokens)), c.scheme_id, round(scores[i], 4), method))
        return out
