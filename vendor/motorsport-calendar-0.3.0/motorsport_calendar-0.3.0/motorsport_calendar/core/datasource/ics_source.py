"""IcsDataSource — interface for sources that consume iCalendar feeds."""

from abc import abstractmethod

from .base import DataSource


class IcsDataSource(DataSource):
    """Abstract base for sources that consume ICS / iCalendar feeds.

    Concrete subclasses must implement :meth:`fetch_ics`. The returned
    string is the raw iCalendar text; callers are responsible for parsing
    it with the ``icalendar`` library or equivalent.

    Example::

        class MyIcsFeedSource(IcsDataSource):
            async def fetch_ics(self, url: str) -> str:
                async with httpx.AsyncClient() as client:
                    r = await client.get(url)
                    r.raise_for_status()
                    return r.text
    """

    @abstractmethod
    async def fetch_ics(self, url: str) -> str:
        """Fetch raw ICS content from *url*.

        Args:
            url: Absolute URL of the iCalendar feed.

        Returns:
            Raw iCalendar text (``BEGIN:VCALENDAR … END:VCALENDAR``).

        Raises:
            httpx.HTTPStatusError: On HTTP 4xx / 5xx responses.
            httpx.TimeoutException: When the request exceeds the timeout.
        """
