"""
Metrics collector for aggregating and persisting pipeline metrics.

Provides:
- Periodic metrics persistence to JSON
- Metrics aggregation across runs
- Historical metrics tracking
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from etl_pipeline.config import get_project_root
from etl_pipeline.utils.logging import get_logger
from etl_pipeline.utils.metrics import get_metrics, get_pipeline_metrics

logger = get_logger("monitoring.metrics")


class MetricsCollector:
    """
    Collects and persists pipeline metrics.

    Features:
    - Periodic flushing to JSON file
    - Historical metrics tracking
    - Aggregation across pipeline runs
    """

    def __init__(
        self,
        metrics_path: str | Path = "data/metrics/pipeline_metrics.json",
        history_path: str | Path = "data/metrics/metrics_history.jsonl",
        flush_interval: float = 60.0,
    ) -> None:
        """
        Initialize metrics collector.

        Args:
            metrics_path: Path to current metrics JSON file
            history_path: Path to metrics history (JSONL format)
            flush_interval: Seconds between automatic flushes
        """
        self.metrics_path = self._resolve_path(metrics_path)
        self.history_path = self._resolve_path(history_path)
        self.flush_interval = flush_interval
        self._flush_task: asyncio.Task[None] | None = None
        self._running = False

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve path relative to project root."""
        p = Path(path)
        if not p.is_absolute():
            p = get_project_root() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def start(self) -> None:
        """Start periodic metrics flushing."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("Metrics collector started", extra={"flush_interval": self.flush_interval})

    def stop(self) -> None:
        """Stop periodic metrics flushing."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
        logger.info("Metrics collector stopped")

    async def _periodic_flush(self) -> None:
        """Periodically flush metrics to disk."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error flushing metrics: {e}")

    async def flush(self) -> None:
        """Flush current metrics to disk."""
        metrics = self.collect()

        # Write current metrics
        try:
            self.metrics_path.write_text(json.dumps(metrics, indent=2))
            logger.debug(f"Metrics flushed to {self.metrics_path}")
        except Exception as e:
            logger.error(f"Failed to write metrics: {e}")

        # Append to history
        try:
            history_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **metrics,
            }
            with self.history_path.open("a") as f:
                f.write(json.dumps(history_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write metrics history: {e}")

    def collect(self) -> dict[str, Any]:
        """Collect all current metrics."""
        registry = get_metrics()
        pipeline = get_pipeline_metrics()

        return {
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "registry": registry.get_all_metrics(),
            "pipeline": pipeline.get_pipeline_summary(),
        }

    def get_current_metrics(self) -> dict[str, Any]:
        """Get current metrics without persisting."""
        return self.collect()

    def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Load metrics history.

        Args:
            limit: Maximum number of entries to load (most recent)

        Returns:
            List of historical metrics entries
        """
        if not self.history_path.exists():
            return []

        entries = []
        try:
            with self.history_path.open() as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to load metrics history: {e}")
            return []

        # Return most recent entries
        return entries[-limit:]

    def get_trends(self, metric_name: str, periods: int = 10) -> dict[str, Any]:
        """
        Get trend data for a specific metric.

        Args:
            metric_name: Name of the metric to track
            periods: Number of historical periods to analyze

        Returns:
            Trend information including direction and values
        """
        history = self.load_history(limit=periods)
        if not history:
            return {"error": "No historical data available"}

        values = []
        for entry in history:
            # Try to extract metric value from nested structure
            value = self._extract_metric(entry, metric_name)
            if value is not None:
                values.append(
                    {
                        "timestamp": entry.get("timestamp"),
                        "value": value,
                    }
                )

        if len(values) < 2:
            return {"metric": metric_name, "values": values, "trend": "insufficient_data"}

        # Calculate trend
        first_val = values[0]["value"]
        last_val = values[-1]["value"]

        if first_val == 0:
            change_pct = 100.0 if last_val > 0 else 0.0
        else:
            change_pct = ((last_val - first_val) / first_val) * 100

        trend = "increasing" if change_pct > 5 else "decreasing" if change_pct < -5 else "stable"

        return {
            "metric": metric_name,
            "values": values,
            "trend": trend,
            "change_percent": round(change_pct, 2),
            "first_value": first_val,
            "last_value": last_val,
        }

    def _extract_metric(self, entry: dict[str, Any], metric_name: str) -> float | None:
        """Extract a metric value from a historical entry."""
        # Handle dotted paths like "pipeline.extraction.total_records"
        parts = metric_name.split(".")
        current = entry

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        if isinstance(current, (int, float)):
            return float(current)
        return None

    async def __aenter__(self) -> MetricsCollector:
        """Async context manager entry."""
        self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.flush()
        self.stop()


# Global collector instance
_collector: MetricsCollector | None = None


def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
