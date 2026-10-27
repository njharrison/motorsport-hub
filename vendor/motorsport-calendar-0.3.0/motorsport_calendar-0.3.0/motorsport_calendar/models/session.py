"""Session and SessionType models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class SessionType(StrEnum):
    """Type of a motorsport session."""

    FP1 = "FP1"
    FP2 = "FP2"
    FP3 = "FP3"
    QUALIFYING = "QUALIFYING"
    SPRINT_QUALIFYING = "SPRINT_QUALIFYING"
    SPRINT = "SPRINT"
    RACE = "RACE"
    FREE_PRACTICE = "FREE_PRACTICE"
    TEST = "TEST"
    HYPERPOLE = "HYPERPOLE"


class Session(BaseModel):
    """A single on-track session within an event."""

    model_config = ConfigDict(frozen=True)

    type: SessionType
    start_datetime: datetime
    end_datetime: datetime
    title: str
    description: str | None = None

    @model_validator(mode="after")
    def _validate_datetimes(self) -> "Session":
        if self.start_datetime.tzinfo is None:
            raise ValueError("start_datetime must be timezone-aware")
        if self.end_datetime.tzinfo is None:
            raise ValueError("end_datetime must be timezone-aware")
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be strictly after start_datetime")
        return self
