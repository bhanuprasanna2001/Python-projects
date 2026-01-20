# Project 7: Parallel Processing

## 🎯 Learning Objectives
- Understand CPU-bound vs I/O-bound tasks
- Use multiprocessing for CPU-intensive work
- Use threading for I/O-bound operations
- Implement ProcessPoolExecutor and ThreadPoolExecutor
- Handle shared state and inter-process communication

## 📁 Project Structure
```
07-parallel-processing/
├── cpu_bound.py          # CPU-intensive examples
├── io_bound.py           # I/O-bound examples
├── pool_executors.py     # ProcessPool/ThreadPool
├── shared_state.py       # Sharing data between processes
├── multiprocess_queue.py # Inter-process communication
├── benchmarks.py         # Performance comparisons
├── main.py               # Demo runner
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## 🔑 Key Concepts

### When to Use What

| Task Type | Best Solution | Example |
|-----------|--------------|---------|
| CPU-bound | multiprocessing | Image processing, calculations |
| I/O-bound | threading/asyncio | API calls, file I/O |
| Mixed | ProcessPoolExecutor | Batch processing |

### GIL (Global Interpreter Lock)
- Python threads can't run Python code in parallel
- multiprocessing bypasses GIL by using separate processes
- Each process has its own memory space

## 📚 Topics Covered
- multiprocessing module
- threading module
- ProcessPoolExecutor
- ThreadPoolExecutor
- Queue for IPC
- Shared memory
