"""Storage backends for persisting scraped data."""

from web_scraper.storage.base import Storage
from web_scraper.storage.csv_storage import CSVStorage
from web_scraper.storage.sqlite_storage import SQLiteStorage

__all__ = ["CSVStorage", "SQLiteStorage", "Storage"]
