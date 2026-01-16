"""Utility modules for web scraper."""

from web_scraper.utils.retry import retry
from web_scraper.utils.logger import setup_logger

__all__ = ["retry", "setup_logger"]