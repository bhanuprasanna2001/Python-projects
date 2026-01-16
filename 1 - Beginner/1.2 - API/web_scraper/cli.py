"""Command-line interface for web scraper."""

from __future__ import annotations

import argparse
import logging
import sys

from web_scraper.config import ConfigManager
from web_scraper.crawler import Crawler
from web_scraper.exceptions import ScraperError, ConfigError
from web_scraper.utils.logger import setup_logger
from web_scraper.utils.rate_limiter import RateLimiter


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="web_scraper",
        description="Multi-page web scraper with rate limiting.",
    )
    
    parser.add_argument(
        "cfg_path",
        nargs="?",
        default="configs/sites.yaml",
        help="YAML config path"
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=1,
        help="Maximum pages to crawl (default: 1)"
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


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
        
        rate_limiter = RateLimiter(default_delay=args.delay)
        crawler = Crawler(rate_limiter=rate_limiter)
        
        total_books = 0
        for result in crawler.crawl(start_url, max_pages=args.pages):
            for book in result.books:
                print(f"{book.title} - {book.price}")
            total_books += len(result.books)
        
        logger.info(f"Scraping complete. Total books: {total_books}")
        return 0
    
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except ScraperError as e:
        logger.error(f"Scraping failed: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130