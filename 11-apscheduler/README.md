# Project 11: APScheduler - Advanced Python Scheduler

A comprehensive mini-project demonstrating **APScheduler** for scheduled task execution.

## What You'll Learn

- Scheduler types (Background, Blocking, Async)
- Trigger types (Interval, Cron, Date)
- Job stores (Memory, SQLAlchemy, Redis)
- Job management (add, remove, pause, resume)
- Error handling and missed jobs
- Combining with FastAPI/Flask

## Project Structure

```
11-apscheduler/
├── README.md
├── requirements.txt
├── basic_scheduler.py     # Basic scheduler examples
├── triggers.py            # Different trigger types
├── job_stores.py          # Persistent job stores
├── async_scheduler.py     # AsyncIO scheduler
├── fastapi_scheduler.py   # Integration with FastAPI
└── advanced.py            # Advanced patterns
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run examples
python basic_scheduler.py
python triggers.py
python fastapi_scheduler.py
```

## Key Concepts

### Scheduler Types
- **BackgroundScheduler**: Runs in the background
- **BlockingScheduler**: Blocks the main thread
- **AsyncIOScheduler**: For asyncio applications
- **GeventScheduler**: For gevent applications

### Trigger Types
- **interval**: Run at fixed intervals
- **cron**: Run at specific times (cron-like)
- **date**: Run once at a specific date/time
- **combining**: Combine multiple triggers

### Job Stores
- **MemoryJobStore**: In-memory (default)
- **SQLAlchemyJobStore**: SQL databases
- **RedisJobStore**: Redis
- **MongoDBJobStore**: MongoDB

## Best Practices

1. Use appropriate scheduler for your app type
2. Set `max_instances` to prevent job overlap
3. Use persistent job stores for reliability
4. Handle missed jobs with `misfire_grace_time`
5. Add proper error handling
6. Use coalesce for catching up
