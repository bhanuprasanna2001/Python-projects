"""Custom exception hierarchy for the GitHub Client.

This module defines a comprehensive exception hierarchy that maps HTTP status codes
and error conditions to specific, typed exceptions. This allows consumers to handle
different error scenarios with precision.

Exception Hierarchy:
    GitHubError (base)
    ├── ConfigurationError     - Invalid config, missing required params
    ├── AuthenticationError    - 401, invalid/expired token
    ├── AuthorizationError     - 403, insufficient permissions
    ├── NotFoundError          - 404, resource doesn't exist
    ├── ValidationError        - 422, invalid request payload
    ├── RateLimitError         - 429/403 rate limit exceeded
    ├── ServerError            - 5xx server errors
    └── NetworkError           - Connection failures, timeouts

Example:
    >>> try:
    ...     user = client.users.get("nonexistent-user-12345")
    ... except NotFoundError as e:
    ...     print(f"User not found: {e}")
    ... except RateLimitError as e:
    ...     print(f"Rate limited. Reset at: {e.reset_at}")

"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class GitHubError(Exception):
    """Base exception for all GitHub API errors.

    All exceptions raised by this library inherit from this class,
    making it easy to catch any GitHub-related error.

    Attributes:
        message: Human-readable error description.
        response_data: Raw response data from the API, if available.

    """

    def __init__(
        self,
        message: str,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.

        """
        self.message = message
        self.response_data = response_data or {}
        super().__init__(message)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"{self.__class__.__name__}(message={self.message!r})"


class ConfigurationError(GitHubError):
    """Raised when client configuration is invalid.

    This includes missing required parameters, invalid URLs,
    or incompatible configuration combinations.

    Example:
        >>> GitHubClient(base_url="not-a-url")
        ConfigurationError: Invalid base URL: not-a-url

    """


class AuthenticationError(GitHubError):
    """Raised when authentication fails (HTTP 401).

    This typically indicates an invalid, expired, or revoked token.

    Attributes:
        status_code: Always 401.

    Example:
        >>> client = GitHubClient(token="invalid_token")
        >>> client.users.get_authenticated()
        AuthenticationError: Bad credentials

    """

    status_code: int = 401

    def __init__(
        self,
        message: str = "Authentication failed",
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize authentication error."""
        super().__init__(message, response_data)


class AuthorizationError(GitHubError):
    """Raised when the user lacks permission (HTTP 403).

    This indicates the token is valid but lacks the required scopes
    or the user doesn't have access to the requested resource.

    Attributes:
        status_code: Always 403.
        required_scopes: Scopes needed for this operation, if known.

    Example:
        >>> client.repos.delete("owner", "private-repo")
        AuthorizationError: Must have admin rights to Repository

    """

    status_code: int = 403

    def __init__(
        self,
        message: str = "Permission denied",
        response_data: dict[str, Any] | None = None,
        required_scopes: list[str] | None = None,
    ) -> None:
        """Initialize authorization error.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.
            required_scopes: OAuth scopes required for this operation.

        """
        self.required_scopes = required_scopes or []
        super().__init__(message, response_data)


class NotFoundError(GitHubError):
    """Raised when a resource doesn't exist (HTTP 404).

    Note: GitHub returns 404 for private resources the user can't access,
    not just for resources that don't exist. This is intentional to prevent
    enumeration attacks.

    Attributes:
        status_code: Always 404.
        resource_type: Type of resource (user, repo, etc.), if known.
        resource_id: Identifier of the missing resource, if known.

    Example:
        >>> client.users.get("this-user-does-not-exist-12345")
        NotFoundError: User 'this-user-does-not-exist-12345' not found

    """

    status_code: int = 404

    def __init__(
        self,
        message: str = "Resource not found",
        response_data: dict[str, Any] | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        """Initialize not found error.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.
            resource_type: Type of resource that wasn't found.
            resource_id: Identifier of the resource.

        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, response_data)


class ValidationError(GitHubError):
    """Raised when the request payload is invalid (HTTP 422).

    GitHub returns detailed validation errors that this exception preserves.

    Attributes:
        status_code: Always 422.
        errors: List of field-level validation errors from GitHub.

    Example:
        >>> client.issues.create("owner", "repo", title="", body="test")
        ValidationError: Validation Failed - title: cannot be blank

    """

    status_code: int = 422

    def __init__(
        self,
        message: str = "Validation failed",
        response_data: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.
            errors: List of field-level validation errors.

        """
        self.errors = errors or []
        super().__init__(message, response_data)

    @property
    def field_errors(self) -> dict[str, str]:
        """Return a mapping of field names to error messages."""
        return {
            error.get("field", "unknown"): error.get("message", "invalid") for error in self.errors
        }


class RateLimitError(GitHubError):
    """Raised when API rate limit is exceeded (HTTP 429 or 403 with rate limit).

    GitHub has two types of rate limits:
    - Primary: 5000 requests/hour for authenticated users
    - Secondary: Abuse detection for rapid requests

    Attributes:
        status_code: 429 or 403.
        limit: Maximum requests allowed in the window.
        remaining: Requests remaining (usually 0 when this is raised).
        reset_at: When the rate limit resets.
        retry_after: Seconds until the limit resets.
        is_secondary: True if this is a secondary (abuse) rate limit.

    Example:
        >>> try:
        ...     for i in range(10000):
        ...         client.users.get("octocat")
        ... except RateLimitError as e:
        ...     print(f"Rate limited. Try again at {e.reset_at}")

    """

    status_code: int = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        response_data: dict[str, Any] | None = None,
        limit: int | None = None,
        remaining: int = 0,
        reset_at: datetime | None = None,
        retry_after: int | None = None,
        is_secondary: bool = False,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.
            limit: Maximum requests allowed.
            remaining: Requests remaining.
            reset_at: Datetime when limit resets.
            retry_after: Seconds until reset.
            is_secondary: Whether this is an abuse/secondary limit.

        """
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after
        self.is_secondary = is_secondary
        super().__init__(message, response_data)

    def __str__(self) -> str:
        """Return a detailed error message with reset time."""
        base = self.message
        if self.reset_at:
            base += f" (resets at {self.reset_at.isoformat()})"
        if self.retry_after:
            base += f" (retry after {self.retry_after}s)"
        return base


class ServerError(GitHubError):
    """Raised when GitHub returns a server error (HTTP 5xx).

    These errors are typically transient and the request can be retried.

    Attributes:
        status_code: The actual 5xx status code.

    Example:
        >>> client.users.get("octocat")
        ServerError: 503 Service Unavailable

    """

    def __init__(
        self,
        message: str = "GitHub server error",
        response_data: dict[str, Any] | None = None,
        status_code: int = 500,
    ) -> None:
        """Initialize server error.

        Args:
            message: Human-readable error description.
            response_data: Raw response data from the API.
            status_code: The HTTP status code (5xx).

        """
        self.status_code = status_code
        super().__init__(message, response_data)


class NetworkError(GitHubError):
    """Raised when a network-level error occurs.

    This includes connection failures, DNS resolution errors,
    timeouts, and SSL/TLS errors.

    Attributes:
        original_error: The underlying exception that caused this error.
        is_retryable: Whether this error is likely transient.

    Example:
        >>> client.users.get("octocat")  # No internet
        NetworkError: Connection failed: [Errno -2] Name does not resolve

    """

    def __init__(
        self,
        message: str = "Network error",
        original_error: Exception | None = None,
    ) -> None:
        """Initialize network error.

        Args:
            message: Human-readable error description.
            original_error: The underlying exception.

        """
        self.original_error = original_error
        self.is_retryable = self._classify_retryable(original_error)
        super().__init__(message, response_data=None)

    @staticmethod
    def _classify_retryable(error: Exception | None) -> bool:
        """Determine if the network error is likely transient.

        Args:
            error: The original exception.

        Returns:
            True if the error is likely transient and retryable.

        """
        if error is None:
            return True

        error_msg = str(error).lower()

        # DNS errors are not retryable (configuration issue)
        dns_indicators = [
            "failed to resolve",
            "nodename nor servname",
            "name or service not known",
            "getaddrinfo failed",
        ]
        if any(indicator in error_msg for indicator in dns_indicators):
            return False

        # These are typically transient
        transient_indicators = [
            "connection refused",
            "connection reset",
            "broken pipe",
            "timed out",
            "timeout",
        ]
        return any(indicator in error_msg for indicator in transient_indicators)


# =============================================================================
# Exception Factory
# =============================================================================


def exception_from_response(
    status_code: int,
    response_data: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> GitHubError:
    """Create the appropriate exception from an HTTP response.

    This factory function maps HTTP status codes to specific exception types
    and extracts relevant information from the response.

    Args:
        status_code: HTTP status code.
        response_data: Parsed JSON response body.
        headers: Response headers (for rate limit info).

    Returns:
        The appropriate GitHubError subclass.

    """
    headers = headers or {}
    message = response_data.get("message", f"HTTP {status_code}")

    # Handle rate limit errors (403 with rate limit message or 429)
    if status_code == 429 or (
        status_code == 403
        and ("rate limit" in message.lower() or "X-RateLimit-Remaining" in headers)
    ):
        return _create_rate_limit_error(message, response_data, headers)

    # Handle server errors (5xx)
    if 500 <= status_code < 600:
        return ServerError(
            message=message,
            response_data=response_data,
            status_code=status_code,
        )

    # Map status codes to exception types
    exception_map: dict[int, type[GitHubError]] = {
        401: AuthenticationError,
        403: AuthorizationError,
        404: NotFoundError,
    }

    if status_code in exception_map:
        return exception_map[status_code](message=message, response_data=response_data)

    # Handle validation errors specially (need errors list)
    if status_code == 422:
        errors = response_data.get("errors", [])
        return ValidationError(message=message, response_data=response_data, errors=errors)

    # Fallback for unexpected status codes
    return GitHubError(message=f"HTTP {status_code}: {message}", response_data=response_data)


def _create_rate_limit_error(
    message: str,
    response_data: dict[str, Any],
    headers: dict[str, str],
) -> RateLimitError:
    """Create a RateLimitError with details from headers.

    Args:
        message: Error message from response.
        response_data: Parsed JSON response body.
        headers: Response headers containing rate limit info.

    Returns:
        A RateLimitError with extracted rate limit information.

    """
    limit = int(headers.get("X-RateLimit-Limit", 0)) or None
    remaining = int(headers.get("X-RateLimit-Remaining", 0))

    reset_timestamp = headers.get("X-RateLimit-Reset")
    reset_at = datetime.fromtimestamp(int(reset_timestamp)) if reset_timestamp else None

    retry_after_str = headers.get("Retry-After")
    retry_after = int(retry_after_str) if retry_after_str else None

    is_secondary = "secondary" in message.lower() or "abuse" in message.lower()

    return RateLimitError(
        message=message,
        response_data=response_data,
        limit=limit,
        remaining=remaining,
        reset_at=reset_at,
        retry_after=retry_after,
        is_secondary=is_secondary,
    )
