"""HtmlDataSource — interface for sources that scrape HTML pages."""

from abc import abstractmethod

from .base import DataSource


class HtmlDataSource(DataSource):
    """Abstract base for sources that fetch and parse HTML pages.

    Concrete subclasses must implement :meth:`fetch_html`. Typical
    implementations use ``httpx`` or ``playwright`` to retrieve the page
    and ``BeautifulSoup`` / ``lxml`` to extract structured data.

    Example::

        class MyScraperSource(HtmlDataSource):
            async def fetch_html(self, url: str) -> str:
                async with httpx.AsyncClient() as client:
                    r = await client.get(url)
                    r.raise_for_status()
                    return r.text
    """

    @abstractmethod
    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML content from *url*.

        Args:
            url: Absolute URL of the page to fetch.

        Returns:
            Raw HTML source as a string.

        Raises:
            httpx.HTTPStatusError: On HTTP 4xx / 5xx responses.
            httpx.TimeoutException: When the request exceeds the timeout.
        """
