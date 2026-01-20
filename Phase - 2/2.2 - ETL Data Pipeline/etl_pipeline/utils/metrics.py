"""
Metrics utilities for performance measurement and observability.

Provides:
- Timing decorators for functions
- Counter and gauge primitives
- Histogram for latency tracking
- Context managers for scoped timing
"""

from __future__ import annotations

import functools
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median, stdev
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class TimingStats:
    """Statistics for a timed operation."""

    count: int = 0
    total_seconds: float = 0.0
    min_seconds: float = float("inf")
    max_seconds: float = 0.0
    samples: list[float] = field(default_factory=list)

    def record(self, duration: float) -> None:
        """Record a timing sample."""
        self.count += 1
        self.total_seconds += duration
        self.min_seconds = min(self.min_seconds, duration)
        self.max_seconds = max(self.max_seconds, duration)
        # Keep last 1000 samples for percentile calculation
        if len(self.samples) >= 1000:
            self.samples.pop(0)
        self.samples.append(duration)

    @property
    def avg_seconds(self) -> float:
        """Average duration in seconds."""
        if self.count == 0:
            return 0.0
        return self.total_seconds / self.count

    @property
    def median_seconds(self) -> float:
        """Median duration in seconds."""
        if not self.samples:
            return 0.0
        return median(self.samples)

    @property
    def p95_seconds(self) -> float:
        """95th percentile duration in seconds."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def p99_seconds(self) -> float:
        """99th percentile duration in seconds."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def stddev_seconds(self) -> float:
        """Standard deviation of duration."""
        if len(self.samples) < 2:
            return 0.0
        return stdev(self.samples)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "count": self.count,
            "total_seconds": round(self.total_seconds, 4),
            "avg_seconds": round(self.avg_seconds, 4),
            "min_seconds": round(self.min_seconds, 4) if self.count > 0 else 0,
            "max_seconds": round(self.max_seconds, 4),
            "median_seconds": round(self.median_seconds, 4),
            "p95_seconds": round(self.p95_seconds, 4),
            "p99_seconds": round(self.p99_seconds, 4),
            "stddev_seconds": round(self.stddev_seconds, 4),
        }


class MetricsRegistry:
    """
    Central registry for all application metrics.

    Thread-safe singleton that collects counters, gauges, and timing data.
    """

    _instance: MetricsRegistry | None = None
    _initialized: bool = False

    def __new__(cls) -> MetricsRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._timings: dict[str, TimingStats] = defaultdict(TimingStats)
        self._labels: dict[str, dict[str, Any]] = defaultdict(dict)
        self._start_time = datetime.utcnow()

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._counters.clear()
        self._gauges.clear()
        self._timings.clear()
        self._labels.clear()
        self._start_time = datetime.utcnow()

    # --- Counters ---

    def increment(self, name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value
        if labels:
            self._labels[key] = labels

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    # --- Gauges ---

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        if labels:
            self._labels[key] = labels

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)

    # --- Timings ---

    def record_timing(
        self, name: str, duration: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a timing measurement."""
        key = self._make_key(name, labels)
        self._timings[key].record(duration)
        if labels:
            self._labels[key] = labels

    def get_timing(self, name: str, labels: dict[str, str] | None = None) -> TimingStats:
        """Get timing statistics."""
        key = self._make_key(name, labels)
        return self._timings.get(key, TimingStats())

    @contextmanager
    def time(self, name: str, labels: dict[str, str] | None = None) -> Generator[None, None, None]:
        """Context manager for timing a block of code."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.record_timing(name, duration, labels)

    # --- Helpers ---

    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "uptime_seconds": round(uptime, 2),
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timings": {k: v.to_dict() for k, v in self._timings.items()},
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of key metrics."""
        return {
            "total_counters": len(self._counters),
            "total_gauges": len(self._gauges),
            "total_timings": len(self._timings),
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
        }


# Global metrics registry
_metrics = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Get the global metrics registry."""
    return _metrics


def reset_metrics() -> None:
    """Reset all metrics (for testing)."""
    _metrics.reset()


# --- Decorators ---


def timed(
    name: str | None = None, labels: dict[str, str] | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to time a synchronous function.

    Args:
        name: Metric name (defaults to function name)
        labels: Additional labels for the metric

    Example:
        @timed("database_query")
        def query_database():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        metric_name = name or f"function.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                _metrics.record_timing(metric_name, duration, labels)

        return wrapper

    return decorator


def async_timed(
    name: str | None = None, labels: dict[str, str] | None = None
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator to time an async function.

    Args:
        name: Metric name (defaults to function name)
        labels: Additional labels for the metric

    Example:
        @async_timed("api_call")
        async def fetch_data():
            ...
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        metric_name = name or f"function.{func.__name__}"

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                _metrics.record_timing(metric_name, duration, labels)

        return wrapper

    return decorator


def counted(
    name: str | None = None, labels: dict[str, str] | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to count function calls.

    Args:
        name: Metric name (defaults to function name)
        labels: Additional labels for the metric
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        metric_name = name or f"calls.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            _metrics.increment(metric_name, labels=labels)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# --- Pipeline-Specific Metrics ---


class PipelineMetrics:
    """
    High-level metrics for ETL pipeline operations.

    Provides semantic methods for common pipeline metrics.
    """

    def __init__(self, registry: MetricsRegistry | None = None) -> None:
        self.registry = registry or get_metrics()

    def record_extraction(
        self,
        source: str,
        records: int,
        duration: float,
        errors: int = 0,
    ) -> None:
        """Record metrics for an extraction operation."""
        labels = {"source": source}
        self.registry.increment("extraction.records_total", records, labels)
        self.registry.increment("extraction.runs_total", 1, labels)
        self.registry.record_timing("extraction.duration_seconds", duration, labels)
        if errors > 0:
            self.registry.increment("extraction.errors_total", errors, labels)

    def record_transformation(
        self,
        input_count: int,
        output_count: int,
        duration: float,
        dropped: int = 0,
    ) -> None:
        """Record metrics for a transformation operation."""
        self.registry.increment("transformation.input_total", input_count)
        self.registry.increment("transformation.output_total", output_count)
        self.registry.increment("transformation.dropped_total", dropped)
        self.registry.record_timing("transformation.duration_seconds", duration)
        self.registry.set_gauge(
            "transformation.drop_ratio",
            dropped / input_count if input_count > 0 else 0.0,
        )

    def record_loading(
        self,
        target: str,
        inserted: int,
        updated: int,
        skipped: int,
        failed: int,
        duration: float,
    ) -> None:
        """Record metrics for a loading operation."""
        labels = {"target": target}
        self.registry.increment("loading.inserted_total", inserted, labels)
        self.registry.increment("loading.updated_total", updated, labels)
        self.registry.increment("loading.skipped_total", skipped, labels)
        self.registry.increment("loading.failed_total", failed, labels)
        self.registry.increment("loading.runs_total", 1, labels)
        self.registry.record_timing("loading.duration_seconds", duration, labels)

    def record_pipeline_run(
        self,
        status: str,
        duration: float,
        extracted: int,
        transformed: int,
        loaded: int,
    ) -> None:
        """Record metrics for a complete pipeline run."""
        labels = {"status": status}
        self.registry.increment("pipeline.runs_total", 1, labels)
        self.registry.record_timing("pipeline.duration_seconds", duration, labels)
        self.registry.set_gauge("pipeline.last_extracted", float(extracted))
        self.registry.set_gauge("pipeline.last_transformed", float(transformed))
        self.registry.set_gauge("pipeline.last_loaded", float(loaded))
        self.registry.set_gauge(
            "pipeline.last_run_timestamp",
            datetime.utcnow().timestamp(),
        )

    def _sum_counters(self, prefix: str) -> int:
        """Sum all counters that start with the given prefix."""
        total = 0
        for key, value in self.registry._counters.items():
            # Handle both labeled (with {}) and unlabeled counters
            base_key = key.split("{")[0] if "{" in key else key
            if base_key == prefix:
                total += value
        return total

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Get a summary of pipeline metrics."""
        return {
            "extraction": {
                "total_records": self._sum_counters("extraction.records_total"),
                "total_runs": self._sum_counters("extraction.runs_total"),
                "total_errors": self._sum_counters("extraction.errors_total"),
                "timing": self.registry.get_timing("extraction.duration_seconds").to_dict(),
            },
            "transformation": {
                "total_input": self._sum_counters("transformation.input_total"),
                "total_output": self._sum_counters("transformation.output_total"),
                "total_dropped": self._sum_counters("transformation.dropped_total"),
                "drop_ratio": self.registry.get_gauge("transformation.drop_ratio"),
                "timing": self.registry.get_timing("transformation.duration_seconds").to_dict(),
            },
            "loading": {
                "total_inserted": self._sum_counters("loading.inserted_total"),
                "total_updated": self._sum_counters("loading.updated_total"),
                "total_failed": self._sum_counters("loading.failed_total"),
                "timing": self.registry.get_timing("loading.duration_seconds").to_dict(),
            },
            "pipeline": {
                "total_runs": self._sum_counters("pipeline.runs_total"),
                "last_extracted": self.registry.get_gauge("pipeline.last_extracted"),
                "last_transformed": self.registry.get_gauge("pipeline.last_transformed"),
                "last_loaded": self.registry.get_gauge("pipeline.last_loaded"),
                "timing": self.registry.get_timing("pipeline.duration_seconds").to_dict(),
            },
        }


# Global pipeline metrics instance
_pipeline_metrics = PipelineMetrics()


def get_pipeline_metrics() -> PipelineMetrics:
    """Get the global pipeline metrics instance."""
    return _pipeline_metrics
