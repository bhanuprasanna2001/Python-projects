"""Custom exceptions for web scraper."""

from __future__ import annotations

class ScraperError(Exception):
    """Base exception for all scraper errors."""


class ConfigError(ScraperError):
    """Configuration errors (invalid URLs, DNS failures)."""


class NetworkError(ScraperError):
    """Network-related errors (connection, timeout)."""


class HTTPError(ScraperError):
    """HTTP status code errors."""
    
    def __init__(self, status_code: int, message: str) -> None:
        """Initialize HTTP error with status code."""
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class ParseError(ScraperError):
    """HTML parsing errors."""