"""
API Gateway
===========
Central entry point for all microservices.
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import asyncio
from datetime import datetime, timezone
import uuid
import time


# =============================================================================
# Configuration
# =============================================================================

class ServiceConfig:
    """Service registry configuration."""
    
    SERVICES = {
        "user": "http://localhost:8001",
        "order": "http://localhost:8002",
        "notification": "http://localhost:8003",
    }
    
    TIMEOUT = 10.0
    RETRY_COUNT = 3


# =============================================================================
# Gateway App
# =============================================================================

app = FastAPI(
    title="API Gateway",
    description="Central gateway for microservices",
    version="1.0.0",
)


# =============================================================================
# HTTP Client
# =============================================================================

class ServiceClient:
    """
    HTTP client for calling downstream services.
    """
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=ServiceConfig.TIMEOUT,
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def call_service(
        self,
        service: str,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Call a downstream service.
        """
        base_url = ServiceConfig.SERVICES.get(service)
        if not base_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service}' not found"
            )
        
        client = await self.get_client()
        url = f"{base_url}{path}"
        
        try:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service '{service}' timeout"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service '{service}' unavailable: {str(e)}"
            )


service_client = ServiceClient()


@app.on_event("shutdown")
async def shutdown_event():
    await service_client.close()


# =============================================================================
# Middleware
# =============================================================================

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID for request tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Store in request state for later use
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    
    # Add to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.perf_counter()
    
    response = await call_next(request)
    
    duration = time.perf_counter() - start_time
    print(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    
    return response


# =============================================================================
# Gateway Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Gateway information."""
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "services": list(ServiceConfig.SERVICES.keys()),
    }


@app.get("/health")
async def health():
    """Gateway health check."""
    return {"status": "healthy"}


@app.get("/services/health")
async def services_health():
    """Check health of all downstream services."""
    health_status = {}
    
    async def check_service(name: str, url: str):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/health")
                return name, "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            return name, "unavailable"
    
    tasks = [
        check_service(name, url)
        for name, url in ServiceConfig.SERVICES.items()
    ]
    
    results = await asyncio.gather(*tasks)
    health_status = dict(results)
    
    overall = "healthy" if all(s == "healthy" for s in health_status.values()) else "degraded"
    
    return {
        "gateway": "healthy",
        "services": health_status,
        "overall": overall,
    }


# =============================================================================
# User Service Routes
# =============================================================================

@app.get("/users")
async def get_users(request: Request):
    """Get all users."""
    return await service_client.call_service(
        service="user",
        method="GET",
        path="/users",
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    """Get user by ID."""
    return await service_client.call_service(
        service="user",
        method="GET",
        path=f"/users/{user_id}",
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


@app.post("/users")
async def create_user(request: Request):
    """Create a new user."""
    data = await request.json()
    return await service_client.call_service(
        service="user",
        method="POST",
        path="/users",
        data=data,
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


# =============================================================================
# Order Service Routes
# =============================================================================

@app.get("/orders")
async def get_orders(request: Request, user_id: Optional[int] = None):
    """Get orders."""
    path = f"/orders?user_id={user_id}" if user_id else "/orders"
    return await service_client.call_service(
        service="order",
        method="GET",
        path=path,
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


@app.get("/orders/{order_id}")
async def get_order(order_id: int, request: Request):
    """Get order by ID."""
    return await service_client.call_service(
        service="order",
        method="GET",
        path=f"/orders/{order_id}",
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


@app.post("/orders")
async def create_order(request: Request):
    """Create a new order."""
    data = await request.json()
    return await service_client.call_service(
        service="order",
        method="POST",
        path="/orders",
        data=data,
        headers={"X-Correlation-ID": request.state.correlation_id},
    )


# =============================================================================
# Aggregated Endpoints (Backend for Frontend pattern)
# =============================================================================

@app.get("/users/{user_id}/profile")
async def get_user_profile(user_id: int, request: Request):
    """
    Get user profile with orders (aggregated response).
    Demonstrates the BFF (Backend for Frontend) pattern.
    """
    headers = {"X-Correlation-ID": request.state.correlation_id}
    
    # Fetch user and orders in parallel
    user_task = service_client.call_service(
        "user", "GET", f"/users/{user_id}", headers=headers
    )
    orders_task = service_client.call_service(
        "order", "GET", f"/orders?user_id={user_id}", headers=headers
    )
    
    try:
        user, orders = await asyncio.gather(user_task, orders_task)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        raise
    
    # Aggregate response
    return {
        "user": user,
        "orders": orders,
        "summary": {
            "total_orders": len(orders) if isinstance(orders, list) else 0,
        },
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    API Gateway
    ================================================
    
    Gateway endpoints:
    - GET /users - List users
    - GET /users/{id} - Get user
    - GET /orders - List orders
    - GET /orders/{id} - Get order
    - GET /users/{id}/profile - Aggregated user profile
    
    Health:
    - GET /health - Gateway health
    - GET /services/health - All services health
    
    Make sure to start the microservices first:
    - User Service: port 8001
    - Order Service: port 8002
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
