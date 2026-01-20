# Project 14: Redis & RabbitMQ Message Queues

A comprehensive mini-project demonstrating **Redis** and **RabbitMQ** for caching and message queuing.

## What You'll Learn

### Redis
- Basic operations (GET, SET, EXPIRE)
- Data structures (Lists, Sets, Hashes, Sorted Sets)
- Pub/Sub messaging
- Caching patterns
- Distributed locks
- Rate limiting

### RabbitMQ
- Message publishing and consuming
- Queue patterns (work queues, pub/sub, routing)
- Exchange types (direct, fanout, topic)
- Message acknowledgment
- Dead letter queues
- RPC pattern

## Project Structure

```
14-redis-rabbitmq/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── redis/
│   ├── basic_operations.py   # CRUD operations
│   ├── data_structures.py    # Lists, Sets, Hashes
│   ├── caching.py            # Caching patterns
│   ├── pubsub.py             # Publish/Subscribe
│   └── distributed_lock.py   # Distributed locking
├── rabbitmq/
│   ├── producer.py           # Message producer
│   ├── consumer.py           # Message consumer
│   ├── work_queue.py         # Work queue pattern
│   ├── pubsub.py             # Fanout exchange
│   ├── routing.py            # Direct/Topic routing
│   └── rpc.py                # RPC pattern
└── combined_example.py       # Using both together
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis and RabbitMQ
docker-compose up -d

# Access RabbitMQ Management UI
open http://localhost:15672
# Username: guest, Password: guest

# Run examples
python redis/basic_operations.py
python rabbitmq/work_queue.py
```

## When to Use What

### Use Redis for:
- Caching (session data, API responses)
- Real-time analytics
- Leaderboards
- Rate limiting
- Simple pub/sub

### Use RabbitMQ for:
- Reliable message delivery
- Complex routing
- Task distribution
- Microservice communication
- When message acknowledgment is critical
