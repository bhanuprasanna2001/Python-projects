"""Tests for exception classification logic.

WHY TEST THIS:
- Risk: HIGH - wrong classification means wrong retry behavior
- Complexity: Medium - string matching with multiple patterns
- Easy to test: YES - pure function, no dependencies

WHAT WE'RE TESTING:
1. DNS errors → should NOT retry (configuration issue)
2. Transient errors → should retry (temporary network issue)
3. Unknown errors → should NOT retry (fail fast principle)
"""

import pytest
from requests.exceptions import ConnectionError
from web_scraper.exceptions import classify_connection_error


class TestClassifyConnectionError:
    """Test error classification for retry decisions."""

    # =========================================================================
    # DNS ERRORS - Should NOT retry (these are configuration problems)
    # =========================================================================

    @pytest.mark.parametrize(
        "error_message",
        [
            "Failed to resolve 'example.com'",
            "nodename nor servname provided, or not known",
            "Name or service not known",
            "getaddrinfo failed",
        ],
    )
    def test_dns_errors_are_not_retryable(self, error_message: str) -> None:
        """DNS resolution failures should not be retried.

        Reasoning: DNS failures indicate a configuration problem (wrong URL).
        Retrying won't help - the URL needs to be fixed.
        """
        error = ConnectionError(error_message)

        assert classify_connection_error(error) is False

    # =========================================================================
    # TRANSIENT ERRORS - Should retry (temporary network issues)
    # =========================================================================

    @pytest.mark.parametrize(
        "error_message",
        [
            "Connection refused",
            "Connection reset by peer",
            "Broken pipe",
            "Network is unreachable",
        ],
    )
    def test_transient_errors_are_retryable(self, error_message: str) -> None:
        """Transient network errors should be retried.

        Reasoning: These errors are temporary - the server might be
        restarting, network might be flaky. Worth retrying.
        """
        error = ConnectionError(error_message)

        assert classify_connection_error(error) is True

    # =========================================================================
    # UNKNOWN ERRORS - Should NOT retry (fail fast)
    # =========================================================================

    def test_unknown_error_fails_fast(self) -> None:
        """Unknown errors should not be retried.

        Reasoning: If we don't recognize the error, it's safer to fail
        fast and let the user investigate rather than retry blindly.
        """
        error = ConnectionError("Some weird error we've never seen")

        assert classify_connection_error(error) is False

    def test_empty_error_message_fails_fast(self) -> None:
        """Empty error messages should fail fast."""
        error = ConnectionError("")

        assert classify_connection_error(error) is False

    # =========================================================================
    # CASE INSENSITIVITY - Error messages vary in casing
    # =========================================================================

    def test_classification_is_case_insensitive(self) -> None:
        """Error classification should work regardless of case.

        Reasoning: Different systems/libraries may format error
        messages differently. We shouldn't miss a match due to casing.
        """
        error = ConnectionError("CONNECTION REFUSED")

        assert classify_connection_error(error) is True
