"""Unit tests for the exceptions module."""

from __future__ import annotations

from datetime import datetime

from github_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    GitHubError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    exception_from_response,
)


class TestGitHubError:
    """Tests for the base GitHubError class."""

    def test_basic_error(self):
        """Test creating a basic error."""
        error = GitHubError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.response_data == {}

    def test_error_with_response_data(self):
        """Test error with response data."""
        data = {"message": "Not found", "documentation_url": "https://docs.github.com"}
        error = GitHubError("Not found", response_data=data)
        assert error.response_data == data

    def test_repr(self):
        """Test string representation."""
        error = GitHubError("Test error")
        assert "GitHubError" in repr(error)
        assert "Test error" in repr(error)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_default_message(self):
        """Test default error message."""
        error = AuthenticationError()
        assert "Authentication failed" in str(error)
        assert error.status_code == 401

    def test_custom_message(self):
        """Test custom error message."""
        error = AuthenticationError("Bad credentials")
        assert str(error) == "Bad credentials"


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_default_message(self):
        """Test default error message."""
        error = AuthorizationError()
        assert "Permission denied" in str(error)
        assert error.status_code == 403

    def test_with_scopes(self):
        """Test with required scopes."""
        error = AuthorizationError(
            "Missing scope",
            required_scopes=["repo", "user"],
        )
        assert error.required_scopes == ["repo", "user"]


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_basic_not_found(self):
        """Test basic not found error."""
        error = NotFoundError("User not found")
        assert error.status_code == 404
        assert error.resource_type is None

    def test_with_resource_info(self):
        """Test with resource information."""
        error = NotFoundError(
            "User 'test' not found",
            resource_type="user",
            resource_id="test",
        )
        assert error.resource_type == "user"
        assert error.resource_id == "test"


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Validation failed")
        assert error.status_code == 422
        assert error.errors == []

    def test_with_field_errors(self):
        """Test with field-level errors."""
        errors = [
            {"field": "title", "message": "cannot be blank"},
            {"field": "body", "message": "is too short"},
        ]
        error = ValidationError("Validation failed", errors=errors)
        assert error.errors == errors
        assert error.field_errors == {
            "title": "cannot be blank",
            "body": "is too short",
        }


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_basic_rate_limit(self):
        """Test basic rate limit error."""
        error = RateLimitError()
        assert error.status_code == 429
        assert error.remaining == 0

    def test_with_details(self):
        """Test with full details."""
        reset_time = datetime(2024, 1, 1, 12, 0, 0)
        error = RateLimitError(
            "Rate limit exceeded",
            limit=5000,
            remaining=0,
            reset_at=reset_time,
            retry_after=3600,
            is_secondary=False,
        )
        assert error.limit == 5000
        assert error.remaining == 0
        assert error.reset_at == reset_time
        assert error.retry_after == 3600
        assert not error.is_secondary

    def test_str_with_reset_time(self):
        """Test string representation with reset time."""
        reset_time = datetime(2024, 1, 1, 12, 0, 0)
        error = RateLimitError("Rate limit exceeded", reset_at=reset_time)
        assert "2024-01-01" in str(error)

    def test_secondary_rate_limit(self):
        """Test secondary (abuse) rate limit."""
        error = RateLimitError("Secondary rate limit", is_secondary=True)
        assert error.is_secondary


class TestServerError:
    """Tests for ServerError."""

    def test_default_status(self):
        """Test default status code."""
        error = ServerError()
        assert error.status_code == 500

    def test_custom_status(self):
        """Test custom status code."""
        error = ServerError("Service unavailable", status_code=503)
        assert error.status_code == 503


class TestNetworkError:
    """Tests for NetworkError."""

    def test_basic_network_error(self):
        """Test basic network error."""
        error = NetworkError("Connection failed")
        assert error.original_error is None
        assert error.is_retryable

    def test_with_original_error(self):
        """Test with original exception."""
        original = ConnectionError("Connection refused")
        error = NetworkError("Failed", original_error=original)
        assert error.original_error is original
        assert error.is_retryable

    def test_dns_error_not_retryable(self):
        """Test DNS errors are not retryable."""
        original = Exception("getaddrinfo failed")
        error = NetworkError("DNS failed", original_error=original)
        assert not error.is_retryable

    def test_timeout_is_retryable(self):
        """Test timeout errors are retryable."""
        original = Exception("Connection timed out")
        error = NetworkError("Timeout", original_error=original)
        assert error.is_retryable


class TestExceptionFactory:
    """Tests for the exception_from_response factory function."""

    def test_401_creates_authentication_error(self):
        """Test 401 creates AuthenticationError."""
        error = exception_from_response(401, {"message": "Bad credentials"})
        assert isinstance(error, AuthenticationError)
        assert "Bad credentials" in str(error)

    def test_403_creates_authorization_error(self):
        """Test 403 creates AuthorizationError."""
        error = exception_from_response(403, {"message": "Forbidden"})
        assert isinstance(error, AuthorizationError)

    def test_403_rate_limit_creates_rate_limit_error(self):
        """Test 403 with rate limit message creates RateLimitError."""
        error = exception_from_response(
            403,
            {"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0"},
        )
        assert isinstance(error, RateLimitError)

    def test_404_creates_not_found_error(self):
        """Test 404 creates NotFoundError."""
        error = exception_from_response(404, {"message": "Not Found"})
        assert isinstance(error, NotFoundError)

    def test_422_creates_validation_error(self):
        """Test 422 creates ValidationError."""
        data = {
            "message": "Validation Failed",
            "errors": [{"field": "title", "message": "blank"}],
        }
        error = exception_from_response(422, data)
        assert isinstance(error, ValidationError)
        assert len(error.errors) == 1

    def test_429_creates_rate_limit_error(self):
        """Test 429 creates RateLimitError."""
        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1609459200",
        }
        error = exception_from_response(429, {"message": "Rate limit"}, headers=headers)
        assert isinstance(error, RateLimitError)
        assert error.limit == 5000
        assert error.remaining == 0

    def test_500_creates_server_error(self):
        """Test 5xx creates ServerError."""
        error = exception_from_response(500, {"message": "Internal error"})
        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_503_creates_server_error(self):
        """Test 503 creates ServerError."""
        error = exception_from_response(503, {"message": "Unavailable"})
        assert isinstance(error, ServerError)
        assert error.status_code == 503

    def test_unknown_status_creates_base_error(self):
        """Test unknown status creates GitHubError."""
        error = exception_from_response(418, {"message": "I'm a teapot"})
        assert isinstance(error, GitHubError)
        assert "418" in str(error)
