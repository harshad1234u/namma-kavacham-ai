from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.civic.development.data import Demographics, Infrastructure, Project, Provenance
from app.civic.schemes.models import ExplanationOut


class RequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)
    lang: str = "en"
    state: str = Field(max_length=60)
    district: str = Field(min_length=2, max_length=60)
    area_id: str | None = Field(default=None, max_length=60)  # a demo locality, when the citizen picked one
    locality: str | None = Field(default=None, max_length=80)
    pincode: str | None = Field(default=None, pattern=r"^[1-9][0-9]{5}$")  # validated, not stored
    category: str | None = None  # citizen's choice overrides detection
    urgency: Literal["low", "medium", "high"] | None = None
    source: Literal["text", "voice"] = "text"
    consent: Literal[True]  # the citizen agreed to aggregate, anonymised use of this report
    ai_consent: bool = False


class ClassifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)
    lang: str = "en"
    ai_consent: bool = False


class ClassificationOut(BaseModel):
    category: str | None
    category_label: str | None
    issue_type: str | None
    urgency: str
    confidence: str
    reason: str
    language: str
    method: str
    ai_note: str | None


class RequestReceipt(BaseModel):
    id: str
    category: str
    category_label: str
    issue_type: str | None
    state: str
    district: str
    locality: str | None
    urgency: str
    created_at: date
    statuses: list[str]
    issue_id: str
    photo_attached: bool
    classification: ClassificationOut | None = None
    note: str = "Your report is aggregated anonymously with others for analysis. It has not been sent to any government office."


class ComponentOut(BaseModel):
    name: str
    weight: float
    assessed: bool
    value: float | None
    points: float | None
    note: str


class IssueSummary(BaseModel):
    id: str
    category: str
    category_label: str
    state: str
    district: str
    locality: str | None
    lat: float | None
    lng: float | None
    report_count: int
    priority_score: int | None
    priority_level: str
    gap_level: str
    hotspot: bool
    high_urgency_reports: int
    data_completeness: float
    demo_data: bool


class IssueDetail(IssueSummary):
    components: list[ComponentOut]
    gap_reasons: list[str]
    population: int | None
    infrastructure_metric: str | None
    infrastructure_value: int | None
    demographics: Demographics | None
    infrastructure: Infrastructure | None
    projects: list[Project]
    themes: list[tuple[str, int]]
    timeline: list[tuple[str, int]]
    relevant_schemes: list[dict[str, str]]
    insight: ExplanationOut
    provenance: dict[str, Provenance]
    disclaimer: str


class Dashboard(BaseModel):
    total_requests: int
    active_issues: int
    hotspots: int
    high_priority_issues: int
    by_category: list[tuple[str, int]]
    by_district: list[tuple[str, int]]
    requests_over_time: list[tuple[str, int]]
    priority_distribution: dict[str, int]
    gap_distribution: dict[str, int]
    scheme_demand: list[dict[str, Any]]
    top_hotspots: list[IssueSummary]
    provenance: Provenance
    disclaimer: str


class PrioritizeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area_id: str
    category: str
