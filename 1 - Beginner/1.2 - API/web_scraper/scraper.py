"""Web Pages Scraper"""

from __future__ import annotations

import logging
import aiohttp
import asyncio
import requests
from requests.exceptions import (
    RequestException,
    Timeout,
    ConnectionError
)

from web_scraper.exceptions import NetworkError, HTTPError, ConfigError
from web_scraper.utils.retry import retry

logger = logging.getLogger(__name__)


def _classify_connection_error(error: ConnectionError) -> bool:
    """Classify if a connection error is retryable.
    
    Args:
        error: The connection error to classify
        
    Returns:
        True if error is transient and retryable, False otherwise
    """
    error_msg = str(error).lower()
    
    # DNS resolution errors - don't retry (config issue)
    dns_indicators = [
        'failed to resolve',
        'nodename nor servname',
        'name or service not known',
        'getaddrinfo failed',
    ]
    
    if any(indicator in error_msg for indicator in dns_indicators):
        return False
    
    # Transient network errors - should retry
    transient_indicators = [
        'connection refused',
        'connection reset',
        'broken pipe',
        'network is unreachable',
    ]
    
    if any(indicator in error_msg for indicator in transient_indicators):
        return True
    
    # Unknown connection error - don't retry (fail fast)
    return False


class Scraper:
    """Handles scrapping from websites.
    
    This class uses the requests library to scrap the webpage.
    """
    
    def __init__(self, url: str, timeout: int = 10) -> None:
        """Initialize Scrapper"""
        self.url = url
        self.timeout = timeout
        logger.info(f"Initialized scraper for {url}")
    
    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(NetworkError,))
    def fetch_sync(self) -> bytes:
        """Synchronous Scrapping with error handling and retries.
        
        Returns:
            Response content as bytes
            
        Raises:
            ConfigError: For DNS/configuration issues (not retried)
            NetworkError: For transient network issues (retried)
            HTTPError: For HTTP 5xx errors (retried via NetworkError)
        """
        logger.debug(f"Fetching {self.url}")
        
        try:
            response = requests.get(url=self.url, timeout=self.timeout)
            
            # Check HTTP status codes
            if response.status_code >= 500:
                # Server errors are transient - wrap as NetworkError for retry
                error_msg = f"Server error ({response.status_code}) at {self.url}"
                logger.warning(error_msg)
                raise NetworkError(error_msg)
            elif response.status_code >= 400:
                # Client errors are permanent - raise HTTPError (no retry)
                raise HTTPError(
                    response.status_code,
                    f"Client error at {self.url}"
                )
                
            logger.info(f"Successfully fetched {self.url} ({len(response.content)} bytes)")
            return response.content
        
        except Timeout as e:
            logger.warning(f"Timeout for {self.url}")
            raise NetworkError(f"Request timeout after {self.timeout}s") from e
            
        except ConnectionError as e:
            # Classify the error
            if _classify_connection_error(e):
                # Transient network error - raise NetworkError for retry
                logger.warning(f"Transient network error for {self.url}: {e}")
                raise NetworkError(f"Network connection failed") from e
            else:
                # DNS/config error - raise ConfigError (no retry)
                logger.error(f"DNS resolution failed for {self.url}")
                raise ConfigError(
                    f"Failed to resolve hostname. Check your URL in the config file: {self.url}"
                ) from e
                
        except RequestException as e:
            logger.error(f"Request failed for {self.url}: {e}")
            raise NetworkError(f"Request failed: {e}") from e
    
    