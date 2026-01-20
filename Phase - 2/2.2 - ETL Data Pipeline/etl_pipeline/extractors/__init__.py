"""Data extractors for the ETL pipeline."""

from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.extractors.csv_extractor import CSVExtractor
from etl_pipeline.extractors.github_extractor import GitHubExtractor
from etl_pipeline.extractors.sqlite_extractor import SQLiteExtractor

__all__ = [
    "BaseExtractor",
    "CSVExtractor",
    "GitHubExtractor",
    "SQLiteExtractor",
]
