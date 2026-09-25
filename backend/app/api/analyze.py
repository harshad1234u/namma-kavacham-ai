"""POST /v1/analyze — the single orchestrator.

Sequence: validate → confirm reviewed → provenance → URLs → deterministic rules
→ threat intel → government claim → evidence → risk → explanation → compose.
Raw content lives only in this request's memory and is never logged.
"""

import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    DomainCheckOut,
    ErrorResponse,
    ProvenanceOut,
    ProviderFlags,
    RiskOut,
    UrlIntelligenceOut,
)
from app.schemas.threat_intelligence import ThreatIntelResult
from app.services import evidence_normalizer as ev
from app.services import response_composer as rc
from app.services.ai_explainer import ExplanationContext, Explainer, build_explainer, template_explanation
from app.services.government.claim_detector import detect_claims
from app.services.government.kb import load_kb
from app.services.government.kb_comparator import compare_claims
from app.services.message_rules import normalize_text, run_message_rules
from app.services.ocr_stub import UnsupportedImageError, extract_text_stub
from app.services.risk_engine import RiskEngineInput, compute_risk
from app.services.threat_intelligence.base import ThreatIntelProvider
from app.services.threat_intelligence.virustotal import build_provider
from app.services.url_analyzer import (
    DomainCheckHit,
    NormalizedUrl,
    extract_urls,
    normalize_url,
    run_domain_checks,
)

router = APIRouter(prefix="/v1", tags=["analysis"])
log = get_logger("analyze")

VT_PRIVACY_NOTE = (
    "Only the extracted link (not your message) is sent to VirusTotal, a third-party service, "
    "to look up existing reports."
)


def get_threat_intel_provider(settings: Settings = Depends(get_settings)) -> ThreatIntelProvider:
    return build_provider(settings)


def get_explainer(settings: Settings = Depends(get_settings)) -> Explainer:
    return build_explainer(settings)


def sanitize_errors(exc: ValidationError) -> list[dict]:
    # Pydantic echoes the offending input; strip it so submitted content never appears in errors.
    return [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]


def _unprocessable(detail: object) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


async def _read_screenshot(upload: UploadFile, settings: Settings) -> bytes:
    data = await upload.read(settings.max_upload_bytes + 1)
    await upload.close()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Screenshot exceeds the size limit")
    if not data:
        raise _unprocessable("Screenshot file is empty")
    return data


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={413: {"model": ErrorResponse}, 415: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Assess a reviewed message, URL, or screenshot for scam risk",
)
async def analyze(
    payload: str = Form(..., description="JSON-encoded AnalyzeRequest"),
    screenshot: UploadFile | None = File(default=None, description="Optional PNG/JPEG/WebP screenshot"),
    settings: Settings = Depends(get_settings),
    provider: ThreatIntelProvider = Depends(get_threat_intel_provider),
    explainer: Explainer = Depends(get_explainer),
) -> AnalyzeResponse:
    started = time.monotonic()
    analysis_id = str(uuid.uuid4())

    try:
        request = AnalyzeRequest.model_validate_json(payload)
    except ValidationError as exc:
        raise _unprocessable(sanitize_errors(exc)) from None

    body = request.content.body
    if len(body) > settings.max_message_body_chars:
        raise _unprocessable(f"content.body exceeds {settings.max_message_body_chars} characters")

    # Screenshot: validated by content, OCR'd (stub), then dropped from memory.
    ocr_attempted = False
    if screenshot is not None and screenshot.filename:
        if not request.privacy.upload_confirmed:
            raise _unprocessable("privacy.upload_confirmed must be true to upload a screenshot")
        image = await _read_screenshot(screenshot, settings)
        try:
            ocr_text = extract_text_stub(image, screenshot.content_type)
        except UnsupportedImageError as exc:
            raise HTTPException(415, str(exc)) from None
        finally:
            del image
        ocr_attempted = True
        if not body.strip() and ocr_text:
            body = ocr_text
    elif not body.strip():
        raise _unprocessable("Nothing to analyse: provide message text, a URL, or a screenshot")

    text = normalize_text(body)

    # URLs
    raw_urls = extract_urls(body)
    domain_hits_by_url: list[tuple[str, list[DomainCheckHit]]] = []
    normalized_urls: list[str] = []
    parsed_urls: list[NormalizedUrl] = []
    for raw in raw_urls:
        try:
            normalized = normalize_url(raw)
        except ValueError:
            continue
        parsed_urls.append(normalized)
        normalized_urls.append(normalized.normalized)
        domain_hits_by_url.append((normalized.normalized, run_domain_checks(normalized)))
    primary_url = normalized_urls[0] if normalized_urls else None

    # Deterministic message rules
    rule_hits = run_message_rules(text)

    # Threat intelligence (primary URL only, to respect provider quota)
    intel: ThreatIntelResult | None = None
    if primary_url:
        intel = ThreatIntelResult.model_validate(await provider.check_url(primary_url))

    # Government claim vs curated KB (deterministic; independent of the rules above)
    kb = load_kb()
    rule_signals = {h.signal for h in rule_hits}
    claims = detect_claims(text, kb, rule_signals, bool(parsed_urls))
    government = compare_claims(claims, kb, text, rule_signals, parsed_urls)

    # Evidence + risk
    evidence = ev.normalize_evidence(
        ev.from_rule_hits(rule_hits),
        ev.from_domain_hits(domain_hits_by_url),
        ev.from_threat_intel(intel),
        ev.from_government_claim(government),
    )
    all_domain_hits = [h for _, hits in domain_hits_by_url for h in hits]
    risk = compute_risk(RiskEngineInput(rule_hits, all_domain_hits, intel, government))
    assessment_status = "assessed" if text else "insufficient_content"

    missing = rc.missing_metadata(request, intel, bool(primary_url), ocr_attempted, government)
    steps_en, steps_ta = rc.safe_next_steps(
        risk.level,
        set(risk.contributing_signals),
        bool(primary_url),
        list(zip(government.safe_guidance_en, government.safe_guidance_ta)),
    )

    allowed_domains = {u.hostname for u in parsed_urls} | {u.registrable_domain for u in parsed_urls}
    allowed_domains |= {d for e in kb.entries if e.id in government.matched_kb_entries for d in e.official_domains}
    allowed_domains.add("cybercrime.gov.in")
    ctx = ExplanationContext(
        level=risk.level,
        evidence=evidence,
        missing_metadata=missing,
        score=risk.score,
        government=government,
        link_reputation={"provider": intel.provider, "status": intel.status.value} if intel else None,
        safe_next_steps=steps_en,
        allowed_domains=allowed_domains,
    )
    if assessment_status == "insufficient_content":
        explanation = template_explanation(ctx, "disabled")
    else:
        explanation = await explainer.explain(ctx)
    if assessment_status == "insufficient_content":
        explanation.en = (
            "No text could be analysed, so no risk assessment was made. This is not a safe result. "
            "Please type or paste the message text and submit again."
        )
        explanation.ta = (
            "பகுப்பாய்வு செய்ய உரை எதுவும் இல்லை, எனவே ஆபத்து மதிப்பீடு செய்யப்படவில்லை. இது பாதுகாப்பான முடிவு அல்ல. "
            "செய்தியின் உரையைத் தட்டச்சு செய்து அல்லது ஒட்டி மீண்டும் சமர்ப்பிக்கவும்."
        )

    vt_enabled = settings.virustotal_active
    limits_en, limits_ta = rc.limitations(bool(primary_url), intel, explanation.ai_status == "generated")
    ai_attempted = explanation.ai_status in ("generated", "unavailable", "rejected")
    response = AnalyzeResponse(
        analysis_id=analysis_id,
        risk=RiskOut(
            assessment_status=assessment_status,
            level=risk.level,
            score=risk.score,
            verdict_scope=rc.VERDICT_SCOPE,
            verdict_scope_ta=rc.VERDICT_SCOPE_TA,
        ),
        evidence=evidence,
        url_intelligence=UrlIntelligenceOut(
            extracted_urls=normalized_urls,
            primary_url=primary_url,
            domain_checks=[
                DomainCheckOut(signal=h.signal, confidence=h.confidence, detail=h.detail_en, url=url)
                for url, hits in domain_hits_by_url for h in hits
            ],
            provider_enabled=vt_enabled,
            provider_result=intel,
            privacy_note=VT_PRIVACY_NOTE if primary_url and vt_enabled else None,
        ),
        government_claim=government,
        provenance=ProvenanceOut(
            content_source=request.content.source,
            image_origin=request.content.image_origin,
            user_confirmed=request.content.user_confirmed,
            attachment_received=ocr_attempted,
            # Browser OCR: the text arrives already extracted and no image is received.
            ocr_status="not_available_in_this_build" if ocr_attempted
            else "extracted" if request.content.source in ("ocr", "user_corrected_ocr") else "not_applicable",
            character_count=len(body),
        ),
        sender_assessment=rc.sender_assessment(request),
        missing_metadata=missing,
        limitations=limits_en + government.limitations,
        limitations_ta=limits_ta + government.limitations_ta,
        safe_next_steps=steps_en,
        safe_next_steps_ta=steps_ta,
        explanation=explanation,
        provider_flags=ProviderFlags(
            virustotal_enabled=vt_enabled,
            virustotal_available=intel.available if intel else None,
            ai_provider=settings.active_llm_provider,
            ai_enabled=settings.active_llm_provider != "template",
            ai_available=explanation.ai_status in ("generated", "rejected") if ai_attempted else None,
        ),
    )

    log.info(
        "analysis_completed",
        extra={
            "analysis_id": analysis_id,
            "content_source": request.content.source,
            "image_origin": request.content.image_origin,
            "char_count": len(body),
            "url_count": len(normalized_urls),
            "rule_hits": len(rule_hits),
            "risk_level": risk.level,
            "risk_score": risk.score,
            "vt_status": intel.status.value if intel else None,
            "gov_claim_status": government.claim_status.value,
            "ai_status": explanation.ai_status,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        },
    )
    return response
