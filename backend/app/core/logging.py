"""Structured logging that refuses to emit sensitive fields.

Only safe operational metadata (request id, counts, statuses, timings) should
be passed via `extra=`. Any denylisted key is replaced before formatting, so a
careless call site cannot leak message bodies, OCR text, or secrets.
"""

import json
import logging
import re

SENSITIVE_KEYS = frozenset(
    {
        "body",
        "text",
        "message",
        "matched_text",
        "ocr_text",
        "screenshot",
        "image",
        "phone_number",
        "sender",
        "url",
        "api_key",
        "authorization",
        "x-apikey",
        "payload",
    }
)

_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}

_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_OTP_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def scrub(text: str) -> str:
    return _OTP_RE.sub("<num>", _PHONE_RE.sub("<phone>", text))


class RedactingJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "event": scrub(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_"):
                continue
            entry[key] = "<redacted>" if key.lower() in SENSITIVE_KEYS else value
        if record.exc_info:
            entry["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(entry, default=str, ensure_ascii=False)


_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingJsonFormatter())
    root = logging.getLogger("nk")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
    # httpx logs full request URLs at INFO, which would leak submitted URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"nk.{name}")
