from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith(("postgresql://", "postgres://")):
            return value.replace("postgresql://", "postgresql+psycopg://", 1).replace("postgres://", "postgresql+psycopg://", 1)
        return value

    environment: str = "development"
    database_url: str = Field(min_length=1)
    redis_url: str = "redis://redis:6379/0"
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    email_delivery_backend: Literal["sync", "celery"] = "sync"
    secret_key: str = "dev-only-change-me"
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    ai_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_reasoning_effort: str = "medium"  # low | medium | high (gpt-oss models)
    ai_timeout_seconds: float = 60.0
    ai_max_tool_rounds: int = 5  # how many times the assistant may call data tools for one question
    ai_max_output_tokens: int = 4096  # includes the model's reasoning tokens
    smtp_host: str = ""  # empty = emails are only written to the log (development)
    smtp_port: int = 587  # 587 uses STARTTLS, 465 uses implicit TLS
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "FleetMind <no-reply@localhost>"
    resend_api_key: str = ""
    email_from: str = ""
    afromessage_api_key: str = ""
    afromessage_sender: str = ""
    afromessage_identifier_id: str = ""
    sms_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "fleetmind-documents"
    document_max_bytes: int = Field(default=10_000_000, ge=1, le=50_000_000)
    sim_tick_seconds: float = 2.0  # how often simulated GPS positions update
    sim_speed_boost: float = 8.0  # demo speed-up so movement is visible on a city map
    gps_ingest_max_age_seconds: int = Field(default=604_800, ge=60, le=31_536_000)
    tracking_link_max_ttl_hours: int = Field(default=720, ge=1, le=2160)
    osrm_base_url: str = ""
    osrm_profile: str = "driving"
    osrm_timeout_seconds: float = Field(default=8.0, gt=0, le=60)

    @model_validator(mode="after")
    def _production_secret(self):
        if self.environment == "production" and self.secret_key.startswith(("dev-only", "replace_with")):
            raise ValueError("Set a real SECRET_KEY in production")
        return self

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
