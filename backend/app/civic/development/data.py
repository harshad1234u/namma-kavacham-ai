"""Load and validate the development datasets. Missing values stay None and are never read as zero."""
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.civic.development.taxonomy import CATEGORIES

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "civic" / "development"
ProjectStatus = Literal["proposed", "planned", "approved", "ongoing", "completed", "delayed"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(_Strict):
    type: Literal["demo", "official"]
    name: str
    last_updated: date
    scope: str | None = None
    note: str | None = None
    url: str | None = None


class Area(_Strict):
    area_id: str
    state: str
    district: str
    area: str
    lat: float
    lng: float


class Demographics(_Strict):
    area_id: str
    population: int
    households: int | None = None
    children_percent: float | None = None
    elderly_percent: float | None = None
    literacy_rate: float | None = None


class Infrastructure(_Strict):
    area_id: str
    water_facilities: int | None = None
    road_km: int | None = None
    health_facilities: int | None = None
    schools: int | None = None
    sanitation_facilities: int | None = None
    transport_points: int | None = None
    police_points: int | None = None


class Project(_Strict):
    project_id: str
    name: str
    area_id: str
    category: str
    budget_inr: int
    status: ProjectStatus
    start_date: date
    expected_completion: date


class SeedRequest(_Strict):
    id: str
    text: str
    language: str
    category: str
    area_id: str
    urgency: Literal["low", "medium", "high"]
    source: Literal["text", "voice"]
    created_at: date


class StateList(_Strict):
    source: Provenance
    names: list[str]


class DevData(_Strict):
    states: StateList
    areas_source: Provenance
    areas: list[Area]
    demographics_source: Provenance
    demographics: list[Demographics]
    infrastructure_source: Provenance
    infrastructure: list[Infrastructure]
    investments_source: Provenance
    investments: list[Project]
    requests_source: Provenance
    seed_requests: list[SeedRequest]

    @model_validator(mode="after")
    def _consistent(self) -> "DevData":
        ids = {a.area_id for a in self.areas}
        if len(ids) != len(self.areas):
            raise ValueError("duplicate area id")
        for rows, name in ((self.demographics, "demographics"), (self.infrastructure, "infrastructure"),
                           (self.investments, "investments"), (self.seed_requests, "requests")):
            bad = [r.area_id for r in rows if r.area_id not in ids]
            if bad:
                raise ValueError(f"{name} reference unknown areas {bad[:3]}")
        cats = [x.category for x in (*self.investments, *self.seed_requests) if x.category not in CATEGORIES]
        if cats:
            raise ValueError(f"unknown categories {cats[:3]}")
        if len(self.states.names) != 36:
            raise ValueError("expected 28 States + 8 Union Territories")
        return self

    def area(self, area_id: str) -> Area | None:
        return next((a for a in self.areas if a.area_id == area_id), None)

    def demographics_for(self, area_id: str) -> Demographics | None:
        return next((d for d in self.demographics if d.area_id == area_id), None)

    def infrastructure_for(self, area_id: str) -> Infrastructure | None:
        return next((i for i in self.infrastructure if i.area_id == area_id), None)

    def projects_for(self, area_id: str, category: str) -> list[Project]:
        return [p for p in self.investments if p.area_id == area_id and p.category == category]


def _read(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def parse(areas: dict, demo: dict, infra: dict, inv: dict, reqs: dict) -> DevData:
    return DevData(states=areas["states_and_uts"], areas_source=areas["source"], areas=areas["areas"],
                   demographics_source=demo["source"], demographics=demo["profiles"],
                   infrastructure_source=infra["source"], infrastructure=infra["profiles"],
                   investments_source=inv["source"], investments=inv["projects"],
                   requests_source=reqs["source"], seed_requests=reqs["requests"])


@lru_cache
def load_dev_data() -> DevData:
    return parse(*(_read(n) for n in ("areas.json", "demographics.json", "infrastructure.json", "investments.json", "requests_seed.json")))
