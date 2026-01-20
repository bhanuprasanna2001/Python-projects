"""Utility modules for the GitHub Client.

This package contains cross-cutting concerns and helper utilities:
- http: HTTP client wrapper
- logger: Structured logging configuration
- retry: Retry logic with exponential backoff
- rate_limiter: Proactive rate limiting
- cache: Response caching with TTL
- pagination: Pagination utilities

"""

from github_client.utils.cache import ResponseCache, make_cache_key
from github_client.utils.http import HTTPClient, HTTPResponse
from github_client.utils.pagination import (
    PaginatedResponse,
    collect_all,
    paginate,
    parse_link_header,
)
from github_client.utils.rate_limiter import RateLimiter, RateLimitInfo
from github_client.utils.retry import RetryConfig, retry

__all__ = [
    "HTTPClient",
    "HTTPResponse",
    "PaginatedResponse",
    "RateLimitInfo",
    "RateLimiter",
    "ResponseCache",
    "RetryConfig",
    "collect_all",
    "make_cache_key",
    "paginate",
    "parse_link_header",
    "retry",
]
