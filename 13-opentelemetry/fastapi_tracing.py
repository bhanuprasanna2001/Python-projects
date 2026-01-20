"""
FastAPI with OpenTelemetry Tracing
==================================
Complete FastAPI application with distributed tracing.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
import time
import random

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

# Instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Propagation
from opentelemetry.propagate import inject, extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


# =============================================================================
# Setup Tracing
# =============================================================================

def setup_tracing(service_name: str) -> trace.Tracer:
    """Configure OpenTelemetry with Jaeger exporter."""
    
    # Resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })
    
    # Create provider
    provider = TracerProvider(resource=resource)
    
    # Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    # Alternative: OTLP exporter
    # otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    # provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set global provider
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)


# =============================================================================
# FastAPI Application
# =============================================================================

tracer = setup_tracing("fastapi-demo")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting FastAPI with OpenTelemetry tracing...")
    
    # Instrument httpx for outgoing requests
    HTTPXClientInstrumentor().instrument()
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="FastAPI OpenTelemetry Demo",
    lifespan=lifespan,
)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)


# =============================================================================
# Custom Tracing Middleware
# =============================================================================

@app.middleware("http")
async def add_trace_info(request: Request, call_next):
    """Middleware to add trace info to response headers."""
    response = await call_next(request)
    
    # Get current span
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        response.headers["X-Trace-ID"] = format(ctx.trace_id, '032x')
        response.headers["X-Span-ID"] = format(ctx.span_id, '016x')
    
    return response


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FastAPI OpenTelemetry Demo",
        "docs": "/docs",
        "jaeger_ui": "http://localhost:16686",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user with custom spans."""
    
    with tracer.start_as_current_span("fetch-user-data") as span:
        span.set_attribute("user.id", user_id)
        
        # Simulate database lookup
        with tracer.start_as_current_span("database-query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", "SELECT * FROM users WHERE id = ?")
            
            # Simulate query time
            await asyncio.sleep(0.1)
            
            if user_id > 1000:
                raise HTTPException(status_code=404, detail="User not found")
        
        # Simulate processing
        with tracer.start_as_current_span("process-user-data"):
            await asyncio.sleep(0.05)
        
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }


@app.post("/orders")
async def create_order(user_id: int, product_id: int, quantity: int = 1):
    """Create order with multiple traced operations."""
    
    with tracer.start_as_current_span("create-order") as span:
        span.set_attribute("order.user_id", user_id)
        span.set_attribute("order.product_id", product_id)
        span.set_attribute("order.quantity", quantity)
        
        # Validate user
        with tracer.start_as_current_span("validate-user"):
            await asyncio.sleep(0.05)
        
        # Check inventory
        with tracer.start_as_current_span("check-inventory") as inv_span:
            inv_span.set_attribute("inventory.product_id", product_id)
            await asyncio.sleep(0.05)
            
            # Simulate inventory check
            available = random.randint(0, 100)
            inv_span.set_attribute("inventory.available", available)
            
            if available < quantity:
                span.add_event("Insufficient inventory", {
                    "available": available,
                    "requested": quantity,
                })
                raise HTTPException(400, "Insufficient inventory")
        
        # Create order in database
        with tracer.start_as_current_span("save-order") as db_span:
            db_span.set_attribute("db.operation", "INSERT")
            await asyncio.sleep(0.1)
            order_id = random.randint(1000, 9999)
            db_span.set_attribute("order.id", order_id)
        
        # Send notification
        with tracer.start_as_current_span("send-notification") as notif_span:
            notif_span.set_attribute("notification.type", "email")
            notif_span.set_attribute("notification.recipient", f"user{user_id}@example.com")
            await asyncio.sleep(0.05)
        
        span.add_event("Order created", {"order_id": order_id})
        
        return {
            "order_id": order_id,
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "status": "created",
        }


@app.get("/chain")
async def chain_call():
    """
    Demonstrate cross-service tracing with HTTP calls.
    Calls external service and propagates trace context.
    """
    
    with tracer.start_as_current_span("chain-request") as span:
        span.set_attribute("chain.step", 1)
        
        # Prepare headers for trace propagation
        headers = {}
        inject(headers)  # Inject trace context
        
        # Call external service (httpx is instrumented)
        async with httpx.AsyncClient() as client:
            try:
                # Call another endpoint
                response = await client.get(
                    "http://localhost:8000/health",
                    headers=headers,
                )
                span.set_attribute("external.status_code", response.status_code)
                
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("external.error", str(e))
        
        return {
            "message": "Chain call completed",
            "trace_id": format(span.get_span_context().trace_id, '032x'),
        }


@app.get("/error")
async def error_endpoint():
    """Endpoint that raises an error (demonstrates error tracing)."""
    
    with tracer.start_as_current_span("error-operation") as span:
        span.add_event("About to raise error")
        
        try:
            raise ValueError("This is a test error!")
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(500, "Internal server error")


@app.get("/slow")
async def slow_endpoint(duration: float = 2.0):
    """Slow endpoint for performance analysis."""
    
    with tracer.start_as_current_span("slow-operation") as span:
        span.set_attribute("duration.requested", duration)
        
        # Step 1
        with tracer.start_as_current_span("step-1"):
            await asyncio.sleep(duration * 0.3)
        
        # Step 2
        with tracer.start_as_current_span("step-2"):
            await asyncio.sleep(duration * 0.4)
        
        # Step 3
        with tracer.start_as_current_span("step-3"):
            await asyncio.sleep(duration * 0.3)
        
        return {"message": f"Completed after {duration}s"}


# =============================================================================
# Baggage Example
# =============================================================================

from opentelemetry import baggage
from opentelemetry.context import attach, detach


@app.get("/baggage")
async def baggage_example():
    """Demonstrate baggage for cross-span context."""
    
    # Set baggage
    ctx = baggage.set_baggage("user.id", "12345")
    ctx = baggage.set_baggage("tenant.id", "tenant-abc", context=ctx)
    token = attach(ctx)
    
    try:
        with tracer.start_as_current_span("baggage-demo") as span:
            # Read baggage
            user_id = baggage.get_baggage("user.id")
            tenant_id = baggage.get_baggage("tenant.id")
            
            span.set_attribute("baggage.user_id", user_id or "")
            span.set_attribute("baggage.tenant_id", tenant_id or "")
            
            # Child span also has access to baggage
            with tracer.start_as_current_span("child-span"):
                child_user_id = baggage.get_baggage("user.id")
            
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "message": "Baggage propagated",
            }
    finally:
        detach(token)


# =============================================================================
# Main
# =============================================================================

import asyncio

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("FastAPI OpenTelemetry Demo")
    print("=" * 60)
    print("Jaeger UI: http://localhost:16686")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
