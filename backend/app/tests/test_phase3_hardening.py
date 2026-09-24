"""Phase 3 release hardening: no tracebacks or content on unexpected errors, docs hidden in production."""

import importlib
import logging

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.tests.conftest import make_payload

SENTINEL = "Share OTP 482913 with officer at 98765-43210"


class ExplodingExplainer:
    async def explain(self, ctx):
        raise RuntimeError(f"input_value='{SENTINEL}'")


def test_unexpected_error_returns_generic_500_without_content(make_client, caplog, capsys):
    client = make_client(explainer=ExplodingExplainer())
    with caplog.at_level(logging.DEBUG):
        r = client.post("/v1/analyze", data={"payload": make_payload(SENTINEL)})
    assert r.status_code == 500
    assert r.json() == {"error": "internal_error", "detail": "Analysis failed"}
    captured = capsys.readouterr()
    for output in (r.text, caplog.text, captured.out, captured.err):
        assert "482913" not in output and "98765" not in output and "Traceback" not in output


def test_api_docs_hidden_in_production(monkeypatch):
    import app.main as main

    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        prod = importlib.reload(main)
        client = TestClient(prod.app)
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/healthz").status_code == 200
    finally:
        monkeypatch.delenv("ENVIRONMENT")
        get_settings.cache_clear()
        importlib.reload(main)
