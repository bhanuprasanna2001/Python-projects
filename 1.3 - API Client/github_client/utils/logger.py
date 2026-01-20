"""Logging configuration for the GitHub Client.

This module provides a pre-configured logger for the library.
Users can customize logging by configuring the 'github_client' logger.

Example:
    >>> import logging
    >>> logging.getLogger("github_client").setLevel(logging.DEBUG)

"""

from __future__ import annotations

import logging
import sys
from typing import TextIO

# Create library logger
logger = logging.getLogger("github_client")

# Set default level to WARNING to avoid noise
logger.setLevel(logging.WARNING)

# Add a null handler to prevent "No handler found" warnings
logger.addHandler(logging.NullHandler())


def configure_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    stream: TextIO | None = None,
) -> None:
    """Configure logging for the GitHub Client library.

    This is a convenience function for quickly setting up logging.
    For use, configure logging through your application's
    logging setup instead.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        format_string: Custom format string for log messages.
        stream: Output stream (defaults to sys.stderr).

    Example:
        >>> from github_client.utils.logger import configure_logging
        >>> configure_logging(level=logging.DEBUG)

    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if stream is None:
        stream = sys.stderr

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(format_string))

    logger.addHandler(handler)
    logger.setLevel(level)
