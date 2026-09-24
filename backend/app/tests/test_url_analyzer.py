import pytest

from app.services.url_analyzer import extract_urls, levenshtein, normalize_url, run_domain_checks


def risk_signals(url: str) -> set[str]:
    return {h.signal for h in run_domain_checks(normalize_url(url)) if h.kind == "risk"}


def test_extracts_multiple_urls_from_mixed_text():
    text = "விவரங்களுக்கு http://a-example.in/x பார்க்கவும், or www.test.com. Also visit uidai.gov.in!"
    assert extract_urls(text) == ["http://a-example.in/x", "www.test.com", "uidai.gov.in"]


def test_does_not_extract_email_domain():
    assert extract_urls("mail me at someone@gmail.com") == []


def test_dedupes_and_strips_trailing_punctuation():
    assert extract_urls("Go to https://x.com/a). Again https://x.com/a.") == ["https://x.com/a"]


def test_normalizes_scheme_less_host():
    n = normalize_url("WWW.Example.COM")
    assert n.normalized == "http://www.example.com/"
    assert n.registrable_domain == "example.com"


def test_normalizes_defanged_url_and_drops_fragment_and_default_port():
    n = normalize_url("hxxps://Example.com:443/path#frag")
    assert n.normalized == "https://example.com/path"


def test_registrable_domain_for_gov_in():
    n = normalize_url("https://myaadhaar.uidai.gov.in/login")
    assert n.registrable_domain == "uidai.gov.in"
    assert n.subdomain_labels == ["myaadhaar"]


def test_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        normalize_url("javascript:alert(1)")


def test_government_lookalike_domain():
    assert "government_lookalike_domain" in risk_signals("http://pm-kisan-gov.in/verify")


def test_official_prefix_used_as_subdomain_is_flagged():
    signals = risk_signals("http://uidai.gov.in.verify-kyc.com/login")
    assert "government_lookalike_domain" in signals


@pytest.mark.parametrize("url", ["https://uidal.in/update", "http://incornetax.com/refund", "https://cybercrlme.org"])
def test_typosquat(url):
    assert "lookalike_domain_typosquat" in risk_signals(url)


def test_unrelated_short_domain_is_not_typosquat():
    assert "lookalike_domain_typosquat" not in risk_signals("https://india.com/")


def test_suspicious_tld():
    assert "suspicious_tld" in risk_signals("https://payment-desk.cc/")


def test_ip_literal():
    assert "raw_ip_host" in risk_signals("http://185.23.44.9/login")


def test_userinfo_trick():
    assert "userinfo_in_url" in risk_signals("http://uidai.gov.in@evil.example/")


def test_punycode_host():
    assert "internationalized_lookalike_host" in risk_signals("https://xn--uida-5ra.com/")


def test_apk_download():
    assert "executable_download_link" in risk_signals("http://files.example.com/update.apk")


def test_official_domain_triggers_no_risk_but_notes_namespace():
    hits = run_domain_checks(normalize_url("https://uidai.gov.in/"))
    assert [h for h in hits if h.kind == "risk"] == []
    assert any(h.signal == "government_namespace_domain" and h.kind == "info" for h in hits)


def test_ordinary_non_government_domain_is_not_flagged():
    # Never "not a government domain = scam".
    assert risk_signals("https://www.wikipedia.org/wiki/India") == set()


def test_levenshtein():
    assert levenshtein("uidai.gov.in", "uidal.gov.in") == 1
    assert levenshtein("abc", "abc") == 0
