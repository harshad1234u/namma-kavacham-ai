import json

import pytest
from pydantic import ValidationError

from app.schemas.analysis import HARD_MAX_BODY_CHARS, AnalyzeRequest


def _req(**content) -> dict:
    base = {"body": "hello", "source": "pasted_text", "user_confirmed": True}
    base.update(content)
    return {"content": base, "privacy": {"upload_confirmed": True}}


def test_valid_request_defaults_are_unverified_and_both_languages():
    r = AnalyzeRequest.model_validate(_req())
    assert r.language_preference == "both"
    assert r.sender is None


def test_user_confirmed_false_is_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_req(user_confirmed=False))


def test_user_confirmed_missing_is_rejected():
    data = _req()
    del data["content"]["user_confirmed"]
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(data)


def test_empty_body_rejected_for_text_input():
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_req(body="   "))


def test_empty_body_allowed_for_screenshot_path():
    data = _req(body="", source="ocr")
    data["attachment"] = {"type": "screenshot", "provenance": "user_upload"}
    assert AnalyzeRequest.model_validate(data).attachment is not None


def test_attachment_requires_upload_confirmation():
    data = _req(body="", source="ocr")
    data["attachment"] = {"type": "screenshot"}
    data["privacy"]["upload_confirmed"] = False
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(data)


def test_hard_body_limit_enforced():
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_req(body="a" * (HARD_MAX_BODY_CHARS + 1)))


def test_unknown_source_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_req(source="trusted_sms"))


def test_sender_cannot_be_submitted_as_verified():
    data = _req()
    data["sender"] = {"value": "HDFCBK", "kind": "alphanumeric_sender_id", "verification_status": "verified"}
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(data)


def test_extra_fields_rejected():
    data = _req()
    data["risk_level"] = "LOW"  # client must not be able to supply a verdict
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate_json(json.dumps(data))
