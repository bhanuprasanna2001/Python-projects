# Project 10: Celery Task Queue

A comprehensive mini-project demonstrating **Celery** for distributed task processing.

## What You'll Learn

- Task definition and execution
- Task chains, groups, and chords
- Periodic/scheduled tasks with celery beat
- Error handling and retries
- Task monitoring and tracking
- Result backends
- Priority queues

## Project Structure

```
10-celery/
├── README.md
├── requirements.txt
├── celery_app.py        # Celery application configuration
├── tasks/
│   ├── __init__.py
│   ├── basic.py         # Basic task examples
│   ├── workflows.py     # Chains, groups, chords
│   └── advanced.py      # Retries, error handling
├── beat_schedule.py     # Periodic task configuration
├── worker.py            # Worker entry point
└── client.py            # Task invocation examples
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (message broker)
docker run -d -p 6379:6379 --name redis redis:alpine

# Start Celery worker
celery -A celery_app worker --loglevel=info

# Start Celery beat (for periodic tasks)
celery -A celery_app beat --loglevel=info

# Or run both together
celery -A celery_app worker --beat --loglevel=info
```

## Key Concepts

### Task States
- PENDING: Task waiting to be executed
- STARTED: Task has started
- SUCCESS: Task completed successfully
- FAILURE: Task raised an exception
- RETRY: Task is being retried
- REVOKED: Task was cancelled

### Task Signatures
```python
# Immediate execution
result = add.delay(2, 2)

# Signature for deferred execution
sig = add.s(2, 2)
sig.delay()

# Partial signature
partial = add.s(2)  # Only first arg
partial.delay(3)    # Provides second arg
```

### Workflows
```python
# Chain: sequential execution
chain(task1.s(), task2.s(), task3.s())()

# Group: parallel execution
group(task1.s(), task2.s(), task3.s())()

# Chord: group + callback
chord([task1.s(), task2.s()], callback.s())()
```

## Monitoring

```bash
# Flower - Web-based monitoring
pip install flower
celery -A celery_app flower

# Command line
celery -A celery_app inspect active
celery -A celery_app inspect reserved
celery -A celery_app status
```

## Best Practices

1. **Idempotency**: Tasks should be safe to retry
2. **Atomicity**: Tasks should be atomic operations
3. **Keep tasks small**: Break large tasks into smaller ones
4. **Use result backends sparingly**: Only when needed
5. **Set timeouts**: Prevent stuck tasks
6. **Handle failures gracefully**: Use retries with backoff
