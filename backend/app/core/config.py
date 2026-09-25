from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    # Later files override earlier ones: backend/.env wins over the repo-root .env.
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Which explainer runs: "groq", "gemini", or "template". The chosen provider must also be enabled and keyed.
    llm_provider: str = "template"
    groq_enabled: bool = False
    groq_api_key: SecretStr = SecretStr("")
    groq_text_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = 20.0
    gemini_api_key: SecretStr = SecretStr("")
    gemini_enabled: bool = False
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 12.0
    virustotal_enabled: bool = False
    virustotal_api_key: SecretStr = SecretStr("")
    virustotal_timeout_seconds: float = 6.0

    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    max_message_body_chars: int = 8000
    max_upload_bytes: int = 8 * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def virustotal_active(self) -> bool:
        return self.virustotal_enabled and bool(self.virustotal_api_key.get_secret_value())

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.get_secret_value())

    @property
    def gemini_active(self) -> bool:
        return self.gemini_enabled and self.gemini_configured

    @property
    def groq_active(self) -> bool:
        return self.groq_enabled and bool(self.groq_api_key.get_secret_value()) and bool(self.groq_text_model.strip())

    @property
    def active_llm_provider(self) -> str:
        provider = self.llm_provider.strip().lower()
        if provider == "groq" and self.groq_active:
            return "groq"
        if provider == "gemini" and self.gemini_active:
            return "gemini"
        return "template"


@lru_cache
def get_settings() -> Settings:
    return Settings()
