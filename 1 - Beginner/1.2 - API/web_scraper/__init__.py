"""Multi-source web scraper package."""

from web_scraper.scraper import Scraper
from web_scraper.parser import Parser
from web_scraper.crawler import Crawler
from web_scraper.config import ConfigManager
from web_scraper.exceptions import ScraperError, ConfigError, NetworkError, HTTPError, ParseError

__all__ = [
    "Scraper",
    "Parser",
    "Crawler",
    "ConfigManager",
    "ScraperError",
    "ConfigError",
    "NetworkError",
    "HTTPError",
    "ParseError",
]