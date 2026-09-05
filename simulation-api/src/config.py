"""Minimal settings for the one thing this service needs to know about the
outside world: where the real backend is, to forward customer replies to it."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # The main backend's API - see `backend/src/api/routes/recovery_cases.py`.
    BACKEND_API_BASE_URL: str = "http://localhost:8000/api"
    BACKEND_API_TIMEOUT_SECONDS: float = 10.0


settings = Settings()
