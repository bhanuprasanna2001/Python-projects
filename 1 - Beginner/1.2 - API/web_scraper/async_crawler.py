"""Async crawler for multi-page scraping.

ASYNC CRAWLING STRATEGIES
=========================

1. SEQUENTIAL (what we implement here):
   - Fetch page 1 → Parse → Fetch page 2 → Parse → ...
   - Still uses async, but doesn't parallelize within a domain
   - Respects rate limiting and is polite to servers
   - Good for: single-domain scraping

2. CONCURRENT WITHIN PAGE (also shown):
   - Fetch multiple resources from ONE page concurrently
   - E.g., fetch all book detail pages at once
   - Uses asyncio.gather() or asyncio.TaskGroup
   - Good for: fetching detail pages, images, etc.

3. CONCURRENT ACROSS DOMAINS (not implemented):
   - Scrape multiple websites simultaneously
   - Each domain has its own rate limiter
   - Good for: aggregator scrapers

The key insight: async shines when you have multiple independent I/O operations.
For a single domain with rate limiting, async adds complexity without much benefit.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

import aiohttp

from web_scraper.async_scraper import fetch_with_retry
from web_scraper.models import Book
from web_scraper.parser import Parser
from web_scraper.utils.robots import RobotsChecker

logger = logging.getLogger(__name__)


@dataclass
class AsyncCrawlResult:
    """Result from crawling a single page (async version)."""

    url: str
    books: list[Book]
    next_url: str | None


class AsyncCrawler:
    """Async multi-page crawler.

    DIFFERENCES FROM SYNC CRAWLER:
    1. Uses 'async def' and 'await' keywords
    2. Uses aiohttp session instead of requests
    3. Yields results via 'async for' (AsyncIterator)
    4. Uses asyncio.sleep() for rate limiting (non-blocking)

    WHEN TO USE:
    - When you need to fetch detail pages for each book concurrently
    - When scraping multiple domains simultaneously
    - When you want to learn async Python!

    WHEN NOT TO USE:
    - Simple sequential scraping of one domain
    - When rate limiting is the bottleneck anyway
    """

    def __init__(
        self,
        robots_checker: RobotsChecker | None = None,
        timeout: int = 10,
        delay: float = 1.0,
    ) -> None:
        """Initialize async crawler.

        Args:
            robots_checker: Robots checker (created if None)
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
        """
        self._robots_checker = robots_checker or RobotsChecker()
        self._timeout = timeout
        self._delay = delay

    async def crawl(
        self,
        start_url: str,
        max_pages: int = 10,
    ) -> AsyncIterator[AsyncCrawlResult]:
        """Crawl pages asynchronously.

        USAGE:
            crawler = AsyncCrawler()
            async for result in crawler.crawl("https://..."):
                print(result.books)

        The 'async for' is key - it allows yielding from an async generator.
        """
        url: str | None = start_url
        pages_crawled = 0

        # Create ONE session for all requests (connection pooling)
        # This is a key aiohttp best practice!
        async with aiohttp.ClientSession() as session:
            while url and pages_crawled < max_pages:
                # Check robots.txt (sync operation, but fast)
                if not self._robots_checker.can_fetch(url):
                    logger.warning(f"[ASYNC] Blocked by robots.txt: {url}")
                    break

                # Rate limiting with async sleep (non-blocking!)
                if pages_crawled > 0:
                    logger.debug(f"[ASYNC] Waiting {self._delay}s...")
                    await asyncio.sleep(self._delay)

                # Fetch with retry
                logger.info(f"[ASYNC] Crawling page {pages_crawled + 1}: {url}")
                content = await fetch_with_retry(
                    url=url,
                    session=session,
                    timeout=self._timeout,
                )

                # Parse (sync operation - CPU bound, no benefit from async)
                parser = Parser(content, base_url=url)
                books = parser.parse()
                next_url = parser.get_next_page_url()

                yield AsyncCrawlResult(url=url, books=books, next_url=next_url)

                url = next_url
                pages_crawled += 1

        logger.info(f"[ASYNC] Crawl complete. Pages: {pages_crawled}")


async def run_async_crawler(
    start_url: str,
    max_pages: int = 10,
    delay: float = 1.0,
) -> list[AsyncCrawlResult]:
    """Convenience function to run async crawler.

    Returns all results as a list (loads into memory).
    For large crawls, use the async iterator directly.
    """
    crawler = AsyncCrawler(delay=delay)
    results = []

    async for result in crawler.crawl(start_url, max_pages):
        results.append(result)

    return results
