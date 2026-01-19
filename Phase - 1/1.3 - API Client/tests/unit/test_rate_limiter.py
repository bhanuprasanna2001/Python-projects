"""Unit tests for the rate limiter module."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from github_client.utils.rate_limiter import RateLimiter, RateLimitInfo


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass."""

    def test_is_exceeded_when_remaining_zero(self):
        """is_exceeded should be True when remaining is 0."""
        info = RateLimitInfo(limit=5000, remaining=0, reset_at=datetime.now())
        assert info.is_exceeded is True

    def test_is_exceeded_when_remaining_positive(self):
        """is_exceeded should be False when remaining is positive."""
        info = RateLimitInfo(limit=5000, remaining=100, reset_at=datetime.now())
        assert info.is_exceeded is False

    def test_utilization_calculation(self):
        """utilization should calculate correctly."""
        info = RateLimitInfo(limit=100, remaining=75, reset_at=datetime.now())
        assert info.utilization == 0.25  # 25% used

        info2 = RateLimitInfo(limit=100, remaining=0, reset_at=datetime.now())
        assert info2.utilization == 1.0  # 100% used

    def test_utilization_with_zero_limit(self):
        """utilization should be 1.0 when limit is 0."""
        info = RateLimitInfo(limit=0, remaining=0, reset_at=datetime.now())
        assert info.utilization == 1.0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_default_buffer(self):
        """Default buffer should be 0.1."""
        limiter = RateLimiter()
        assert limiter.buffer == 0.1

    def test_custom_buffer(self):
        """Custom buffer should be respected."""
        limiter = RateLimiter(buffer=0.2)
        assert limiter.buffer == 0.2

    def test_update_from_headers(self):
        """Should parse rate limit headers correctly."""
        limiter = RateLimiter()
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": str(reset_timestamp),
            "X-RateLimit-Resource": "core",
        }

        limiter.update_from_headers(headers)

        info = limiter.get_limit_info("core")
        assert info is not None
        assert info.limit == 5000
        assert info.remaining == 4999
        assert info.resource == "core"

    def test_update_from_headers_missing_values(self):
        """Should handle missing headers gracefully."""
        limiter = RateLimiter()

        headers = {"X-RateLimit-Limit": "5000"}  # Missing other headers

        limiter.update_from_headers(headers)

        # Should not create an entry with incomplete data
        info = limiter.get_limit_info("core")
        assert info is None

    def test_get_remaining(self):
        """Should return remaining count."""
        limiter = RateLimiter()
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4500",
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)

        remaining = limiter.get_remaining("core")
        assert remaining == 4500

    def test_get_remaining_unknown_resource(self):
        """Should return None for unknown resource."""
        limiter = RateLimiter()
        assert limiter.get_remaining("unknown") is None

    def test_should_throttle_above_buffer(self):
        """Should not throttle when remaining is above buffer."""
        limiter = RateLimiter(buffer=0.1)  # 10% buffer
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "1000",  # 20% remaining, above 10% buffer
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        assert limiter.should_throttle("core") is False

    def test_should_throttle_below_buffer(self):
        """Should throttle when remaining is below buffer."""
        limiter = RateLimiter(buffer=0.1)  # 10% buffer
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "400",  # 8% remaining, below 10% buffer
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        assert limiter.should_throttle("core") is True

    def test_get_wait_time_no_throttle(self):
        """Should return 0 when no throttle needed."""
        limiter = RateLimiter(buffer=0.1)
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "2000",
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        assert limiter.get_wait_time("core") == 0.0

    def test_get_wait_time_needs_throttle(self):
        """Should return wait time when throttle needed."""
        limiter = RateLimiter(buffer=0.1)
        reset_timestamp = int(datetime.now().timestamp()) + 60  # 60 seconds from now

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "100",  # Well below buffer
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        wait_time = limiter.get_wait_time("core")
        assert 55 <= wait_time <= 65  # Approximately 60 seconds

    @patch("github_client.utils.rate_limiter.time.sleep")
    def test_wait_if_needed_no_wait(self, mock_sleep):
        """Should not sleep when no wait needed."""
        limiter = RateLimiter(buffer=0.1)
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "2000",
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        waited = limiter.wait_if_needed("core")

        assert waited == 0.0
        mock_sleep.assert_not_called()

    @patch("github_client.utils.rate_limiter.time.sleep")
    def test_wait_if_needed_with_wait(self, mock_sleep):
        """Should sleep when wait needed."""
        limiter = RateLimiter(buffer=0.1)
        reset_timestamp = int(datetime.now().timestamp()) + 10  # 10 seconds from now

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "100",  # Below buffer
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        limiter.wait_if_needed("core")

        mock_sleep.assert_called_once()
        # Should have slept approximately 10 seconds
        call_args = mock_sleep.call_args[0][0]
        assert 5 <= call_args <= 15

    def test_clear(self):
        """Should clear all stored limits."""
        limiter = RateLimiter()
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4000",
            "X-RateLimit-Reset": str(reset_timestamp),
        }

        limiter.update_from_headers(headers)
        assert limiter.get_limit_info("core") is not None

        limiter.clear()
        assert limiter.get_limit_info("core") is None

    def test_multiple_resources(self):
        """Should track multiple resources independently."""
        limiter = RateLimiter()
        reset_timestamp = int(datetime.now().timestamp()) + 3600

        core_headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4000",
            "X-RateLimit-Reset": str(reset_timestamp),
            "X-RateLimit-Resource": "core",
        }

        search_headers = {
            "X-RateLimit-Limit": "30",
            "X-RateLimit-Remaining": "25",
            "X-RateLimit-Reset": str(reset_timestamp),
            "X-RateLimit-Resource": "search",
        }

        limiter.update_from_headers(core_headers)
        limiter.update_from_headers(search_headers)

        core_info = limiter.get_limit_info("core")
        search_info = limiter.get_limit_info("search")

        assert core_info is not None
        assert core_info.limit == 5000
        assert search_info is not None
        assert search_info.limit == 30
