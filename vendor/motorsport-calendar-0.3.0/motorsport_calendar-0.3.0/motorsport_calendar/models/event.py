"""Event model — a race weekend (round) within a championship season."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .championship import Championship
from .circuit import Circuit
from .session import Session


class EventStatus(StrEnum):
    """Lifecycle status of a race event."""

    SCHEDULED = "scheduled"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    FINISHED = "finished"


class Event(BaseModel):
    """A race weekend: one round of a championship, at a circuit, with its sessions."""

    model_config = ConfigDict(frozen=True)

    championship: Championship
    season: int = Field(ge=1950, le=2100)
    round: int = Field(ge=1)
    name: str
    circuit: Circuit
    sessions: tuple[Session, ...] = ()
    event_uid: str = Field(
        min_length=1,
        description=(
            "Stable unique identifier used as UID in ICS exports "
            "(e.g. 'f1-2025-01-aus@motorsport-calendar')"
        ),
    )
    status: EventStatus = EventStatus.SCHEDULED
