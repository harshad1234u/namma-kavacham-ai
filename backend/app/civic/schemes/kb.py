import json
from functools import lru_cache
from pathlib import Path

from app.civic.schemes.schema import Scheme, SchemeKb

SCHEMES_DIR = Path(__file__).resolve().parents[2] / "data" / "civic" / "schemes"


def parse_kb(raw_schemes: list[dict]) -> SchemeKb:
    return SchemeKb.model_validate({"schema_version": "2.0", "schemes": raw_schemes})


@lru_cache
def load_scheme_kb() -> SchemeKb:
    """One JSON file per scheme. A malformed or unsourced entry fails start-up instead of being served."""
    raw = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCHEMES_DIR.glob("*.json"))]
    return parse_kb(raw)


def get_scheme(scheme_id: str) -> Scheme | None:
    return next((s for s in load_scheme_kb().schemes if s.id == scheme_id), None)
