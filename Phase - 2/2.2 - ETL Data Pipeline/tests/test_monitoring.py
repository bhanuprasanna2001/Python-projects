"""Tests for monitoring components."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from etl_pipeline.monitoring.alerts import (
    Alert,
    AlertLevel,
    AlertManager,
)
from etl_pipeline.monitoring.health import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    OverallHealth,
)
from etl_pipeline.monitoring.metrics_collector import MetricsCollector


class TestHealthChecker:
    """Tests for HealthChecker class."""

    @pytest.mark.asyncio
    async def test_healthy_check(self) -> None:
        """Test a healthy check returns correct status."""
        checker = HealthChecker()

        async def healthy_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
                message="All good",
            )

        checker.register("test", healthy_check)
        result = await checker.check("test")

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_unhealthy_check(self) -> None:
        """Test an unhealthy check returns correct status."""
        checker = HealthChecker()

        async def unhealthy_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="test",
                status=HealthStatus.UNHEALTHY,
                message="Something is wrong",
            )

        checker.register("unhealthy", unhealthy_check)
        result = await checker.check("unhealthy")

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_exception_handling(self) -> None:
        """Test that exceptions in checks are handled gracefully."""
        checker = HealthChecker()

        async def failing_check() -> HealthCheckResult:
            raise RuntimeError("Check failed")

        checker.register("failing", failing_check)
        result = await checker.check("failing")

        assert result.status == HealthStatus.UNHEALTHY
        assert "Check failed" in result.message

    @pytest.mark.asyncio
    async def test_latency_tracking(self) -> None:
        """Test that latency is tracked correctly."""
        checker = HealthChecker()

        async def slow_check() -> HealthCheckResult:
            await asyncio.sleep(0.1)
            return HealthCheckResult(name="slow", status=HealthStatus.HEALTHY)

        checker.register("slow", slow_check)
        result = await checker.check("slow")

        assert result.latency_ms >= 100

    @pytest.mark.asyncio
    async def test_check_all(self) -> None:
        """Test running all checks."""
        checker = HealthChecker()

        # Override with simple checks
        checker._checks.clear()

        async def check1() -> HealthCheckResult:
            return HealthCheckResult(name="check1", status=HealthStatus.HEALTHY)

        async def check2() -> HealthCheckResult:
            return HealthCheckResult(name="check2", status=HealthStatus.HEALTHY)

        checker.register("check1", check1)
        checker.register("check2", check2)

        overall = await checker.check_all()

        assert isinstance(overall, OverallHealth)
        assert overall.status == HealthStatus.HEALTHY
        assert len(overall.checks) == 2

    @pytest.mark.asyncio
    async def test_overall_status_degraded(self) -> None:
        """Test overall status when some checks are degraded."""
        checker = HealthChecker()
        checker._checks.clear()

        async def healthy() -> HealthCheckResult:
            return HealthCheckResult(name="healthy", status=HealthStatus.HEALTHY)

        async def degraded() -> HealthCheckResult:
            return HealthCheckResult(name="degraded", status=HealthStatus.DEGRADED)

        checker.register("healthy", healthy)
        checker.register("degraded", degraded)

        overall = await checker.check_all()
        assert overall.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_unknown_check(self) -> None:
        """Test checking an unknown check name."""
        checker = HealthChecker()
        result = await checker.check("nonexistent")

        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK",
            latency_ms=50.5,
            details={"key": "value"},
        )

        d = result.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "healthy"
        assert d["message"] == "OK"
        assert d["latency_ms"] == 50.5
        assert d["details"]["key"] == "value"


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self) -> None:
        """Test creating an alert."""
        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test Alert",
            message="This is a test",
        )

        assert alert.level == AlertLevel.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test"
        assert alert.timestamp is not None

    def test_alert_to_dict(self) -> None:
        """Test converting alert to dictionary."""
        alert = Alert(
            level=AlertLevel.ERROR,
            title="Error Alert",
            message="Something went wrong",
            source="test",
        )

        d = alert.to_dict()
        assert d["level"] == "error"
        assert d["title"] == "Error Alert"
        assert d["source"] == "test"

    def test_slack_payload(self) -> None:
        """Test Slack payload formatting."""
        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test",
            message="Test message",
        )

        payload = alert.to_slack_payload()
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1

    def test_discord_payload(self) -> None:
        """Test Discord payload formatting."""
        alert = Alert(
            level=AlertLevel.INFO,
            title="Test",
            message="Test message",
        )

        payload = alert.to_discord_payload()
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1


class TestAlertManager:
    """Tests for AlertManager class."""

    def test_initialization(self) -> None:
        """Test alert manager initialization."""
        manager = AlertManager()
        assert manager.enabled is True

    def test_initialization_with_webhook(self) -> None:
        """Test alert manager with webhook."""
        manager = AlertManager(
            webhook_url="http://test.webhook.com",
            webhook_type="slack",
        )
        assert manager.webhook_url == "http://test.webhook.com"
        assert manager.webhook_type == "slack"

    def test_throttle_check(self) -> None:
        """Test alert throttling logic."""
        manager = AlertManager(throttle_minutes=5.0)

        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test",
            message="First",
        )

        # First alert should not be throttled
        assert manager._should_throttle(alert) is False

        # Record the alert
        manager._record_alert(alert)

        # Second identical alert should be throttled
        assert manager._should_throttle(alert) is True

    def test_alert_history(self) -> None:
        """Test that alerts are recorded in history."""
        manager = AlertManager()

        alert = Alert(
            level=AlertLevel.INFO,
            title="Test",
            message="Test message",
        )

        manager._record_alert(alert)
        assert len(manager._alert_history) == 1


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test collector initialization."""
        collector = MetricsCollector(
            metrics_path=tmp_path / "metrics.json",
            history_path=tmp_path / "history.jsonl",
            flush_interval=10,
        )
        assert collector.flush_interval == 10

    def test_path_resolution(self, tmp_path: Path) -> None:
        """Test path resolution."""
        collector = MetricsCollector(
            metrics_path=tmp_path / "metrics.json",
        )
        assert collector.metrics_path == tmp_path / "metrics.json"

    @pytest.mark.asyncio
    async def test_flush(self, tmp_path: Path) -> None:
        """Test flushing metrics to file."""
        collector = MetricsCollector(
            metrics_path=tmp_path / "metrics.json",
            history_path=tmp_path / "history.jsonl",
        )

        await collector.flush()
        # File should be created
        assert collector.metrics_path.exists()

    def test_collect_metrics(self, tmp_path: Path) -> None:
        """Test collecting current metrics."""
        collector = MetricsCollector(
            metrics_path=tmp_path / "metrics.json",
        )

        metrics = collector.collect()
        assert "collected_at" in metrics
        assert "pipeline" in metrics


class TestAlertLevel:
    """Tests for AlertLevel enum."""

    def test_alert_levels(self) -> None:
        """Test alert level values."""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_statuses(self) -> None:
        """Test health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestOverallHealth:
    """Tests for OverallHealth dataclass."""

    def test_to_dict(self) -> None:
        """Test converting overall health to dict."""
        checks = [
            HealthCheckResult(name="check1", status=HealthStatus.HEALTHY),
            HealthCheckResult(name="check2", status=HealthStatus.DEGRADED),
        ]
        overall = OverallHealth(
            status=HealthStatus.DEGRADED,
            checks=checks,
        )

        d = overall.to_dict()
        assert d["status"] == "degraded"
        assert len(d["checks"]) == 2
        assert d["summary"]["healthy"] == 1
        assert d["summary"]["degraded"] == 1
