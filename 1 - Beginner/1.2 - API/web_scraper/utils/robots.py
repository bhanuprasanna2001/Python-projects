"""robots.txt compliance checker."""

from __future__ import annotations

import logging
from functools import lru_cache
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Checks URL crawlability against robots.txt rules.
    
    Caches robots.txt per domain to avoid repeated fetches.
    """
    
    def __init__(self, user_agent: str = "*") -> None:
        """Initialize checker with user agent string."""
        self._user_agent = user_agent
    
    @lru_cache(maxsize=32)
    def _get_parser(self, domain: str) -> RobotFileParser:
        """Fetch and parse robots.txt for domain (cached)."""
        parser = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        try:
            parser.set_url(robots_url)
            parser.read()
        except Exception as e:
            logger.warning(f"Failed to fetch {robots_url}: {e}. Allowing all.")
        return parser
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        domain = urlparse(url).netloc
        parser = self._get_parser(domain)
        return parser.can_fetch(self._user_agent, url)
    
    def crawl_delay(self, url: str) -> float | None:
        """Get crawl delay for domain, if specified in robots.txt."""
        domain = urlparse(url).netloc
        parser = self._get_parser(domain)
        return parser.crawl_delay(self._user_agent)
