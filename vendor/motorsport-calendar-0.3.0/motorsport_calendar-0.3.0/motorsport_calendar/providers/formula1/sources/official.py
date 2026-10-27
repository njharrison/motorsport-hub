"""OfficialFormula1Source — fetches from the official F1 website/API."""

from motorsport_calendar.models import Event
from motorsport_calendar.providers.formula1.source import Formula1Source


class OfficialFormula1Source(Formula1Source):
    """Fetches F1 season data from the official Formula 1 website.

    Not yet implemented. Will scrape or call the official API endpoint.
    """

    async def get_season(self, year: int) -> list[Event]:
        raise NotImplementedError
