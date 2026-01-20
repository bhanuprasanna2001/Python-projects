"""
Structured logging utilities for the ETL pipeline.

Provides JSON-formatted logs with context for debugging and monitoring.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Output format:
    {"timestamp": "...", "level": "INFO", "logger": "...", "message": "...", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info for errors
        if record.levelno >= logging.ERROR:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
                "message",
                "taskName",
            }:
                log_data[key] = value

        return json.dumps(log_data, default=str)


class ContextLogger(logging.LoggerAdapter[logging.Logger]):
    """
    Logger adapter that adds context to all log messages.

    Usage:
        logger = get_logger("extractor", source="github", job_id="abc123")
        logger.info("Extracting data")  # Includes source and job_id in output
    """

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        """Add context to log message."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra or {})
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    log_format: str = "structured",
    log_file: str | Path | None = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("structured" for JSON, "simple" for text)
        log_file: Optional file path for log output
    """
    root_logger = logging.getLogger("etl_pipeline")
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter: logging.Formatter
    if log_format == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str, **context: Any) -> ContextLogger:
    """
    Get a logger with optional context.

    Args:
        name: Logger name (will be prefixed with 'etl_pipeline.')
        **context: Key-value pairs to include in all log messages

    Returns:
        ContextLogger instance

    Example:
        logger = get_logger("extractor", source="github")
        logger.info("Starting extraction")
    """
    full_name = f"etl_pipeline.{name}" if not name.startswith("etl_pipeline") else name
    base_logger = logging.getLogger(full_name)
    return ContextLogger(base_logger, context)
