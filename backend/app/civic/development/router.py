"""/v1/development: citizen development requests and aggregate, anonymised development intelligence."""
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.civic.development.classifier import Classification, classify
from app.civic.development.data import load_dev_data
from app.civic.development.engine import LEVEL_ORDER, Issue, PriorityConfig, analyse, issue_key, request_statuses, themes, weekly
from app.civic.development.insight import insight
from app.civic.development.models import (
    ClassificationOut,
    ClassifyIn,
    ComponentOut,
    Dashboard,
    IssueDetail,
    IssueSummary,
    PrioritizeIn,
    RequestIn,
    RequestReceipt,
)
from app.civic.development.store import RequestStore, StoredRequest, get_store, new_id, today
from app.civic.development.taxonomy import CATEGORIES
from app.civic.languages import normalize_code
from app.civic.nim.guard import minimise_pii
from app.civic.nim.provider import SarvamMProvider, build_chat
from app.civic.schemes.identify import identify_schemes
from app.civic.schemes.kb import load_scheme_kb
from app.civic.schemes.models import ExplanationOut
from app.civic.settings import CivicSettings, get_civic_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/development", tags=["development"])  # mounted under /v1 by app.civic.router
log = get_logger("civic.development")

DISCLAIMER = ("Development priority is an analytical aid computed from citizen reports and the available datasets. "
              "It is not a government decision, approval or commitment. Demonstration data is synthetic.")
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
CATEGORY_NEED_TAGS = {"water": ["drinking_water"], "housing": ["housing"], "employment": ["employment"],
                      "agriculture": ["farming_income_support", "crop_insurance"], "healthcare": ["health_insurance"],
                      "education": ["education_scholarship"]}


def get_dev_store() -> RequestStore:
    return get_store()


def get_dev_chat(s: CivicSettings = Depends(get_civic_settings)) -> SarvamMProvider | None:
    return build_chat(s)


def _cfg(s: CivicSettings) -> PriorityConfig:
    return PriorityConfig.from_settings(s)


def _class_out(c: Classification) -> ClassificationOut:
    return ClassificationOut(category=c.category, category_label=CATEGORIES[c.category].labels["en"] if c.category else None,
                             issue_type=c.issue_type, urgency=c.urgency, confidence=c.confidence, reason=c.reason,
                             language=c.language, method=c.method, ai_note=c.ai_note)


def _summary(i: Issue) -> IssueSummary:
    return IssueSummary(id=i.id, category=i.category, category_label=CATEGORIES[i.category].labels["en"], state=i.state,
                        district=i.district, locality=i.locality, lat=i.lat, lng=i.lng, report_count=i.report_count,
                        priority_score=i.priority.score, priority_level=i.priority.level, gap_level=i.gap.level,
                        hotspot=i.hotspot, high_urgency_reports=sum(r.urgency == "high" for r in i.requests),
                        data_completeness=i.priority.data_completeness, demo_data=i.area_id is not None)


def _filtered(store: RequestStore, s: CivicSettings, state: str | None, district: str | None, category: str | None,
              date_from: date | None, date_to: date | None) -> dict[str, Issue]:
    reqs = [r for r in store.all()
            if (not state or r.state.lower() == state.lower()) and (not district or r.district.lower() == district.lower())
            and (not category or r.category == category)
            and (not date_from or r.created_at >= date_from) and (not date_to or r.created_at <= date_to)]
    return analyse(reqs, load_dev_data(), _cfg(s))


def _sorted(issues: list[Issue], sort: str) -> list[Issue]:
    keys = {
        "priority": lambda i: (i.priority.score if i.priority.score is not None else -1, i.report_count),
        "reports": lambda i: (i.report_count, i.priority.score or -1),
        "urgency": lambda i: (sum(r.urgency == "high" for r in i.requests), i.report_count),
    }
    return sorted(issues, key=keys.get(sort, keys["priority"]), reverse=True)


# ---------- meta & data ----------
@router.get("/meta")
async def meta(s: CivicSettings = Depends(get_civic_settings)) -> dict:
    data = load_dev_data()
    return {
        "categories": [{"id": c.id, "labels": c.labels, "issue_types": [{"id": i.id, "label": i.label} for i in c.issues]}
                       for c in CATEGORIES.values()],
        "statuses": ["received", "aggregated", "priority_assessed", "included_in_insight"],
        "priority_levels": {"critical": "80-100", "high": "60-79", "medium": "40-59", "lower": "0-39",
                            "unable_to_assess": "not enough context data"},
        "weights": _cfg(s).weights,
        "hotspot_min_reports": s.dev_hotspot_min_reports,
        "states_and_uts": data.states.names,
        "states_source": data.states.source,
        "demo_areas": [a.model_dump() for a in data.areas],
        "provenance": data.areas_source,
        "disclaimer": DISCLAIMER,
    }


@router.get("/data/{kind}")
async def dataset(kind: str) -> dict:
    d = load_dev_data()
    table = {"demographics": (d.demographics_source, d.demographics), "infrastructure": (d.infrastructure_source, d.infrastructure),
             "investments": (d.investments_source, d.investments), "areas": (d.areas_source, d.areas)}
    if kind not in table:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    source, rows = table[kind]
    return {"source": source, "rows": rows}


# ---------- citizen requests ----------
@router.post("/classify", response_model=ClassificationOut)
async def classify_request(req: ClassifyIn, chat=Depends(get_dev_chat)) -> ClassificationOut:
    return _class_out(await classify(req.text, chat if req.ai_consent else None))


@router.post("/requests", response_model=RequestReceipt)
async def submit_request(payload: str = Form(..., max_length=8000), photo: UploadFile | None = File(None),
                         chat=Depends(get_dev_chat), store: RequestStore = Depends(get_dev_store),
                         s: CivicSettings = Depends(get_civic_settings)) -> RequestReceipt:
    try:
        req = RequestIn.model_validate_json(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]) from None
    data = load_dev_data()
    if req.state.upper() not in data.states.names:
        raise HTTPException(status_code=422, detail="Unknown State/UT")
    area = data.area(req.area_id) if req.area_id else None
    if req.area_id and (area is None or area.state != req.state.upper() or area.district.lower() != req.district.lower()):
        raise HTTPException(status_code=422, detail="Unknown locality for this district")
    if req.category and req.category not in CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown category")
    photo_attached = False
    if photo is not None and photo.filename:
        if photo.content_type not in PHOTO_TYPES:
            raise HTTPException(status_code=415, detail="Photo must be JPEG, PNG or WebP")
        content = await photo.read(MAX_PHOTO_BYTES + 1)
        if len(content) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="Photo is larger than 5 MB")
        photo_attached = bool(content)
        del content  # supporting evidence only; not analysed or stored in this build
    c = await classify(req.text, chat if req.ai_consent else None, req.category, req.urgency)
    if c.category is None:
        raise HTTPException(status_code=422, detail="Could not detect a category; please choose one")
    clean, _ = minimise_pii(req.text)
    stored = store.add(StoredRequest(
        new_id(), clean, c.language, c.category, c.issue_type, area.area_id if area else None, req.state.upper(),
        area.district if area else req.district.strip().title(), area.area if area else (req.locality or None),
        c.urgency, req.source, today(), [m.scheme_id for m in identify_schemes(clean)], photo_attached))
    issues = analyse(store.all(), data, _cfg(s))
    log.info("development_request_received", extra={"category": c.category, "method": c.method, "demo_area": bool(area)})
    return RequestReceipt(id=stored.id, category=c.category, category_label=CATEGORIES[c.category].labels["en"],
                          issue_type=c.issue_type, state=stored.state, district=stored.district, locality=stored.locality,
                          urgency=c.urgency, created_at=stored.created_at, statuses=request_statuses(stored, issues),
                          issue_id=issue_key(stored), photo_attached=photo_attached, classification=_class_out(c))


@router.get("/requests", response_model=list[RequestReceipt])
async def my_requests(ids: str, store: RequestStore = Depends(get_dev_store),
                      s: CivicSettings = Depends(get_civic_settings)) -> list[RequestReceipt]:
    """Only the reports whose ids the caller already holds (no listing of other people's reports)."""
    wanted = [i for i in ids.split(",") if i.startswith("REQ-")][:50]
    issues = analyse(store.all(), load_dev_data(), _cfg(s))
    return [RequestReceipt(id=r.id, category=r.category, category_label=CATEGORIES[r.category].labels["en"], issue_type=r.issue_type,
                           state=r.state, district=r.district, locality=r.locality, urgency=r.urgency, created_at=r.created_at,
                           statuses=request_statuses(r, issues), issue_id=issue_key(r), photo_attached=r.photo_attached)
            for r in store.get_many(wanted)]


# ---------- aggregate intelligence ----------
@router.get("/issues", response_model=list[IssueSummary])
async def list_issues(state: str | None = None, district: str | None = None, category: str | None = None,
                      min_level: str = "unable_to_assess", date_from: date | None = None, date_to: date | None = None,
                      sort: str = "priority", hotspots_only: bool = False, store: RequestStore = Depends(get_dev_store),
                      s: CivicSettings = Depends(get_civic_settings)) -> list[IssueSummary]:
    if min_level not in LEVEL_ORDER:
        raise HTTPException(status_code=422, detail="Unknown priority level")
    issues = _filtered(store, s, state, district, category, date_from, date_to).values()
    keep = [i for i in issues if LEVEL_ORDER[i.priority.level] >= LEVEL_ORDER[min_level] and (i.hotspot or not hotspots_only)]
    return [_summary(i) for i in _sorted(keep, sort)]


@router.get("/hotspots", response_model=list[IssueSummary])
async def list_hotspots(state: str | None = None, district: str | None = None, category: str | None = None,
                        date_from: date | None = None, date_to: date | None = None, sort: str = "priority",
                        store: RequestStore = Depends(get_dev_store), s: CivicSettings = Depends(get_civic_settings)) -> list[IssueSummary]:
    issues = _filtered(store, s, state, district, category, date_from, date_to).values()
    return [_summary(i) for i in _sorted([i for i in issues if i.hotspot], sort)]


def _relevant_schemes(category: str) -> list[dict[str, str]]:
    tags = set(CATEGORY_NEED_TAGS.get(category, []))
    return [{"id": s.id, "name": s.names["en"]} for s in load_scheme_kb().schemes if tags & set(s.need_tags)]


@router.get("/hotspots/{issue_id}", response_model=IssueDetail)
async def issue_detail(issue_id: str, lang: str = "en", store: RequestStore = Depends(get_dev_store),
                       chat=Depends(get_dev_chat), s: CivicSettings = Depends(get_civic_settings)) -> IssueDetail:
    iss = analyse(store.all(), load_dev_data(), _cfg(s)).get(issue_id)
    if iss is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    data, lang = load_dev_data(), normalize_code(lang)
    ex = await insight(iss, lang, chat, s.nvidia_nim_api_key.get_secret_value())
    prov = {"requests": data.requests_source}
    if iss.area_id:
        prov |= {"demographics": data.demographics_source, "infrastructure": data.infrastructure_source,
                 "investments": data.investments_source}
    return IssueDetail(
        **_summary(iss).model_dump(),
        components=[ComponentOut(**c.__dict__) for c in iss.priority.components], gap_reasons=iss.gap.reasons,
        population=iss.population, infrastructure_metric=iss.infra_metric, infrastructure_value=iss.infra_value,
        demographics=data.demographics_for(iss.area_id) if iss.area_id else None,
        infrastructure=data.infrastructure_for(iss.area_id) if iss.area_id else None,
        projects=iss.projects, themes=themes(iss), timeline=weekly(iss.requests, today()),
        relevant_schemes=_relevant_schemes(iss.category),
        insight=ExplanationOut(text=ex.text, lang=ex.lang, status=ex.status, model=ex.model),
        provenance=prov, disclaimer=DISCLAIMER,
    )


@router.post("/prioritize", response_model=IssueSummary)
async def prioritize(req: PrioritizeIn, store: RequestStore = Depends(get_dev_store),
                     s: CivicSettings = Depends(get_civic_settings)) -> IssueSummary:
    iss = analyse(store.all(), load_dev_data(), _cfg(s)).get(f"{req.area_id}__{req.category}")
    if iss is None:
        raise HTTPException(status_code=404, detail="No citizen reports for this area and category")
    return _summary(iss)


@router.get("/dashboard", response_model=Dashboard)
async def dashboard(state: str | None = None, district: str | None = None, category: str | None = None,
                    date_from: date | None = None, date_to: date | None = None,
                    store: RequestStore = Depends(get_dev_store), s: CivicSettings = Depends(get_civic_settings)) -> Dashboard:
    issues = list(_filtered(store, s, state, district, category, date_from, date_to).values())
    reqs = [r for i in issues for r in i.requests]
    names = {sc.id: sc.names["en"] for sc in load_scheme_kb().schemes}
    demand = Counter((sid, r.district) for r in reqs for sid in r.scheme_ids)
    return Dashboard(
        total_requests=len(reqs), active_issues=len(issues), hotspots=sum(i.hotspot for i in issues),
        high_priority_issues=sum(i.priority.level in ("critical", "high") for i in issues),
        by_category=Counter(CATEGORIES[r.category].labels["en"] for r in reqs).most_common(),
        by_district=Counter(f"{r.district}, {r.state.title()}" for r in reqs).most_common(),
        requests_over_time=weekly(reqs, today()),
        priority_distribution=dict(Counter(i.priority.level for i in issues)),
        gap_distribution=dict(Counter(i.gap.level for i in issues)),
        scheme_demand=[{"scheme_id": sid, "scheme": names.get(sid, sid), "district": d, "mentions": n} for (sid, d), n in demand.most_common(10)],
        top_hotspots=[_summary(i) for i in _sorted([i for i in issues if i.hotspot], "priority")[:10]],
        provenance=load_dev_data().requests_source, disclaimer=DISCLAIMER,
    )
