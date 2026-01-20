# Project 18: Event Processing
# Online vs Offline Events, Event Sourcing Basics

## Overview

This project covers event-driven architecture patterns:
- Online (real-time) vs Offline (batch) event processing
- Event sourcing fundamentals
- Event store implementation
- CQRS pattern basics
- Event-driven communication

## Project Structure

```
18-event-processing/
├── README.md
├── requirements.txt
├── event_basics.py         # Event classes and fundamentals
├── event_store.py          # Event store implementation
├── online_processing.py    # Real-time event processing
├── offline_processing.py   # Batch event processing
└── cqrs_example.py         # CQRS pattern demonstration
```

## Key Concepts

### Online vs Offline Processing

| Aspect | Online (Real-time) | Offline (Batch) |
|--------|-------------------|-----------------|
| Latency | Milliseconds | Minutes to hours |
| Volume | Per event | Bulk events |
| Use Case | User actions, alerts | Analytics, reports |
| Consistency | Eventual | Strong |
| Technology | Kafka, Redis Streams | Spark, Airflow |

### Event Sourcing

Instead of storing current state, store all changes (events):

```python
# Traditional: Store current state
account = {"balance": 100}

# Event Sourcing: Store events
events = [
    {"type": "AccountCreated", "balance": 0},
    {"type": "MoneyDeposited", "amount": 150},
    {"type": "MoneyWithdrawn", "amount": 50},
]
# Current state = replay events -> balance = 100
```

### CQRS (Command Query Responsibility Segregation)

- **Commands**: Write operations (separate model)
- **Queries**: Read operations (separate model, optimized views)
- Events connect the two models

## Running Examples

```bash
# Install dependencies
pip install -r requirements.txt

# Run event basics
python event_basics.py

# Run event store demo
python event_store.py

# Run online processing
python online_processing.py

# Run offline processing
python offline_processing.py

# Run CQRS example
python cqrs_example.py
```

## Best Practices

1. **Immutable Events**: Never modify past events
2. **Event Versioning**: Plan for schema evolution
3. **Idempotency**: Handle duplicate events gracefully
4. **Snapshots**: Periodically snapshot for faster replay
5. **Projection**: Build read models from events
