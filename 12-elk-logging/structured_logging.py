"""
Structured Logging for ELK
==========================
JSON-structured logging that's easy to parse and search in Elasticsearch.
"""

import logging
import json
import traceback
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger
import uuid
from contextvars import ContextVar

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


# =============================================================================
# Custom JSON Formatter
# =============================================================================

class ELKJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter optimized for ELK stack.
    """
    
    def __init__(
        self,
        service_name: str = "python-app",
        environment: str = "development",
        **kwargs
    ):
        self.service_name = service_name
        self.environment = environment
        super().__init__(**kwargs)
    
    def add_fields(self, log_record: Dict, record: logging.LogRecord, message_dict: Dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Standard ELK fields
        log_record['@timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service'] = self.service_name
        log_record['environment'] = self.environment
        
        # Source location
        log_record['source'] = {
            'file': record.filename,
            'line': record.lineno,
            'function': record.funcName,
            'module': record.module,
        }
        
        # Process info
        log_record['process'] = {
            'id': record.process,
            'name': record.processName,
        }
        
        # Thread info
        log_record['thread'] = {
            'id': record.thread,
            'name': record.threadName,
        }
        
        # Request correlation ID
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id
        
        # Exception info
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stacktrace': ''.join(traceback.format_exception(*record.exc_info)),
            }


# =============================================================================
# Logging Configuration
# =============================================================================

def setup_logging(
    service_name: str = "python-app",
    environment: str = "development",
    log_level: str = "INFO",
    json_output: bool = True,
) -> logging.Logger:
    """
    Configure logging for ELK stack.
    
    Args:
        service_name: Name of the service/application
        environment: Environment (development, staging, production)
        log_level: Logging level
        json_output: Whether to output JSON (True) or human-readable (False)
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_output:
        formatter = ELKJsonFormatter(
            service_name=service_name,
            environment=environment,
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# =============================================================================
# Context Manager for Request ID
# =============================================================================

class RequestContext:
    """Context manager for request-scoped logging context."""
    
    def __init__(self, request_id: Optional[str] = None, **extra_context):
        self.request_id = request_id or str(uuid.uuid4())
        self.extra_context = extra_context
        self.token = None
    
    def __enter__(self):
        self.token = request_id_var.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        request_id_var.reset(self.token)
        return False


# =============================================================================
# Structured Logger Class
# =============================================================================

class StructuredLogger:
    """
    Logger that adds structured context to all log messages.
    """
    
    def __init__(self, name: str, default_context: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(name)
        self.default_context = default_context or {}
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method that adds context."""
        # Merge default context with kwargs
        context = {**self.default_context, **kwargs}
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            context['request_id'] = request_id
        
        # Log with context as extra
        self.logger.log(level, message, extra=context)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger with additional context."""
        new_context = {**self.default_context, **kwargs}
        return StructuredLogger(self.logger.name, new_context)


# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Setup logging
    setup_logging(
        service_name="demo-service",
        environment="development",
        log_level="DEBUG",
        json_output=True,
    )
    
    logger = StructuredLogger("demo")
    
    print("=== Basic Logging ===")
    logger.info("Application started", version="1.0.0")
    logger.debug("Debug message", details={"key": "value"})
    
    print("\n=== Logging with Context ===")
    # Bind context to logger
    user_logger = logger.bind(user_id=123, user_email="user@example.com")
    user_logger.info("User logged in")
    user_logger.info("User performed action", action="purchase", item_id=456)
    
    print("\n=== Request Context ===")
    with RequestContext(request_id="req-12345") as ctx:
        logger.info("Processing request", endpoint="/api/users")
        logger.info("Request completed", status=200, duration_ms=45)
    
    print("\n=== Error Logging ===")
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("Error occurred", exc_info=True, operation="division")
