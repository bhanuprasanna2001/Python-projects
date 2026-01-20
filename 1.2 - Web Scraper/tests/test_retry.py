"""Tests for retry decorator.

WHY TEST THIS:
- Risk: HIGH - wrong retry behavior can cause silent failures or infinite loops
- Complexity: HIGH - timing, exception handling, state tracking
- Easy to test: MEDIUM - need to track call counts, mock time

WHAT WE'RE TESTING:
1. Successful call → no retry
2. Failure then success → retries until success
3. Max failures → raises exception after max attempts
4. Non-matching exception → not caught, no retry
"""

from unittest.mock import MagicMock, patch

import pytest
from web_scraper.utils.retry import retry


class TestRetryDecorator:
    """Test retry logic with exponential backoff."""

    # =========================================================================
    # SUCCESS CASES
    # =========================================================================

    def test_success_on_first_try_no_retry(self) -> None:
        """Function that succeeds immediately should not retry.

        Reasoning: No point retrying if nothing failed.
        """
        mock_func = MagicMock(return_value="success")

        @retry(max_attempts=3, exceptions=(Exception,))
        def decorated():
            return mock_func()

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1  # Called exactly once

    # =========================================================================
    # RETRY THEN SUCCESS
    # =========================================================================

    @patch("web_scraper.utils.retry.time.sleep")  # Don't actually sleep in tests
    def test_retry_on_failure_then_success(self, mock_sleep: MagicMock) -> None:
        """Function that fails then succeeds should retry.

        Reasoning: Transient failures should be retried - that's the whole point.
        """
        mock_func = MagicMock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, backoff_factor=2.0, exceptions=(ValueError,))
        def decorated():
            return mock_func()

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2  # Failed once, succeeded once
        mock_sleep.assert_called_once()  # Slept between retries

    # =========================================================================
    # MAX RETRIES EXCEEDED
    # =========================================================================

    @patch("web_scraper.utils.retry.time.sleep")
    def test_raises_after_max_attempts(self, mock_sleep: MagicMock) -> None:
        """Function that always fails should raise after max attempts.

        Reasoning: Can't retry forever - need to give up eventually.
        """
        mock_func = MagicMock(side_effect=ValueError("always fails"))

        @retry(max_attempts=3, exceptions=(ValueError,))
        def decorated():
            return mock_func()

        with pytest.raises(ValueError, match="always fails"):
            decorated()

        assert mock_func.call_count == 3  # Tried exactly max_attempts times

    # =========================================================================
    # EXCEPTION FILTERING
    # =========================================================================

    def test_non_matching_exception_not_retried(self) -> None:
        """Exceptions not in the exceptions tuple should not be retried.

        Reasoning: Only retry specific, known-recoverable exceptions.
        Unexpected exceptions should propagate immediately.
        """
        mock_func = MagicMock(side_effect=TypeError("unexpected"))

        @retry(max_attempts=3, exceptions=(ValueError,))  # Only catch ValueError
        def decorated():
            return mock_func()

        with pytest.raises(TypeError):
            decorated()

        assert mock_func.call_count == 1  # No retry for non-matching exception

    # =========================================================================
    # BACKOFF TIMING
    # =========================================================================

    @patch("web_scraper.utils.retry.time.sleep")
    def test_exponential_backoff_timing(self, mock_sleep: MagicMock) -> None:
        """Backoff should increase exponentially.

        Reasoning: Exponential backoff prevents hammering a failing service
        and gives it time to recover.
        """
        mock_func = MagicMock(side_effect=[ValueError(), ValueError(), "success"])

        @retry(max_attempts=3, backoff_factor=2.0, exceptions=(ValueError,))
        def decorated():
            return mock_func()

        decorated()

        # backoff_factor=2.0: wait times are 2^1=2, 2^2=4
        sleep_times = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_times == [2.0, 4.0]

    # =========================================================================
    # PRESERVES FUNCTION METADATA
    # =========================================================================

    def test_preserves_function_name(self) -> None:
        """Decorated function should preserve original name.

        Reasoning: Helps with debugging and logging.
        """

        @retry(max_attempts=3, exceptions=(Exception,))
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
