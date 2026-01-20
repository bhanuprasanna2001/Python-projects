"""
Synchronous Communication Patterns
==================================
HTTP/REST-based service-to-service communication.
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, List, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import random
import time


# =============================================================================
# Service Discovery
# =============================================================================

class ServiceRegistry:
    """
    Simple service registry for discovering service endpoints.
    In production, use tools like Consul, etcd, or Kubernetes DNS.
    """
    
    def __init__(self):
        self._services: Dict[str, List[str]] = {}
        self._health_status: Dict[str, bool] = {}
    
    def register(self, service_name: str, endpoint: str):
        """Register a service endpoint."""
        if service_name not in self._services:
            self._services[service_name] = []
        
        if endpoint not in self._services[service_name]:
            self._services[service_name].append(endpoint)
            self._health_status[endpoint] = True
        
        print(f"Registered {service_name} at {endpoint}")
    
    def deregister(self, service_name: str, endpoint: str):
        """Remove a service endpoint."""
        if service_name in self._services:
            self._services[service_name] = [
                e for e in self._services[service_name] if e != endpoint
            ]
            self._health_status.pop(endpoint, None)
    
    def get_endpoints(self, service_name: str) -> List[str]:
        """Get all endpoints for a service."""
        return self._services.get(service_name, [])
    
    def get_healthy_endpoint(self, service_name: str) -> Optional[str]:
        """Get a healthy endpoint using round-robin."""
        endpoints = self.get_endpoints(service_name)
        healthy = [e for e in endpoints if self._health_status.get(e, False)]
        
        if not healthy:
            return None
        
        # Simple round-robin (in production, use proper load balancing)
        return random.choice(healthy)
    
    def mark_unhealthy(self, endpoint: str):
        """Mark an endpoint as unhealthy."""
        self._health_status[endpoint] = False
    
    def mark_healthy(self, endpoint: str):
        """Mark an endpoint as healthy."""
        self._health_status[endpoint] = True


# Global registry
registry = ServiceRegistry()


# =============================================================================
# HTTP Client with Retry
# =============================================================================

class RetryStrategy(Enum):
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True
    retry_on_status: List[int] = None
    
    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 500, 502, 503, 504]
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        if self.strategy == RetryStrategy.NONE:
            return 0
        
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        
        elif self.strategy == RetryStrategy.FIBONACCI:
            a, b = 1, 1
            for _ in range(attempt):
                a, b = b, a + b
            delay = self.base_delay * a
        
        else:
            delay = self.base_delay
        
        # Apply max delay cap
        delay = min(delay, self.max_delay)
        
        # Add jitter
        if self.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay


class ServiceClient:
    """
    HTTP client for service-to-service communication with:
    - Retry with backoff
    - Timeout handling
    - Circuit breaker integration
    - Request tracing
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        timeout: float = 10.0,
    ):
        self.retry_config = retry_config or RetryConfig()
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.
        """
        client = await self.get_client()
        
        # Add correlation ID header
        request_headers = headers or {}
        if correlation_id:
            request_headers["X-Correlation-ID"] = correlation_id
        
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json,
                    params=params,
                )
                
                # Check if we should retry based on status
                if response.status_code in self.retry_config.retry_on_status:
                    if attempt < self.retry_config.max_retries:
                        delay = self.retry_config.get_delay(attempt)
                        print(f"Retry {attempt + 1}/{self.retry_config.max_retries} "
                              f"for {method} {url} (status {response.status_code}), "
                              f"waiting {delay:.2f}s")
                        await asyncio.sleep(delay)
                        continue
                
                return response
                
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    print(f"Timeout on {method} {url}, retry {attempt + 1}, "
                          f"waiting {delay:.2f}s")
                    await asyncio.sleep(delay)
                    continue
                raise
                
            except httpx.RequestError as e:
                last_error = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    print(f"Error on {method} {url}: {e}, retry {attempt + 1}, "
                          f"waiting {delay:.2f}s")
                    await asyncio.sleep(delay)
                    continue
                raise
        
        # If we get here, all retries exhausted
        if last_error:
            raise last_error
        raise Exception("All retries exhausted")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)


# =============================================================================
# Request/Response Patterns
# =============================================================================

@dataclass
class ServiceRequest:
    """Standardized service request."""
    service: str
    method: str
    path: str
    data: Optional[Dict] = None
    params: Optional[Dict] = None
    headers: Optional[Dict] = None
    correlation_id: Optional[str] = None
    timeout: Optional[float] = None


@dataclass
class ServiceResponse:
    """Standardized service response."""
    status_code: int
    data: Optional[Dict]
    headers: Dict
    latency_ms: float
    service: str
    success: bool
    error: Optional[str] = None


class ServiceGateway:
    """
    Gateway for making service calls with:
    - Service discovery
    - Load balancing
    - Response normalization
    """
    
    def __init__(self, registry: ServiceRegistry, client: ServiceClient):
        self.registry = registry
        self.client = client
    
    async def call(self, request: ServiceRequest) -> ServiceResponse:
        """Make a service call."""
        start_time = time.perf_counter()
        
        # Get service endpoint
        endpoint = self.registry.get_healthy_endpoint(request.service)
        
        if not endpoint:
            return ServiceResponse(
                status_code=503,
                data=None,
                headers={},
                latency_ms=0,
                service=request.service,
                success=False,
                error=f"No healthy endpoints for service '{request.service}'",
            )
        
        url = f"{endpoint}{request.path}"
        
        try:
            response = await self.client.request(
                method=request.method,
                url=url,
                json=request.data,
                params=request.params,
                headers=request.headers,
                correlation_id=request.correlation_id,
            )
            
            latency = (time.perf_counter() - start_time) * 1000
            
            return ServiceResponse(
                status_code=response.status_code,
                data=response.json() if response.content else None,
                headers=dict(response.headers),
                latency_ms=latency,
                service=request.service,
                success=200 <= response.status_code < 300,
            )
            
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            
            # Mark endpoint as unhealthy
            self.registry.mark_unhealthy(endpoint)
            
            return ServiceResponse(
                status_code=500,
                data=None,
                headers={},
                latency_ms=latency,
                service=request.service,
                success=False,
                error=str(e),
            )


# =============================================================================
# Parallel Requests
# =============================================================================

async def parallel_calls(
    gateway: ServiceGateway,
    requests: List[ServiceRequest],
) -> List[ServiceResponse]:
    """
    Execute multiple service calls in parallel.
    """
    tasks = [gateway.call(req) for req in requests]
    return await asyncio.gather(*tasks)


async def call_with_fallback(
    gateway: ServiceGateway,
    primary: ServiceRequest,
    fallback: ServiceRequest,
) -> ServiceResponse:
    """
    Try primary service, fall back to secondary on failure.
    """
    response = await gateway.call(primary)
    
    if not response.success:
        print(f"Primary service '{primary.service}' failed, trying fallback")
        response = await gateway.call(fallback)
    
    return response


# =============================================================================
# Demo
# =============================================================================

async def demo():
    """Demonstrate synchronous communication patterns."""
    
    print("=" * 60)
    print("Synchronous Communication Patterns Demo")
    print("=" * 60)
    
    # Setup
    registry.register("user", "http://localhost:8001")
    registry.register("order", "http://localhost:8002")
    
    client = ServiceClient(
        retry_config=RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=0.5,
        )
    )
    
    gateway = ServiceGateway(registry, client)
    
    # 1. Simple call
    print("\n1. Simple Service Call")
    print("-" * 40)
    
    request = ServiceRequest(
        service="user",
        method="GET",
        path="/users",
        correlation_id="demo-123",
    )
    
    response = await gateway.call(request)
    print(f"Status: {response.status_code}")
    print(f"Latency: {response.latency_ms:.2f}ms")
    print(f"Success: {response.success}")
    
    # 2. Parallel calls
    print("\n2. Parallel Service Calls")
    print("-" * 40)
    
    requests = [
        ServiceRequest("user", "GET", "/users/1", correlation_id="parallel-1"),
        ServiceRequest("order", "GET", "/orders", correlation_id="parallel-2"),
    ]
    
    responses = await parallel_calls(gateway, requests)
    
    for req, resp in zip(requests, responses):
        print(f"{req.service}: {resp.status_code} ({resp.latency_ms:.2f}ms)")
    
    # 3. Call with timeout demo
    print("\n3. Timeout Handling")
    print("-" * 40)
    
    short_timeout_client = ServiceClient(
        retry_config=RetryConfig(max_retries=1),
        timeout=0.001,  # Very short timeout
    )
    
    short_gateway = ServiceGateway(registry, short_timeout_client)
    
    request = ServiceRequest(
        service="user",
        method="GET",
        path="/users",
    )
    
    response = await short_gateway.call(request)
    print(f"Status: {response.status_code}")
    print(f"Error: {response.error}")
    
    # Cleanup
    await client.close()
    await short_timeout_client.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("""
    ================================================
    Synchronous Communication Patterns
    ================================================
    
    This module demonstrates:
    
    1. Service Discovery
       - Register/deregister services
       - Health-based endpoint selection
    
    2. HTTP Client with Retry
       - Multiple retry strategies
       - Jitter and backoff
       - Configurable retry conditions
    
    3. Request/Response Patterns
       - Standardized request/response objects
       - Latency tracking
       - Error handling
    
    4. Advanced Patterns
       - Parallel service calls
       - Fallback patterns
    
    Start the User and Order services first:
    - python services/user_service.py
    - python services/order_service.py
    ================================================
    """)
    
    asyncio.run(demo())
