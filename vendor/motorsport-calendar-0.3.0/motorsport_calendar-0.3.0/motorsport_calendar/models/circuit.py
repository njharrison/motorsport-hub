"""Circuit model."""

from pydantic import BaseModel, ConfigDict


class Circuit(BaseModel):
    """A physical motorsport circuit."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    city: str
    country: str
    timezone: str
