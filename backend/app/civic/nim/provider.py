"""NVIDIA NIM clients (OpenAI-compatible HTTP API).

NIMProvider            - auth, timeout, one retry on 429/5xx, safe error reasons
  SarvamMProvider      - chat completions returning JSON (guided decoding when the endpoint supports it)
  NemotronEmbeddingProvider - query/passage embeddings for retrieval

Nothing here decides anything: callers validate every output and fall back to deterministic logic
on any NIMError.
"""
import asyncio
import json
import re
import time
from typing import Literal

import httpx

from app.civic.settings import CivicSettings
from app.services.ai_explainer import _retry_wait


class NIMError(RuntimeError):
    """A NIM call failed. `reason` is safe to log (no content, no key)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class NIMProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 20.0,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._key = api_key
        self._timeout = timeout
        self._transport = transport

    async def _post(self, path: str, body: dict) -> dict:
        deadline = time.monotonic() + self._timeout
        headers = {"Authorization": f"Bearer {self._key}", "Accept": "application/json"}
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            for attempt in range(2):
                try:
                    r = await client.post(f"{self.base_url}{path}", headers=headers, json=body)
                except httpx.TimeoutException:
                    raise NIMError("timeout") from None
                except httpx.HTTPError:
                    raise NIMError("connection_error") from None
                if r.status_code == 200:
                    try:
                        return r.json()
                    except ValueError:
                        raise NIMError("invalid_json") from None
                wait = _retry_wait(r)
                if attempt == 0 and wait is not None and time.monotonic() + wait < deadline - 1:
                    await asyncio.sleep(wait)
                    continue
                code = r.status_code
                reasons = {401: "auth", 403: "auth", 404: "model_not_found", 410: "model_retired"}
                raise NIMError(reasons.get(code, f"http_{code}"))
        raise NIMError("unreachable")


_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_JSON_OBJ = re.compile(r"\{.*\}", re.S)


def parse_json_reply(text: str) -> dict:
    """Sarvam-M is a hybrid reasoning model: drop any <think> block, then read the JSON object."""
    m = _JSON_OBJ.search(_THINK.sub("", text or ""))
    if not m:
        raise NIMError("no_json")
    try:
        out = json.loads(m.group(0))
    except ValueError:
        raise NIMError("malformed_json") from None
    if not isinstance(out, dict):
        raise NIMError("malformed_json")
    return out


class SarvamMProvider(NIMProvider):
    async def chat_json(self, system: str, user: str, schema: dict, max_tokens: int = 1200) -> dict:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "nvext": {"guided_json": schema},
        }
        try:
            data = await self._post("/chat/completions", body)
        except NIMError as exc:
            if exc.reason != "http_400":
                raise
            body.pop("nvext")  # endpoint without guided decoding: rely on the prompt + our validation
            data = await self._post("/chat/completions", body)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise NIMError("unexpected_shape") from None
        return parse_json_reply(content)


class NemotronEmbeddingProvider(NIMProvider):
    async def embed(self, texts: list[str], input_type: Literal["query", "passage"]) -> list[list[float]]:
        if not texts:
            return []
        data = await self._post("/embeddings", {
            "model": self.model, "input": texts, "input_type": input_type,
            "encoding_format": "float", "truncate": "END",
        })
        try:
            rows = sorted(data["data"], key=lambda r: r["index"])
            vectors = [list(map(float, r["embedding"])) for r in rows]
        except (KeyError, TypeError, ValueError):
            raise NIMError("unexpected_shape") from None
        if len(vectors) != len(texts):
            raise NIMError("unexpected_shape")
        return vectors


def build_chat(settings: CivicSettings) -> SarvamMProvider | None:
    if not settings.ai_active:
        return None
    return SarvamMProvider(settings.nvidia_nim_base_url, settings.nvidia_nim_api_key.get_secret_value(),
                           settings.nvidia_nim_sarvam_model, settings.nvidia_nim_timeout_seconds)


def build_embedder(settings: CivicSettings) -> NemotronEmbeddingProvider | None:
    if not settings.ai_active:
        return None
    return NemotronEmbeddingProvider(settings.nvidia_nim_base_url, settings.embedding_key(),
                                     settings.nvidia_nim_embedding_model, settings.nvidia_nim_timeout_seconds)
