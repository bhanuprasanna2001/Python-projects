"""Logging configuration for web scraper."""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from datetime import datetime

def setup_logger(
    name: str = "web_scrapper",
    log_dir: Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure logging with file and console handlers
    
    Args:
        name: Logger name
        log_dir: Directory for log files (default: logs/)
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"scraper_{datetime.now():%Y%m%d}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger