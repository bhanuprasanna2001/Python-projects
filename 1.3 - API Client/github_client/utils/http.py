"""HTTP client wrapper for the GitHub API.

This module provides a thin wrapper around httpx that handles:
- Base URL and headers configuration
- Authentication injection
- Response parsing and error handling
- Automatic JSON content type handling
- Retry logic with exponential backoff
- Rate limit tracking and throttling
- Response caching with TTL and ETag support

The HTTPClient is an internal implementation detail and should not be
used directly by library consumers. Use GitHubClient instead.

"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from github_client.exceptions import (
    NetworkError,
    RateLimitError,
    ServerError,
    exception_from_response,
)
from github_client.utils.cache import ResponseCache, make_cache_key
from github_client.utils.rate_limiter import RateLimiter
from github_client.utils.retry import calculate_backoff, is_retryable_error

if TYPE_CHECKING:
    from github_client.auth import AuthStrategy
    from github_client.config import ClientConfig

logger = logging.getLogger(__name__)


class HTTPClient:
    """Low-level HTTP client for GitHub API requests.

    This class handles the mechanics of making HTTP requests and
    converting responses to appropriate data structures or exceptions.
    Includes retry logic, rate limiting, and response caching.

    Note:
        This is an internal class. Use GitHubClient for the public API.

    """

    __slots__ = ("_auth", "_cache", "_client", "_config", "_rate_limiter")

    # GitHub API headers
    ACCEPT_HEADER = "application/vnd.github+json"
    API_VERSION_HEADER = "2022-11-28"

    def __init__(
        self,
        config: ClientConfig,
        auth: AuthStrategy,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            config: Client configuration.
            auth: Authentication strategy.

        """
        self._config = config
        self._auth = auth
        self._client = self._create_client()
        self._rate_limiter = RateLimiter(buffer=config.rate_limit_buffer)
        self._cache = ResponseCache(default_ttl=config.cache_ttl) if config.cache_enabled else None

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get the rate limiter instance."""
        return self._rate_limiter

    @property
    def cache(self) -> ResponseCache | None:
        """Get the cache instance."""
        return self._cache

    def _create_client(self) -> httpx.Client:
        """Create and configure the httpx client.

        Returns:
            Configured httpx.Client instance.

        """
        return httpx.Client(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(self._config.timeout),
            headers={
                "Accept": self.ACCEPT_HEADER,
                "X-GitHub-Api-Version": self.API_VERSION_HEADER,
                "User-Agent": self._config.user_agent,
            },
            follow_redirects=True,
        )

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        """Make an HTTP request to the GitHub API.

        Includes retry logic, rate limit handling, and caching.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            endpoint: API endpoint path (e.g., "/users/octocat").
            params: Query parameters.
            json_data: JSON body for POST/PUT/PATCH requests.

        Returns:
            HTTPResponse containing the parsed data and metadata.

        Raises:
            GitHubError: For API errors (4xx, 5xx).
            NetworkError: For connection failures.

        """
        # Check cache for GET requests
        cache_key = None
        if method == "GET" and self._cache:
            cache_key = make_cache_key(method, endpoint, params, self._auth.is_authenticated)
            cached = self._cache.get(cache_key)
            if cached:
                return HTTPResponse(
                    data=cached.data,
                    status_code=200,
                    headers={},
                )

        # Execute with retry logic
        return self._request_with_retry(method, endpoint, params, json_data, cache_key)

    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        cache_key: str | None,
    ) -> HTTPResponse:
        """Execute request with retry logic.

        Args:
            method: HTTP method.
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON body.
            cache_key: Cache key for GET requests.

        Returns:
            HTTPResponse with parsed data.

        """
        last_error: Exception | None = None
        max_attempts = self._config.max_retries + 1  # +1 for initial attempt

        for attempt in range(max_attempts):
            try:
                # Wait if rate limited
                resource = "search" if "/search/" in endpoint else "core"
                self._rate_limiter.wait_if_needed(resource)

                # Execute the request
                return self._execute_request(method, endpoint, params, json_data, cache_key)

            except (RateLimitError, ServerError, NetworkError) as e:
                last_error = e

                if not is_retryable_error(e):
                    raise

                if attempt >= max_attempts - 1:
                    logger.warning(
                        "Max retries (%d) exhausted for %s %s",
                        max_attempts - 1,
                        method,
                        endpoint,
                    )
                    raise

                # Calculate delay
                if isinstance(e, RateLimitError) and e.retry_after:
                    delay = float(e.retry_after)
                else:
                    delay = calculate_backoff(
                        attempt,
                        base_delay=1.0,
                        factor=self._config.retry_backoff_factor,
                    )

                logger.info(
                    "Retry %d/%d for %s %s after %.2fs: %s",
                    attempt + 1,
                    max_attempts - 1,
                    method,
                    endpoint,
                    delay,
                    str(e),
                )

                time.sleep(delay)

        if last_error:
            raise last_error
        raise RuntimeError("Unexpected retry loop exit")

    def _execute_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        cache_key: str | None,
    ) -> HTTPResponse:
        """Execute a single HTTP request.

        Args:
            method: HTTP method.
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON body.
            cache_key: Cache key for conditional requests.

        Returns:
            HTTPResponse with parsed data.

        """
        # Build the request
        request = self._client.build_request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data,
        )

        # Apply authentication
        request = self._auth.apply(request)

        # Add conditional request header if we have a cached ETag
        if cache_key and self._cache:
            etag = self._cache.get_etag(cache_key)
            if etag:
                request.headers["If-None-Match"] = etag

        logger.debug("Request: %s %s", method, request.url)

        try:
            response = self._client.send(request)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}", original_error=e) from e
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", original_error=e) from e
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP error: {e}", original_error=e) from e

        return self._process_response(response, cache_key)

    def _process_response(
        self,
        response: httpx.Response,
        cache_key: str | None = None,
    ) -> HTTPResponse:
        """Process the HTTP response.

        Args:
            response: The httpx response object.
            cache_key: Cache key for storing/updating cache.

        Returns:
            HTTPResponse with parsed data.

        Raises:
            GitHubError: If the response indicates an error.

        """
        # Extract headers for rate limit tracking
        headers = dict(response.headers)

        # Update rate limiter from response headers
        self._rate_limiter.update_from_headers(headers)

        # Handle 304 Not Modified (cache hit with ETag)
        if response.status_code == 304 and cache_key and self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                # Refresh TTL on successful conditional request
                self._cache.refresh_ttl(cache_key)
                logger.debug("304 Not Modified, using cached response")
                return HTTPResponse(
                    data=cached.data,
                    status_code=200,
                    headers=headers,
                )

        # Parse JSON body (empty for 204 No Content)
        if response.status_code == 204:
            data: dict[str, Any] | list[Any] = {}
        elif response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
        else:
            data = {}

        logger.debug(
            "Response: %d %s (remaining: %s)",
            response.status_code,
            response.reason_phrase,
            headers.get("X-RateLimit-Remaining", "N/A"),
        )

        # Check for errors
        if response.status_code >= 400:
            # Ensure data is a dict for error handling
            error_data = data if isinstance(data, dict) else {"message": str(data)}
            raise exception_from_response(
                status_code=response.status_code,
                response_data=error_data,
                headers=headers,
            )

        # Cache successful GET responses
        if cache_key and self._cache and response.status_code == 200:
            etag = headers.get("ETag")
            self._cache.set(cache_key, data, etag=etag)

        return HTTPResponse(
            data=data,
            status_code=response.status_code,
            headers=headers,
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        """Make a GET request.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.

        Returns:
            HTTPResponse with the response data.

        """
        return self.request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        """Make a POST request.

        Args:
            endpoint: API endpoint path.
            json_data: JSON body.

        Returns:
            HTTPResponse with the response data.

        """
        return self.request("POST", endpoint, json_data=json_data)

    def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        """Make a PUT request.

        Args:
            endpoint: API endpoint path.
            json_data: JSON body.

        Returns:
            HTTPResponse with the response data.

        """
        return self.request("PUT", endpoint, json_data=json_data)

    def patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        """Make a PATCH request.

        Args:
            endpoint: API endpoint path.
            json_data: JSON body.

        Returns:
            HTTPResponse with the response data.

        """
        return self.request("PATCH", endpoint, json_data=json_data)

    def delete(
        self,
        endpoint: str,
    ) -> HTTPResponse:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint path.

        Returns:
            HTTPResponse with the response data.

        """
        return self.request("DELETE", endpoint)

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> HTTPClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager and close client."""
        self.close()


class HTTPResponse:
    """Container for HTTP response data and metadata.

    This class provides easy access to response data along with
    metadata needed for pagination and rate limiting.

    Attributes:
        data: Parsed JSON response body.
        status_code: HTTP status code.
        headers: Response headers.

    """

    __slots__ = ("data", "headers", "status_code")

    def __init__(
        self,
        data: dict[str, Any] | list[Any],
        status_code: int,
        headers: dict[str, str],
    ) -> None:
        """Initialize the response container.

        Args:
            data: Parsed response body.
            status_code: HTTP status code.
            headers: Response headers.

        """
        self.data = data
        self.status_code = status_code
        self.headers = headers

    @property
    def rate_limit_remaining(self) -> int | None:
        """Get remaining rate limit from headers."""
        value = self.headers.get("X-RateLimit-Remaining")
        return int(value) if value else None

    @property
    def rate_limit_limit(self) -> int | None:
        """Get rate limit ceiling from headers."""
        value = self.headers.get("X-RateLimit-Limit")
        return int(value) if value else None

    @property
    def rate_limit_reset(self) -> int | None:
        """Get rate limit reset timestamp from headers."""
        value = self.headers.get("X-RateLimit-Reset")
        return int(value) if value else None

    @property
    def etag(self) -> str | None:
        """Get ETag for conditional requests."""
        return self.headers.get("ETag")

    @property
    def link_header(self) -> str | None:
        """Get Link header for pagination."""
        return self.headers.get("Link")

    def __repr__(self) -> str:
        """Return a representation of the response."""
        return f"HTTPResponse(status={self.status_code}, data_type={type(self.data).__name__})"
