# Python MINI Learning Projects

A collection of **20 focused mini-projects**, where each one is demonstrating the core essential engineering concepts and technologies.

## 📋 Project Overview

| # | Project | Topic | Key Concepts |
|---|---------|-------|--------------|
| 1 | `01-websockets` | WebSockets | Real-time bidirectional communication, connection management |
| 2 | `02-sqlalchemy` | SQLAlchemy | ORM, sessions, relationships, queries, connection pooling |
| 3 | `03-async-python` | Async Programming | asyncio, coroutines, tasks, event loops, gather |
| 4 | `04-alembic` | Database Migrations | Version control for schemas, upgrade/downgrade |
| 5 | `05-fastapi-gateway` | FastAPI & API Gateway | REST APIs, routing, middleware, gateway patterns |
| 6 | `06-etl-pipeline` | ETL | Extract, Transform, Load patterns |
| 7 | `07-parallel-processing` | Parallel Processing | multiprocessing, threading, ProcessPoolExecutor |
| 8 | `08-testing` | Testing | pytest, fixtures, mocking, coverage, integration tests |
| 9 | `09-postgresql` | PostgreSQL | Advanced queries, indexing, transactions, JSONB |
| 10 | `10-celery` | Celery | Distributed task queues, workers, scheduling |
| 11 | `11-apscheduler` | APScheduler | Job scheduling, cron triggers, background tasks |
| 12 | `12-elk-logging` | ELK Stack | Elasticsearch, Logstash, Kibana, structured logging |
| 13 | `13-opentelemetry` | Observability | Distributed tracing, spans, metrics, instrumentation |
| 14 | `14-redis-rabbitmq` | Message Brokers | Caching, pub/sub, message queues |
| 15 | `15-jwt` | JWT | Token generation, validation, refresh tokens |
| 16 | `16-authentication` | Auth | OAuth2, sessions, password hashing, RBAC |
| 17 | `17-resilience` | Resilience Patterns | Rate limiting, retry, backoff, jitter, throttling |
| 18 | `18-event-processing` | Event Processing | Online vs offline events, event sourcing |
| 19 | `19-prometheus-grafana` | Monitoring | Metrics, dashboards, circuit breakers, alerts |
| 20 | `20-microservices` | Microservices | Service mesh, communication, orchestration |

---

## 🏗️ Architecture Philosophy

Each project follows these principles:
- **Self-contained**: Can be run independently
- **Focused**: Demonstrates ONE core concept deeply
- **Practical**: Real-world applicable patterns
- **Well-documented**: Clear explanations and comments
- **Docker-ready**: Containerized for easy deployment

---

## 🚀 Quick Start

```bash
# Each project has its own README and setup
cd 01-websockets
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python main.py
```

---

## 📚 Detailed Project Descriptions

### 1. WebSockets (`01-websockets`)
**Learn**: Real-time bidirectional communication
- WebSocket server with FastAPI
- Connection management (connect/disconnect)
- Broadcasting messages to multiple clients
- Heartbeat/ping-pong mechanism
- Room-based messaging

### 2. SQLAlchemy (`02-sqlalchemy`)
**Learn**: Python ORM fundamentals
- Declarative models with relationships
- Session management and transactions
- Query building (select, join, filter)
- Connection pooling
- Async SQLAlchemy (optional)

### 3. Async Python (`03-async-python`)
**Learn**: Asynchronous programming
- `async`/`await` syntax
- Event loops and coroutines
- `asyncio.gather()` for concurrent tasks
- Async context managers
- Task cancellation and timeouts

### 4. Alembic (`04-alembic`)
**Learn**: Database migration management
- Initial migration setup
- Auto-generating migrations
- Upgrade and downgrade operations
- Data migrations
- Multi-database migrations

### 5. FastAPI & API Gateway (`05-fastapi-gateway`)
**Learn**: Modern API development
- RESTful endpoint design
- Request/response validation with Pydantic
- Dependency injection
- API Gateway pattern implementation
- Rate limiting at gateway level

### 6. ETL Pipeline (`06-etl-pipeline`)
**Learn**: Data pipeline patterns
- Extract from multiple sources (CSV, API, DB)
- Transform with validation and cleaning
- Load to destination (DB, files)
- Error handling and logging
- Incremental vs full loads

### 7. Parallel Processing (`07-parallel-processing`)
**Learn**: CPU-bound task optimization
- `multiprocessing` module
- `ProcessPoolExecutor` and `ThreadPoolExecutor`
- Shared memory and queues
- CPU vs I/O bound task handling
- Worker pools

### 8. Testing (`08-testing`)
**Learn**: Comprehensive testing strategies
- Unit tests with pytest
- Fixtures and parametrization
- Mocking external services
- Integration tests
- Test coverage reporting

### 9. PostgreSQL (`09-postgresql`)
**Learn**: Advanced database operations
- Complex queries (CTEs, window functions)
- Indexing strategies (B-tree, GIN, GiST)
- JSONB operations
- Transactions and isolation levels
- Performance tuning

### 10. Celery (`10-celery`)
**Learn**: Distributed task processing
- Task definition and routing
- Worker configuration
- Task chaining and groups
- Result backends
- Monitoring with Flower

### 11. APScheduler (`11-apscheduler`)
**Learn**: Job scheduling
- Interval and cron triggers
- Background scheduler
- Persistent job stores
- Job listeners and events
- Timezone handling

### 12. ELK Logging (`12-elk-logging`)
**Learn**: Centralized logging
- Structured logging in Python
- Logstash configuration
- Elasticsearch indexing
- Kibana dashboards
- Log aggregation patterns

### 13. OpenTelemetry (`13-opentelemetry`)
**Learn**: Distributed tracing
- Trace and span creation
- Context propagation
- Metric collection
- Jaeger/Zipkin integration
- Auto-instrumentation

### 14. Redis/RabbitMQ (`14-redis-rabbitmq`)
**Learn**: Message brokers and caching
- Redis caching patterns
- Pub/Sub messaging
- RabbitMQ queues and exchanges
- Message acknowledgment
- Dead letter queues

### 15. JWT (`15-jwt`)
**Learn**: Token-based security
- JWT structure (header, payload, signature)
- Token generation and validation
- Refresh token rotation
- Token blacklisting
- Claims and scopes

### 16. Authentication (`16-authentication`)
**Learn**: Complete auth system
- Password hashing (bcrypt)
- OAuth2 with FastAPI
- Session management
- Role-based access control (RBAC)
- Multi-factor authentication basics

### 17. Resilience Patterns (`17-resilience`)
**Learn**: Fault tolerance
- Rate limiting (token bucket, sliding window)
- Retry with exponential backoff
- Jitter for thundering herd prevention
- Timeout handling
- Bulkhead pattern

### 18. Event Processing (`18-event-processing`)
**Learn**: Event-driven architecture
- Online (real-time) event processing
- Offline (batch) event processing
- Event sourcing basics
- CQRS pattern introduction
- Event replay

### 19. Prometheus & Grafana (`19-prometheus-grafana`)
**Learn**: Metrics and visualization
- Custom Prometheus metrics
- Metric types (counter, gauge, histogram)
- Grafana dashboard creation
- Circuit breaker implementation
- Alerting rules

### 20. Microservices (`20-microservices`)
**Learn**: Service architecture
- Service decomposition
- Inter-service communication (sync/async)
- Service discovery
- API composition
- Saga pattern for distributed transactions

---

## 🐳 Docker Compose Services

Many projects require supporting services. A shared `docker-compose.yml` is provided:

```yaml
# Shared services across projects
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
  
  redis:
    image: redis:7
    ports: ["6379:6379"]
  
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]
  
  elasticsearch:
    image: elasticsearch:8.11.0
    ports: ["9200:9200"]
  
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "6831:6831/udp"]
```

---

## 📖 Learning Path

**Recommended order for beginners:**
1. Start with **Async Python** (3) - Foundation for modern Python
2. Move to **SQLAlchemy** (2) - Database interactions
3. Then **FastAPI** (5) - API development
4. Add **Testing** (8) - Quality assurance
5. Explore **PostgreSQL** (9) - Advanced DB operations
6. Learn **Alembic** (4) - Schema management
7. Continue with remaining projects based on interest

**For experienced developers:**
- Jump directly to topics you want to master
- Each project is independent

---

## 🛠️ Common Dependencies

```txt
# Core
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
psycopg2-binary>=2.9.9

# Async
aiohttp>=3.9.0
httpx>=0.25.0

# Task Queues
celery>=5.3.0
redis>=5.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Observability
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
prometheus-client>=0.19.0

# Security
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

---

## 📝 License

MIT License - Feel free to use for learning and projects.

---

**Happy Learning! 🎓**
