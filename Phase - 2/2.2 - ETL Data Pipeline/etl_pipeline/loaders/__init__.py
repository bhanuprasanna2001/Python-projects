"""Data loaders for the ETL pipeline."""

from etl_pipeline.loaders.base import BaseLoader
from etl_pipeline.loaders.postgres_loader import PostgresLoader
from etl_pipeline.loaders.sqlite_loader import SQLiteLoader

__all__ = [
    "BaseLoader",
    "PostgresLoader",
    "SQLiteLoader",
]
