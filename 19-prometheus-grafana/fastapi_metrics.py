"""
FastAPI with Prometheus Metrics
===============================
Complete FastAPI application with Prometheus instrumentation.
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    REGISTRY,
)
import time
import random
import asyncio
from functools import wraps
from typing import Callable
import psutil


# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(title="Metrics Demo API")


# =============================================================================
# Define Metrics
# =============================================================================

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

# Response size
RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000]
)

# Error metrics
EXCEPTIONS_TOTAL = Counter(
    'http_exceptions_total',
    'Total HTTP exceptions',
    ['method', 'endpoint', 'exception_type']
)

# Application info
APP_INFO = Info('fastapi_app', 'Application information')
APP_INFO.info({
    'version': '1.0.0',
    'environment': 'development',
})

# System metrics
SYSTEM_CPU_USAGE = Gauge('system_cpu_usage_percent', 'System CPU usage')
SYSTEM_MEMORY_USAGE = Gauge('system_memory_usage_percent', 'System memory usage')
PROCESS_MEMORY = Gauge('process_memory_bytes', 'Process memory usage')


# =============================================================================
# Metrics Middleware
# =============================================================================

@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to collect metrics for all requests.
    """
    method = request.method
    path = request.url.path
    
    # Skip metrics endpoint itself
    if path == "/metrics":
        return await call_next(request)
    
    # Normalize path to avoid high cardinality
    # e.g., /users/123 -> /users/{id}
    endpoint = normalize_path(path)
    
    # Track in-progress requests
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    
    # Measure latency
    start_time = time.perf_counter()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        latency = time.perf_counter() - start_time
        status = str(response.status_code)
        
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
        
        # Response size
        if hasattr(response, 'body'):
            RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(len(response.body))
        
        return response
        
    except Exception as e:
        # Track exceptions
        EXCEPTIONS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            exception_type=type(e).__name__
        ).inc()
        raise
        
    finally:
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()


def normalize_path(path: str) -> str:
    """
    Normalize path to reduce cardinality.
    Replace numeric IDs with placeholders.
    """
    parts = path.split('/')
    normalized = []
    
    for part in parts:
        if part.isdigit():
            normalized.append('{id}')
        elif part and len(part) == 36 and '-' in part:  # UUID-like
            normalized.append('{uuid}')
        else:
            normalized.append(part)
    
    return '/'.join(normalized) or '/'


# =============================================================================
# Background Task: System Metrics
# =============================================================================

async def update_system_metrics():
    """Background task to update system metrics."""
    while True:
        try:
            # CPU usage
            SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
            
            # Memory usage
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.percent)
            
            # Process memory
            process = psutil.Process()
            PROCESS_MEMORY.set(process.memory_info().rss)
            
        except Exception as e:
            print(f"Error updating system metrics: {e}")
        
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup."""
    asyncio.create_task(update_system_metrics())


# =============================================================================
# Metrics Endpoint
# =============================================================================

@app.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics.
    """
    return PlainTextResponse(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# Demo Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FastAPI Metrics Demo",
        "endpoints": {
            "/metrics": "Prometheus metrics",
            "/users": "Get users",
            "/users/{id}": "Get user by ID",
            "/slow": "Slow endpoint (random latency)",
            "/error": "Error endpoint",
        }
    }


@app.get("/users")
async def get_users():
    """Get all users."""
    # Simulate some work
    await asyncio.sleep(random.uniform(0.01, 0.05))
    
    return {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
    }


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    await asyncio.sleep(random.uniform(0.01, 0.03))
    
    if user_id > 100:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"id": user_id, "name": f"User {user_id}"}


@app.post("/users")
async def create_user(name: str = "New User"):
    """Create a new user."""
    await asyncio.sleep(random.uniform(0.02, 0.1))
    
    return {"id": random.randint(100, 999), "name": name}


@app.get("/slow")
async def slow_endpoint():
    """Endpoint with random latency."""
    # Simulate variable latency
    latency = random.expovariate(1/0.5)  # Mean 0.5 seconds
    await asyncio.sleep(min(latency, 5))  # Cap at 5 seconds
    
    return {"message": "Slow response", "latency": latency}


@app.get("/error")
async def error_endpoint():
    """Endpoint that sometimes fails."""
    if random.random() < 0.5:
        raise HTTPException(status_code=500, detail="Random error")
    
    return {"message": "Success (lucky!)"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
    }


# =============================================================================
# Custom Business Metrics
# =============================================================================

# Business metrics
ORDERS_CREATED = Counter('orders_created_total', 'Total orders created', ['status'])
ORDER_VALUE = Histogram(
    'order_value_dollars',
    'Order value in dollars',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)
ACTIVE_CARTS = Gauge('active_carts', 'Number of active shopping carts')


@app.post("/orders")
async def create_order():
    """Create an order (simulated)."""
    order_value = random.uniform(20, 500)
    
    # Simulate processing
    await asyncio.sleep(random.uniform(0.05, 0.2))
    
    # Randomly succeed or fail
    if random.random() < 0.9:
        ORDERS_CREATED.labels(status='success').inc()
        ORDER_VALUE.observe(order_value)
        return {"order_id": random.randint(1000, 9999), "value": order_value}
    else:
        ORDERS_CREATED.labels(status='failed').inc()
        raise HTTPException(status_code=500, detail="Order processing failed")


@app.post("/cart/add")
async def add_to_cart():
    """Add item to cart."""
    ACTIVE_CARTS.inc()
    return {"message": "Item added to cart"}


@app.post("/cart/checkout")
async def checkout():
    """Checkout cart."""
    ACTIVE_CARTS.dec()
    return {"message": "Checkout complete"}


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    FastAPI Metrics Demo
    ================================================
    
    Endpoints:
    - GET /metrics - Prometheus metrics
    - GET /users - List users
    - GET /users/{id} - Get user
    - POST /orders - Create order
    - GET /slow - Slow endpoint
    - GET /error - Error endpoint
    
    Metrics available at: http://localhost:8000/metrics
    
    Try these PromQL queries in Prometheus:
    - rate(http_requests_total[5m])
    - histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
    - http_requests_in_progress
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
