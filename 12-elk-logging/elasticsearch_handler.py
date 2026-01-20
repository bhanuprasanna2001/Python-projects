"""
Elasticsearch Custom Log Handler
================================
Direct logging to Elasticsearch without Logstash.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from queue import Queue
from threading import Thread, Event
import json
import atexit


# =============================================================================
# Elasticsearch Handler
# =============================================================================

class ElasticsearchHandler(logging.Handler):
    """
    Custom logging handler that sends logs directly to Elasticsearch.
    Uses buffering for efficiency.
    """
    
    def __init__(
        self,
        hosts: List[str] = ["http://localhost:9200"],
        index_prefix: str = "logs",
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        **es_kwargs
    ):
        """
        Initialize Elasticsearch handler.
        
        Args:
            hosts: List of Elasticsearch hosts
            index_prefix: Prefix for index names (will add date)
            buffer_size: Number of logs to buffer before flushing
            flush_interval: Seconds between automatic flushes
            **es_kwargs: Additional args for Elasticsearch client
        """
        super().__init__()
        
        from elasticsearch import Elasticsearch
        
        self.es = Elasticsearch(hosts, **es_kwargs)
        self.index_prefix = index_prefix
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Buffer for log records
        self.buffer: Queue = Queue()
        
        # Background flush thread
        self.stop_event = Event()
        self.flush_thread = Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
        
        # Register cleanup
        atexit.register(self.close)
    
    def emit(self, record: logging.LogRecord):
        """Handle a log record."""
        try:
            log_entry = self._format_record(record)
            self.buffer.put(log_entry)
            
            # Flush if buffer is full
            if self.buffer.qsize() >= self.buffer_size:
                self._flush()
        except Exception:
            self.handleError(record)
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record for Elasticsearch."""
        # Get the index name (with date)
        index = f"{self.index_prefix}-{datetime.utcnow():%Y.%m.%d}"
        
        # Build document
        doc = {
            '@timestamp': datetime.utcnow().isoformat() + 'Z',
            'message': record.getMessage(),
            'level': record.levelname,
            'logger': record.name,
            'source': {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName,
                'module': record.module,
            },
            'process': {
                'id': record.process,
                'name': record.processName,
            },
            'thread': {
                'id': record.thread,
                'name': record.threadName,
            },
        }
        
        # Add exception info
        if record.exc_info:
            import traceback
            doc['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stacktrace': ''.join(traceback.format_exception(*record.exc_info)),
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith('_'):
                try:
                    json.dumps(value)  # Check if serializable
                    doc[key] = value
                except (TypeError, ValueError):
                    doc[key] = str(value)
        
        return {'_index': index, '_source': doc}
    
    def _flush(self):
        """Flush buffered logs to Elasticsearch."""
        from elasticsearch.helpers import bulk
        
        # Collect all buffered items
        items = []
        while not self.buffer.empty():
            try:
                items.append(self.buffer.get_nowait())
            except Exception:
                break
        
        if items:
            try:
                # Bulk index
                actions = [
                    {
                        '_index': item['_index'],
                        '_source': item['_source'],
                    }
                    for item in items
                ]
                bulk(self.es, actions)
            except Exception as e:
                # Log to stderr instead of re-logging
                import sys
                print(f"Failed to flush logs to ES: {e}", file=sys.stderr)
    
    def _flush_worker(self):
        """Background worker for periodic flushing."""
        while not self.stop_event.wait(self.flush_interval):
            self._flush()
    
    def close(self):
        """Close the handler and flush remaining logs."""
        self.stop_event.set()
        self._flush()
        super().close()


# =============================================================================
# Async Elasticsearch Handler
# =============================================================================

class AsyncElasticsearchHandler(logging.Handler):
    """
    Async version of Elasticsearch handler using aiohttp.
    """
    
    def __init__(
        self,
        hosts: List[str] = ["http://localhost:9200"],
        index_prefix: str = "logs",
        buffer_size: int = 100,
    ):
        super().__init__()
        
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.buffer: List[Dict] = []
        self.buffer_size = buffer_size
    
    def emit(self, record: logging.LogRecord):
        """Buffer log record for async sending."""
        try:
            log_entry = self._format_record(record)
            self.buffer.append(log_entry)
            
            if len(self.buffer) >= self.buffer_size:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._async_flush())
                except RuntimeError:
                    # No running loop, create one
                    asyncio.run(self._async_flush())
        except Exception:
            self.handleError(record)
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record."""
        index = f"{self.index_prefix}-{datetime.utcnow():%Y.%m.%d}"
        
        return {
            '_index': index,
            '_source': {
                '@timestamp': datetime.utcnow().isoformat() + 'Z',
                'message': record.getMessage(),
                'level': record.levelname,
                'logger': record.name,
            }
        }
    
    async def _async_flush(self):
        """Flush logs asynchronously."""
        import aiohttp
        
        if not self.buffer:
            return
        
        items = self.buffer.copy()
        self.buffer.clear()
        
        # Build bulk request body
        body_lines = []
        for item in items:
            body_lines.append(json.dumps({'index': {'_index': item['_index']}}))
            body_lines.append(json.dumps(item['_source']))
        
        body = '\n'.join(body_lines) + '\n'
        
        async with aiohttp.ClientSession() as session:
            for host in self.hosts:
                try:
                    async with session.post(
                        f"{host}/_bulk",
                        data=body,
                        headers={'Content-Type': 'application/json'},
                    ) as resp:
                        if resp.status == 200:
                            return
                except Exception:
                    continue


# =============================================================================
# TCP/Logstash Handler
# =============================================================================

class LogstashTCPHandler(logging.Handler):
    """
    Handler that sends JSON logs to Logstash via TCP.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5000,
        **kwargs
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self._connect()
    
    def _connect(self):
        """Create TCP connection."""
        import socket
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
        except Exception as e:
            import sys
            print(f"Failed to connect to Logstash: {e}", file=sys.stderr)
            self.socket = None
    
    def emit(self, record: logging.LogRecord):
        """Send log record to Logstash."""
        if not self.socket:
            self._connect()
            if not self.socket:
                return
        
        try:
            log_entry = {
                '@timestamp': datetime.utcnow().isoformat() + 'Z',
                'message': record.getMessage(),
                'level': record.levelname,
                'logger': record.name,
                'source_file': record.filename,
                'source_line': record.lineno,
            }
            
            # Add exception if present
            if record.exc_info:
                import traceback
                log_entry['exception'] = ''.join(
                    traceback.format_exception(*record.exc_info)
                )
            
            # Send JSON + newline
            message = json.dumps(log_entry) + '\n'
            self.socket.send(message.encode('utf-8'))
            
        except Exception:
            self.handleError(record)
            self.socket = None
    
    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
        super().close()


# =============================================================================
# Setup Functions
# =============================================================================

def setup_elasticsearch_logging(
    es_hosts: List[str] = ["http://localhost:9200"],
    index_prefix: str = "app-logs",
    log_level: str = "INFO",
) -> logging.Logger:
    """Setup logging with Elasticsearch handler."""
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add ES handler
    es_handler = ElasticsearchHandler(
        hosts=es_hosts,
        index_prefix=index_prefix,
    )
    es_handler.setLevel(logging.DEBUG)
    logger.addHandler(es_handler)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    return logger


def setup_logstash_logging(
    host: str = "localhost",
    port: int = 5000,
    log_level: str = "INFO",
) -> logging.Logger:
    """Setup logging with Logstash TCP handler."""
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add Logstash handler
    logstash_handler = LogstashTCPHandler(host=host, port=port)
    logstash_handler.setLevel(logging.DEBUG)
    logger.addHandler(logstash_handler)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    return logger


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    # Setup with Elasticsearch
    logger = setup_elasticsearch_logging(
        es_hosts=["http://localhost:9200"],
        index_prefix="demo-logs",
    )
    
    # Log some messages
    logger.info("Application started", extra={"version": "1.0.0"})
    logger.warning("This is a warning", extra={"code": "WARN001"})
    
    try:
        raise ValueError("Something went wrong!")
    except Exception:
        logger.error("An error occurred", exc_info=True)
    
    print("Logs sent to Elasticsearch!")
