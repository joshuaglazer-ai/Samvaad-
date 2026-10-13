from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .config import CONCERN_CATEGORIES, DISTRICTS, EDUCATION_LEVELS, get_settings

Lang = Literal["en", "kn", "hi", "te"]
Mode = Literal["together", "two_devices", "learner_only"]


def DeviceId():  # noqa: N802 - a fresh Field per model; a random id per phone, never personal data
    return Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9-]*$")


class AspirationIn(BaseModel):
    """A goal in the family's own words (voice/text) or picked from Browse / "Not sure yet" (database trades)."""
    text: str | None = Field(default=None, max_length=300)
    language: Lang = "en"
    source: Literal["voice", "text", "browse", "quiz"]
    selected_slugs: list[str] = Field(default=[], max_length=3)
    confirmed: bool = True


class AspirationSave(AspirationIn):
    who: Literal["learner", "parent"]
    device_id: str | None = DeviceId()


class MatchIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    language: Lang = "en"


class SuggestIn(BaseModel):
    likes: list[Literal["hands", "people", "machines", "outdoors", "computers"]] = []
    near_home: bool | None = None
    district: str | None = None
    language: Lang = "en"


class SessionCreate(BaseModel):
    language: Lang = "en"
    district: str
    learner_education: str
    learner_interests: list[str] = []
    top_concerns: list[str] = []
    income_bracket: str | None = None
    helper_mode: bool = False
    consent_given: bool
    participation_mode: Mode = "together"
    device_id: str | None = DeviceId()
    aspiration: AspirationIn | None = None
    parent_hope: AspirationIn | None = None

    @field_validator("district")
    @classmethod
    def _district(cls, v: str) -> str:
        if v not in DISTRICTS:
            raise ValueError(f"district must be one of {DISTRICTS}")
        return v

    @field_validator("learner_education")
    @classmethod
    def _edu(cls, v: str) -> str:
        if v not in EDUCATION_LEVELS:
            raise ValueError(f"learner_education must be one of {EDUCATION_LEVELS}")
        return v

    @field_validator("top_concerns")
    @classmethod
    def _concerns(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if c not in CONCERN_CATEGORIES]
        if bad:
            raise ValueError(f"unknown concerns {bad}")
        return v

    @field_validator("income_bracket")
    @classmethod
    def _income(cls, v: str | None) -> str | None:
        if v is not None and v not in get_settings().income_bracket_list:
            raise ValueError(f"income_bracket must be one of {get_settings().income_bracket_list}")
        return v


class SessionUpdate(BaseModel):
    language: Lang | None = None
    helper_mode: bool | None = None


class MoodIn(BaseModel):
    respondent: Literal["learner", "parent"]
    phase: Literal["pre", "post"]
    value: int = Field(ge=1, le=5)
    device_id: str | None = DeviceId()


class AlignmentIn(BaseModel):
    respondent: Literal["learner", "parent"]
    ranking: list[str]
    device_id: str | None = DeviceId()


class JoinIn(BaseModel):
    code: str = Field(pattern=r"^\d{4}$")
    language: Lang = "en"
    device_id: str | None = DeviceId()


class ChatIn(BaseModel):
    session_id: str
    speaker: Literal["learner", "parent", "helper"]
    text: str = Field(min_length=1, max_length=1000)
    language: Lang = "en"
    device_id: str | None = DeviceId()


class EventIn(BaseModel):
    session_id: str | None = None
    event_type: str = Field(min_length=1, max_length=40)
    payload: dict = {}


class EscalateIn(BaseModel):
    session_id: str
    trigger: Literal["user_request", "no_data", "negative_sentiment", "sensitive_topic", "repeated_failure"] = "user_request"


class CallbackIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    preferred_time: Literal["morning", "afternoon", "evening"] = "morning"
    consent: bool

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit() or ch == "+")
        if sum(ch.isdigit() for ch in digits) < 10:
            raise ValueError("phone number looks too short")
        return digits


class CaseUpdate(BaseModel):
    status: Literal["pending", "assigned", "in_progress", "resolved"] | None = None
    assigned_to: str | None = Field(default=None, max_length=80)


class CounsellorReply(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
