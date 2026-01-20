# Project 13: OpenTelemetry - Distributed Tracing

A comprehensive mini-project demonstrating **OpenTelemetry** for distributed tracing and observability.

## What You'll Learn

- Traces, spans, and context propagation
- Automatic instrumentation
- Manual instrumentation
- Exporters (Jaeger, OTLP, Console)
- Metrics collection
- Baggage and attributes
- FastAPI integration

## Project Structure

```
13-opentelemetry/
├── README.md
├── requirements.txt
├── docker-compose.yml        # Jaeger setup
├── tracing_basics.py         # Basic tracing concepts
├── auto_instrumentation.py   # Automatic instrumentation
├── manual_instrumentation.py # Manual spans and traces
├── context_propagation.py    # Cross-service tracing
├── metrics.py                # Metrics collection
└── fastapi_tracing.py        # FastAPI integration
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Jaeger (for trace visualization)
docker-compose up -d

# Access Jaeger UI
open http://localhost:16686

# Run examples
python tracing_basics.py
python fastapi_tracing.py
```

## Key Concepts

### Traces
A trace represents the entire journey of a request through a system.

### Spans
Individual units of work within a trace. Each span has:
- Name
- Start/end time
- Status
- Attributes
- Events
- Links

### Context
Carries trace information across service boundaries.

### Propagation
How trace context is transmitted (HTTP headers, etc.)

## Exporters

- **Console**: Print traces to console (debugging)
- **Jaeger**: Popular open-source tracing backend
- **OTLP**: OpenTelemetry Protocol (recommended)
- **Zipkin**: Alternative tracing backend

## Best Practices

1. Use semantic conventions for span names
2. Add meaningful attributes
3. Handle errors with proper status
4. Use automatic instrumentation where possible
5. Sample appropriately in production
6. Propagate context across services
