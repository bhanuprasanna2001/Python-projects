"""
Alerting system for pipeline monitoring.

Provides:
- Webhook-based alerts (Slack, Discord, generic)
- Configurable alert thresholds
- Alert deduplication and throttling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx

from etl_pipeline.utils.logging import get_logger

logger = get_logger("monitoring.alerts")


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert to be sent."""

    level: AlertLevel
    title: str
    message: str
    source: str = "etl_pipeline"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() + "Z",
            "metadata": self.metadata,
        }

    def to_slack_payload(self) -> dict[str, Any]:
        """Format as Slack webhook payload."""
        color_map = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ffcc00",
            AlertLevel.ERROR: "#ff6600",
            AlertLevel.CRITICAL: "#ff0000",
        }

        return {
            "attachments": [
                {
                    "color": color_map.get(self.level, "#808080"),
                    "title": f"[{self.level.value.upper()}] {self.title}",
                    "text": self.message,
                    "fields": [
                        {"title": "Source", "value": self.source, "short": True},
                        {
                            "title": "Time",
                            "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ]
                    + [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in self.metadata.items()
                    ],
                    "footer": "ETL Pipeline Monitoring",
                    "ts": int(self.timestamp.timestamp()),
                }
            ]
        }

    def to_discord_payload(self) -> dict[str, Any]:
        """Format as Discord webhook payload."""
        color_map = {
            AlertLevel.INFO: 0x36A64F,
            AlertLevel.WARNING: 0xFFCC00,
            AlertLevel.ERROR: 0xFF6600,
            AlertLevel.CRITICAL: 0xFF0000,
        }

        return {
            "embeds": [
                {
                    "title": f"[{self.level.value.upper()}] {self.title}",
                    "description": self.message,
                    "color": color_map.get(self.level, 0x808080),
                    "fields": [
                        {"name": "Source", "value": self.source, "inline": True},
                        {
                            "name": "Time",
                            "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "inline": True,
                        },
                    ]
                    + [
                        {"name": k, "value": str(v), "inline": True}
                        for k, v in self.metadata.items()
                    ],
                    "footer": {"text": "ETL Pipeline Monitoring"},
                    "timestamp": self.timestamp.isoformat() + "Z",
                }
            ]
        }


class AlertManager:
    """
    Manages alert delivery with throttling and deduplication.

    Features:
    - Multiple webhook support (Slack, Discord, generic)
    - Alert throttling to prevent spam
    - Alert history tracking
    - Configurable thresholds
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        webhook_type: str = "generic",  # slack, discord, generic
        throttle_minutes: float = 5.0,
        enabled: bool = True,
    ) -> None:
        """
        Initialize alert manager.

        Args:
            webhook_url: URL to send alerts to
            webhook_type: Type of webhook (slack, discord, generic)
            throttle_minutes: Minimum minutes between identical alerts
            enabled: Whether alerting is enabled
        """
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type
        self.throttle_minutes = throttle_minutes
        self.enabled = enabled

        self._alert_history: list[Alert] = []
        self._last_alert_times: dict[str, datetime] = {}
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _should_throttle(self, alert: Alert) -> bool:
        """Check if alert should be throttled."""
        key = f"{alert.level.value}:{alert.title}"
        last_time = self._last_alert_times.get(key)

        if last_time is None:
            return False

        elapsed = datetime.utcnow() - last_time
        return elapsed < timedelta(minutes=self.throttle_minutes)

    def _record_alert(self, alert: Alert) -> None:
        """Record alert in history."""
        key = f"{alert.level.value}:{alert.title}"
        self._last_alert_times[key] = alert.timestamp
        self._alert_history.append(alert)

        # Keep only last 100 alerts
        if len(self._alert_history) > 100:
            self._alert_history = self._alert_history[-100:]

    def _format_payload(self, alert: Alert) -> dict[str, Any]:
        """Format alert for the configured webhook type."""
        if self.webhook_type == "slack":
            return alert.to_slack_payload()
        elif self.webhook_type == "discord":
            return alert.to_discord_payload()
        else:
            return alert.to_dict()

    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert.

        Args:
            alert: The alert to send

        Returns:
            True if alert was sent successfully
        """
        if not self.enabled:
            logger.debug(f"Alerting disabled, not sending: {alert.title}")
            self._record_alert(alert)
            return False

        if self._should_throttle(alert):
            logger.debug(f"Alert throttled: {alert.title}")
            return False

        self._record_alert(alert)

        # Log the alert regardless of webhook
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(alert.level, logger.info)

        log_method(
            f"ALERT: {alert.title} - {alert.message}",
            extra={"alert": alert.to_dict()},
        )

        # Send to webhook if configured
        if self.webhook_url:
            try:
                client = await self._get_client()
                payload = self._format_payload(alert)

                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code >= 400:
                    logger.error(
                        f"Webhook returned error: {response.status_code}",
                        extra={"response": response.text},
                    )
                    return False

                logger.info(f"Alert sent to webhook: {alert.title}")
                return True

            except Exception as e:
                logger.error(f"Failed to send alert to webhook: {e}")
                return False

        return True

    # --- Convenience Methods ---

    async def info(self, title: str, message: str, **metadata: Any) -> bool:
        """Send an info-level alert."""
        return await self.send_alert(
            Alert(level=AlertLevel.INFO, title=title, message=message, metadata=metadata)
        )

    async def warning(self, title: str, message: str, **metadata: Any) -> bool:
        """Send a warning-level alert."""
        return await self.send_alert(
            Alert(level=AlertLevel.WARNING, title=title, message=message, metadata=metadata)
        )

    async def error(self, title: str, message: str, **metadata: Any) -> bool:
        """Send an error-level alert."""
        return await self.send_alert(
            Alert(level=AlertLevel.ERROR, title=title, message=message, metadata=metadata)
        )

    async def critical(self, title: str, message: str, **metadata: Any) -> bool:
        """Send a critical-level alert."""
        return await self.send_alert(
            Alert(level=AlertLevel.CRITICAL, title=title, message=message, metadata=metadata)
        )

    # --- Pipeline-Specific Alerts ---

    async def pipeline_failed(self, job_id: str, error: str, duration: float | None = None) -> bool:
        """Send alert for pipeline failure."""
        return await self.error(
            title="Pipeline Failed",
            message=f"Pipeline job failed with error: {error}",
            job_id=job_id,
            duration_seconds=duration,
        )

    async def pipeline_degraded(self, job_id: str, reason: str, metric: str, value: float) -> bool:
        """Send alert for degraded pipeline performance."""
        return await self.warning(
            title="Pipeline Degraded",
            message=f"Pipeline performance degraded: {reason}",
            job_id=job_id,
            metric=metric,
            value=value,
        )

    async def low_record_count(self, source: str, expected: int, actual: int) -> bool:
        """Send alert for unexpectedly low record count."""
        return await self.warning(
            title="Low Record Count",
            message=f"Source '{source}' returned fewer records than expected",
            source=source,
            expected=expected,
            actual=actual,
            shortage_percent=round((1 - actual / expected) * 100, 1) if expected > 0 else 100,
        )

    async def data_quality_issue(self, metric: str, threshold: float, actual: float) -> bool:
        """Send alert for data quality issues."""
        return await self.warning(
            title="Data Quality Issue",
            message=f"Data quality metric '{metric}' below threshold",
            metric=metric,
            threshold=threshold,
            actual=actual,
        )

    async def source_unavailable(self, source: str, error: str) -> bool:
        """Send alert for source connectivity issues."""
        return await self.error(
            title="Source Unavailable",
            message=f"Failed to connect to data source: {source}",
            source=source,
            error=error,
        )

    # --- History ---

    def get_alert_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent alert history."""
        return [a.to_dict() for a in self._alert_history[-limit:]]

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Global alert manager instance
_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def configure_alerts(
    webhook_url: str | None = None,
    webhook_type: str = "generic",
    enabled: bool = True,
) -> AlertManager:
    """Configure the global alert manager."""
    global _alert_manager
    _alert_manager = AlertManager(
        webhook_url=webhook_url,
        webhook_type=webhook_type,
        enabled=enabled,
    )
    return _alert_manager
