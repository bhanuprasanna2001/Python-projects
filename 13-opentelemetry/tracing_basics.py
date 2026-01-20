"""
OpenTelemetry Tracing Basics
============================
Fundamental concepts of distributed tracing with OpenTelemetry.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import time
import random


# =============================================================================
# Setup Tracing
# =============================================================================

def setup_tracing(service_name: str = "demo-service") -> trace.Tracer:
    """
    Configure OpenTelemetry tracing with console exporter.
    """
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add console exporter (for debugging)
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer
    return trace.get_tracer(__name__)


# =============================================================================
# Basic Span Creation
# =============================================================================

def basic_span_example(tracer: trace.Tracer):
    """
    Create a basic span to track an operation.
    """
    print("\n=== Basic Span Example ===\n")
    
    # Start a span using context manager
    with tracer.start_as_current_span("basic-operation") as span:
        # Simulate some work
        print("Doing some work...")
        time.sleep(0.5)
        
        # The span automatically ends when exiting the context


def span_with_attributes(tracer: trace.Tracer):
    """
    Create a span with attributes (metadata).
    """
    print("\n=== Span with Attributes ===\n")
    
    with tracer.start_as_current_span("user-lookup") as span:
        user_id = 12345
        
        # Add attributes (key-value pairs)
        span.set_attribute("user.id", user_id)
        span.set_attribute("user.type", "premium")
        span.set_attribute("cache.hit", False)
        
        # Semantic convention attributes
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.url", "https://api.example.com/users/12345")
        
        print(f"Looking up user {user_id}...")
        time.sleep(0.3)


def span_with_events(tracer: trace.Tracer):
    """
    Add events to a span to mark significant moments.
    """
    print("\n=== Span with Events ===\n")
    
    with tracer.start_as_current_span("data-processing") as span:
        # Event: Starting data fetch
        span.add_event("Starting data fetch")
        time.sleep(0.2)
        
        # Event with attributes
        span.add_event(
            "Data fetched",
            attributes={
                "records.count": 1000,
                "source": "database",
            }
        )
        
        # Processing event
        span.add_event("Processing records")
        time.sleep(0.3)
        
        # Completion event
        span.add_event(
            "Processing complete",
            attributes={"records.processed": 1000}
        )
        
        print("Data processing completed")


def span_with_status(tracer: trace.Tracer):
    """
    Set span status to indicate success or failure.
    """
    print("\n=== Span with Status ===\n")
    
    # Successful operation
    with tracer.start_as_current_span("successful-operation") as span:
        print("Performing successful operation...")
        time.sleep(0.2)
        span.set_status(Status(StatusCode.OK))
    
    # Failed operation
    with tracer.start_as_current_span("failed-operation") as span:
        try:
            print("Performing operation that will fail...")
            raise ValueError("Something went wrong!")
        except Exception as e:
            # Record the exception
            span.record_exception(e)
            # Set error status
            span.set_status(Status(StatusCode.ERROR, str(e)))
            print(f"Caught error: {e}")


# =============================================================================
# Nested Spans (Parent-Child Relationship)
# =============================================================================

def nested_spans_example(tracer: trace.Tracer):
    """
    Create nested spans to show operation hierarchy.
    """
    print("\n=== Nested Spans Example ===\n")
    
    with tracer.start_as_current_span("http-request") as parent:
        parent.set_attribute("http.method", "POST")
        parent.set_attribute("http.url", "/api/orders")
        
        print("Processing HTTP request...")
        
        # Child span: validation
        with tracer.start_as_current_span("validate-request") as child1:
            child1.set_attribute("validation.type", "schema")
            print("  Validating request...")
            time.sleep(0.1)
        
        # Child span: database
        with tracer.start_as_current_span("database-query") as child2:
            child2.set_attribute("db.system", "postgresql")
            child2.set_attribute("db.statement", "INSERT INTO orders...")
            print("  Executing database query...")
            time.sleep(0.2)
            
            # Grandchild span
            with tracer.start_as_current_span("index-update") as grandchild:
                grandchild.set_attribute("index.name", "orders_idx")
                print("    Updating index...")
                time.sleep(0.1)
        
        # Child span: notification
        with tracer.start_as_current_span("send-notification") as child3:
            child3.set_attribute("notification.type", "email")
            print("  Sending notification...")
            time.sleep(0.1)
        
        print("Request processing complete")


# =============================================================================
# Manual Span Management
# =============================================================================

def manual_span_management(tracer: trace.Tracer):
    """
    Manually manage span lifecycle (without context manager).
    """
    print("\n=== Manual Span Management ===\n")
    
    # Start span manually
    span = tracer.start_span("manual-operation")
    
    try:
        span.set_attribute("operation.type", "manual")
        
        print("Performing manual operation...")
        time.sleep(0.2)
        
        if random.random() < 0.3:
            raise RuntimeError("Random failure!")
        
        span.set_status(Status(StatusCode.OK))
        
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        print(f"Error: {e}")
        
    finally:
        # Must explicitly end the span
        span.end()
        print("Span ended")


# =============================================================================
# Span Context and Propagation
# =============================================================================

def span_context_example(tracer: trace.Tracer):
    """
    Work with span context for propagation.
    """
    print("\n=== Span Context Example ===\n")
    
    with tracer.start_as_current_span("parent-span") as span:
        # Get span context
        ctx = span.get_span_context()
        
        print(f"Trace ID: {format(ctx.trace_id, '032x')}")
        print(f"Span ID: {format(ctx.span_id, '016x')}")
        print(f"Trace Flags: {ctx.trace_flags}")
        print(f"Is Valid: {ctx.is_valid}")
        print(f"Is Remote: {ctx.is_remote}")
        
        # Extract for propagation (e.g., HTTP headers)
        propagator = TraceContextTextMapPropagator()
        carrier = {}
        propagator.inject(carrier)
        
        print(f"\nPropagation Headers: {carrier}")


# =============================================================================
# Span Links
# =============================================================================

def span_links_example(tracer: trace.Tracer):
    """
    Create spans with links to other spans (not parent-child).
    """
    print("\n=== Span Links Example ===\n")
    
    # First span
    with tracer.start_as_current_span("producer-span") as producer:
        producer.set_attribute("message.queue", "orders")
        producer_ctx = producer.get_span_context()
        print("Producer created message")
    
    # Later, create consumer span linked to producer
    link = trace.Link(producer_ctx, attributes={"link.type": "producer"})
    
    with tracer.start_as_current_span(
        "consumer-span",
        links=[link]
    ) as consumer:
        consumer.set_attribute("message.queue", "orders")
        print("Consumer processing message (linked to producer)")


# =============================================================================
# Span Kind
# =============================================================================

def span_kind_example(tracer: trace.Tracer):
    """
    Demonstrate different span kinds.
    """
    print("\n=== Span Kind Example ===\n")
    
    # Internal: Default, internal operation
    with tracer.start_as_current_span(
        "internal-operation",
        kind=trace.SpanKind.INTERNAL
    ):
        print("Internal operation")
    
    # Server: Handling incoming request
    with tracer.start_as_current_span(
        "handle-request",
        kind=trace.SpanKind.SERVER
    ):
        print("Server handling request")
    
    # Client: Making outgoing request
    with tracer.start_as_current_span(
        "http-call",
        kind=trace.SpanKind.CLIENT
    ):
        print("Client making request")
    
    # Producer: Creating a message
    with tracer.start_as_current_span(
        "send-message",
        kind=trace.SpanKind.PRODUCER
    ):
        print("Producer sending message")
    
    # Consumer: Receiving a message
    with tracer.start_as_current_span(
        "receive-message",
        kind=trace.SpanKind.CONSUMER
    ):
        print("Consumer receiving message")


# =============================================================================
# Decorator for Tracing
# =============================================================================

def traced(tracer: trace.Tracer, name: str = None):
    """Decorator to automatically trace functions."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Setup tracing
    tracer = setup_tracing("tracing-basics-demo")
    
    print("=" * 60)
    print("OpenTelemetry Tracing Basics")
    print("=" * 60)
    
    # Run examples
    basic_span_example(tracer)
    span_with_attributes(tracer)
    span_with_events(tracer)
    span_with_status(tracer)
    nested_spans_example(tracer)
    manual_span_management(tracer)
    span_context_example(tracer)
    span_links_example(tracer)
    span_kind_example(tracer)
    
    # Using decorator
    @traced(tracer, "decorated-function")
    def my_function(x, y):
        time.sleep(0.1)
        return x + y
    
    print("\n=== Traced Decorator ===\n")
    result = my_function(5, 3)
    print(f"Result: {result}")
    
    print("\n" + "=" * 60)
    print("Examples completed! Check console output for spans.")
    print("=" * 60)
