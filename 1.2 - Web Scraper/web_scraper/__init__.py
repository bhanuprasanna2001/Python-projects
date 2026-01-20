"""Multi-source web scraper package."""

from web_scraper.config import ConfigManager
from web_scraper.crawler import Crawler
from web_scraper.exceptions import ConfigError, HTTPError, NetworkError, ParseError, ScraperError
from web_scraper.parser import Parser
from web_scraper.scraper import Scraper

__all__ = [
    "ConfigError",
    "ConfigManager",
    "Crawler",
    "HTTPError",
    "NetworkError",
    "ParseError",
    "Parser",
    "Scraper",
    "ScraperError",
]
