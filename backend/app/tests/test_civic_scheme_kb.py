import copy
import json

import pytest
from pydantic import ValidationError

from app.civic.schemes.attributes import ATTRIBUTES, NEED_TAGS
from app.civic.schemes.kb import SCHEMES_DIR, load_scheme_kb, parse_kb
from app.civic.schemes.schema import host_of, is_official_host, norm


def _raw() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCHEMES_DIR.glob("*.json"))]


def test_kb_loads_and_file_names_match_ids():
    kb = load_scheme_kb()
    assert len(kb.schemes) >= 10
    assert sorted(p.stem for p in SCHEMES_DIR.glob("*.json")) == sorted(s.id for s in kb.schemes)


def test_every_statement_is_backed_by_a_recorded_quote_from_an_official_source():
    for s in load_scheme_kb().schemes:
        sources = {src.id: src for src in s.sources}
        for st in s.statements():
            src = sources[st.source_ref]
            assert is_official_host(host_of(src.url)), src.url
            assert any(norm(st.quote) in norm(q) for q in src.quotes), (s.id, st.quote[:40])


def test_every_scheme_has_an_official_channel_and_a_verification_date():
    for s in load_scheme_kb().schemes:
        assert s.last_verified and all(src.retrieved for src in s.sources)
        urls = [c.official_url for c in s.channels if c.official_url]
        assert urls, f"{s.id} has no official online channel"
        assert all(is_official_host(host_of(u)) for u in urls)


def test_amounts_appear_in_their_quote():
    """A benefit amount must be stated by the source, not computed or remembered."""
    for s in load_scheme_kb().schemes:
        for b in s.benefits:
            if b.amount_inr is not None:
                digits = norm(b.quote).replace(",", "")
                amount = b.amount_inr
                spoken = {100000: "1 lakh", 200000: "2 lakh", 1000000: "10 lakh", 120000: "1.20 lakh"}
                assert str(amount) in digits or spoken.get(amount, "#") in digits or (amount == 200000 and "two lacs" in digits), (s.id, amount)


def test_criteria_use_known_vocabulary():
    for s in load_scheme_kb().schemes:
        assert set(s.need_tags) <= set(NEED_TAGS)
        for c in s.eligibility:
            assert c.attribute == "other" or c.attribute in ATTRIBUTES


def _mutate(fn):
    raw = _raw()
    fn(raw[0])
    return raw


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda s: s["sources"][0].update(url="https://example.com/page"), id="non-government source"),
        pytest.param(lambda s: s["sources"][0].update(url="http://" + s["sources"][0]["url"][8:]), id="http source"),
        pytest.param(lambda s: s["description"].update(quote="A sentence the source never said."), id="quote not in source"),
        pytest.param(lambda s: s["description"].update(source_ref="missing"), id="unknown source_ref"),
        pytest.param(lambda s: s["sources"][0].update(quotes=[]), id="source without quotes"),
        pytest.param(lambda s: s.update(need_tags=["free_money"]), id="unknown need tag"),
        pytest.param(lambda s: s["eligibility"].append({**copy.deepcopy(s["eligibility"][0]), "id": "x", "attribute": "shoe_size", "operator": "eq", "value": 9}), id="unknown attribute"),
        pytest.param(lambda s: s["eligibility"].append({**copy.deepcopy(s["eligibility"][0]), "id": "y", "attribute": "occupation", "operator": "eq", "value": "astronaut"}), id="enum value outside vocabulary"),
        pytest.param(lambda s: s["channels"].append({"type": "online_portal", "label": {"en": "x"}, "official_url": "https://apply-now.gov.in/", "source_ref": s["sources"][0]["id"]}), id="channel off the scheme's domains"),
        pytest.param(lambda s: s["names"].update(xx="?"), id="unknown language code"),
        pytest.param(lambda s: s["names"].pop("en"), id="missing English"),
        pytest.param(lambda s: s.update(level="state"), id="state scheme without state"),
        pytest.param(lambda s: s.update(unexpected=True), id="extra field"),
    ],
)
def test_malformed_scheme_is_rejected(mutation):
    with pytest.raises(ValidationError):
        parse_kb(_mutate(mutation))


def test_duplicate_alias_across_schemes_is_rejected():
    raw = _raw()
    raw[1]["aliases"] = [*raw[1]["aliases"], raw[0]["abbreviations"][0]]
    with pytest.raises(ValidationError):
        parse_kb(raw)
