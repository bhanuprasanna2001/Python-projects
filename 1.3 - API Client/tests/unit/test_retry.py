"""Unit tests for the retry module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from github_client.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from github_client.utils.retry import (
    RetryConfig,
    calculate_backoff,
    is_retryable_error,
    retry,
)


class TestIsRetryableError:
    """Tests for is_retryable_error function."""

    def test_rate_limit_error_is_retryable(self):
        """RateLimitError should be retryable."""
        error = RateLimitError("Rate limit exceeded")
        assert is_retryable_error(error) is True

    def test_server_error_500_is_retryable(self):
        """Server 500 error should be retryable."""
        error = ServerError("Internal server error", status_code=500)
        assert is_retryable_error(error) is True

    def test_server_error_502_is_retryable(self):
        """Server 502 error should be retryable."""
        error = ServerError("Bad gateway", status_code=502)
        assert is_retryable_error(error) is True

    def test_server_error_503_is_retryable(self):
        """Server 503 error should be retryable."""
        error = ServerError("Service unavailable", status_code=503)
        assert is_retryable_error(error) is True

    def test_network_error_timeout_is_retryable(self):
        """Network timeout should be retryable."""
        error = NetworkError("Connection timed out")
        error.is_retryable = True
        assert is_retryable_error(error) is True

    def test_network_error_dns_not_retryable(self):
        """DNS errors should not be retryable."""
        error = NetworkError("Failed to resolve hostname")
        error.is_retryable = False
        assert is_retryable_error(error) is False

    def test_authentication_error_not_retryable(self):
        """Authentication errors should not be retryable."""
        error = AuthenticationError("Bad credentials")
        assert is_retryable_error(error) is False

    def test_not_found_error_not_retryable(self):
        """Not found errors should not be retryable."""
        error = NotFoundError("Resource not found")
        assert is_retryable_error(error) is False


class TestCalculateBackoff:
    """Tests for calculate_backoff function."""

    def test_first_attempt_uses_base_delay(self):
        """First attempt should use base delay."""
        delay = calculate_backoff(0, base_delay=1.0, factor=2.0, jitter=False)
        assert delay == 1.0

    def test_exponential_increase(self):
        """Delay should increase exponentially."""
        delay0 = calculate_backoff(0, base_delay=1.0, factor=2.0, jitter=False)
        delay1 = calculate_backoff(1, base_delay=1.0, factor=2.0, jitter=False)
        delay2 = calculate_backoff(2, base_delay=1.0, factor=2.0, jitter=False)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_max_delay_caps_value(self):
        """Delay should not exceed max_delay."""
        delay = calculate_backoff(10, base_delay=1.0, factor=2.0, max_delay=30.0, jitter=False)
        assert delay == 30.0

    def test_jitter_adds_randomness(self):
        """Jitter should add randomness to delay."""
        delays = [calculate_backoff(1, base_delay=1.0, factor=2.0, jitter=True) for _ in range(10)]
        # With jitter, delays should vary
        assert len(set(delays)) > 1
        # All delays should be in the jitter range (±25%)
        for delay in delays:
            assert 1.5 <= delay <= 2.5  # 2.0 * (0.75 to 1.25)


class TestRetryDecorator:
    """Tests for the retry decorator."""

    def test_no_retry_on_success(self):
        """Successful calls should not retry."""
        call_count = 0

        @retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_server_error(self):
        """Should retry on server errors."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServerError("Server error", status_code=500)
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exhausted(self):
        """Should raise after max retries exhausted."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ServerError("Server error", status_code=500)

        with pytest.raises(ServerError):
            always_fails()

        assert call_count == 3

    def test_no_retry_on_client_error(self):
        """Should not retry on client errors."""
        call_count = 0

        @retry(max_attempts=3)
        def client_error_func():
            nonlocal call_count
            call_count += 1
            raise NotFoundError("Not found")

        with pytest.raises(NotFoundError):
            client_error_func()

        assert call_count == 1

    @patch("github_client.utils.retry.time.sleep")
    def test_respects_rate_limit_retry_after(self, mock_sleep):
        """Should respect Retry-After from rate limit errors."""
        call_count = 0

        @retry(max_attempts=2, base_delay=1.0)
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limited", retry_after=5)
            return "success"

        result = rate_limited()
        assert result == "success"
        # Should have slept for the retry_after duration
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 5.0


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.backoff_factor == 2.0
        assert config.max_delay == 60.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(max_attempts=5, base_delay=2.0, backoff_factor=1.5, max_delay=30.0)
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.backoff_factor == 1.5
        assert config.max_delay == 30.0

    def test_from_client_config(self):
        """Test creating RetryConfig from ClientConfig."""
        mock_config = MagicMock()
        mock_config.max_retries = 5
        mock_config.retry_backoff_factor = 1.5

        retry_config = RetryConfig.from_client_config(mock_config)
        assert retry_config.max_attempts == 5
        assert retry_config.backoff_factor == 1.5
