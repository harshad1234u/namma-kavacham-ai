"""Tanglish urgency / negation regression set (Phase 3 experiment, adopted).

The positives and negatives mirror the isolated experiment: scoped consequence patterns
catch "block aagidum"-style threats without firing on everyday chat, and the Tanglish
negation only applies when it directly follows the matched verb.
"""

import pytest

from app.services.message_rules import run_message_rules

URGENCY = "urgency_or_threat_language"


def signals(text: str) -> dict[str, str]:
    return {h.signal: h.confidence for h in run_message_rules(text)}


@pytest.mark.parametrize(
    "text",
    [
        "Sir unga account block aagidum, ippove KYC update pannunga",
        "Unga SIM card 24 hours la block aagidum",
        "PAN card cancel aagidum seekiram link pannunga",
        "Gas connection disconnect aagidum, kadaisi naal inniku",
        "Unga pension stop aagidum, udanae verify pannunga",
        "Unga loan account freeze aayidum, ippove pay pannunga",
        "Your account block panniduvom if you don't update today",
        "Aadhaar suspend aagidum, OTP share pannunga",
    ],
)
def test_tanglish_consequence_is_urgency(text):
    assert URGENCY in signals(text)


@pytest.mark.parametrize(
    "text",
    [
        "Machi movie ku ippove kilambu, show start aagidum",
        "Rain vandha current cut aagum, candle vechiko",
        "Bus seekiram vandhudum, wait pannu",
        "Block aagidum nu varra message ellam scam, nambatheenga",
        "Class cancel aagidum nu sonnanga, relax",
        "Phone battery ippove dead aagidum, apram pesuren",
        "Ice cream melt aagidum, seekiram vaa",
        "Kadaisi naal college la semma fun",
    ],
)
def test_everyday_tanglish_is_not_urgency(text):
    assert URGENCY not in signals(text)


@pytest.mark.parametrize(
    "text",
    [
        "Bank eppovume OTP kekka maatanga, share pannatheenga",
        "OTP yaarukkum share pannatheenga",
        "UPI PIN send pannadheenga, bank kekka maatanga",
    ],
)
def test_tanglish_advisory_is_not_a_credential_request(text):
    assert "credential_request" not in signals(text)


def test_dont_tell_anyone_does_not_hide_a_credential_request():
    # "Share the OTP, don't tell anyone" — the negation is about secrecy, not about sharing.
    assert signals("OTP share pannunga, yaarukkum sollatheenga").get("credential_request") == "high"


def test_english_and_tamil_urgency_unchanged():
    assert signals("Your electricity will be disconnected tonight")[URGENCY] == "high"
    assert URGENCY in signals("உங்கள் ஆதார் இன்று இரவு இடைநிறுத்தப்படும்")
