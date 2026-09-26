"""Citizen query -> understanding -> curated KB or official retrieval -> deterministic verdict -> explanation."""
from dataclasses import dataclass

from app.civic.nim.guard import minimise_pii
from app.civic.nim.provider import NemotronEmbeddingProvider, SarvamMProvider
from app.civic.retrieval.service import OfficialSourceRetriever, RetrievalResult
from app.civic.schemes.explain import Explanation, explain
from app.civic.schemes.understand import Understanding, understand
from app.civic.schemes.verify import VerifyOutcome, verify_against_evidence, verify_against_kb


@dataclass(frozen=True)
class PipelineResult:
    understanding: Understanding
    outcome: VerifyOutcome
    retrieval: RetrievalResult | None
    explanation: Explanation


async def run(text: str, url: str | None, lang: str, ai_consent: bool, chat: SarvamMProvider | None,
              embedder: NemotronEmbeddingProvider | None, retriever: OfficialSourceRetriever | None,
              secret: str = "") -> PipelineResult:
    # Citizen text reaches NIM (chat or query embedding) only with consent.
    u = await understand(text, chat if ai_consent else None)
    outcome = verify_against_kb(text, url, u.scheme_ids)
    retrieval = None
    if outcome is None:
        if retriever is not None:
            query = u.scheme_name or minimise_pii(text)[0]
            retrieval = await retriever.retrieve(query, embedder if ai_consent else None, k=8)
        outcome = verify_against_evidence(text, url, u.scheme_name, retrieval)
    # The explainer never sees citizen text, only the decided result and public evidence.
    return PipelineResult(u, outcome, retrieval, await explain(outcome, lang, chat, secret))
