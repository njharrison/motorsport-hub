"""JsonDataSource — interface for sources that consume JSON APIs."""

from abc import abstractmethod
from typing import Any

from .base import DataSource


class JsonDataSource(DataSource):
    """Abstract base for sources that fetch JSON data over HTTP.

    Concrete subclasses must implement :meth:`fetch_json`. The method
    should handle HTTP connection management, caching, and error
    propagation; callers receive a fully-parsed Python structure.

    Example::

        class MyApiSource(JsonDataSource):
            async def fetch_json(
                self, url: str, params: dict[str, Any]
            ) -> list[Any] | dict[str, Any]:
                async with httpx.AsyncClient() as client:
                    r = await client.get(url, params=params)
                    r.raise_for_status()
                    return r.json()
    """

    @abstractmethod
    async def fetch_json(self, url: str, params: dict[str, Any]) -> list[Any] | dict[str, Any]:
        """Fetch JSON from *url* with optional query *params*.

        Args:
            url: Absolute URL of the JSON endpoint.
            params: Query-string parameters to append to the request.

        Returns:
            Parsed JSON as a ``list`` or a ``dict``.

        Raises:
            httpx.HTTPStatusError: On HTTP 4xx / 5xx responses.
            httpx.TimeoutException: When the request exceeds the timeout.
        """
