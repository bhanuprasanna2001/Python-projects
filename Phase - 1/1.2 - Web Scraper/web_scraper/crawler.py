"""Multi-page crawler orchestrating scraper, parser, and utilities."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from web_scraper.models import Book
from web_scraper.parser import Parser
from web_scraper.scraper import Scraper
from web_scraper.utils.rate_limiter import RateLimiter
from web_scraper.utils.robots import RobotsChecker

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result from crawling a single page."""

    url: str
    books: list[Book]
    next_url: str | None


class Crawler:
    """Orchestrates multi-page crawling with rate limiting and robots.txt compliance.

    Composes Scraper + Parser + RateLimiter + RobotsChecker.
    Uses iterator pattern to yield results page-by-page (memory efficient).
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        robots_checker: RobotsChecker | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize crawler with optional dependencies.

        Args:
            rate_limiter: Rate limiter instance (created if None)
            robots_checker: Robots checker instance (created if None)
            timeout: Request timeout in seconds
        """
        self._rate_limiter = rate_limiter or RateLimiter()
        self._robots_checker = robots_checker or RobotsChecker()
        self._timeout = timeout

    def crawl(
        self,
        start_url: str,
        max_pages: int = 10,
    ) -> Iterator[CrawlResult]:
        """Crawl pages starting from URL, yielding results.

        Args:
            start_url: URL to begin crawling
            max_pages: Maximum pages to crawl (safety limit)

        Yields:
            CrawlResult for each successfully crawled page
        """
        url: str | None = start_url
        pages_crawled = 0

        while url and pages_crawled < max_pages:
            # Check robots.txt
            if not self._robots_checker.can_fetch(url):
                logger.warning(f"Blocked by robots.txt: {url}")
                break

            # Respect rate limits
            self._rate_limiter.wait(url)

            # Fetch and parse
            logger.info(f"Crawling page {pages_crawled + 1}: {url}")
            scraper = Scraper(url=url, timeout=self._timeout)
            content = scraper.fetch_sync()
            parser = Parser(content, base_url=url)

            books = parser.parse()
            next_url = parser.get_next_page_url()

            yield CrawlResult(url=url, books=books, next_url=next_url)

            url = next_url
            pages_crawled += 1

        logger.info(f"Crawl complete. Pages crawled: {pages_crawled}")
