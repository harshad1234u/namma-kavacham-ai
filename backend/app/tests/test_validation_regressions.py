"""Regressions for defects found in the complete-validation pass (docs/complete-validation-report.md)."""

import pytest

from app.services.message_rules import run_message_rules
from app.services.url_analyzer import extract_urls, normalize_url, run_domain_checks


def signals(text: str) -> set[str]:
    return {h.signal for h in run_message_rules(text)}


def domain_signals(url: str) -> set[str]:
    return {h.signal for h in run_domain_checks(normalize_url(url))}


# BUG-001: the name part of a UPI ID was extracted as a link and scored as a government lookalike domain.
@pytest.mark.parametrize("text", ["Pay Rs 99 to laptop.gov@ybl now", "send fee to kisan.help.in@paytm"])
def test_upi_id_is_not_extracted_as_a_link(text):
    assert extract_urls(text) == []


def test_real_links_next_to_upi_ids_are_still_extracted():
    assert extract_urls("pay to a.b@ybl or open pmkisan-gov.in/verify") == ["pmkisan-gov.in/verify"]


# BUG-002: a bare domain has no scheme, so it is not evidence of a plain-http link.
@pytest.mark.parametrize("url", ["pmkisan.gov.in", "www.uidai.gov.in", "cybercrime.gov.in/report"])
def test_bare_domain_is_not_flagged_as_no_https(url):
    assert "no_https" not in domain_signals(url)


@pytest.mark.parametrize("url", ["http://pmkisan.gov.in", "HTTP://evil.cc/x", "hxxp://evil.cc/x"])
def test_explicit_http_is_still_flagged(url):
    assert "no_https" in domain_signals(url)


# BUG-003: Tamil negative imperative (-ாதீங்க / -ாதீர்கள்) was not treated as negation.
@pytest.mark.parametrize("text", [
    "OTP யாருக்கும் சொல்லாதீங்க",
    "உங்கள் OTP-ஐ யாரிடமும் பகிராதீர்கள்",
    "ஆதார் link பண்ணுங்க https://uidai.gov.in — OTP யாருக்கும் சொல்லாதீங்க",
])
def test_tamil_negative_imperative_is_advice_not_a_request(text):
    assert "credential_request" not in signals(text)


def test_share_then_tell_no_one_is_still_a_credential_request():
    # The negative imperative applies to "tell", not to the earlier "share" request.
    assert "credential_request" in signals("உங்கள் OTP-ஐ பகிருங்கள், யாரிடமும் சொல்லாதீர்கள்")


# BUG-004: Tamil callback and Tanglish payment requests in their natural word order were missed.
def test_tamil_number_then_call_is_a_callback_request():
    assert "unverified_callback_number" in signals("உடனடியாக 9876543210 அழைக்கவும்")


def test_tamil_do_not_call_is_not_a_callback_request():
    assert "unverified_callback_number" not in signals("9876543210 அழைக்க வேண்டாம்")


def test_tanglish_fee_then_send_is_a_payment_request():
    assert "payment_or_fee_request" in signals("50 rupees fee ah 9876543210 gpay la anuppunga")


# BUG-005: /healthz reported only gemini_configured, never the provider actually in use.
@pytest.mark.parametrize("env, expected", [
    ({"LLM_PROVIDER": "groq", "GROQ_ENABLED": "true", "GROQ_API_KEY": "gsk_fake_test_key_0000000000"}, "groq"),
    ({"LLM_PROVIDER": "groq", "GROQ_ENABLED": "true", "GROQ_API_KEY": ""}, "template"),  # enabled but no key
    ({"LLM_PROVIDER": "template"}, "template"),
])
def test_healthz_reports_active_ai_provider_without_secrets(monkeypatch, env, expected):
    import importlib

    from fastapi.testclient import TestClient

    import app.main as main
    from app.core.config import get_settings

    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    try:
        body = TestClient(importlib.reload(main).app).get("/healthz")
        assert body.json()["ai_provider"] == expected
        assert "gsk_" not in body.text and "api_key" not in body.text.lower()
    finally:
        for k in env:
            monkeypatch.delenv(k)
        get_settings.cache_clear()
        importlib.reload(main)
