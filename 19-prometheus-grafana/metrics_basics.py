"""
Prometheus Metrics Basics
=========================
Understanding and using Prometheus metric types.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    Enum,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    start_http_server,
    push_to_gateway,
)
import time
import random
import threading


# =============================================================================
# Counter - Monotonically increasing values
# =============================================================================

# Basic counter
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

# Counter methods
def demonstrate_counter():
    """Demonstrate counter usage."""
    print("\n=== Counter ===\n")
    
    # Increment by 1
    http_requests_total.labels(method='GET', endpoint='/api/users', status='200').inc()
    
    # Increment by specific amount
    http_requests_total.labels(method='POST', endpoint='/api/orders', status='201').inc(5)
    
    # Using count_exceptions to track errors
    errors_total = Counter('errors_total', 'Total errors')
    
    @errors_total.count_exceptions()
    def might_fail():
        if random.random() < 0.5:
            raise ValueError("Random failure")
    
    for _ in range(10):
        try:
            might_fail()
        except ValueError:
            pass
    
    print(f"Requests counted: {http_requests_total._value}")
    print(f"Errors counted: {errors_total._value}")


# =============================================================================
# Gauge - Values that can go up and down
# =============================================================================

# Basic gauge
active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    ['service']
)

# Gauge with process info
temperature_celsius = Gauge(
    'temperature_celsius',
    'Current temperature in Celsius'
)

def demonstrate_gauge():
    """Demonstrate gauge usage."""
    print("\n=== Gauge ===\n")
    
    # Set to specific value
    active_connections.labels(service='api').set(42)
    
    # Increment/decrement
    active_connections.labels(service='api').inc()
    active_connections.labels(service='api').dec(5)
    
    # Track in-progress operations
    in_progress = Gauge('operations_in_progress', 'Operations currently in progress')
    
    @in_progress.track_inprogress()
    def long_operation():
        time.sleep(0.1)
    
    # Set to current time
    last_request_time = Gauge('last_request_unixtime', 'Time of last request')
    last_request_time.set_to_current_time()
    
    # Context manager for timing
    processing_time = Gauge('processing_seconds', 'Time spent processing')
    
    with processing_time.time():
        time.sleep(0.05)
    
    print(f"Active connections: {active_connections.labels(service='api')._value}")
    print(f"Processing time: {processing_time._value}")


# =============================================================================
# Histogram - Distribution of values (latency, sizes)
# =============================================================================

# Default buckets: .005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, INF
request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]  # Custom buckets
)

# Histogram for sizes
response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000]
)

def demonstrate_histogram():
    """Demonstrate histogram usage."""
    print("\n=== Histogram ===\n")
    
    # Observe values
    for _ in range(100):
        latency = random.expovariate(1/0.2)  # Mean 0.2 seconds
        request_latency.labels(method='GET', endpoint='/api').observe(latency)
    
    # Using time() context manager
    with request_latency.labels(method='POST', endpoint='/api').time():
        time.sleep(random.uniform(0.01, 0.1))
    
    # Observe response sizes
    for _ in range(50):
        size = random.randint(100, 50000)
        response_size_bytes.observe(size)
    
    print("Histogram records observations in buckets")
    print("Use histogram_quantile() in PromQL to calculate percentiles")


# =============================================================================
# Summary - Pre-calculated quantiles (client-side)
# =============================================================================

# Summary with quantiles
request_latency_summary = Summary(
    'http_request_latency_summary_seconds',
    'HTTP request latency summary',
    ['handler']
)

# Summary with specific quantiles (expensive to calculate)
# Note: Summaries cannot be aggregated across instances
request_processing = Summary(
    'request_processing_seconds',
    'Time spent processing request',
)

def demonstrate_summary():
    """Demonstrate summary usage."""
    print("\n=== Summary ===\n")
    
    # Observe values
    for _ in range(100):
        latency = random.expovariate(1/0.15)
        request_latency_summary.labels(handler='main').observe(latency)
    
    # Using time() decorator
    @request_processing.time()
    def process_request():
        time.sleep(random.uniform(0.01, 0.05))
    
    for _ in range(20):
        process_request()
    
    print("Summary provides count, sum, and pre-calculated quantiles")
    print("Prefer histograms for most use cases (aggregatable)")


# =============================================================================
# Info - Static information labels
# =============================================================================

# Application info
app_info = Info('app', 'Application information')

def demonstrate_info():
    """Demonstrate info usage."""
    print("\n=== Info ===\n")
    
    app_info.info({
        'version': '1.2.3',
        'git_commit': 'abc123',
        'build_time': '2024-01-15T10:30:00Z',
        'python_version': '3.11',
    })
    
    print("Info metric provides static labels about the application")


# =============================================================================
# Enum - Current state from predefined options
# =============================================================================

# Service state
service_state = Enum(
    'service_state',
    'Current service state',
    ['service'],
    states=['starting', 'running', 'stopping', 'stopped']
)

def demonstrate_enum():
    """Demonstrate enum usage."""
    print("\n=== Enum ===\n")
    
    # Set state
    service_state.labels(service='api').state('running')
    
    # Simulating state transitions
    for state in ['starting', 'running', 'stopping', 'stopped']:
        service_state.labels(service='api').state(state)
        print(f"Service state: {state}")
        time.sleep(0.1)


# =============================================================================
# Custom Registry (for isolation)
# =============================================================================

def demonstrate_custom_registry():
    """Demonstrate using a custom registry."""
    print("\n=== Custom Registry ===\n")
    
    # Create a new registry
    registry = CollectorRegistry()
    
    # Create metrics in custom registry
    custom_counter = Counter(
        'custom_requests_total',
        'Custom counter',
        registry=registry
    )
    
    custom_counter.inc(10)
    
    # Generate metrics output
    output = generate_latest(registry)
    print(f"Custom registry metrics:\n{output.decode()[:500]}...")


# =============================================================================
# Demo Server
# =============================================================================

def run_metrics_server(port: int = 8001):
    """Run a simple metrics server."""
    print(f"\n=== Starting Metrics Server on port {port} ===\n")
    
    # Start HTTP server to expose metrics
    start_http_server(port)
    print(f"Metrics available at http://localhost:{port}/metrics")
    
    # Simulate some activity
    def generate_metrics():
        while True:
            # Simulate requests
            method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
            endpoint = random.choice(['/api/users', '/api/orders', '/api/products'])
            status = random.choices(['200', '201', '400', '500'], weights=[70, 15, 10, 5])[0]
            
            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            
            # Simulate latency
            latency = random.expovariate(1/0.1)
            request_latency.labels(method=method, endpoint=endpoint).observe(latency)
            
            # Update active connections
            active_connections.labels(service='api').set(random.randint(10, 100))
            
            time.sleep(0.1)
    
    # Start background thread
    thread = threading.Thread(target=generate_metrics, daemon=True)
    thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping metrics server")


# =============================================================================
# Main Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Prometheus Metrics Basics Demo")
    print("=" * 60)
    
    demonstrate_counter()
    demonstrate_gauge()
    demonstrate_histogram()
    demonstrate_summary()
    demonstrate_info()
    demonstrate_enum()
    demonstrate_custom_registry()
    
    # Uncomment to run metrics server
    # run_metrics_server(8001)
    
    print("\n" + "=" * 60)
    print("Run run_metrics_server() to expose metrics on port 8001")
    print("=" * 60)
