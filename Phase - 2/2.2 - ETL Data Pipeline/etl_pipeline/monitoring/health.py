"""
Health check system for pipeline monitoring.

Provides:
- Component health checks
- Dependency verification
- Overall system health status
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite

from etl_pipeline.config import get_project_root, get_settings
from etl_pipeline.utils.logging import get_logger
from etl_pipeline.utils.metrics import get_metrics

logger = get_logger("monitoring.health")


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms else None,
            "details": self.details,
            "checked_at": self.checked_at.isoformat() + "Z",
        }


@dataclass
class OverallHealth:
    """Overall system health status."""

    status: HealthStatus
    checks: list[HealthCheckResult]
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "summary": {
                "total": len(self.checks),
                "healthy": sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY),
            },
            "checked_at": self.checked_at.isoformat() + "Z",
        }


class HealthChecker:
    """
    Performs health checks on pipeline components.

    Features:
    - Configurable health checks
    - Dependency checks (database, sources)
    - Staleness detection
    - Extensible check registration
    """

    def __init__(self) -> None:
        """Initialize health checker."""
        self._checks: dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register("database", self._check_database)
        self.register("disk_space", self._check_disk_space)
        self.register("pipeline_staleness", self._check_pipeline_staleness)
        self.register("metrics_system", self._check_metrics_system)

    def register(self, name: str, check: Callable[[], Awaitable[HealthCheckResult]]) -> None:
        """Register a health check."""
        self._checks[name] = check

    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)

    async def check(self, name: str) -> HealthCheckResult:
        """Run a single health check by name."""
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found",
            )

        try:
            start = datetime.utcnow()
            result = await self._checks[name]()
            result.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
            return result
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed with error: {e!s}",
            )

    async def check_all(self) -> OverallHealth:
        """Run all registered health checks."""
        results = await asyncio.gather(
            *[self.check(name) for name in self._checks],
            return_exceptions=True,
        )

        check_results: list[HealthCheckResult] = []
        for name, result in zip(self._checks.keys(), results, strict=False):
            if isinstance(result, Exception):
                check_results.append(
                    HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(result),
                    )
                )
            elif isinstance(result, HealthCheckResult):
                check_results.append(result)

        # Determine overall status
        statuses = [r.status for r in check_results]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        return OverallHealth(
            status=overall_status,
            checks=check_results,
        )

    # --- Default Health Checks ---

    async def _check_database(self) -> HealthCheckResult:
        """Check database connectivity."""
        try:
            settings = get_settings()
            db_path_raw = settings.loading.sqlite.path

            if not Path(db_path_raw).is_absolute():
                db_path = str(get_project_root() / db_path_raw)
            else:
                db_path = db_path_raw

            if not Path(db_path).exists():
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    message="Database file does not exist (may be first run)",
                    details={"path": str(db_path)},
                )

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM etl_records")
                row = await cursor.fetchone()
                record_count = row[0] if row else 0

                cursor = await db.execute("SELECT MAX(loaded_at) FROM etl_records")
                row = await cursor.fetchone()
                last_loaded = row[0] if row and row[0] else None

            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database accessible",
                details={
                    "path": str(db_path),
                    "record_count": record_count,
                    "last_loaded": last_loaded,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {e!s}",
            )

    async def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            import shutil

            data_dir = get_project_root() / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            total, used, free = shutil.disk_usage(data_dir)
            free_gb = free / (1024**3)
            free_percent = (free / total) * 100

            if free_gb < 1:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Only {free_gb:.2f} GB free"
            elif free_gb < 5:
                status = HealthStatus.DEGRADED
                message = f"Warning: Only {free_gb:.2f} GB free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Adequate disk space: {free_gb:.2f} GB free"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free_gb, 2),
                    "free_percent": round(free_percent, 1),
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Could not check disk space: {e!s}",
            )

    async def _check_pipeline_staleness(self) -> HealthCheckResult:
        """Check if pipeline has run recently."""
        try:
            settings = get_settings()
            db_path_raw = settings.loading.sqlite.path

            if not Path(db_path_raw).is_absolute():
                db_path = str(get_project_root() / db_path_raw)
            else:
                db_path = db_path_raw

            if not Path(db_path).exists():
                return HealthCheckResult(
                    name="pipeline_staleness",
                    status=HealthStatus.DEGRADED,
                    message="No pipeline runs recorded yet",
                )

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT MAX(loaded_at) FROM etl_records")
                row = await cursor.fetchone()
                last_loaded = row[0] if row and row[0] else None

            if not last_loaded:
                return HealthCheckResult(
                    name="pipeline_staleness",
                    status=HealthStatus.DEGRADED,
                    message="No data has been loaded yet",
                )

            # Parse the timestamp
            last_run = datetime.fromisoformat(last_loaded.replace("Z", "+00:00"))
            if last_run.tzinfo:
                last_run = last_run.replace(tzinfo=None)

            age = datetime.utcnow() - last_run
            age_hours = age.total_seconds() / 3600

            # Staleness thresholds
            if age_hours > 24:
                status = HealthStatus.UNHEALTHY
                message = f"Pipeline data is stale: last run {age_hours:.1f} hours ago"
            elif age_hours > 6:
                status = HealthStatus.DEGRADED
                message = f"Pipeline data may be stale: last run {age_hours:.1f} hours ago"
            else:
                status = HealthStatus.HEALTHY
                message = f"Pipeline data is fresh: last run {age_hours:.1f} hours ago"

            return HealthCheckResult(
                name="pipeline_staleness",
                status=status,
                message=message,
                details={
                    "last_run": last_loaded,
                    "age_hours": round(age_hours, 2),
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="pipeline_staleness",
                status=HealthStatus.UNKNOWN,
                message=f"Could not check staleness: {e!s}",
            )

    async def _check_metrics_system(self) -> HealthCheckResult:
        """Check metrics system is working."""
        try:
            registry = get_metrics()
            summary = registry.get_summary()

            return HealthCheckResult(
                name="metrics_system",
                status=HealthStatus.HEALTHY,
                message="Metrics system operational",
                details=summary,
            )

        except Exception as e:
            return HealthCheckResult(
                name="metrics_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Metrics system error: {e!s}",
            )


# Global health checker instance
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
