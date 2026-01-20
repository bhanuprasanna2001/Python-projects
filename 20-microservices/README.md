# Project 20: Microservices Communication
# Service Discovery, Communication Patterns, API Gateway

## Overview

This project covers microservices architecture patterns:
- Service-to-service communication
- Synchronous (REST, gRPC) vs Asynchronous (Message Queue)
- Service discovery patterns
- API Gateway patterns
- Saga pattern for distributed transactions

## Project Structure

```
20-microservices/
├── README.md
├── requirements.txt
├── docker-compose.yml        # Multiple services setup
├── gateway/
│   └── main.py              # API Gateway
├── services/
│   ├── user_service.py      # User microservice
│   ├── order_service.py     # Order microservice
│   └── notification_service.py  # Notification service
├── communication/
│   ├── sync_patterns.py     # REST, HTTP clients
│   └── async_patterns.py    # Message-based communication
├── service_discovery.py     # Service registry
└── saga_pattern.py          # Distributed transactions
```

## Key Concepts

### Communication Patterns

| Pattern | When to Use | Pros | Cons |
|---------|-------------|------|------|
| REST | Simple CRUD | Simple, HTTP | Tight coupling |
| gRPC | High performance | Fast, typed | Complex setup |
| Message Queue | Async processing | Decoupled | Eventual consistency |
| Event-Driven | Loose coupling | Scalable | Complex debugging |

### Service Discovery

1. **Client-side**: Client queries registry
2. **Server-side**: Load balancer queries registry
3. **DNS-based**: Kubernetes DNS, Consul DNS

### API Gateway Responsibilities

- Authentication/Authorization
- Rate limiting
- Request routing
- Protocol translation
- Response aggregation
- Caching

### Saga Pattern (Distributed Transactions)

```
Choreography:
Service A → Event → Service B → Event → Service C

Orchestration:
Saga Orchestrator → Command → Service A
                  → Command → Service B
                  → Command → Service C
```

## Running Examples

```bash
# Install dependencies
pip install -r requirements.txt

# Start services with docker-compose
docker-compose up -d

# Or run individual services
uvicorn gateway.main:app --port 8000
uvicorn services.user_service:app --port 8001
uvicorn services.order_service:app --port 8002

# Test the gateway
curl http://localhost:8000/users
curl http://localhost:8000/orders
```

## Best Practices

1. **Design for Failure**: Expect services to be unavailable
2. **Idempotency**: Handle duplicate requests
3. **Timeouts**: Always set timeouts for service calls
4. **Circuit Breaker**: Prevent cascade failures
5. **Correlation IDs**: Track requests across services
6. **Health Checks**: Implement /health endpoints
7. **Graceful Shutdown**: Handle SIGTERM properly
