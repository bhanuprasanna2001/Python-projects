"""
ETL Pipeline - Automated data extraction, transformation, and loading.

A production-ready ETL pipeline with:
- Multiple data source extractors (API, CSV, SQLite)
- Configurable data transformations
- Database loading with upsert support
- Scheduling and monitoring
"""

from etl_pipeline.config import Settings

__version__ = "0.1.0"
__all__ = ["Settings", "__version__"]
