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
    # Which LLM answers: mock | sarvam | gemini | anthropic. LLM_MODE is the older name and is still honoured.
    llm_provider: str = ""
    llm_mode: str = "mock"
    # If the chosen provider fails (error, rate limit), try the next configured one in this order, then mock.
    llm_fallback_order: str = "sarvam,gemini,anthropic"
    llm_max_retries: int = 2           # retries on 429 / 503, with backoff
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai/v1"
    sarvam_model: str = "sarvam-105b"
    sarvam_fast_model: str = "sarvam-105b"   # sarvam-30b was deprecated by Sarvam (Oct 2026); 105b at low effort
    sarvam_tool_mode: str = "native"         # native | backend (backend: the server calls data tools itself)
    sarvam_voice_fallback: bool = True       # Sarvam speech when the browser has no voice for the language
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-flash-latest"
    gemini_fast_model: str = "gemini-flash-lite-latest"
    gemini_tool_mode: str = "native"
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

    def provider_key(self, name: str) -> str:
        return {"sarvam": self.sarvam_api_key, "gemini": self.gemini_api_key,
                "anthropic": self.anthropic_api_key}.get(name, "")

    @property
    def chosen_provider(self) -> str:
        p = (self.llm_provider or self.llm_mode or "mock").strip().lower()
        return p if p in ("mock", "sarvam", "gemini", "anthropic") else "mock"

    @property
    def provider_chain(self) -> list[str]:
        """The chosen provider (if it has a key), then the other configured providers in fallback order, then mock.
        Choosing mock means mock only — no network calls."""
        first = self.chosen_provider
        if first == "mock":
            return ["mock"]
        order = [first] + [p.strip().lower() for p in self.llm_fallback_order.split(",") if p.strip()]
        chain = [p for p in dict.fromkeys(order) if p in ("sarvam", "gemini", "anthropic") and self.provider_key(p)]
        return chain + ["mock"]

    @property
    def use_mock_llm(self) -> bool:
        return self.provider_chain[0] == "mock"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def income_bracket_list(self) -> list[str]:
        return [b.strip() for b in self.income_brackets.split(",") if b.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
