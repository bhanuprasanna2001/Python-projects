# Project 3: Async Python

## 🎯 Learning Objectives
- Understand async/await syntax and coroutines
- Master asyncio event loop and tasks
- Handle concurrent operations with gather/wait
- Implement async context managers and iterators
- Manage task cancellation and timeouts

## 📁 Project Structure
```
03-async-python/
├── basics.py           # async/await fundamentals
├── tasks.py            # Task creation and management
├── concurrency.py      # gather, wait, as_completed
├── patterns.py         # Common async patterns
├── context_managers.py # Async context managers
├── iterators.py        # Async iterators and generators
├── real_world.py       # Practical examples
├── main.py             # Demo runner
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## 🔑 Key Concepts

### Sync vs Async
```python
# Synchronous (blocking)
def fetch_data():
    response = requests.get(url)  # Blocks here
    return response.json()

# Asynchronous (non-blocking)
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        response = await session.get(url)  # Yields control
        return await response.json()
```

### Event Loop
```
┌─────────────────────────────────────┐
│           Event Loop                │
│                                     │
│   ┌─────┐  ┌─────┐  ┌─────┐        │
│   │Task1│  │Task2│  │Task3│        │
│   └──┬──┘  └──┬──┘  └──┬──┘        │
│      │        │        │            │
│   Running  Waiting  Waiting         │
│      ↓        ↓        ↓            │
│   Yields → Runs → Yields → Runs...  │
└─────────────────────────────────────┘
```

## 📚 Topics Covered
- Coroutines and async functions
- asyncio.gather() for concurrent execution
- Task creation and management
- Timeouts and cancellation
- Async context managers
- Async iterators and generators
- Semaphores for rate limiting
- Real-world HTTP client examples
