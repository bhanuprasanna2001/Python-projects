"""Configuration management for the GitHub Client.

This module provides a flexible configuration system that supports:
- Programmatic configuration via constructor arguments
- Environment variable overrides
- Sensible defaults for all options

Configuration Precedence (highest to lowest):
    1. Constructor arguments
    2. Environment variables
    3. Default values

Environment Variables:
    GITHUB_TOKEN: Personal access token for authentication
    GITHUB_BASE_URL: API base URL (default: https://api.github.com)
    GITHUB_TIMEOUT: Request timeout in seconds (default: 30)
    GITHUB_MAX_RETRIES: Maximum retry attempts (default: 3)
    GITHUB_CACHE_TTL: Cache time-to-live in seconds (default: 300)

Example:
    >>> # Using defaults with env vars
    >>> config = ClientConfig()
    >>>
    >>> # Override specific settings
    >>> config = ClientConfig(timeout=60.0, max_retries=5)
    >>>
    >>> # Full programmatic configuration
    >>> config = ClientConfig(
    ...     token="ghp_xxx",
    ...     timeout=30.0,
    ...     cache_enabled=True,
    ... )

"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

from github_client.exceptions import ConfigurationError

# Auto-load .env file if it exists (searches current dir and parents)
_env_file = Path.cwd() / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()  # Try to find .env in parent directories


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Immutable configuration for the GitHub API client.

    This class uses dataclass with frozen=True to ensure configuration
    cannot be modified after creation, preventing subtle bugs.

    Attributes:
        base_url: GitHub API base URL.
        token: Personal access token for authentication.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts for failed requests.
        retry_backoff_factor: Exponential backoff multiplier between retries.
        cache_enabled: Whether to cache responses.
        cache_ttl: Cache time-to-live in seconds.
        rate_limit_buffer: Fraction of rate limit to reserve (0.0-1.0).
        user_agent: User-Agent header for requests.
        per_page: Default items per page for paginated requests.

    """

    # Class-level constants
    DEFAULT_BASE_URL: ClassVar[str] = "https://api.github.com"
    DEFAULT_TIMEOUT: ClassVar[float] = 30.0
    DEFAULT_MAX_RETRIES: ClassVar[int] = 3
    DEFAULT_CACHE_TTL: ClassVar[int] = 300
    DEFAULT_PER_PAGE: ClassVar[int] = 30
    MAX_PER_PAGE: ClassVar[int] = 100

    # Configuration fields with defaults
    base_url: str = field(
        default_factory=lambda: _get_env("GITHUB_BASE_URL", ClientConfig.DEFAULT_BASE_URL)
    )
    token: str | None = field(default_factory=lambda: _get_env_optional("GITHUB_TOKEN"))
    timeout: float = field(
        default_factory=lambda: float(_get_env("GITHUB_TIMEOUT", str(ClientConfig.DEFAULT_TIMEOUT)))
    )
    max_retries: int = field(
        default_factory=lambda: int(
            _get_env("GITHUB_MAX_RETRIES", str(ClientConfig.DEFAULT_MAX_RETRIES))
        )
    )
    retry_backoff_factor: float = 1.5
    cache_enabled: bool = True
    cache_ttl: int = field(
        default_factory=lambda: int(
            _get_env("GITHUB_CACHE_TTL", str(ClientConfig.DEFAULT_CACHE_TTL))
        )
    )
    rate_limit_buffer: float = 0.1
    user_agent: str = "python-github-client/1.0"
    per_page: int = DEFAULT_PER_PAGE

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate all configuration values.

        Raises:
            ConfigurationError: If any configuration value is invalid.

        """
        # Validate base_url
        if not self.base_url:
            raise ConfigurationError("base_url cannot be empty")
        if not self.base_url.startswith(("http://", "https://")):
            raise ConfigurationError(
                f"Invalid base_url: {self.base_url} (must start with http:// or https://)"
            )

        # Remove trailing slash for consistency
        if self.base_url.endswith("/"):
            # Use object.__setattr__ since dataclass is frozen
            object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

        # Validate timeout
        if self.timeout <= 0:
            raise ConfigurationError(f"timeout must be positive, got {self.timeout}")

        # Validate max_retries
        if self.max_retries < 0:
            raise ConfigurationError(f"max_retries cannot be negative, got {self.max_retries}")

        # Validate retry_backoff_factor
        if self.retry_backoff_factor < 1.0:
            raise ConfigurationError(
                f"retry_backoff_factor must be >= 1.0, got {self.retry_backoff_factor}"
            )

        # Validate cache_ttl
        if self.cache_ttl < 0:
            raise ConfigurationError(f"cache_ttl cannot be negative, got {self.cache_ttl}")

        # Validate rate_limit_buffer
        if not 0.0 <= self.rate_limit_buffer < 1.0:
            raise ConfigurationError(
                f"rate_limit_buffer must be between 0.0 and 1.0, got {self.rate_limit_buffer}"
            )

        # Validate per_page
        if not 1 <= self.per_page <= self.MAX_PER_PAGE:
            raise ConfigurationError(
                f"per_page must be between 1 and {self.MAX_PER_PAGE}, got {self.per_page}"
            )

    @property
    def is_authenticated(self) -> bool:
        """Check if the configuration includes authentication."""
        return self.token is not None and len(self.token) > 0

    def with_overrides(self, **kwargs: object) -> ClientConfig:
        """Create a new configuration with specified overrides.

        This is useful for creating variations of a base configuration
        without modifying the original.

        Args:
            **kwargs: Configuration values to override.

        Returns:
            A new ClientConfig with the specified overrides.

        Example:
            >>> base_config = ClientConfig(token="ghp_xxx")
            >>> test_config = base_config.with_overrides(timeout=5.0)

        """
        current_values: dict[str, str | float | int | bool | None] = {
            "base_url": self.base_url,
            "token": self.token,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_backoff_factor": self.retry_backoff_factor,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "rate_limit_buffer": self.rate_limit_buffer,
            "user_agent": self.user_agent,
            "per_page": self.per_page,
        }
        current_values.update(kwargs)  # type: ignore[arg-type]
        return ClientConfig(**current_values)  # type: ignore[arg-type]


def _get_env(key: str, default: str) -> str:
    """Get environment variable with default.

    Args:
        key: Environment variable name.
        default: Default value if not set.

    Returns:
        The environment variable value or default.

    """
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


def _get_env_optional(key: str) -> str | None:
    """Get optional environment variable.

    Args:
        key: Environment variable name.

    Returns:
        The environment variable value or None.

    """
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    return value
