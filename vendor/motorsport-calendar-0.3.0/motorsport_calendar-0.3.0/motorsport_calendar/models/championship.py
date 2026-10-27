"""Championship model."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ChampionshipCategory(StrEnum):
    """Broad category of a motorsport championship."""

    SINGLE_SEATER = "Single Seater"
    ENDURANCE = "Endurance"
    GT = "GT"
    TOURING_CAR = "Touring Car"
    RALLY = "Rally"
    MOTORBIKE = "Motorbike"
    OVAL = "Oval"
    OTHER = "Other"


class Championship(BaseModel):
    """A motorsport championship (series), independent of any season."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    category: ChampionshipCategory
