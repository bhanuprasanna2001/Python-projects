"""Command-line interface for web scraper."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from web_scraper.parser import Parser
from web_scraper.scraper import Scraper
from web_scraper.config import ConfigManager
from web_scraper.exceptions import ScraperError, ConfigError
from web_scraper.utils.logger import setup_logger


def parse_datetime(value: str) -> datetime:
    """Parse datetime from string."""
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime format: '{value}'. Use: YYYY-MM-DD HH:MM"
        ) from err
        
        
def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="web_scraper",
        description="A clean CLI web scrapping application.",
    )
    
    parser.add_argument(
        "cfg_path",
        nargs="?",
        default="configs/sites.yaml",
        help="YAML Config Path"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(level=log_level)
    
    try:
        logger.info("Starting web scraper")
        
        cfg_manager = ConfigManager(args.cfg_path)
        config = cfg_manager.load_config()
        
        site_url = config["sites"]["books"]["base_url"]
        web_scraper = Scraper(url=site_url)
        
        scraped_content = web_scraper.fetch_sync()
        web_parser = Parser(scraped_content)
        
        web_parser.parse()
        
        logger.info("Scraping completed successfully")
    
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except ScraperError as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)