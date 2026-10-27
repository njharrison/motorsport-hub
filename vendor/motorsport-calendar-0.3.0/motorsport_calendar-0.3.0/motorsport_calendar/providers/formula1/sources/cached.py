"""CachedFormula1Source — caching decorator around any Formula1Source."""

from motorsport_calendar.models import Event
from motorsport_calendar.providers.formula1.source import Formula1Source


class CachedFormula1Source(Formula1Source):
    """Wraps another Formula1Source and caches results to avoid redundant requests.

    Not yet implemented. The caching strategy (in-memory, file, Redis…) is
    left to the implementation.

    Args:
        source: The underlying source to cache responses from.
    """

    def __init__(self, source: Formula1Source) -> None:
        self._source = source

    async def get_season(self, year: int) -> list[Event]:
        raise NotImplementedError
