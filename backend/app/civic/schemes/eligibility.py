"""Compare a citizen's answers with a scheme's documented criteria. Never decides on missing information."""
from dataclasses import dataclass
from typing import Any, Literal

from app.civic.schemes.attributes import ATTRIBUTES
from app.civic.schemes.schema import Criterion, Scheme

CriterionOutcome = Literal["satisfied", "not_satisfied", "unknown", "not_machine_checkable"]
Overall = Literal["eligible_on_available_info", "possibly_eligible", "not_enough_information", "criteria_not_satisfied"]


class AnswerError(ValueError):
    pass


def validate_answers(answers: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for name, value in answers.items():
        attr = ATTRIBUTES.get(name)
        if attr is None:
            raise AnswerError(f"unknown attribute {name!r}")
        if value is None:
            continue  # "I don't know" is allowed and stays unknown
        if attr.type == "bool" and not isinstance(value, bool):
            raise AnswerError(f"{name} must be true/false")
        if attr.type == "int" and (isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 10**9):
            raise AnswerError(f"{name} must be a non-negative whole number")
        if attr.type == "enum" and value not in attr.values:
            raise AnswerError(f"{name} must be one of {list(attr.values)}")
        clean[name] = value
    return clean


def _condition_holds(c: Criterion, v: Any) -> bool:
    op, x = c.operator, c.value
    return {
        "eq": lambda: v == x,
        "in": lambda: v in x,
        "not_in": lambda: v not in x,
        "gte": lambda: v >= x,
        "lte": lambda: v <= x,
        "between": lambda: x[0] <= v <= x[1],
        "is_true": lambda: v is True,
        "is_false": lambda: v is False,
    }[op]()


def check_criterion(c: Criterion, answers: dict[str, Any]) -> CriterionOutcome:
    if c.attribute == "other":
        return "not_machine_checkable"
    if c.attribute not in answers:
        return "unknown"
    holds = _condition_holds(c, answers[c.attribute])
    # Inclusion: condition must hold. Exclusion: the condition describes who is excluded.
    return "satisfied" if holds == (c.kind == "inclusion") else "not_satisfied"


@dataclass(frozen=True)
class EligibilityOutcome:
    overall: Overall
    per_criterion: list[tuple[Criterion, CriterionOutcome]]
    missing_attributes: list[str]


def evaluate(scheme: Scheme, answers: dict[str, Any]) -> EligibilityOutcome:
    per = [(c, check_criterion(c, answers)) for c in scheme.eligibility]
    outcomes = [o for _, o in per]
    missing = sorted({c.attribute for c, o in per if o == "unknown"})
    if "not_satisfied" in outcomes:
        overall: Overall = "criteria_not_satisfied"
    elif "unknown" in outcomes or "satisfied" not in outcomes:
        overall = "not_enough_information"
    elif "not_machine_checkable" in outcomes or not scheme.criteria_complete:
        overall = "possibly_eligible"
    else:
        overall = "eligible_on_available_info"
    return EligibilityOutcome(overall, per, missing)


def question_attributes(scheme: Scheme) -> list[str]:
    seen: list[str] = []
    for c in scheme.eligibility:
        if c.attribute != "other" and c.attribute not in seen:
            seen.append(c.attribute)
    return seen
