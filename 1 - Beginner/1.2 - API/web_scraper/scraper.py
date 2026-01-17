"""Web scraper with user-agent rotation."""

from __future__ import annotations

import builtins
import logging
from collections.abc import Iterator

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from web_scraper.exceptions import (
    ConfigError,
    HTTPError,
    NetworkError,
    classify_connection_error,
)
from web_scraper.utils.retry import retry
from web_scraper.utils.user_agents import rotating_user_agents

logger = logging.getLogger(__name__)

# Module-level generator for consistent rotation across all Scraper instances
_user_agent_cycle: Iterator[str] = rotating_user_agents()


class Scraper:
    """Fetches web pages with automatic user-agent rotation.

    Each request uses a different user-agent from the rotation pool.
    """

    def __init__(self, url: str, timeout: int = 10) -> None:
        """Initialize scraper for a URL."""
        self.url = url
        self.timeout = timeout

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(NetworkError,))
    def fetch_sync(self) -> bytes:
        """Fetch page content with retry logic and rotating user-agent.

        Returns:
            Response content as bytes

        Raises:
            ConfigError: For DNS/configuration issues (not retried)
            NetworkError: For transient network issues (retried)
            HTTPError: For HTTP 4xx errors (not retried)
        """
        user_agent = next(_user_agent_cycle)
        headers = {"User-Agent": user_agent}

        logger.debug(f"Fetching {self.url}")

        try:
            response = requests.get(
                url=self.url,
                timeout=self.timeout,
                headers=headers,
            )

            # Check HTTP status codes
            if response.status_code >= 500:
                # Server errors are transient - wrap as NetworkError for retry
                error_msg = f"Server error ({response.status_code}) at {self.url}"
                logger.warning(error_msg)
                raise NetworkError(error_msg)
            elif response.status_code >= 400:
                # Client errors are permanent - raise HTTPError (no retry)
                raise HTTPError(response.status_code, f"Client error at {self.url}")

            logger.info(f"Successfully fetched {self.url} ({len(response.content)} bytes)")
            return bytes(response.content)

        except Timeout as e:
            logger.warning(f"Timeout for {self.url}")
            raise NetworkError(f"Request timeout after {self.timeout}s") from e

        except ConnectionError as e:
            # Classify the error - wrap in builtins.ConnectionError for typing
            builtin_error = builtins.ConnectionError(str(e))
            if classify_connection_error(builtin_error):
                # Transient network error - raise NetworkError for retry
                logger.warning(f"Transient network error for {self.url}: {e}")
                raise NetworkError("Network connection failed") from e
            else:
                # DNS/config error - raise ConfigError (no retry)
                logger.error(f"DNS resolution failed for {self.url}")
                raise ConfigError(
                    f"Failed to resolve hostname. Check your URL in the config file: {self.url}"
                ) from e

        except RequestException as e:
            logger.error(f"Request failed for {self.url}: {e}")
            raise NetworkError(f"Request failed: {e}") from e
