"""Configuration for the civic modules' AI (NVIDIA NIM). Kept apart from app.core.config on purpose.

AI is off unless AI_ENABLED=true and an API key is set; every AI feature has a deterministic fallback.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class CivicSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_BACKEND_DIR.parent / ".env", _BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    ai_enabled: bool = False
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_api_key: SecretStr = SecretStr("")
    nvidia_nim_sarvam_model: str = "sarvamai/sarvam-m"
    nvidia_nim_embedding_model: str = "nvidia/nemotron-3-embed-1b"
    nvidia_nim_timeout_seconds: float = 20.0
    # Official-source retrieval (live fetch of the reviewed seed registry).
    retrieval_enabled: bool = True
    retrieval_timeout_seconds: float = 12.0
    retrieval_cache_seconds: int = 6 * 3600

    @property
    def ai_active(self) -> bool:
        return self.ai_enabled and bool(self.nvidia_nim_api_key.get_secret_value())


@lru_cache
def get_civic_settings() -> CivicSettings:
    return CivicSettings()
