"""
API Gateway
===========
Central entry point that routes requests to backend services.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import time
from typing import Dict
import asyncio

app = FastAPI(
    title="API Gateway",
    description="Central gateway for microservices",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Service Registry
# ============================================================

SERVICES: Dict[str, str] = {
    "users": "http://localhost:8001",
    "products": "http://localhost:8002",
}


# ============================================================
# Middleware
# ============================================================

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add request timing to response headers."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing."""
    import uuid
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# ============================================================
# Gateway Endpoints
# ============================================================

@app.get("/")
async def root():
    """Gateway health check."""
    return {
        "service": "API Gateway",
        "status": "healthy",
        "services": list(SERVICES.keys())
    }


@app.get("/health")
async def health_check():
    """Check health of all backend services."""
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, base_url in SERVICES.items():
            try:
                response = await client.get(f"{base_url}/health")
                results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                results[service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
    
    return {
        "gateway": "healthy",
        "services": results
    }


# ============================================================
# Proxy Routes
# ============================================================

@app.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_request(service: str, path: str, request: Request):
    """
    Proxy requests to backend services.
    
    Example:
        GET /api/users/1 -> GET http://localhost:8001/1
        POST /api/products -> POST http://localhost:8002/
    """
    if service not in SERVICES:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found"
        )
    
    base_url = SERVICES[service]
    target_url = f"{base_url}/{path}"
    
    # Forward request headers
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header
    
    # Get request body
    body = await request.body()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            return JSONResponse(
                content=response.json() if response.content else None,
                status_code=response.status_code,
                headers={
                    "X-Upstream-Service": service,
                    "X-Upstream-Response-Time": str(response.elapsed.total_seconds())
                }
            )
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Service '{service}' timeout"
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Service '{service}' unavailable"
            )


# ============================================================
# Aggregation Endpoints
# ============================================================

@app.get("/api/dashboard")
async def dashboard():
    """
    Aggregate data from multiple services.
    Demonstrates service composition.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Parallel requests to multiple services
        tasks = [
            client.get(f"{SERVICES['users']}/stats"),
            client.get(f"{SERVICES['products']}/stats"),
        ]
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            result = {}
            
            for i, (service, response) in enumerate(zip(["users", "products"], responses)):
                if isinstance(response, Exception):
                    result[service] = {"error": str(response)}
                else:
                    result[service] = response.json() if response.status_code == 200 else {"error": "Failed"}
            
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Dashboard aggregation failed: {str(e)}"
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
