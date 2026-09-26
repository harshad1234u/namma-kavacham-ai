import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.civic.development import data as data_mod
from app.civic.development.classifier import classify, classify_deterministic, detect_language
from app.civic.development.data import load_dev_data, parse
from app.civic.development.engine import PriorityConfig, analyse, compute_priority, level_for
from app.civic.development.router import get_dev_chat, get_dev_store
from app.civic.development.store import RequestStore
from app.civic.nim.provider import NIMError
from app.civic.settings import CivicSettings
from app.main import app

CFG = PriorityConfig.from_settings(CivicSettings(_env_file=None))
WATER_HOTSPOT = "tiruchirappalli-a__water"


@pytest.fixture
def store():
    s = RequestStore()
    s.seed()
    return s


@pytest.fixture
def issues(store):
    return analyse(store.all(), load_dev_data(), CFG)


# ---------- datasets & provenance ----------
def test_datasets_are_labelled_demo_and_states_are_official():
    d = load_dev_data()
    for src in (d.areas_source, d.demographics_source, d.infrastructure_source, d.investments_source, d.requests_source):
        assert src.type == "demo" and "not census" in src.note.lower()
    assert d.states.source.type == "official" and d.states.source.url == "https://dbtbharat.gov.in/"
    assert len(d.states.names) == 36 and "TAMIL NADU" in d.states.names
    assert all(p.name.startswith("Demo:") for p in d.investments)


def test_dataset_integrity_is_enforced():
    raw = [json.loads((data_mod.DATA_DIR / n).read_text(encoding="utf-8")) for n in
           ("areas.json", "demographics.json", "infrastructure.json", "investments.json", "requests_seed.json")]
    bad = json.loads(json.dumps(raw))
    bad[1]["profiles"][0]["area_id"] = "atlantis"
    with pytest.raises(ValidationError):
        parse(*bad)
    bad = json.loads(json.dumps(raw))
    bad[0]["source"]["type"] = "official-ish"
    with pytest.raises(ValidationError):
        parse(*bad)


# ---------- classification ----------
@pytest.mark.parametrize("text,category,lang", [
    ("Our village does not have proper drinking water facilities. We have to travel 4 km every day.", "water", "en"),
    ("எங்கள் பகுதியில் குடிநீர் வசதி சரியாக இல்லை. தினமும் 4 கிலோமீட்டர் செல்ல வேண்டியுள்ளது.", "water", "ta"),
    ("Enga area la water facility sari illa.", "water", "romanised_indic"),
    ("सड़क में बड़े गड्ढे हैं, बारिश में पानी भर जाता है।", "roads", "devanagari"),
    ("Road near our government school is completely damaged and buses cannot enter during rain.", "roads", "en"),
])
def test_deterministic_classification(text, category, lang):
    c = classify_deterministic(text)
    assert c.category == category and c.language == lang and c.method == "deterministic" and c.reason


def test_urgency_and_issue_type_are_extracted():
    c = classify_deterministic("Tap water is dirty and children are falling sick")
    assert c.category == "water" and c.issue_type == "contamination" and c.urgency == "high"


def test_unclear_text_is_unclassified_not_guessed():
    c = classify_deterministic("Please help us with our problem")
    assert c.category is None and c.confidence == "low"


def test_citizen_choice_overrides_detection():
    c = classify_deterministic("water is not coming", user_category="roads", user_urgency="low")
    assert c.category == "roads" and c.urgency == "low" and c.method == "user_selected"


def test_language_detection_is_honest_about_shared_scripts():
    assert detect_language("আমাদের গ্রামে জল নেই") == "bengali"  # Bengali script is shared with Assamese
    assert detect_language("మా గ్రామంలో నీరు లేదు") == "te"


class FakeSarvam:
    model = "sarvamai/sarvam-m"

    def __init__(self, reply=None, fail=False):
        self.reply, self.fail, self.prompts = reply, fail, []

    async def chat_json(self, system, user, schema, max_tokens=1200):
        self.prompts.append(user)
        if self.fail:
            raise NIMError("timeout")
        return self.reply


async def test_ai_classification_only_accepts_the_closed_taxonomy():
    telugu = "మా గ్రామంలో తాగునీరు లేదు, ఫోన్ 9876543210"
    ok = await classify(telugu, FakeSarvam({"category": "water", "issue_type": "no_supply", "urgency": "high", "reason": "drinking water"}))
    assert ok.category == "water" and ok.method == "ai_assisted"
    bad = await classify(telugu, FakeSarvam({"category": "space_programme", "issue_type": "x", "urgency": "extreme", "reason": ""}))
    assert bad.category is None and bad.ai_note == "ai_answer_outside_taxonomy"
    chat = FakeSarvam(fail=True)
    down = await classify(telugu, chat)
    assert down.method == "deterministic" and down.ai_note == "timeout"
    assert "9876543210" not in chat.prompts[0]


async def test_ai_is_not_called_when_keywords_suffice_or_citizen_chose():
    chat = FakeSarvam({"category": "roads", "issue_type": None, "urgency": "low", "reason": ""})
    assert (await classify("no drinking water in our area", chat)).category == "water"
    assert (await classify("మా గ్రామంలో సమస్య", chat, user_category="housing")).category == "housing"
    assert chat.prompts == []


# ---------- priority engine ----------
@pytest.mark.parametrize("score,level", [(100, "critical"), (80, "critical"), (79, "high"), (60, "high"), (59, "medium"),
                                         (40, "medium"), (39, "lower"), (0, "lower"), (None, "unable_to_assess")])
def test_priority_thresholds(score, level):
    assert level_for(score) == level


def test_headline_demo_hotspot(issues):
    iss = issues[WATER_HOTSPOT]
    assert iss.hotspot and iss.priority.level == "critical" and iss.gap.level == "high"
    assert iss.priority.score == round(sum(c.points for c in iss.priority.components))
    assert iss.priority.data_completeness == 1.0
    assert "No matching project in the available investment dataset." in iss.gap.reasons


def test_priority_is_deterministic(store):
    a = analyse(store.all(), load_dev_data(), CFG)
    b = analyse(list(reversed(store.all())), load_dev_data(), CFG)
    assert {k: v.priority.score for k, v in a.items()} == {k: v.priority.score for k, v in b.items()}


def test_weights_are_configurable(issues):
    iss = issues[WATER_HOTSPOT]
    only_demand = replace(CFG, weights={**{k: 0.0001 for k in CFG.weights}, "citizen_demand": 100})
    p = compute_priority(iss, only_demand)
    demand = p.components[0]
    assert abs(demand.points - 100 * demand.value) < 0.1  # all weight on demand


def test_missing_population_is_reported_not_scored_low(issues):
    iss = issues["madurai-c__digital_connectivity"]  # demo area without demographics; category has no infra metric
    comps = {c.name: c for c in iss.priority.components}
    assert not comps["population_impact"].assessed
    assert comps["population_impact"].note == "Population impact cannot be assessed from available data."
    assert comps["population_impact"].points is None and iss.priority.data_completeness < 1


def test_missing_infrastructure_is_unavailable_not_absent(issues):
    iss = issues["gaya-c__housing"]
    comps = {c.name: c for c in iss.priority.components}
    assert not comps["infrastructure_gap"].assessed and "No infrastructure" not in iss.gap.reasons[0][:15]


def test_place_outside_demo_data_is_unable_to_assess(store):
    from app.civic.development.store import StoredRequest
    from datetime import date

    for i in range(3):
        store.add(StoredRequest(f"REQ-X{i}", "no water", "en", "water", "no_supply", None, "ASSAM", "Kamrup", None, "high", "text", date(2026, 9, 1)))
    iss = analyse(store.all(), load_dev_data(), CFG)["assam--kamrup__water"]
    assert iss.priority.level == "unable_to_assess" and iss.priority.score is None
    notes = " ".join(c.note for c in iss.priority.components)
    assert "No matching investment information is available in the current dataset." in notes
    assert "Infrastructure data unavailable." in notes


def test_investment_status_reduces_gap(issues):
    delayed = {c.name: c for c in issues["madurai-a__healthcare"].priority.components}["investment_gap"]
    assert delayed.value == 0.7 and "delayed" in delayed.note


# ---------- API ----------
@pytest.fixture
def api(client, store):
    app.dependency_overrides[get_dev_store] = lambda: store
    app.dependency_overrides[get_dev_chat] = lambda: None
    yield client
    app.dependency_overrides.pop(get_dev_store, None)
    app.dependency_overrides.pop(get_dev_chat, None)


def _submit(api, photo=None, **kw):
    payload = {"text": "Water is not coming to our street for a week, children are sick", "state": "TAMIL NADU",
               "district": "Tiruchirappalli", "area_id": "tiruchirappalli-a", "consent": True, **kw}
    files = {"photo": photo} if photo else None
    return api.post("/v1/development/requests", data={"payload": json.dumps(payload)}, files=files)


def test_submit_request_is_aggregated_and_never_claims_government_action(api):
    r = _submit(api)
    body = r.json()
    assert r.status_code == 200 and body["category"] == "water" and body["issue_id"] == WATER_HOTSPOT
    assert body["statuses"] == ["received", "aggregated", "priority_assessed", "included_in_insight"]
    assert "not been sent to any government office" in body["note"]
    mine = api.get(f"/v1/development/requests?ids={body['id']}").json()
    assert [m["id"] for m in mine] == [body["id"]]
    assert api.get("/v1/development/requests?ids=DEMO-0001").json() == []  # cannot list others' reports


def test_submit_validation(api):
    assert _submit(api, consent=False).status_code == 422
    assert _submit(api, state="ATLANTIS").status_code == 422
    assert _submit(api, area_id="pune-a").status_code == 422  # locality not in the given district
    assert _submit(api, pincode="12345").status_code == 422
    assert _submit(api, text="Please help", area_id=None).status_code == 422  # no category detected, none chosen
    ok = _submit(api, text="Please help", category="housing", area_id=None, district="Kamrup", state="ASSAM")
    assert ok.status_code == 200 and ok.json()["statuses"] == ["received", "aggregated"]


def test_photo_is_checked_and_discarded(api):
    assert _submit(api, photo=("p.gif", b"GIF89a", "image/gif")).status_code == 415
    assert _submit(api, photo=("p.jpg", b"\xff" * (5 * 1024 * 1024 + 1), "image/jpeg")).status_code == 413
    ok = _submit(api, photo=("p.jpg", b"\xff\xd8\xff" + b"0" * 100, "image/jpeg"))
    assert ok.status_code == 200 and ok.json()["photo_attached"] is True


def test_public_endpoints_never_expose_citizen_text(api):
    _submit(api, text="Secret personal story about my neighbour Ravi at 12 Temple Street, water leak")
    blobs = [api.get(u).text for u in ("/v1/development/dashboard", "/v1/development/issues", "/v1/development/hotspots",
                                       f"/v1/development/hotspots/{WATER_HOTSPOT}")]
    assert all("Ravi" not in b and "Temple Street" not in b and "Secret" not in b for b in blobs)


def test_hotspots_filters_and_detail(api):
    hs = api.get("/v1/development/hotspots").json()
    assert hs[0]["id"] == WATER_HOTSPOT and all(h["hotspot"] for h in hs)
    assert all(h["category"] == "roads" for h in api.get("/v1/development/issues?category=roads").json())
    assert all(h["district"] == "Gaya" for h in api.get("/v1/development/issues?district=Gaya").json())
    high = api.get("/v1/development/issues?min_level=high").json()
    assert high and all(h["priority_level"] in ("high", "critical") for h in high)
    assert api.get("/v1/development/issues?min_level=urgent").status_code == 422
    d = api.get(f"/v1/development/hotspots/{WATER_HOTSPOT}").json()
    assert d["insight"]["status"] == "template" and "87/100" in d["insight"]["text"]
    assert d["provenance"]["demographics"]["type"] == "demo" and d["projects"] == []
    assert len(d["timeline"]) == 13 and d["themes"][0][1] > 0
    assert api.get("/v1/development/hotspots/nowhere__water").status_code == 404


def test_dashboard_and_meta(api):
    d = api.get("/v1/development/dashboard").json()
    assert d["total_requests"] >= 535 and d["hotspots"] >= 4 and d["provenance"]["type"] == "demo"
    assert "not a government decision" in d["disclaimer"]
    m = api.get("/v1/development/meta").json()
    assert len(m["categories"]) == 12 and len(m["states_and_uts"]) == 36 and m["weights"]["citizen_demand"] == 30
    assert api.get("/v1/development/data/investments").json()["source"]["type"] == "demo"
    assert api.get("/v1/development/data/secrets").status_code == 404
