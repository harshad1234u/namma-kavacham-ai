import pytest

from app.civic.languages import (
    get_language,
    guess_from_script,
    load_languages,
    normalize_code,
    script_profile,
)

SCHEDULED = {
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok", "mai", "ml",
    "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur",
}


def test_registry_has_exactly_the_22_scheduled_languages_plus_english():
    reg = load_languages()
    assert {lang.code for lang in reg.languages if lang.scheduled} == SCHEDULED
    assert get_language("en") is not None and not get_language("en").scheduled


def test_no_language_is_marked_reviewed_without_a_review_record():
    for lang in load_languages().languages:
        assert "reviewed" not in lang.support.model_dump().values(), lang.code


def test_rtl_languages_are_flagged():
    assert {lang.code for lang in load_languages().languages if lang.dir == "rtl"} == {"ks", "sd", "ur"}


@pytest.mark.parametrize(
    "text,script,lang",
    [
        ("எங்கள் பகுதியில் குடிநீர் இல்லை", "tamil", "ta"),
        ("మా గ్రామంలో నీరు లేదు", "telugu", "te"),
        ("ನಮ್ಮ ಊರಿನಲ್ಲಿ ನೀರಿಲ್ಲ", "kannada", "kn"),
        ("ਸਾਡੇ ਪਿੰਡ ਵਿੱਚ ਪਾਣੀ ਨਹੀਂ", "gurmukhi", "pa"),
        ("ᱟᱢᱟᱜ ᱟᱹᱛᱩ", "ol_chiki", "sat"),
    ],
)
def test_single_language_scripts_are_high_confidence(text, script, lang):
    g = guess_from_script(text)
    assert g.script == script and g.candidates == (lang,) and g.confidence == "high"


def test_shared_scripts_are_never_resolved_to_one_language():
    g = guess_from_script("हमारे गांव में पीने का पानी नहीं है")
    assert g.script == "devanagari" and g.confidence == "low"
    assert {"hi", "mr", "ne", "sa", "mai", "doi", "kok", "brx"} <= set(g.candidates)
    assert set(guess_from_script("ہمارے گاؤں میں پانی نہیں").candidates) == {"ks", "sd", "ur"}


def test_latin_is_low_confidence_and_flagged_mixed_with_tamil():
    assert guess_from_script("Enga area la water illa").confidence == "low"
    assert guess_from_script("Water problem இங்கே அதிகம் உள்ளது").mixed is True


def test_urls_digits_and_emoji_do_not_count():
    assert script_profile("https://pmkisan.gov.in 12345 😀") == {}
    assert guess_from_script("").confidence == "none"
    assert script_profile("தமிழ் http://x.gov.in")["tamil"] == 1.0


def test_normalize_code_never_raises():
    assert normalize_code("ta") == "ta" and normalize_code("xx") == "en" and normalize_code(None) == "en"


def test_language_endpoint(client):
    r = client.get("/v1/meta/languages")
    assert r.status_code == 200
    body = r.json()
    assert len(body["languages"]) == 23 and "parity" not in body["note"].lower()
