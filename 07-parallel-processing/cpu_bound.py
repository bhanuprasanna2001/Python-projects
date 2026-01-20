"""
Parallel Processing - CPU Bound Tasks
=====================================
Demonstrates multiprocessing for CPU-intensive work.
"""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import math
from typing import List, Tuple


# ============================================================
# CPU-Bound Task Examples
# ============================================================

def is_prime(n: int) -> bool:
    """Check if a number is prime (CPU-intensive)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def count_primes_in_range(start: int, end: int) -> Tuple[int, int, int]:
    """Count primes in a range. Returns (start, end, count)."""
    count = sum(1 for n in range(start, end) if is_prime(n))
    return (start, end, count)


def calculate_factorial(n: int) -> int:
    """Calculate factorial (CPU-intensive for large n)."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


# ============================================================
# Sequential vs Parallel Comparison
# ============================================================

def sequential_primes(ranges: List[Tuple[int, int]]) -> List[int]:
    """Count primes sequentially."""
    results = []
    for start, end in ranges:
        results.append(count_primes_in_range(start, end))
    return results


def parallel_primes_pool(ranges: List[Tuple[int, int]], workers: int = None) -> List:
    """Count primes using ProcessPoolExecutor."""
    workers = workers or mp.cpu_count()
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(count_primes_in_range, start, end)
            for start, end in ranges
        ]
        
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    
    return results


def parallel_primes_map(ranges: List[Tuple[int, int]], workers: int = None) -> List:
    """Count primes using pool.map (simpler API)."""
    workers = workers or mp.cpu_count()
    
    with mp.Pool(workers) as pool:
        results = pool.starmap(count_primes_in_range, ranges)
    
    return results


# ============================================================
# Process with Callback
# ============================================================

def with_callback():
    """Demonstrate callback on completion."""
    results = []
    
    def on_complete(result):
        results.append(result)
        print(f"  Completed: range {result[0]}-{result[1]}, found {result[2]} primes")
    
    ranges = [(1, 50000), (50000, 100000), (100000, 150000), (150000, 200000)]
    
    with mp.Pool(mp.cpu_count()) as pool:
        for start, end in ranges:
            pool.apply_async(
                count_primes_in_range,
                args=(start, end),
                callback=on_complete
            )
        
        pool.close()
        pool.join()
    
    return results


# ============================================================
# Chunking Large Workloads
# ============================================================

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split a list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def process_chunk(numbers: List[int]) -> List[bool]:
    """Process a chunk of numbers."""
    return [is_prime(n) for n in numbers]


def parallel_chunked_processing(numbers: List[int], chunk_size: int = 1000) -> List[bool]:
    """Process large list in parallel chunks."""
    chunks = chunk_list(numbers, chunk_size)
    
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_chunk, chunks))
    
    # Flatten results
    return [item for sublist in results for item in sublist]


# ============================================================
# Demo Runner
# ============================================================

def run_cpu_bound_demo():
    """Run CPU-bound parallel processing demos."""
    print("=" * 60)
    print("CPU-Bound Parallel Processing Demo")
    print("=" * 60)
    print(f"CPU Cores: {mp.cpu_count()}")
    
    # Define work ranges
    ranges = [
        (1, 100000),
        (100000, 200000),
        (200000, 300000),
        (300000, 400000),
    ]
    
    # Sequential
    print("\n--- Sequential Processing ---")
    start = time.perf_counter()
    seq_results = sequential_primes(ranges)
    seq_time = time.perf_counter() - start
    print(f"Time: {seq_time:.2f}s")
    total_primes = sum(r[2] for r in seq_results)
    print(f"Total primes found: {total_primes}")
    
    # Parallel with ProcessPoolExecutor
    print("\n--- Parallel (ProcessPoolExecutor) ---")
    start = time.perf_counter()
    pool_results = parallel_primes_pool(ranges)
    pool_time = time.perf_counter() - start
    print(f"Time: {pool_time:.2f}s")
    print(f"Speedup: {seq_time/pool_time:.2f}x")
    
    # Parallel with Pool.map
    print("\n--- Parallel (Pool.starmap) ---")
    start = time.perf_counter()
    map_results = parallel_primes_map(ranges)
    map_time = time.perf_counter() - start
    print(f"Time: {map_time:.2f}s")
    print(f"Speedup: {seq_time/map_time:.2f}x")
    
    # With callback
    print("\n--- Parallel with Callback ---")
    callback_results = with_callback()
    
    print("\n--- Chunked Processing ---")
    numbers = list(range(100000))
    start = time.perf_counter()
    results = parallel_chunked_processing(numbers, chunk_size=10000)
    chunk_time = time.perf_counter() - start
    print(f"Processed {len(numbers)} numbers in {chunk_time:.2f}s")
    print(f"Found {sum(results)} primes")


if __name__ == "__main__":
    run_cpu_bound_demo()
