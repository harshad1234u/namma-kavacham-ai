"""Deterministic Development Intelligence engine: aggregate -> gap -> priority -> hotspots -> analytics.

Every number here is computed from the stored requests and the datasets; nothing comes from an LLM.
A component with missing data is excluded (and reported), never scored as zero or as "no need".
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from app.civic.development.data import DevData, Project
from app.civic.development.store import StoredRequest
from app.civic.development.taxonomy import CATEGORIES
from app.civic.settings import CivicSettings

Level = Literal["critical", "high", "medium", "lower", "unable_to_assess"]
GapLevel = Literal["high", "medium", "low", "unable_to_assess"]
LEVEL_ORDER = {"critical": 4, "high": 3, "medium": 2, "lower": 1, "unable_to_assess": 0}
# How much an existing project already addresses the need (1.0 = nothing planned).
INVESTMENT_GAP_BY_STATUS = {"proposed": 0.8, "delayed": 0.7, "planned": 0.6, "approved": 0.5, "ongoing": 0.3, "completed": 0.2}
UNAVAILABLE = {
    "population": "Population impact cannot be assessed from available data.",
    "infrastructure": "Infrastructure data unavailable.",
    "investment": "No matching investment information is available in the current dataset.",
}


@dataclass(frozen=True)
class PriorityConfig:
    weights: dict[str, float]
    demand_saturation: int
    population_saturation: int
    hotspot_min_reports: int
    min_completeness: float

    @classmethod
    def from_settings(cls, s: CivicSettings) -> "PriorityConfig":
        return cls({"citizen_demand": s.dev_weight_demand, "population_impact": s.dev_weight_population,
                    "infrastructure_gap": s.dev_weight_infrastructure_gap, "urgency": s.dev_weight_urgency,
                    "investment_gap": s.dev_weight_investment_gap},
                   s.dev_demand_saturation_reports, s.dev_population_saturation, s.dev_hotspot_min_reports,
                   s.dev_min_data_completeness)


@dataclass(frozen=True)
class Component:
    name: str
    weight: float
    assessed: bool
    value: float | None  # 0..1
    points: float | None  # contribution on the 0-100 scale
    note: str


@dataclass(frozen=True)
class Priority:
    score: int | None
    level: Level
    components: list[Component]
    data_completeness: float


@dataclass(frozen=True)
class Gap:
    level: GapLevel
    reasons: list[str]


@dataclass
class Issue:
    id: str
    category: str
    area_id: str | None
    state: str
    district: str
    locality: str | None
    lat: float | None
    lng: float | None
    requests: list[StoredRequest]
    population: int | None = None
    infra_metric: str | None = None
    infra_value: int | None = None
    projects: list[Project] = field(default_factory=list)
    investment_covered: bool = False
    gap: Gap | None = None
    priority: Priority | None = None
    hotspot: bool = False

    @property
    def report_count(self) -> int:
        return len(self.requests)


def level_for(score: int | None) -> Level:
    if score is None:
        return "unable_to_assess"
    return "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 40 else "lower"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def issue_key(r: StoredRequest) -> str:
    place = r.area_id or f"{_slug(r.state)}--{_slug(r.district)}"
    return f"{place}__{r.category}"


def aggregate(requests: list[StoredRequest], data: DevData) -> dict[str, Issue]:
    issues: dict[str, Issue] = {}
    for r in requests:
        key = issue_key(r)
        if key not in issues:
            area = data.area(r.area_id) if r.area_id else None
            issues[key] = Issue(key, r.category, r.area_id, r.state, r.district, area.area if area else r.locality,
                                area.lat if area else None, area.lng if area else None, [])
        issues[key].requests.append(r)
    for iss in issues.values():
        if iss.area_id:
            demo = data.demographics_for(iss.area_id)
            iss.population = demo.population if demo else None
            cat = CATEGORIES[iss.category]
            iss.infra_metric = cat.infra_metric
            infra = data.infrastructure_for(iss.area_id)
            iss.infra_value = getattr(infra, cat.infra_metric) if infra and cat.infra_metric else None
            iss.projects = data.projects_for(iss.area_id, iss.category)
            iss.investment_covered = True  # the investment dataset covers every demo area
    return issues


def _components(iss: Issue, cfg: PriorityConfig) -> list[Component]:
    w, n = cfg.weights, iss.report_count
    comps = []
    d = min(1.0, math.log1p(n) / math.log1p(cfg.demand_saturation))
    comps.append(Component("citizen_demand", w["citizen_demand"], True, d, None, f"{n} citizen reports."))
    if iss.population is not None:
        p = min(1.0, iss.population / cfg.population_saturation)
        comps.append(Component("population_impact", w["population_impact"], True, p, None,
                               f"Area population {iss.population:,} (upper bound of people affected)."))
    else:
        comps.append(Component("population_impact", w["population_impact"], False, None, None, UNAVAILABLE["population"]))
    cat = CATEGORIES[iss.category]
    if cat.infra_metric is None:
        comps.append(Component("infrastructure_gap", w["infrastructure_gap"], False, None, None,
                               "No infrastructure indicator is defined for this category in the dataset."))
    elif iss.infra_value is None or iss.population is None:
        comps.append(Component("infrastructure_gap", w["infrastructure_gap"], False, None, None, UNAVAILABLE["infrastructure"]))
    else:
        per10k = iss.infra_value / (iss.population / 10_000)
        g = max(0.0, min(1.0, 1 - per10k / cat.benchmark_per_10k))
        comps.append(Component("infrastructure_gap", w["infrastructure_gap"], True, g, None,
                               f"{iss.infra_value} {cat.infra_metric.replace('_', ' ')} = {per10k:.2f} per 10,000 people "
                               f"(analytical benchmark {cat.benchmark_per_10k}, not an official norm)."))
    u = Counter(r.urgency for r in iss.requests)
    comps.append(Component("urgency", w["urgency"], True, (u["high"] + 0.5 * u["medium"]) / n,
                           None, f"{u['high']} high, {u['medium']} medium, {u['low']} low urgency reports."))
    if not iss.investment_covered:
        comps.append(Component("investment_gap", w["investment_gap"], False, None, None, UNAVAILABLE["investment"]))
    elif not iss.projects:
        comps.append(Component("investment_gap", w["investment_gap"], True, 1.0, None,
                               "No matching project in the available investment dataset."))
    else:
        best = min(iss.projects, key=lambda p: INVESTMENT_GAP_BY_STATUS[p.status])
        comps.append(Component("investment_gap", w["investment_gap"], True, INVESTMENT_GAP_BY_STATUS[best.status], None,
                               f"Matching project {best.project_id} is {best.status}."))
    return comps


def compute_priority(iss: Issue, cfg: PriorityConfig) -> Priority:
    comps = _components(iss, cfg)
    total = sum(c.weight for c in comps)
    assessed_w = sum(c.weight for c in comps if c.assessed)
    completeness = assessed_w / total if total else 0.0
    # Points are shown on the 0-100 scale of the weights that could be assessed.
    scaled = [Component(c.name, c.weight, c.assessed, c.value,
                        round(100 * c.weight * c.value / assessed_w, 1) if c.assessed and assessed_w else None, c.note) for c in comps]
    if completeness < cfg.min_completeness:
        return Priority(None, "unable_to_assess", scaled, round(completeness, 2))
    score = round(sum(c.points for c in scaled if c.points is not None))
    return Priority(score, level_for(score), scaled, round(completeness, 2))


def compute_gap(iss: Issue, pr: Priority) -> Gap:
    comp = {c.name: c for c in pr.components}
    reasons, dims = [], []
    demand = comp["citizen_demand"]
    if iss.population:
        rate = iss.report_count / (iss.population / 10_000)
        dims.append(min(1.0, rate / 5))
        if rate >= 3:
            reasons.append(f"High citizen demand: {iss.report_count} reports ({rate:.1f} per 10,000 people).")
    elif demand.value and demand.value >= 0.6:
        reasons.append(f"High citizen demand: {iss.report_count} reports.")
    if iss.population and iss.population >= 100_000:
        reasons.append(f"Large affected population (area population {iss.population:,}).")
    for name in ("infrastructure_gap", "investment_gap"):
        c = comp[name]
        if c.assessed:
            dims.append(c.value)
            if c.value >= 0.4:
                reasons.append(("Limited infrastructure: " if name == "infrastructure_gap" else "") + c.note)
        else:
            reasons.append(c.note)
    if not iss.population:
        reasons.append(UNAVAILABLE["population"])
    if len(dims) < 2:
        return Gap("unable_to_assess", reasons)
    m = sum(dims) / len(dims)
    return Gap("high" if m >= 0.66 else "medium" if m >= 0.33 else "low", reasons)


def analyse(requests: list[StoredRequest], data: DevData, cfg: PriorityConfig) -> dict[str, Issue]:
    issues = aggregate(requests, data)
    for iss in issues.values():
        iss.priority = compute_priority(iss, cfg)
        iss.gap = compute_gap(iss, iss.priority)
        iss.hotspot = iss.report_count >= cfg.hotspot_min_reports and iss.priority.level in ("critical", "high")
    return issues


def themes(iss: Issue) -> list[tuple[str, int]]:
    """Main complaint themes as issue-type labels and counts (never citizens' text)."""
    labels = {i.id: i.label for i in CATEGORIES[iss.category].issues}
    c = Counter(labels.get(r.issue_type or "", "Other / unspecified") for r in iss.requests)
    return c.most_common()


def weekly(requests: list[StoredRequest], today: date, weeks: int = 13) -> list[tuple[str, int]]:
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    counts = Counter((r.created_at - start).days // 7 for r in requests if r.created_at >= start)
    return [((start + timedelta(weeks=i)).isoformat(), counts.get(i, 0)) for i in range(weeks)]


def request_statuses(r: StoredRequest, issues: dict[str, Issue]) -> list[str]:
    """Transparent progress; never implies a government decision."""
    iss = issues.get(issue_key(r))
    out = ["received"]
    if iss:
        out.append("aggregated")
        if iss.priority and iss.priority.level != "unable_to_assess":
            out.append("priority_assessed")
        if iss.hotspot:
            out.append("included_in_insight")
    return out
