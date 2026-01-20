"""
Celery Workflows
================
Task composition: chains, groups, chords, and complex workflows.
"""

from celery_app import app
from celery import chain, group, chord, signature
import time
import random
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Tasks for Workflows
# =============================================================================

@app.task
def fetch_data(source: str) -> dict:
    """Simulates fetching data from a source."""
    time.sleep(random.uniform(0.5, 1.5))  # Simulate I/O
    return {"source": source, "records": random.randint(100, 1000)}


@app.task
def transform_data(data: dict) -> dict:
    """Transforms fetched data."""
    time.sleep(0.5)
    data["transformed"] = True
    data["records"] = data["records"] * 2
    return data


@app.task
def validate_data(data: dict) -> dict:
    """Validates transformed data."""
    time.sleep(0.3)
    data["valid"] = data["records"] > 0
    return data


@app.task
def save_data(data: dict) -> dict:
    """Saves validated data."""
    time.sleep(0.5)
    data["saved"] = True
    return data


@app.task
def aggregate_results(results: list) -> dict:
    """Aggregates results from multiple tasks."""
    total_records = sum(r.get("records", 0) for r in results)
    return {
        "total_sources": len(results),
        "total_records": total_records,
        "sources": [r.get("source") for r in results],
    }


@app.task
def process_chunk(items: list) -> dict:
    """Processes a chunk of items."""
    time.sleep(len(items) * 0.1)
    return {"processed": len(items), "items": items}


# =============================================================================
# Chain: Sequential Execution
# =============================================================================

def run_sequential_pipeline(source: str):
    """
    Chain executes tasks sequentially.
    Result of each task is passed to the next.
    """
    # Method 1: Using chain()
    pipeline = chain(
        fetch_data.s(source),
        transform_data.s(),
        validate_data.s(),
        save_data.s(),
    )
    return pipeline.apply_async()


def run_chain_with_signature():
    """Using signatures for more control."""
    # Create partial signatures
    fetch = fetch_data.signature(args=("database",))
    transform = transform_data.s()
    validate = validate_data.s()
    save = save_data.s()
    
    # Chain them
    workflow = fetch | transform | validate | save
    return workflow.apply_async()


# =============================================================================
# Group: Parallel Execution
# =============================================================================

def run_parallel_fetch(sources: list):
    """
    Group executes tasks in parallel.
    Returns a list of all results.
    """
    # Method 1: Using group()
    parallel_tasks = group(fetch_data.s(source) for source in sources)
    return parallel_tasks.apply_async()


def run_group_with_callback():
    """Execute group and then process results."""
    sources = ["api", "database", "file"]
    
    # Group with a callback that receives all results
    workflow = group(fetch_data.s(s) for s in sources) | aggregate_results.s()
    return workflow.apply_async()


# =============================================================================
# Chord: Group + Callback
# =============================================================================

def run_chord_workflow(sources: list):
    """
    Chord: Parallel tasks + callback when all complete.
    The callback receives results from all tasks.
    """
    # Create header (parallel tasks) and body (callback)
    header = group(fetch_data.s(source) for source in sources)
    callback = aggregate_results.s()
    
    # Execute chord
    return chord(header, callback).apply_async()


def run_chord_with_error_handling():
    """Chord with error handling callback."""
    sources = ["api", "database", "file"]
    
    workflow = chord(
        group(fetch_data.s(s) for s in sources),
        aggregate_results.s().on_error(log_error.s()),
    )
    return workflow.apply_async()


@app.task
def log_error(request, exc, traceback):
    """Error handler for chord."""
    logger.error(f"Chord failed: {exc}")


# =============================================================================
# Complex Workflows
# =============================================================================

def run_map_reduce_workflow(items: list, chunk_size: int = 10):
    """
    Map-reduce pattern: split data, process in parallel, aggregate.
    """
    # Split items into chunks
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    # Map: Process each chunk in parallel
    # Reduce: Aggregate all results
    workflow = chord(
        group(process_chunk.s(chunk) for chunk in chunks),
        aggregate_chunk_results.s(),
    )
    return workflow.apply_async()


@app.task
def aggregate_chunk_results(results: list) -> dict:
    """Aggregates processed chunks."""
    total = sum(r.get("processed", 0) for r in results)
    return {"total_processed": total, "chunks": len(results)}


def run_fan_out_fan_in(data: dict):
    """
    Fan-out/fan-in pattern:
    1. Initial processing
    2. Fan out to multiple parallel tasks
    3. Fan in (aggregate) results
    """
    # Initial task
    initial = preprocess.s(data)
    
    # Fan-out: Multiple processing paths
    parallel = group(
        process_path_a.s(),
        process_path_b.s(),
        process_path_c.s(),
    )
    
    # Fan-in: Combine results
    final = combine_results.s()
    
    # Complete workflow
    workflow = initial | parallel | final
    return workflow.apply_async()


@app.task
def preprocess(data: dict) -> dict:
    """Initial preprocessing."""
    data["preprocessed"] = True
    return data


@app.task
def process_path_a(data: dict) -> dict:
    """Processing path A."""
    return {"path": "A", "result": data.get("value", 0) * 2}


@app.task
def process_path_b(data: dict) -> dict:
    """Processing path B."""
    return {"path": "B", "result": data.get("value", 0) * 3}


@app.task
def process_path_c(data: dict) -> dict:
    """Processing path C."""
    return {"path": "C", "result": data.get("value", 0) * 4}


@app.task
def combine_results(results: list) -> dict:
    """Combines results from all paths."""
    return {
        "combined": True,
        "results": results,
        "total": sum(r.get("result", 0) for r in results),
    }


# =============================================================================
# Conditional Workflows
# =============================================================================

@app.task(bind=True)
def conditional_workflow(self, data: dict):
    """
    Workflow with conditional branching.
    """
    # Check condition and route accordingly
    if data.get("priority") == "high":
        # High priority path
        return chain(
            validate_data.s(data),
            process_urgent.s(),
        ).apply_async()
    else:
        # Normal path
        return chain(
            validate_data.s(data),
            process_normal.s(),
        ).apply_async()


@app.task
def process_urgent(data: dict) -> dict:
    """Urgent processing."""
    logger.warning("URGENT processing!")
    return {"urgent": True, **data}


@app.task
def process_normal(data: dict) -> dict:
    """Normal processing."""
    return {"normal": True, **data}


# =============================================================================
# Retry Workflows
# =============================================================================

@app.task(bind=True, max_retries=3)
def fetch_with_retry(self, url: str):
    """Task that retries on failure within a workflow."""
    try:
        # Simulate occasional failure
        if random.random() < 0.3:
            raise ConnectionError("Simulated connection error")
        return {"url": url, "status": "success"}
    except ConnectionError as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


def run_robust_workflow():
    """Workflow with retry-enabled tasks."""
    urls = ["http://api1.example.com", "http://api2.example.com"]
    
    return chord(
        group(fetch_with_retry.s(url) for url in urls),
        aggregate_results.s(),
    ).apply_async()
