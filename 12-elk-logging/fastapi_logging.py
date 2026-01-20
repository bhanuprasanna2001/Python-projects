"""
FastAPI Logging Integration
===========================
Comprehensive logging for FastAPI applications with ELK support.
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar
from datetime import datetime
import logging
import json
import time
import uuid
from typing import Optional, Callable
import traceback

from structured_logging import setup_logging, StructuredLogger, request_id_var


# =============================================================================
# Setup Logging
# =============================================================================

setup_logging(
    service_name="fastapi-demo",
    environment="development",
    log_level="DEBUG",
    json_output=True,
)

logger = StructuredLogger("fastapi.app")


# =============================================================================
# Request Context Middleware
# =============================================================================

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request context to logs.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Set context variable
        token = request_id_var.set(request_id)
        
        # Store in request state
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(e),
                exc_info=True,
            )
            raise
            
        finally:
            request_id_var.reset(token)


# =============================================================================
# Exception Handler
# =============================================================================

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with logging."""
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Log the exception
    logger.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    
    # Return error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_id": request_id,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP exception handler with logging."""
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Log based on status code
    if exc.status_code >= 500:
        logger.error(
            "HTTP error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
    elif exc.status_code >= 400:
        logger.warning(
            "Client error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id,
        },
    )


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="FastAPI Logging Demo")

# Add middleware
app.add_middleware(RequestContextMiddleware)

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


# =============================================================================
# Logging Decorators
# =============================================================================

def log_function_call(func):
    """Decorator to log function calls."""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_logger = StructuredLogger(f"fastapi.{func.__module__}.{func.__name__}")
        
        func_logger.debug(
            "Function called",
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            
            func_logger.debug(
                "Function completed",
                duration_ms=round(duration, 2),
            )
            return result
            
        except Exception as e:
            duration = (time.time() - start) * 1000
            func_logger.error(
                "Function failed",
                duration_ms=round(duration, 2),
                error=str(e),
                exc_info=True,
            )
            raise
    
    return wrapper


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    return {"message": "FastAPI Logging Demo", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/users/{user_id}")
@log_function_call
async def get_user(user_id: int):
    """Get user by ID with logging."""
    
    # Create user-scoped logger
    user_logger = logger.bind(user_id=user_id)
    
    user_logger.info("Fetching user")
    
    # Simulate database lookup
    if user_id <= 0:
        user_logger.warning("Invalid user ID")
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if user_id > 1000:
        user_logger.info("User not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Simulate fetching user
    user = {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
    }
    
    user_logger.info("User fetched successfully", user_email=user["email"])
    
    return user


@app.post("/users")
async def create_user(name: str, email: str):
    """Create user with logging."""
    
    logger.info(
        "Creating user",
        user_name=name,
        user_email=email,
    )
    
    # Simulate creation
    user = {
        "id": 123,
        "name": name,
        "email": email,
    }
    
    logger.info(
        "User created",
        user_id=user["id"],
    )
    
    return user


@app.get("/error")
async def trigger_error():
    """Endpoint that triggers an error."""
    logger.warning("About to trigger error")
    raise ValueError("This is a test error!")


@app.get("/slow")
async def slow_endpoint():
    """Slow endpoint for timing demonstration."""
    import asyncio
    
    logger.info("Starting slow operation")
    
    await asyncio.sleep(2)
    
    logger.info("Slow operation completed")
    
    return {"message": "Operation completed"}


@app.get("/nested")
async def nested_logging():
    """Demonstrate nested logging with context."""
    
    # Parent context
    logger.info("Starting nested operation")
    
    # Child operation 1
    child_logger = logger.bind(operation="child_1")
    child_logger.info("Processing child operation 1")
    
    # Child operation 2
    child_logger = logger.bind(operation="child_2")
    child_logger.info("Processing child operation 2")
    
    # Grandchild
    grandchild_logger = child_logger.bind(sub_operation="grandchild")
    grandchild_logger.info("Processing grandchild operation")
    
    logger.info("Nested operation completed")
    
    return {"message": "Nested operations completed"}


# =============================================================================
# Database Query Logging Example
# =============================================================================

class DatabaseLogger:
    """Example of logging database operations."""
    
    def __init__(self):
        self.logger = StructuredLogger("fastapi.database")
    
    async def execute_query(self, query: str, params: dict = None):
        """Execute query with logging."""
        
        self.logger.debug(
            "Executing query",
            query=query[:100],  # Truncate for safety
            params_keys=list(params.keys()) if params else [],
        )
        
        start = time.time()
        
        try:
            # Simulate query execution
            import asyncio
            await asyncio.sleep(0.1)
            result = {"rows": 10}
            
            duration = (time.time() - start) * 1000
            
            self.logger.debug(
                "Query completed",
                duration_ms=round(duration, 2),
                rows_affected=result.get("rows", 0),
            )
            
            return result
            
        except Exception as e:
            duration = (time.time() - start) * 1000
            
            self.logger.error(
                "Query failed",
                duration_ms=round(duration, 2),
                error=str(e),
                exc_info=True,
            )
            raise


db = DatabaseLogger()


@app.get("/db-demo")
async def database_demo():
    """Demonstrate database logging."""
    
    result = await db.execute_query(
        "SELECT * FROM users WHERE id = :id",
        {"id": 123}
    )
    
    return {"result": result}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "Starting FastAPI application",
        host="0.0.0.0",
        port=8000,
    )
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
