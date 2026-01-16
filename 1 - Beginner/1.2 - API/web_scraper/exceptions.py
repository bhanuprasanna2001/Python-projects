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


def classify_connection_error(error: ConnectionError) -> bool:
    """Classify if a connection error is retryable.
    
    Args:
        error: The connection error to classify
        
    Returns:
        True if error is transient and retryable, False otherwise
    """
    error_msg = str(error).lower()
    
    # DNS resolution errors - don't retry (config issue)
    dns_indicators = [
        'failed to resolve',
        'nodename nor servname',
        'name or service not known',
        'getaddrinfo failed',
    ]
    
    if any(indicator in error_msg for indicator in dns_indicators):
        return False
    
    # Transient network errors - should retry
    transient_indicators = [
        'connection refused',
        'connection reset',
        'broken pipe',
        'network is unreachable',
    ]
    
    if any(indicator in error_msg for indicator in transient_indicators):
        return True
    
    # Unknown connection error - don't retry (fail fast)
    return False