"""Command-line interface for web scraper."""

from __future__ import annotations

import argparse
import asyncio
import logging

from web_scraper.config import ConfigManager
from web_scraper.exceptions import ConfigError, ScraperError
from web_scraper.storage import CSVStorage, SQLiteStorage, Storage
from web_scraper.utils.logger import setup_logger


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="web_scraper",
        description="Multi-page web scraper with rate limiting.",
    )

    parser.add_argument(
        "cfg_path", nargs="?", default="configs/sites.yaml", help="YAML config path"
    )
    parser.add_argument(
        "--pages", "-p", type=int, default=1, help="Maximum pages to crawl (default: 1)"
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["csv", "sqlite", "both", "none"],
        default="none",
        help="Output storage type (default: none, just print)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use async crawler (educational - same result, different implementation)",
    )

    return parser


def get_storages(output_type: str) -> list[Storage]:
    """Create storage instances based on output type."""
    storages: list[Storage] = []

    if output_type in ("csv", "both"):
        storages.append(CSVStorage("data/books.csv"))
    if output_type in ("sqlite", "both"):
        storages.append(SQLiteStorage("data/scraper.db"))

    return storages


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(level=log_level)

    try:
        logger.info("Starting web scraper")

        cfg_manager = ConfigManager(args.cfg_path)
        config = cfg_manager.load_config()

        start_url = config["sites"]["books"]["base_url"]
        storages = get_storages(args.output)

        # Choose sync or async based on --async flag
        if args.use_async:
            return _run_async(start_url, args, storages, logger)
        else:
            return _run_sync(start_url, args, storages, logger)

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except ScraperError as e:
        logger.error(f"Scraping failed: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130


def _run_sync(
    start_url: str,
    args: argparse.Namespace,
    storages: list[Storage],
    logger: logging.Logger,
) -> int:
    """Run synchronous crawler."""
    from web_scraper.crawler import Crawler
    from web_scraper.utils.rate_limiter import RateLimiter

    rate_limiter = RateLimiter(default_delay=args.delay)
    crawler = Crawler(rate_limiter=rate_limiter)

    total_books = 0
    total_saved = 0

    for result in crawler.crawl(start_url, max_pages=args.pages):
        for book in result.books:
            print(f"{book.title} - {book.price}")

        for storage in storages:
            total_saved += storage.save(result.books)

        total_books += len(result.books)

    logger.info(f"[SYNC] Scraping complete. Total books: {total_books}")
    if storages:
        logger.info(f"Saved {total_saved} new books to storage")

    return 0


def _run_async(
    start_url: str,
    args: argparse.Namespace,
    storages: list[Storage],
    logger: logging.Logger,
) -> int:
    """Run async crawler."""
    from web_scraper.async_crawler import AsyncCrawler

    async def _async_main() -> tuple[int, int]:
        crawler = AsyncCrawler(delay=args.delay)
        total_books = 0
        total_saved = 0

        async for result in crawler.crawl(start_url, max_pages=args.pages):
            for book in result.books:
                print(f"{book.title} - {book.price}")

            for storage in storages:
                total_saved += storage.save(result.books)

            total_books += len(result.books)

        return total_books, total_saved

    # Run the async code
    logger.info("[ASYNC] Using async crawler")
    total_books, total_saved = asyncio.run(_async_main())

    logger.info(f"[ASYNC] Scraping complete. Total books: {total_books}")
    if storages:
        logger.info(f"Saved {total_saved} new books to storage")

    return 0
