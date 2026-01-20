"""Tests for the metrics infrastructure."""

from __future__ import annotations

import asyncio
import time

import pytest

from etl_pipeline.utils.metrics import (
    MetricsRegistry,
    PipelineMetrics,
    TimingStats,
    async_timed,
    get_metrics,
    reset_metrics,
    timed,
)


class TestTimingStats:
    """Tests for TimingStats class."""

    def test_empty_stats(self) -> None:
        """Test stats with no measurements."""
        stats = TimingStats()
        assert stats.count == 0
        assert stats.avg_seconds == 0
        assert stats.total_seconds == 0
        assert stats.max_seconds == 0

    def test_single_measurement(self) -> None:
        """Test stats with single measurement."""
        stats = TimingStats()
        stats.record(1.5)
        assert stats.count == 1
        assert stats.avg_seconds == 1.5
        assert stats.min_seconds == 1.5
        assert stats.max_seconds == 1.5

    def test_multiple_measurements(self) -> None:
        """Test stats with multiple measurements."""
        stats = TimingStats()
        for value in [1.0, 2.0, 3.0, 4.0, 5.0]:
            stats.record(value)

        assert stats.count == 5
        assert stats.avg_seconds == 3.0
        assert stats.min_seconds == 1.0
        assert stats.max_seconds == 5.0

    def test_percentiles(self) -> None:
        """Test percentile calculations."""
        stats = TimingStats()
        for i in range(100):
            stats.record(i)

        # Median should be close to 49-50
        assert 45 <= stats.median_seconds <= 55
        # P95 should be around 95
        assert 90 <= stats.p95_seconds <= 99
        # P99 should be around 99
        assert 95 <= stats.p99_seconds <= 100

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        stats = TimingStats()
        stats.record(1.0)
        stats.record(2.0)

        d = stats.to_dict()
        assert "count" in d
        assert "avg_seconds" in d
        assert "min_seconds" in d
        assert "max_seconds" in d
        assert "p95_seconds" in d
        assert "p99_seconds" in d


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def setup_method(self) -> None:
        """Reset metrics before each test."""
        reset_metrics()

    def test_counter(self) -> None:
        """Test counter operations."""
        registry = get_metrics()
        registry.increment("test_counter")
        assert registry.get_counter("test_counter") == 1

        registry.increment("test_counter", 5)
        assert registry.get_counter("test_counter") == 6

    def test_gauge(self) -> None:
        """Test gauge operations."""
        registry = get_metrics()
        registry.set_gauge("test_gauge", 42)
        assert registry.get_gauge("test_gauge") == 42

        registry.set_gauge("test_gauge", 100)
        assert registry.get_gauge("test_gauge") == 100

    def test_timing(self) -> None:
        """Test timing operations."""
        registry = get_metrics()
        registry.record_timing("test_timing", 1.5)
        registry.record_timing("test_timing", 2.5)

        stats = registry.get_timing("test_timing")
        assert stats.count == 2
        assert stats.avg_seconds == 2.0

    def test_reset(self) -> None:
        """Test resetting all metrics."""
        registry = get_metrics()
        registry.increment("counter")
        registry.set_gauge("gauge", 10)
        registry.record_timing("timing", 1.0)

        reset_metrics()

        assert registry.get_counter("counter") == 0
        assert registry.get_gauge("gauge") == 0
        assert registry.get_timing("timing").count == 0

    def test_get_all_metrics(self) -> None:
        """Test getting all metrics."""
        registry = get_metrics()
        registry.increment("counter")
        registry.set_gauge("gauge", 10)
        registry.record_timing("timing", 1.0)

        all_metrics = registry.get_all_metrics()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "timings" in all_metrics

    def test_labels(self) -> None:
        """Test metrics with labels."""
        registry = get_metrics()
        registry.increment("http_requests", labels={"method": "GET"})
        registry.increment("http_requests", labels={"method": "POST"})

        assert registry.get_counter("http_requests", labels={"method": "GET"}) == 1
        assert registry.get_counter("http_requests", labels={"method": "POST"}) == 1


class TestPipelineMetrics:
    """Tests for PipelineMetrics class."""

    def test_extraction_metrics(self) -> None:
        """Test recording extraction metrics."""
        # Create fresh instance with fresh registry
        registry = MetricsRegistry.__new__(MetricsRegistry)
        registry._initialized = False
        registry.__init__()
        metrics = PipelineMetrics(registry)

        metrics.record_extraction("github", 100, 1.5)

        summary = metrics.get_pipeline_summary()
        assert "extraction" in summary
        assert summary["extraction"]["total_records"] == 100
        assert summary["extraction"]["total_runs"] == 1

    def test_transformation_metrics(self) -> None:
        """Test recording transformation metrics."""
        registry = MetricsRegistry.__new__(MetricsRegistry)
        registry._initialized = False
        registry.__init__()
        metrics = PipelineMetrics(registry)

        metrics.record_transformation(100, 80, 1.0, dropped=20)

        summary = metrics.get_pipeline_summary()
        assert "transformation" in summary
        assert summary["transformation"]["total_input"] == 100
        assert summary["transformation"]["total_output"] == 80
        assert summary["transformation"]["total_dropped"] == 20

    def test_loading_metrics(self) -> None:
        """Test recording loading metrics."""
        registry = MetricsRegistry.__new__(MetricsRegistry)
        registry._initialized = False
        registry.__init__()
        metrics = PipelineMetrics(registry)

        metrics.record_loading("sqlite", 80, 5, 10, 0, 0.5)

        summary = metrics.get_pipeline_summary()
        assert "loading" in summary
        assert summary["loading"]["total_inserted"] == 80
        assert summary["loading"]["total_updated"] == 5

    def test_pipeline_run_metrics(self) -> None:
        """Test recording complete pipeline run."""
        registry = MetricsRegistry.__new__(MetricsRegistry)
        registry._initialized = False
        registry.__init__()
        metrics = PipelineMetrics(registry)

        metrics.record_pipeline_run(
            status="completed",
            duration=5.0,
            extracted=100,
            transformed=90,
            loaded=85,
        )

        summary = metrics.get_pipeline_summary()
        assert summary["pipeline"]["total_runs"] == 1
        assert summary["pipeline"]["last_extracted"] == 100
        assert summary["pipeline"]["last_transformed"] == 90
        assert summary["pipeline"]["last_loaded"] == 85

    def test_full_pipeline_metrics(self) -> None:
        """Test recording full pipeline run."""
        registry = MetricsRegistry.__new__(MetricsRegistry)
        registry._initialized = False
        registry.__init__()
        metrics = PipelineMetrics(registry)

        # Simulate a full pipeline run
        metrics.record_extraction("csv", 100, 0.5)
        metrics.record_extraction("sqlite", 50, 0.3)
        metrics.record_transformation(150, 120, 1.0, dropped=30)
        metrics.record_loading("sqlite", 100, 15, 5, 0, 0.8)

        summary = metrics.get_pipeline_summary()
        assert summary is not None
        assert summary["extraction"]["total_records"] == 150
        assert summary["extraction"]["total_runs"] == 2


class TestTimedDecorators:
    """Tests for timing decorators."""

    def setup_method(self) -> None:
        """Reset metrics before each test."""
        reset_metrics()

    def test_sync_timed_decorator(self) -> None:
        """Test synchronous timing decorator."""
        registry = get_metrics()

        @timed("test_func")
        def slow_function():
            time.sleep(0.1)
            return "result"

        result = slow_function()
        assert result == "result"

        stats = registry.get_timing("test_func")
        assert stats.count == 1
        assert stats.avg_seconds >= 0.1

    @pytest.mark.asyncio
    async def test_async_timed_decorator(self) -> None:
        """Test asynchronous timing decorator."""
        registry = get_metrics()

        @async_timed("async_test_func")
        async def async_slow_function():
            await asyncio.sleep(0.1)
            return "async_result"

        result = await async_slow_function()
        assert result == "async_result"

        stats = registry.get_timing("async_test_func")
        assert stats.count == 1
        assert stats.avg_seconds >= 0.1

    def test_decorator_preserves_exceptions(self) -> None:
        """Test that decorator preserves exceptions."""

        @timed("error_func")
        def error_function():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            error_function()

    def test_context_manager_timing(self) -> None:
        """Test timing context manager."""
        registry = get_metrics()

        with registry.time("context_op"):
            time.sleep(0.05)

        stats = registry.get_timing("context_op")
        assert stats.count == 1
        assert stats.avg_seconds >= 0.05
