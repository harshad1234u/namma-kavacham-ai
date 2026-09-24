import pytest

from app.services.message_rules import run_message_rules


def signals(text: str) -> dict[str, str]:
    return {h.signal: h.confidence for h in run_message_rules(text)}


@pytest.mark.parametrize(
    "text",
    [
        "Share the OTP sent to your mobile to complete verification",
        "Please enter your UPI PIN to receive the refund amount",
        "உங்கள் OTP-ஐ எங்கள் அதிகாரியிடம் பகிரவும்",
        "OTP sollunga sir, account block aagidum",
    ],
)
def test_credential_request_detected(text):
    assert signals(text).get("credential_request") == "high"


@pytest.mark.parametrize(
    "text",
    [
        "Your bank will never ask for your PIN or OTP.",
        "Do not share your OTP with anyone.",
        "உங்கள் OTP-ஐ யாருடனும் பகிர வேண்டாம்.",
    ],
)
def test_advisory_messages_are_not_flagged_as_credential_requests(text):
    assert "credential_request" not in signals(text)


def test_fee_request_is_high_confidence():
    assert signals("Pay ₹99 processing fee to activate your subsidy")["payment_or_fee_request"] == "high"


def test_upi_id_payment_is_high_confidence():
    assert signals("Send the amount to govtbenefit@ybl now")["payment_or_fee_request"] == "high"


def test_generic_payment_is_medium_confidence():
    assert signals("Please pay the bill amount of Rs 480")["payment_or_fee_request"] == "medium"


def test_tamil_fee_request():
    assert "payment_or_fee_request" in signals("பதிவுக் கட்டணம் செலுத்தவும்")


def test_urgency_with_consequence_is_high():
    assert signals("Your connection will be disconnected tonight")["urgency_or_threat_language"] == "high"


def test_urgency_deadline_only_is_medium():
    assert signals("Please reply within 24 hours")["urgency_or_threat_language"] == "medium"


def test_tamil_urgency():
    assert "urgency_or_threat_language" in signals("உங்கள் மின் இணைப்பு இன்று இரவு துண்டிக்கப்படும்")


@pytest.mark.parametrize(
    "text",
    [
        "Download update app at http://x.in/pay.apk",
        "Install this application from the link below",
        "செயலியை பதிவிறக்கம் செய்யவும்",
    ],
)
def test_apk_install_detected(text):
    assert signals(text).get("apk_install_instruction") == "high"


def test_remote_access_app_detected():
    assert "remote_access_app_request" in signals("Install AnyDesk so our officer can help you")


def test_government_impersonation_high():
    assert signals("Your Aadhaar will be suspended today")["government_impersonation_phrasing"] == "high"


def test_government_impersonation_tamil():
    assert "government_impersonation_phrasing" in signals("உங்கள் ஆதார் இடைநிறுத்தப்படும்")


def test_benefit_pending_is_medium_impersonation():
    assert signals("Your PM Kisan installment is pending")["government_impersonation_phrasing"] == "medium"


def test_sensitive_documents():
    assert "sensitive_document_request" in signals("Send your Aadhaar and bank details on WhatsApp")


def test_callback_number_is_low_and_masked():
    hits = [h for h in run_message_rules("Call our officer at 98765-43210 now") if h.signal == "unverified_callback_number"]
    assert hits and hits[0].confidence == "low"
    assert "98765" not in hits[0].matched_text
    assert hits[0].matched_text.endswith("3210 now") or "3210" in hits[0].matched_text


def test_excerpt_snaps_to_word_boundaries():
    text = "Dear Customer, Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill"
    hit = next(h for h in run_message_rules(text) if h.signal == "urgency_or_threat_language")
    assert hit.matched_text.split()[0] in text.lower().split()


def test_benign_message_triggers_nothing():
    assert run_message_rules("Hi Amma, I will reach home by 7. Please keep dinner ready.") == []


def test_empty_text():
    assert run_message_rules("") == []
