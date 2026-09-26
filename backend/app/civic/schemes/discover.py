"""Suggest verified schemes that may be relevant to a citizen's stated needs and circumstances."""
from dataclasses import dataclass
from typing import Any

from app.civic.schemes.eligibility import EligibilityOutcome, evaluate
from app.civic.schemes.kb import load_scheme_kb
from app.civic.schemes.schema import Scheme

_ORDER = {"eligible_on_available_info": 0, "possibly_eligible": 1, "not_enough_information": 2, "criteria_not_satisfied": 3}


@dataclass(frozen=True)
class Suggestion:
    scheme: Scheme
    matched_need_tags: list[str]
    matched_profile: list[str]  # attributes whose documented criterion the stated profile meets
    eligibility: EligibilityOutcome


def discover(need_tags: list[str], profile: dict[str, Any], limit: int = 8) -> list[Suggestion]:
    out: list[Suggestion] = []
    for s in load_scheme_kb().schemes:
        tags = sorted(set(need_tags) & set(s.need_tags))
        elig = evaluate(s, profile)
        # A profile fact only makes a scheme relevant when it meets a positive criterion (e.g. occupation = street vendor).
        prof = sorted({c.attribute for c, o in elig.per_criterion if o == "satisfied" and c.kind == "inclusion" and c.attribute in ("occupation", "gender")})
        if tags or prof:
            out.append(Suggestion(s, tags, prof, elig))
    out.sort(key=lambda x: (_ORDER[x.eligibility.overall] == 3, -(2 * len(x.matched_need_tags) + len(x.matched_profile)), _ORDER[x.eligibility.overall], x.scheme.id))
    return out[:limit]
