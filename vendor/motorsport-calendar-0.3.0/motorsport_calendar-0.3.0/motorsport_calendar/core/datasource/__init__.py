"""Data Acquisition Layer — abstract interfaces for raw data retrieval."""

from .base import DataSource
from .html_source import HtmlDataSource
from .ics_source import IcsDataSource
from .json_source import JsonDataSource

__all__ = ["DataSource", "HtmlDataSource", "IcsDataSource", "JsonDataSource"]
