"""Phase 5 scheme-scam indicators: personal UPI payment, WhatsApp/Telegram application, fee for a free benefit.

Each is a medium-confidence indicator, never proof on its own.
"""

import pytest

from app.services.message_rules import run_message_rules
from app.tests.conftest import make_payload

NEW = {"personal_upi_payment", "unofficial_channel_application", "fee_for_free_benefit"}


def new_signals(text: str) -> set[str]:
    return {h.signal for h in run_message_rules(text)} & NEW


@pytest.mark.parametrize("text", [
    "PM Kisan benefit pending. Pay Rs 50 processing fee to pmkisan.help@ybl",
    "Your scholarship is approved. Send the registration amount on GPay to 98765 43210",
    "அரசு உதவித்தொகை பெற கட்டணம் ரூ.100 ஐ ramesh@okaxis க்கு அனுப்பவும்",
    "subsidy release aaganum na 99 rupees fee ah 9876543210 phonepe la anuppunga",
])
def test_personal_upi_payment_detected(text):
    assert new_signals(text) == {"personal_upi_payment"}


@pytest.mark.parametrize("text", [
    "Hi da, send your dinner share to ramesh@okaxis",  # a UPI ID between friends is ordinary
    "Do not pay any fee to kisan@ybl, it is not from the government",
    "Pay the fee only on the official portal. Do not send money on GPay to 9876543210",
    "Contact support@sbi.co.in for your pension query",  # an email, not a UPI ID
])
def test_personal_upi_payment_not_flagged(text):
    assert "personal_upi_payment" not in new_signals(text)


@pytest.mark.parametrize("text", [
    "Apply for the PM Awas scheme through WhatsApp: wa.me/919876543210",
    "Register for the laptop scheme on Telegram channel t.me/govtlaptop",
    "Join our Telegram group to get the scholarship amount",
    "வாட்ஸ்அப் மூலம் விண்ணப்பிக்கவும்",
    "Magalir urimai thogai ku whatsapp la apply pannunga",
])
def test_unofficial_channel_detected(text):
    assert "unofficial_channel_application" in new_signals(text)


@pytest.mark.parametrize("text", [
    "Do not apply through WhatsApp; use the official portal",
    "Applications are not accepted on WhatsApp or Telegram.",
    "வாட்ஸ்அப் மூலம் விண்ணப்பங்கள் ஏற்கப்படாது",
    "I applied for the scholarship, will send you the screenshot on WhatsApp",
    "Join our WhatsApp group for the college reunion",
])
def test_unofficial_channel_not_flagged(text):
    assert "unofficial_channel_application" not in new_signals(text)


@pytest.mark.parametrize("text", [
    "Get a free laptop under the government scheme. Pay Rs 99 registration fee now",
    "Free gas cylinder for all families! Registration charge Rs 49 only",
    "இலவச மடிக்கணினி பெற பதிவுக் கட்டணம் ரூ.100 செலுத்தவும்",
    "free laptop scheme, registration fees kattunga 200",
    "Solar pump is free of cost. Pay ₹500 processing fee to release it",
])
def test_fee_for_free_benefit_detected(text):
    assert "fee_for_free_benefit" in new_signals(text)


@pytest.mark.parametrize("text", [
    "Free laptop scheme for students: apply on the official portal. No registration fee.",
    "Registration is free. Do not pay any fee to agents.",
    "Call the toll-free helpline 1930 to report fraud. Do not pay anyone.",
    "Feel free to pay the electricity bill online on the official site.",
    "Free delivery on all orders above Rs 499",
    "The Aadhaar update is free of cost at enrolment centres; no charge is collected.",
    "இலவச மடிக்கணினி திட்டம்: கட்டணம் இல்லை",
])
def test_fee_for_free_benefit_not_flagged(text):
    assert "fee_for_free_benefit" not in new_signals(text)


def test_new_indicators_are_medium_not_proof():
    text = ("Free laptop scheme! Apply on WhatsApp wa.me/919876543210 and pay Rs 99 registration fee "
            "to laptop.scheme@ybl")
    hits = {h.signal: h.confidence for h in run_message_rules(text)}
    assert {s: hits[s] for s in NEW} == dict.fromkeys(NEW, "medium")


def test_tamil_rupee_amount_is_a_payment_request():
    # "ரூ.100" has a period, which used to cut the sentence-bounded pattern short.
    hits = {h.signal for h in run_message_rules("பதிவுக் கட்டணம் ரூ.100 செலுத்தவும்")}
    assert "payment_or_fee_request" in hits
    assert not run_message_rules("கட்டணம் ரூ.100 செலுத்த வேண்டாம்")


def test_endpoint_adds_steps_and_requested_action(client):
    body = "PM-Kisan registration: apply through WhatsApp wa.me/919876543210 and pay Rs 50 fee to kisan.help@ybl"
    r = client.post("/v1/analyze", data={"payload": make_payload(body)})
    assert r.status_code == 200
    d = r.json()
    assert {"personal_upi_payment", "unofficial_channel_application"} <= {e["signal"] for e in d["evidence"]}
    assert any("WhatsApp or Telegram" in s for s in d["safe_next_steps"])
    assert len(d["safe_next_steps"]) == len(d["safe_next_steps_ta"])
    actions = [a for c in d["government_claim"]["claims"] for a in c["requested_actions"]]
    assert "apply_through_chat_app" in actions
    assert actions.count("pay_money_or_fee") == len(d["government_claim"]["claims"])  # de-duplicated per claim


def _gov(client, body: str) -> dict:
    r = client.post("/v1/analyze", data={"payload": make_payload(body)})
    assert r.status_code == 200
    return r.json()["government_claim"]


def _link_outcomes(gov: dict) -> list[str]:
    return [f["outcome"] for f in gov["findings"] if f["aspect"] == "official_link"]


@pytest.mark.parametrize("url", ["https://pmjay.gov.in/", "https://beneficiary.nha.gov.in/", "https://nha.gov.in/PM-JAY"])
def test_pmjay_official_domains_match(client, url):
    gov = _gov(client, f"Check your Ayushman card status at {url}")
    assert gov["matched_kb_entries"] == ["ab_pmjay"]
    assert _link_outcomes(gov) == ["supported"]


def test_pmjay_lookalike_domain_contradicts(client):
    gov = _gov(client, "Ayushman Bharat card approved. Verify at http://pmjay-card.in/verify and pay Rs 99 fee")
    assert gov["claim_status"] == "contradicted_by_curated_kb"
    assert _link_outcomes(gov) == ["contradicted"]
    facts = {f["aspect"] for f in gov["findings"]}
    assert "fact:pmjay_cashless_no_message_fee" in facts


def test_nsp_whatsapp_application_uses_curated_fact(client):
    gov = _gov(client, "National Scholarship Portal: apply through WhatsApp wa.me/919876543210 before Friday")
    assert gov["matched_kb_entries"] == ["national_scholarship_portal"]
    aspects = [f["aspect"] for f in gov["findings"]]
    assert "fact:nsp_application_route" in aspects
    # The curated fact covers the WhatsApp request, so no duplicate generic finding is added.
    assert not any(f["aspect"] == "requested_action" and "WhatsApp" in f["detail_en"] for f in gov["findings"])
    assert gov["claim_status"] == "partially_supported_by_curated_kb"  # not covered != contradicted


def test_nsp_lookalike_domain_contradicts(client):
    gov = _gov(client, "Your scholarship is ready at https://scholarships.gov.in.claim-now.cc/login")
    assert gov["matched_kb_entries"] == ["national_scholarship_portal"]
    assert _link_outcomes(gov) == ["contradicted"]


@pytest.mark.parametrize("body", ["Magalir Urimai Thogai Rs 1000 pending, update KYC", "மகளிர் உரிமைத் தொகை நிலுவையில் உள்ளது"])
def test_magalir_urimai_thogai_is_named_but_not_covered(client, body):
    gov = _gov(client, body)
    assert gov["claim_status"] == "not_found_in_curated_kb"
    assert gov["matched_kb_entries"] == []
    assert gov["sources"] == [] and gov["safe_guidance_en"] == []
