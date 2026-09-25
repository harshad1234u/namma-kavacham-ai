import copy
import json

import pytest
from pydantic import ValidationError

from app.services.government.kb import KB_PATH, REQUIRED_CATEGORIES, load_kb, parse_kb

RAW = json.loads(KB_PATH.read_text(encoding="utf-8"))
OFFICIAL_SOURCE_HOSTS = ("pib.gov.in", "incometax.gov.in", "pmkisan.gov.in", "cybercrime.gov.in", "uidai.gov.in",
                         "scholarships.gov.in")


def test_kb_loads_and_covers_all_five_categories():
    kb = load_kb()
    assert {e.category for e in kb.entries} == REQUIRED_CATEGORIES


def test_every_source_is_an_official_https_page_with_retrieval_date():
    for entry in load_kb().entries:
        for src in entry.sources:
            assert src.url.startswith("https://")
            assert any(host in src.url for host in OFFICIAL_SOURCE_HOSTS), src.url
            assert src.retrieved


def test_every_fact_cites_a_quoted_source():
    kb = load_kb()
    for entry in kb.entries:
        for fact in entry.facts:
            assert kb.source(entry, fact.source_ref).quotes, f"{fact.id} cites a source without quotes"


def test_official_domains_are_government_reserved():
    for entry in load_kb().entries:
        assert all(d.endswith((".gov.in", ".nic.in")) for d in entry.official_domains)


def _mutated(fn) -> str:
    data = copy.deepcopy(RAW)
    fn(data)
    return json.dumps(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(entries=[x for x in d["entries"] if x["category"] != "passport"]),  # drops a required category
        lambda d: d["entries"][0]["facts"][0].update(source_ref="missing_source"),
        lambda d: d["entries"][0].update(official_domains=["uidai-help.com"]),
        lambda d: d["entries"][0].update(official_urls=["http://uidai.gov.in/"]),
        lambda d: d["entries"][0].update(unexpected_field=True),
        lambda d: d["entries"][1]["facts"][0].pop("expected_amount_inr"),
        lambda d: d["entries"].append(copy.deepcopy(d["entries"][0])),  # duplicate id
    ],
)
def test_malformed_kb_is_rejected(mutation):
    with pytest.raises(ValidationError):
        parse_kb(_mutated(mutation))
