import io
import json
import logging

from app.schemas.threat_intelligence import ThreatIntelStatus
from app.tests.conftest import (
    ADVISORY,
    BENIGN,
    SCAM_AADHAAR_OTP,
    SCAM_PMKISAN,
    SCAM_TNEB,
    FakeProvider,
    make_payload,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def post(client, payload: str, files=None):
    return client.post("/v1/analyze", data={"payload": payload}, files=files)


def test_scenario_a_deterministic_only_with_vt_disabled(client):
    r = post(client, make_payload(SCAM_TNEB))
    assert r.status_code == 200
    d = r.json()
    assert d["risk"]["level"] in {"HIGH", "CRITICAL"}
    assert d["risk"]["assessment_status"] == "assessed"
    assert d["provider_flags"]["virustotal_enabled"] is False
    vt = d["url_intelligence"]["provider_result"]
    assert vt["status"] == "unavailable" and vt["available"] is False
    assert "url_threat_intelligence_disabled" in d["missing_metadata"]
    assert d["url_intelligence"]["primary_url"] == "http://tneb-billupdate.in/pay.apk"
    assert any("Do not open the link" in s for s in d["safe_next_steps"])
    assert len(d["safe_next_steps"]) == len(d["safe_next_steps_ta"])


def test_vt_malicious_result_is_reflected(make_client):
    provider = FakeProvider(ThreatIntelStatus.MALICIOUS, malicious=5)
    client = make_client(provider=provider, virustotal_enabled=True, virustotal_api_key="k")
    d = post(client, make_payload("http://pm-kisan-gov.in.payment-desk.cc/verify", source="url_input")).json()
    assert provider.calls == ["http://pm-kisan-gov.in.payment-desk.cc/verify"]
    assert d["url_intelligence"]["provider_result"]["status"] == "malicious"
    assert any(e["signal"] == "threat_intel_malicious" and "5 of" in e["description_en"] for e in d["evidence"])
    assert d["provider_flags"]["virustotal_available"] is True
    assert d["url_intelligence"]["privacy_note"]


def test_vt_timeout_never_renders_safe(make_client):
    client = make_client(provider=FakeProvider(ThreatIntelStatus.UNAVAILABLE), virustotal_enabled=True,
                         virustotal_api_key="k")
    r = post(client, make_payload(SCAM_PMKISAN))
    assert r.status_code == 200
    d = r.json()
    assert d["url_intelligence"]["provider_result"]["available"] is False
    assert "url_threat_intelligence_unavailable" in d["missing_metadata"]
    assert d["risk"]["level"] in {"HIGH", "CRITICAL"}
    assert "safe" not in d["risk"]["level"].lower()


def test_vt_not_found_is_listed_as_missing(make_client):
    client = make_client(provider=FakeProvider(ThreatIntelStatus.NOT_FOUND), virustotal_enabled=True,
                         virustotal_api_key="k")
    d = post(client, make_payload("check https://some-new-site.com/offer")).json()
    assert "no_threat_intelligence_report_for_url" in d["missing_metadata"]


def test_scenario_c_impersonation_otp(client):
    d = post(client, make_payload(SCAM_AADHAAR_OTP)).json()
    signals = {e["signal"] for e in d["evidence"]}
    assert {"credential_request", "government_impersonation_phrasing", "urgency_or_threat_language"} <= signals
    assert d["risk"]["level"] in {"HIGH", "CRITICAL"}
    assert d["sender_assessment"]["verification_status"] == "unverified"
    assert "not authenticated" in d["sender_assessment"]["warnings"][0]
    # Phase 2: UIDAI's published advice not to disclose an Aadhaar OTP is in the curated KB.
    gov = d["government_claim"]
    assert gov["claim_status"] == "contradicted_by_curated_kb"
    assert gov["matched_kb_entries"] == ["uidai_aadhaar"]
    assert any(f["outcome"] == "contradicted" and "OTP" in f["detail_en"] for f in gov["findings"])
    assert "government_records_not_checked_live" in d["missing_metadata"]


def test_benign_message_is_low_and_not_labelled_safe(client):
    d = post(client, make_payload(BENIGN)).json()
    assert d["risk"]["level"] == "LOW"
    assert d["government_claim"]["claim_status"] == "not_government_related"
    assert any("does not prove the message is genuine" in s for s in d["safe_next_steps"])


def test_advisory_message_not_flagged_as_credential_request(client):
    d = post(client, make_payload(ADVISORY)).json()
    assert "credential_request" not in {e["signal"] for e in d["evidence"]}


def test_sender_is_masked(client):
    payload = make_payload(BENIGN, sender={"value": "+91 98765 43210", "kind": "phone_number",
                                          "provenance": "user_entered"})
    d = post(client, payload).json()
    assert d["sender_assessment"]["value_masked"].endswith("3210")
    assert "98765" not in d["sender_assessment"]["value_masked"]


def test_screenshot_upload_with_stub_ocr(client):
    payload = make_payload("", source="ocr", attachment={"type": "screenshot", "provenance": "user_upload"})
    r = post(client, payload, files={"screenshot": ("s.png", io.BytesIO(PNG_BYTES), "image/png")})
    assert r.status_code == 200
    d = r.json()
    assert d["provenance"]["ocr_status"] == "not_available_in_this_build"
    assert "screenshot_text_extraction_not_available" in d["missing_metadata"]
    assert d["risk"]["assessment_status"] == "insufficient_content"
    assert "not a safe result" in d["explanation"]["en"]


def test_screenshot_with_reviewed_text_is_analysed(client):
    payload = make_payload(SCAM_AADHAAR_OTP, source="user_corrected_ocr")
    r = post(client, payload, files={"screenshot": ("s.png", io.BytesIO(PNG_BYTES), "image/png")})
    assert r.json()["risk"]["assessment_status"] == "assessed"


def test_non_image_upload_rejected(client):
    payload = make_payload("", source="ocr", attachment={"type": "screenshot"})
    r = post(client, payload, files={"screenshot": ("s.png", io.BytesIO(b"<svg></svg>"), "image/png")})
    assert r.status_code == 415


def test_oversized_upload_rejected(make_client):
    client = make_client(max_upload_bytes=100)
    payload = make_payload("", source="ocr", attachment={"type": "screenshot"})
    r = post(client, payload, files={"screenshot": ("s.png", io.BytesIO(PNG_BYTES + b"\x00" * 200), "image/png")})
    assert r.status_code == 413


def test_body_over_configured_limit_rejected(make_client):
    client = make_client(max_message_body_chars=50)
    assert post(client, make_payload("x" * 51)).status_code == 422


def test_unconfirmed_request_rejected_without_echoing_content(client):
    payload = json.loads(make_payload("SECRET-OTP 482913"))
    payload["content"]["user_confirmed"] = False
    r = post(client, json.dumps(payload))
    assert r.status_code == 422
    assert "482913" not in r.text


def test_malformed_json_rejected(client):
    r = post(client, "{not json")
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"


def test_missing_payload_rejected(client):
    assert client.post("/v1/analyze").status_code == 422


def test_logs_do_not_contain_raw_content(client, caplog):
    logger = logging.getLogger("nk")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger="nk"):
            post(client, make_payload(SCAM_TNEB + " OTP 482913"))
    finally:
        logger.removeHandler(caplog.handler)
    joined = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert "analysis_completed" in joined
    for secret in ("98765", "482913", "tneb-billupdate", "disconnected"):
        assert secret not in joined


def test_openapi_documents_endpoint(client):
    spec = client.get("/openapi.json").json()
    assert "/v1/analyze" in spec["paths"]


def test_camera_image_origin_is_echoed_and_does_not_change_risk(client):
    def analyse(**content):
        payload = json.loads(make_payload(SCAM_AADHAAR_OTP))
        payload["content"].update(content)
        return post(client, json.dumps(payload))

    base = analyse(source="ocr").json()
    for source in ("ocr", "user_corrected_ocr", "manual_entry"):
        d = analyse(source=source, image_origin="camera").json()
        assert d["provenance"]["content_source"] == source
        assert d["provenance"]["image_origin"] == "camera"
        assert (d["risk"]["level"], d["risk"]["score"]) == (base["risk"]["level"], base["risk"]["score"])
        assert d["evidence"] == base["evidence"]
    assert base["provenance"]["image_origin"] is None
    # Browser OCR text arrives already extracted; no image is received.
    assert base["provenance"]["ocr_status"] == "extracted"
    assert base["provenance"]["attachment_received"] is False


def test_image_origin_rejected_for_non_image_sources(client):
    for source in ("pasted_text", "url_input"):
        payload = json.loads(make_payload(SCAM_AADHAAR_OTP, source=source))
        payload["content"]["image_origin"] = "camera"
        assert post(client, json.dumps(payload)).status_code == 422
    payload = json.loads(make_payload(SCAM_AADHAAR_OTP, source="ocr"))
    payload["content"]["image_origin"] = "satellite"
    assert post(client, json.dumps(payload)).status_code == 422
