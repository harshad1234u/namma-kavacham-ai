from fastapi import APIRouter, HTTPException

from app.civic.languages import LanguageRegistry, load_languages, normalize_code
from app.civic.schemes import present
from app.civic.schemes.attributes import NEED_TAGS
from app.civic.schemes.discover import discover
from app.civic.schemes.eligibility import AnswerError, evaluate, question_attributes, validate_answers
from app.civic.schemes.extract import extract
from app.civic.schemes.kb import get_scheme, load_scheme_kb
from app.civic.schemes.models import (
    CriterionResult,
    DiscoverRequest,
    DiscoverResult,
    EligibilityRequest,
    EligibilityResult,
    FindingOut,
    QuestionOut,
    SchemeDetail,
    SchemeSummary,
    SchemeVerificationOut,
    SuggestionOut,
    VerifyRequest,
    VerifyResult,
)
from app.civic.schemes.schema import Scheme
from app.civic.schemes.verify import verify_claim
from app.core.logging import get_logger

router = APIRouter(prefix="/v1", tags=["civic"])
log = get_logger("civic")


@router.get("/meta/languages", response_model=LanguageRegistry)
async def language_support() -> LanguageRegistry:
    """Support matrix for the 22 Scheduled Languages. Never claims parity between languages."""
    return load_languages()


def _scheme_or_404(scheme_id: str) -> Scheme:
    s = get_scheme(scheme_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Scheme not in the verified set")
    return s


@router.get("/schemes", response_model=list[SchemeSummary])
async def list_schemes(lang: str = "en") -> list[SchemeSummary]:
    lang = normalize_code(lang)
    return [present.summary(s, lang) for s in load_scheme_kb().schemes]


@router.get("/schemes/{scheme_id}", response_model=SchemeDetail)
async def scheme_detail(scheme_id: str, lang: str = "en") -> SchemeDetail:
    return present.detail(_scheme_or_404(scheme_id), normalize_code(lang))


@router.get("/schemes/{scheme_id}/eligibility/questions", response_model=list[QuestionOut])
async def eligibility_questions(scheme_id: str, lang: str = "en") -> list[QuestionOut]:
    s = _scheme_or_404(scheme_id)
    lang = normalize_code(lang)
    return [present.question(a, lang) for a in question_attributes(s)]


@router.post("/schemes/{scheme_id}/eligibility", response_model=EligibilityResult)
async def check_eligibility(scheme_id: str, req: EligibilityRequest) -> EligibilityResult:
    s = _scheme_or_404(scheme_id)
    lang = normalize_code(req.lang)
    try:
        answers = validate_answers(req.answers)
    except AnswerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    out = evaluate(s, answers)
    log.info("eligibility_checked", extra={"scheme": s.id, "overall": out.overall, "answered": len(answers)})
    return EligibilityResult(
        scheme_id=s.id,
        overall=out.overall,
        criteria=[CriterionResult(criterion=present.criterion(c, lang), outcome=o) for c, o in out.per_criterion],
        missing_attributes=out.missing_attributes,
        criteria_complete=s.criteria_complete,
        note=present.loc(present.ELIGIBILITY_NOTE, lang),
    )


@router.post("/schemes/verify", response_model=VerifyResult)
async def verify(req: VerifyRequest) -> VerifyResult:
    lang = normalize_code(req.lang)
    out = verify_claim(req.text, req.url)
    log.info("scheme_claim_verified", extra={"status": out.status, "schemes": [r.scheme.id for r in out.schemes]})
    return VerifyResult(
        status=out.status,
        schemes=[
            SchemeVerificationOut(
                scheme=present.summary(r.scheme, lang),
                findings=[FindingOut(aspect=f.aspect, outcome=f.outcome, detail=present.loc({"en": f.detail_en}, lang), source_ref=f.source_ref) for f in r.findings],
                sources=present.sources(r.scheme),
            )
            for r in out.schemes
        ],
        disclosure=present.loc(present.DISCLOSURE, lang),
        search_portal=present.SEARCH_PORTAL if out.status in ("not_found", "unable_to_verify") else None,
    )


@router.post("/schemes/discover", response_model=DiscoverResult)
async def discover_schemes(req: DiscoverRequest) -> DiscoverResult:
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
        ex = extract(req.text or "")
        tags, mode = ex.need_tags, "deterministic"
        profile = {**ex.profile, **profile}  # what the citizen typed in the form wins over extraction
    results = discover(tags, profile)
    log.info("schemes_discovered", extra={"tags": tags, "results": len(results), "mode": mode})
    return DiscoverResult(
        understood_need_tags=tags,
        understood_profile=profile,
        extraction=mode,
        suggestions=[
            SuggestionOut(
                scheme=present.summary(x.scheme, lang), matched_need_tags=x.matched_need_tags, matched_profile=x.matched_profile,
                eligibility=x.eligibility.overall, missing_attributes=x.eligibility.missing_attributes,
            )
            for x in results
        ],
        disclosure=present.loc(present.DISCLOSURE, lang),
        search_portal=present.SEARCH_PORTAL,
    )
