"""Async web scraper using aiohttp.

WHY ASYNC?
==========
Async is beneficial when:
1. You're scraping MULTIPLE DOMAINS concurrently (not rate-limited by same server)
2. You're doing I/O-bound operations while waiting for network
3. You need to handle thousands of connections efficiently

NOT BENEFICIAL WHEN:
- Rate limiting is the bottleneck (our current case with single domain)
- You're CPU-bound (parsing heavy HTML)
- You only make sequential requests to one domain

This implementation exists for EDUCATIONAL purposes - to show how async
works in Python and when you'd use it in a real scraping scenario.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator

import aiohttp
from aiohttp import ClientError, ClientTimeout

from web_scraper.exceptions import (
    ConfigError,
    HTTPError,
    NetworkError,
    classify_connection_error,
)
from web_scraper.utils.user_agents import rotating_user_agents

logger = logging.getLogger(__name__)

# Module-level generator for consistent rotation
_user_agent_cycle: Iterator[str] = rotating_user_agents()


class AsyncScraper:
    """Async HTTP fetcher using aiohttp.

    Key differences from sync Scraper:
    - Uses aiohttp instead of requests
    - Methods are async (defined with 'async def')
    - Must be awaited when called
    - Can run multiple fetches concurrently with asyncio.gather()

    EXAMPLE USAGE:
        async with aiohttp.ClientSession() as session:
            scraper = AsyncScraper("https://example.com", session)
            content = await scraper.fetch()
    """

    def __init__(
        self,
        url: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
    ) -> None:
        """Initialize async scraper.

        Args:
            url: URL to fetch
            session: aiohttp ClientSession (should be reused across requests)
            timeout: Request timeout in seconds
        """
        self.url = url
        self._session = session
        self._timeout = ClientTimeout(total=timeout)

    async def fetch(self) -> bytes:
        """Fetch page content asynchronously.

        Returns:
            Response content as bytes

        Raises:
            ConfigError: For DNS/configuration issues
            NetworkError: For transient network issues
            HTTPError: For HTTP 4xx errors

        NOTE: Retry logic is handled at the crawler level for async,
        because we want to use asyncio.sleep() not time.sleep().
        """
        user_agent = next(_user_agent_cycle)
        headers = {"User-Agent": user_agent}

        logger.debug(f"[ASYNC] Fetching {self.url}")

        try:
            async with self._session.get(
                self.url,
                headers=headers,
                timeout=self._timeout,
            ) as response:
                # Handle HTTP errors
                if response.status >= 500:
                    error_msg = f"Server error ({response.status}) at {self.url}"
                    logger.warning(error_msg)
                    raise NetworkError(error_msg)
                elif response.status >= 400:
                    raise HTTPError(response.status, f"Client error at {self.url}")

                content = await response.read()
                logger.info(f"[ASYNC] Fetched {self.url} ({len(content)} bytes)")
                return content

        except TimeoutError as e:
            logger.warning(f"[ASYNC] Timeout for {self.url}")
            raise NetworkError("Request timeout") from e

        except aiohttp.ClientConnectorError as e:
            # This is aiohttp's equivalent of requests.ConnectionError
            # Classify similar to sync version
            error = ConnectionError(str(e))
            if classify_connection_error(error):
                logger.warning(f"[ASYNC] Transient error for {self.url}: {e}")
                raise NetworkError("Network connection failed") from e
            else:
                logger.error(f"[ASYNC] DNS resolution failed for {self.url}")
                raise ConfigError(f"Failed to resolve: {self.url}") from e

        except ClientError as e:
            logger.error(f"[ASYNC] Request failed for {self.url}: {e}")
            raise NetworkError(f"Request failed: {e}") from e


async def fetch_with_retry(
    url: str,
    session: aiohttp.ClientSession,
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    timeout: int = 10,
) -> bytes:
    """Fetch URL with async retry logic.

    This is a helper function that wraps AsyncScraper with retry logic.
    Unlike the sync version, we use asyncio.sleep() for non-blocking waits.

    Args:
        url: URL to fetch
        session: aiohttp session
        max_attempts: Maximum retry attempts
        backoff_factor: Multiplier for exponential backoff
        timeout: Request timeout

    Returns:
        Response content as bytes
    """
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            scraper = AsyncScraper(url, session, timeout)
            return await scraper.fetch()

        except NetworkError as e:
            last_error = e
            if attempt < max_attempts:
                delay = backoff_factor ** (attempt - 1)
                logger.warning(f"[ASYNC] Attempt {attempt} failed, retrying in {delay:.1f}s...")
                # KEY DIFFERENCE: asyncio.sleep is non-blocking!
                # Other coroutines can run while we wait
                await asyncio.sleep(delay)
            else:
                logger.error(f"[ASYNC] Max attempts ({max_attempts}) reached")

        except (ConfigError, HTTPError):
            # Don't retry config or client errors
            raise

    if last_error:
        raise last_error
    raise NetworkError("Fetch failed with unknown error")
