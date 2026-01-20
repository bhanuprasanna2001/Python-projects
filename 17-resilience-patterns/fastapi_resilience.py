"""
FastAPI Resilience Patterns
===========================
Complete FastAPI application with all resilience patterns integrated.
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from typing import Optional
import asyncio
import random
import time

from rate_limiting import TokenBucket, PerKeyRateLimiter
from retry_patterns import async_retry, BackoffStrategy
from circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError,
    CircuitBreakerRegistry
)


# =============================================================================
# FastAPI App Setup
# =============================================================================

# Rate limiter using slowapi
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Resilience Patterns API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# =============================================================================
# Custom Rate Limiters
# =============================================================================

# Token bucket for API calls
api_bucket = TokenBucket(rate=10, capacity=20)

# Per-user rate limiter
user_rate_limiter = PerKeyRateLimiter(
    lambda: TokenBucket(rate=5, capacity=10)
)


# =============================================================================
# Circuit Breakers
# =============================================================================

# Registry for circuit breakers
cb_registry = CircuitBreakerRegistry()

# Circuit breaker for external API
external_api_cb = cb_registry.get_or_create(
    "external_api",
    CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=30.0,
    )
)

# Circuit breaker for database
database_cb = cb_registry.get_or_create(
    "database",
    CircuitBreakerConfig(
        failure_threshold=5,
        timeout=10.0,
    )
)


# =============================================================================
# Simulated External Service
# =============================================================================

class ExternalServiceSimulator:
    """Simulates an unreliable external service."""
    
    def __init__(self, failure_rate: float = 0.3):
        self.failure_rate = failure_rate
        self.call_count = 0
    
    async def call(self) -> dict:
        """Simulate an API call."""
        self.call_count += 1
        
        # Simulate network latency
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Randomly fail
        if random.random() < self.failure_rate:
            raise ConnectionError("External service unavailable")
        
        return {
            "status": "success",
            "call_number": self.call_count,
            "timestamp": time.time(),
        }


external_service = ExternalServiceSimulator(failure_rate=0.3)


# =============================================================================
# Dependencies
# =============================================================================

async def check_rate_limit(request: Request) -> None:
    """Custom rate limit check using token bucket."""
    if not api_bucket.acquire():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(int(api_bucket.get_wait_time()) + 1)},
        )


async def check_user_rate_limit(
    request: Request,
    user_id: Optional[str] = None
) -> None:
    """Per-user rate limiting."""
    key = user_id or get_remote_address(request)
    
    if not user_rate_limiter.acquire(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for user/IP: {key}",
        )


# =============================================================================
# Models
# =============================================================================

class ExternalCallResponse(BaseModel):
    status: str
    call_number: int
    circuit_state: str
    retries_used: Optional[int] = None


class CircuitBreakerStats(BaseModel):
    name: str
    state: str
    failure_count: int
    success_count: int
    failure_rate: float


# =============================================================================
# Retry-wrapped Service Call
# =============================================================================

@async_retry(
    max_retries=3,
    initial_delay=0.5,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions=(ConnectionError,),
)
async def call_external_with_retry() -> dict:
    """Call external service with retry logic."""
    return await external_service.call()


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "message": "Resilience Patterns API",
        "endpoints": {
            "/external/call": "Call external service (with retry + circuit breaker)",
            "/external/call-simple": "Call without resilience patterns",
            "/rate-limited": "Rate limited endpoint",
            "/user-rate-limited": "Per-user rate limited endpoint",
            "/circuit-breakers": "Circuit breaker stats",
        },
    }


@app.get("/external/call", response_model=ExternalCallResponse)
async def call_external_service(
    _: None = Depends(check_rate_limit)
):
    """
    Call external service with full resilience patterns:
    - Rate limiting
    - Circuit breaker
    - Retry with exponential backoff
    """
    # Check circuit breaker
    if not external_api_cb.can_execute():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable (circuit breaker open)",
            headers={"Retry-After": str(int(external_api_cb.config.timeout))},
        )
    
    try:
        # Call with retry
        result = await call_external_with_retry()
        external_api_cb.record_result(success=True)
        
        return ExternalCallResponse(
            status=result["status"],
            call_number=result["call_number"],
            circuit_state=external_api_cb.state.value,
        )
        
    except ConnectionError as e:
        external_api_cb.record_result(success=False, exception=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service failed after retries: {str(e)}",
        )


@app.get("/external/call-simple")
async def call_external_simple():
    """
    Call external service without resilience patterns.
    Demonstrates what happens without protection.
    """
    try:
        result = await external_service.call()
        return result
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@app.get("/rate-limited")
@limiter.limit("5/minute")
async def rate_limited_endpoint(request: Request):
    """
    Rate limited endpoint using slowapi.
    Allows 5 requests per minute per IP.
    """
    return {
        "message": "This endpoint is rate limited",
        "limit": "5 requests per minute",
        "client_ip": get_remote_address(request),
    }


@app.get("/user-rate-limited/{user_id}")
async def user_rate_limited_endpoint(
    user_id: str,
    request: Request,
    _: None = Depends(check_user_rate_limit)
):
    """
    Per-user rate limited endpoint.
    Each user has their own rate limit bucket.
    """
    return {
        "message": f"Request allowed for user {user_id}",
        "user_id": user_id,
    }


@app.get("/circuit-breakers")
async def get_circuit_breakers():
    """Get status of all circuit breakers."""
    return cb_registry.get_all_stats()


@app.get("/circuit-breakers/{name}")
async def get_circuit_breaker(name: str):
    """Get status of a specific circuit breaker."""
    cb = cb_registry.get(name)
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )
    return cb.get_stats()


@app.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str):
    """Manually reset a circuit breaker."""
    cb = cb_registry.get(name)
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )
    cb.reset()
    return {"message": f"Circuit breaker '{name}' reset", "stats": cb.get_stats()}


@app.get("/rate-limit/status")
async def rate_limit_status():
    """Get current rate limit status."""
    return {
        "global_bucket": {
            "tokens_available": api_bucket.tokens,
            "capacity": api_bucket.capacity,
            "rate": api_bucket.rate,
        },
    }


# =============================================================================
# Middleware for Global Timeout
# =============================================================================

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Add timeout to all requests."""
    try:
        response = await asyncio.wait_for(
            call_next(request),
            timeout=30.0  # 30 second timeout
        )
        return response
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": "Request timeout"},
        )


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(CircuitBreakerOpenError)
async def circuit_breaker_exception_handler(
    request: Request,
    exc: CircuitBreakerOpenError
):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "type": "circuit_breaker_open",
        },
        headers={"Retry-After": "30"},
    )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check with circuit breaker status."""
    cb_stats = cb_registry.get_all_stats()
    
    # Check if any circuit breaker is open
    any_open = any(
        stats["state"] == "open"
        for stats in cb_stats.values()
    )
    
    return {
        "status": "degraded" if any_open else "healthy",
        "circuit_breakers": cb_stats,
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    Resilience Patterns API
    ================================================
    
    Endpoints:
    - GET /external/call - Protected external call
    - GET /rate-limited - Rate limited (5/min)
    - GET /circuit-breakers - View circuit breaker status
    - POST /circuit-breakers/{name}/reset - Reset circuit breaker
    
    Try making multiple rapid requests to see rate limiting.
    Make failing requests to see circuit breaker in action.
    
    OpenAPI docs: http://localhost:8000/docs
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
