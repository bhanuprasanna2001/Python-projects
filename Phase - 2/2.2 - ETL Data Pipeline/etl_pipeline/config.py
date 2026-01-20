"""
Configuration management for the ETL pipeline.

Uses pydantic-settings for environment variable support and YAML config loading.
Configuration hierarchy (later overrides earlier):
1. Default values in Settings class
2. YAML config file (configs/pipeline.yaml)
3. Environment variables (prefixed with ETL_)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get project root directory
def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


class GitHubSourceConfig(BaseModel):
    """GitHub API source configuration."""

    type: Literal["github_api"] = "github_api"
    enabled: bool = True
    endpoint: str = "users/{username}/starred"
    username: str = "torvalds"
    max_items: int = 100
    rate_limit_delay: float = 1.0


class CSVSourceConfig(BaseModel):
    """CSV file source configuration."""

    type: Literal["csv"] = "csv"
    enabled: bool = True
    path: str = "data/raw/weather_sample.csv"


class SQLiteSourceConfig(BaseModel):
    """SQLite database source configuration."""

    type: Literal["sqlite"] = "sqlite"
    enabled: bool = True
    database_path: str = ""
    query: str = "SELECT * FROM books"
    fallback_path: str = "data/raw/books_sample.db"


class SourcesConfig(BaseModel):
    """All data source configurations."""

    github: GitHubSourceConfig = Field(default_factory=GitHubSourceConfig)
    weather: CSVSourceConfig = Field(default_factory=CSVSourceConfig)
    books: SQLiteSourceConfig = Field(default_factory=SQLiteSourceConfig)


class QualityConfig(BaseModel):
    """Data quality thresholds."""

    min_completeness: float = 0.8
    max_duplicates_ratio: float = 0.05


class TransformationConfig(BaseModel):
    """Transformation stage configuration."""

    normalize_dates: bool = True
    handle_missing: Literal["drop", "fill_default", "fill_mean"] = "fill_default"
    deduplicate: bool = True
    quality: QualityConfig = Field(default_factory=QualityConfig)


class SQLiteLoadConfig(BaseModel):
    """SQLite loading configuration."""

    path: str = "data/output/etl_output.db"


class PostgresLoadConfig(BaseModel):
    """PostgreSQL loading configuration."""

    host: str = "localhost"
    port: int = 5432
    database: str = "etl_pipeline"
    user: str = "etl_user"
    password: str = "etl_password"

    @property
    def connection_string(self) -> str:
        """Get async PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def sync_connection_string(self) -> str:
        """Get sync PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class LoadingConfig(BaseModel):
    """Loading stage configuration."""

    target: Literal["sqlite", "postgres"] = "sqlite"
    sqlite: SQLiteLoadConfig = Field(default_factory=SQLiteLoadConfig)
    postgres: PostgresLoadConfig = Field(default_factory=PostgresLoadConfig)
    on_conflict: Literal["skip", "update", "fail"] = "update"
    batch_size: int = 1000


class ScheduledJob(BaseModel):
    """Scheduled job configuration."""

    name: str
    cron: str
    stages: list[str] = Field(default_factory=lambda: ["extract", "transform", "load"])
    full_refresh: bool = False


class SchedulingConfig(BaseModel):
    """Scheduling configuration."""

    enabled: bool = False
    timezone: str = "Europe/Berlin"
    jobs: list[ScheduledJob] = Field(default_factory=list)


class AlertsConfig(BaseModel):
    """Alerting configuration."""

    enabled: bool = False
    webhook_url: str = ""
    on_failure: bool = True
    on_degraded_quality: bool = True
    min_records_threshold: int = 10


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    metrics_enabled: bool = True
    metrics_path: str = "data/metrics/pipeline_metrics.json"
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: Literal["structured", "simple"] = "structured"
    file_path: str = "logs/pipeline.log"
    max_size_mb: int = 10
    backup_count: int = 5


class PipelineConfig(BaseModel):
    """Main pipeline configuration."""

    name: str = "multi-source-etl"
    description: str = "Aggregates data from multiple sources"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    Environment variables are prefixed with ETL_ and override config file values.
    Example: ETL_LOG_LEVEL=DEBUG overrides logging.level
    """

    model_config = SettingsConfigDict(
        env_prefix="ETL_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Environment overrides
    log_level: str = "INFO"
    github_token: str | None = None
    debug: bool = False

    # Loaded from YAML
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    transformations: TransformationConfig = Field(default_factory=TransformationConfig)
    loading: LoadingConfig = Field(default_factory=LoadingConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> Settings:
        """
        Load settings from YAML config file with environment variable overrides.

        Args:
            config_path: Path to YAML config file. Defaults to configs/pipeline.yaml

        Returns:
            Settings instance with merged configuration
        """
        if config_path is None:
            config_path = get_project_root() / "configs" / "pipeline.yaml"

        config_data: dict[str, Any] = {}

        if config_path.exists():
            with config_path.open() as f:
                raw_config = yaml.safe_load(f) or {}
                # Expand environment variables in config values
                config_data = _expand_env_vars(raw_config)

        return cls(**config_data)

    def get_data_dir(self) -> Path:
        """Get the data directory path, creating it if needed."""
        data_dir = get_project_root() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_logs_dir(self) -> Path:
        """Get the logs directory path, creating it if needed."""
        logs_dir = get_project_root() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir


def _expand_env_vars(obj: Any) -> Any:
    """
    Recursively expand environment variables in config values.

    Supports ${VAR} and ${VAR:-default} syntax.
    """
    if isinstance(obj, str):
        # Handle ${VAR:-default} syntax
        import re

        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replacer, obj)
    elif isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    return obj


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_yaml()
