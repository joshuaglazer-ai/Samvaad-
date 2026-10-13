"""Environment settings. Secrets are read only here, on the backend."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DISTRICTS = ["Bengaluru Urban", "Mysuru", "Kalaburagi", "Dharwad"]
STATE = "Karnataka"
DISTRICT_COORDS = {
    "Bengaluru Urban": (12.9716, 77.5946),
    "Mysuru": (12.2958, 76.6394),
    "Kalaburagi": (17.3297, 76.8343),
    "Dharwad": (15.4589, 75.0078),
}
LANGUAGES = ["en", "kn", "hi", "te"]
EDUCATION_LEVELS = ["class_8", "class_10", "class_12", "iti", "diploma", "graduate", "other"]
CONCERN_CATEGORIES = [
    "income", "job_security", "social_status", "safety",
    "cost", "distance_migration", "degree_first", "other",
]
ALIGNMENT_VALUES = ["earning_soon", "near_home", "respect", "study_further", "safety"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./samvaad.db"
    llm_mode: str = "mock"  # mock | anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_fast_model: str = "claude-haiku-5-5"
    # Server-side refusal fallback: "default" lets the API pick a fallback model; empty disables it.
    # Off by default until verified with a real API call (see docs/decisions.md D46).
    anthropic_fallbacks: str = ""
    admin_pin: str = "change-me"
    counsellor_pin: str = "change-me"
    phone_encryption_key: str = ""
    cors_origins: str = "http://localhost:5173"
    income_brackets: str = "<1.5L,1.5-3L,3-6L,>6L,prefer_not_to_say"
    # Analytics: cells with fewer sessions than this are suppressed.
    min_cell_size: int = 5

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        # Hosting providers hand out postgres:// URLs; SQLAlchemy + psycopg 3 needs postgresql+psycopg://
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def use_mock_llm(self) -> bool:
        return self.llm_mode.lower() != "anthropic" or not self.anthropic_api_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def income_bracket_list(self) -> list[str]:
        return [b.strip() for b in self.income_brackets.split(",") if b.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
