from fastapi import APIRouter, Depends, HTTPException

from app.civic.languages import LanguageRegistry, load_languages, normalize_code
from app.civic.nim.provider import NemotronEmbeddingProvider, SarvamMProvider, build_chat, build_embedder
from app.civic.retrieval.service import OfficialSourceRetriever, get_retriever
from app.civic.schemes import present
from app.civic.schemes.attributes import NEED_TAGS
from app.civic.schemes.discover import discover
from app.civic.schemes.eligibility import AnswerError, evaluate, question_attributes, validate_answers
from app.civic.schemes.explain import translate_items
from app.civic.schemes.kb import get_scheme, load_scheme_kb
from app.civic.schemes.models import (
    AskResult,
    CriterionResult,
    DiscoverRequest,
    DiscoverResult,
    EligibilityRequest,
    EligibilityResult,
    EvidenceOut,
    ExplanationOut,
    FindingOut,
    QuestionOut,
    SchemeDetail,
    SchemeSummary,
    SchemeVerificationOut,
    SuggestionOut,
    UnderstandingOut,
    VerifyRequest,
    VerifyResult,
)
from app.civic.schemes.pipeline import PipelineResult, run
from app.civic.schemes.schema import Scheme
from app.civic.schemes.understand import understand
from app.civic.schemes.verify import Finding
from app.civic.settings import CivicSettings, get_civic_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/v1", tags=["civic"])
log = get_logger("civic")


# ---------- dependencies (overridden in tests) ----------
def get_chat(s: CivicSettings = Depends(get_civic_settings)) -> SarvamMProvider | None:
    return build_chat(s)


def get_embedder(s: CivicSettings = Depends(get_civic_settings)) -> NemotronEmbeddingProvider | None:
    return build_embedder(s)


def get_official_retriever(s: CivicSettings = Depends(get_civic_settings)) -> OfficialSourceRetriever | None:
    return get_retriever() if s.retrieval_enabled else None


def _secret(s: CivicSettings) -> str:
    return s.nvidia_nim_api_key.get_secret_value()


# ---------- meta ----------
@router.get("/meta/languages", response_model=LanguageRegistry)
async def language_support() -> LanguageRegistry:
    """Support matrix for the 22 Scheduled Languages. Never claims parity between languages."""
    return load_languages()


@router.get("/meta/ai")
async def ai_status(s: CivicSettings = Depends(get_civic_settings)) -> dict:
    """Which AI is configured for the civic modules (no key material)."""
    return {
        "ai_enabled": s.ai_active,
        "provider": "nvidia_nim" if s.ai_active else None,
        "chat_model": s.nvidia_nim_sarvam_model if s.ai_active else None,
        "embedding_model": s.nvidia_nim_embedding_model if s.ai_active else None,
        "official_retrieval": s.retrieval_enabled,
    }


def _scheme_or_404(scheme_id: str) -> Scheme:
    s = get_scheme(scheme_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Scheme not in the verified set")
    return s


# ---------- catalog ----------
@router.get("/schemes", response_model=list[SchemeSummary])
async def list_schemes(lang: str = "en") -> list[SchemeSummary]:
    lang = normalize_code(lang)
    return [present.summary(s, lang) for s in load_scheme_kb().schemes]


@router.get("/schemes/{scheme_id}", response_model=SchemeDetail)
async def scheme_detail(scheme_id: str, lang: str = "en", translate: bool = False,
                        chat: SarvamMProvider | None = Depends(get_chat),
                        s: CivicSettings = Depends(get_civic_settings)) -> SchemeDetail:
    """Official scheme text. With translate=true, missing languages are machine-translated (public text only)."""
    scheme, lang = _scheme_or_404(scheme_id), normalize_code(lang)
    detail = present.detail(scheme, lang)
    if not translate or lang == "en" or chat is None:
        return detail
    data = detail.model_dump()
    slots: dict[str, dict] = {}

    def collect(node, path: str) -> None:
        if isinstance(node, dict):
            if node.get("status") == "english_fallback" and "text" in node:
                slots[path] = node
            for k, v in node.items():
                collect(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                collect(v, f"{path}.{i}")

    collect(data, "d")
    protected = [*scheme.abbreviations, *scheme.official_domains, *(h.number for h in scheme.helplines)]
    done = await translate_items({k: v["text"] for k, v in slots.items()}, lang, chat, protected, _secret(s))
    for k, text in done.items():
        slots[k].update(text=text, lang=lang, status="machine_translated")
    return SchemeDetail.model_validate(data)


@router.get("/schemes/{scheme_id}/eligibility/questions", response_model=list[QuestionOut])
async def eligibility_questions(scheme_id: str, lang: str = "en") -> list[QuestionOut]:
    scheme = _scheme_or_404(scheme_id)
    lang = normalize_code(lang)
    return [present.question(a, lang) for a in question_attributes(scheme)]


@router.post("/schemes/{scheme_id}/eligibility", response_model=EligibilityResult)
async def check_eligibility(scheme_id: str, req: EligibilityRequest) -> EligibilityResult:
    scheme = _scheme_or_404(scheme_id)
    lang = normalize_code(req.lang)
    try:
        answers = validate_answers(req.answers)
    except AnswerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    out = evaluate(scheme, answers)
    log.info("eligibility_checked", extra={"scheme": scheme.id, "overall": out.overall, "answered": len(answers)})
    return EligibilityResult(
        scheme_id=scheme.id, overall=out.overall,
        criteria=[CriterionResult(criterion=present.criterion(c, lang), outcome=o) for c, o in out.per_criterion],
        missing_attributes=out.missing_attributes, criteria_complete=scheme.criteria_complete,
        note=present.loc(present.ELIGIBILITY_NOTE, lang),
    )


# ---------- verification ----------
def _finding(f: Finding, lang: str) -> FindingOut:
    return FindingOut(aspect=f.aspect, outcome=f.outcome, detail=present.loc({"en": f.detail_en}, lang),
                      source_ref=f.source_ref, evidence_url=f.evidence_url)


def _verify_result(r: PipelineResult, lang: str) -> dict:
    o, u = r.outcome, r.understanding
    return dict(
        status=o.status, basis=o.basis, message=o.message_en,
        schemes=[SchemeVerificationOut(scheme=present.summary(v.scheme, lang), findings=[_finding(f, lang) for f in v.findings],
                                       sources=present.sources(v.scheme)) for v in o.schemes],
        evidence_findings=[_finding(f, lang) for f in o.evidence_findings],
        evidence=[EvidenceOut(url=e.url, title=e.title, domain=e.domain, retrieved_at=e.retrieved_at, quote=e.quote,
                              scheme_id=e.scheme_id, method=e.method) for e in o.evidence],
        sources_checked=r.retrieval.sources_checked if r.retrieval else None,
        understanding=UnderstandingOut(scheme_ids=u.scheme_ids, scheme_name=u.scheme_name, need_tags=u.need_tags,
                                       profile=u.profile, method=u.method, ai_note=u.ai_reason, pii_removed=u.pii_removed),
        explanation=ExplanationOut(text=r.explanation.text, lang=r.explanation.lang, status=r.explanation.status, model=r.explanation.model),
        disclosure=present.loc(present.DISCLOSURE, lang),
        search_portal=present.SEARCH_PORTAL if o.status in ("not_found", "unable_to_verify") else None,
    )


def _log(event: str, r: PipelineResult) -> None:
    log.info(event, extra={"status": r.outcome.status, "basis": r.outcome.basis, "method": r.understanding.method,
                           "explanation": r.explanation.status, "evidence": len(r.outcome.evidence)})


@router.post("/schemes/verify", response_model=VerifyResult)
async def verify(req: VerifyRequest, chat=Depends(get_chat), embedder=Depends(get_embedder),
                 retriever=Depends(get_official_retriever), s: CivicSettings = Depends(get_civic_settings)) -> VerifyResult:
    lang = normalize_code(req.lang)
    r = await run(req.text, req.url, lang, req.ai_consent, chat, embedder, retriever, _secret(s))
    _log("scheme_claim_verified", r)
    return VerifyResult(**_verify_result(r, lang))


def _suggestions(tags: list[str], profile: dict, lang: str) -> list[SuggestionOut]:
    return [SuggestionOut(scheme=present.summary(x.scheme, lang), matched_need_tags=x.matched_need_tags,
                          matched_profile=x.matched_profile, eligibility=x.eligibility.overall,
                          missing_attributes=x.eligibility.missing_attributes) for x in discover(tags, profile)]


@router.post("/schemes/ask", response_model=AskResult)
async def ask(req: VerifyRequest, chat=Depends(get_chat), embedder=Depends(get_embedder),
              retriever=Depends(get_official_retriever), s: CivicSettings = Depends(get_civic_settings)) -> AskResult:
    """One entry point for a citizen's free-text question: verify what it claims, suggest what may help."""
    lang = normalize_code(req.lang)
    r = await run(req.text, req.url, lang, req.ai_consent, chat, embedder, retriever, _secret(s))
    _log("scheme_question_answered", r)
    sugg = _suggestions(r.understanding.need_tags, r.understanding.profile, lang) if r.understanding.need_tags else []
    return AskResult(**_verify_result(r, lang), suggestions=sugg)


@router.post("/schemes/discover", response_model=DiscoverResult)
async def discover_schemes(req: DiscoverRequest, chat=Depends(get_chat)) -> DiscoverResult:
    lang = normalize_code(req.lang)
    try:
        profile = validate_answers(req.profile)
    except AnswerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if req.need_tags is not None:
        unknown = [t for t in req.need_tags if t not in NEED_TAGS]
        if unknown:
            raise HTTPException(status_code=422, detail=f"unknown need tags {unknown}")
        tags, mode = list(req.need_tags), "provided"
    else:
        u = await understand(req.text or "", chat if req.ai_consent else None)
        tags, mode = u.need_tags, u.method
        profile = {**u.profile, **profile}  # what the citizen typed in the form wins over extraction
    suggestions = _suggestions(tags, profile, lang)
    log.info("schemes_discovered", extra={"tags": tags, "results": len(suggestions), "mode": mode})
    return DiscoverResult(understood_need_tags=tags, understood_profile=profile, extraction=mode, suggestions=suggestions,
                          disclosure=present.loc(present.DISCLOSURE, lang), search_portal=present.SEARCH_PORTAL)
