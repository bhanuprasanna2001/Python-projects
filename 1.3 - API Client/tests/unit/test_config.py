"""Unit tests for the configuration module."""

from __future__ import annotations

import os
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest
from github_client.config import ClientConfig
from github_client.exceptions import ConfigurationError


class TestClientConfig:
    """Tests for the ClientConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClientConfig()

        assert config.base_url == "https://api.github.com"
        assert config.token is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_enabled is True
        assert config.cache_ttl == 300
        assert config.per_page == 30

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClientConfig(
            base_url="https://github.example.com/api/v3",
            token="test_token",
            timeout=60.0,
            max_retries=5,
            cache_enabled=False,
            cache_ttl=600,
            per_page=50,
        )

        assert config.base_url == "https://github.example.com/api/v3"
        assert config.token == "test_token"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.cache_enabled is False
        assert config.cache_ttl == 600
        assert config.per_page == 50

    def test_environment_variable_token(self):
        """Test token from environment variable."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            config = ClientConfig()

        assert config.token == "env_token"

    def test_environment_variable_base_url(self):
        """Test base_url from environment variable."""
        with patch.dict(os.environ, {"GITHUB_BASE_URL": "https://custom.api.com"}):
            config = ClientConfig()

        assert config.base_url == "https://custom.api.com"

    def test_constructor_overrides_env_var(self):
        """Test constructor value overrides environment variable."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            config = ClientConfig(token="constructor_token")

        assert config.token == "constructor_token"

    def test_is_authenticated_with_token(self):
        """Test is_authenticated returns True with token."""
        config = ClientConfig(token="test_token")
        assert config.is_authenticated is True

    def test_is_authenticated_without_token(self):
        """Test is_authenticated returns False without token."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClientConfig()
        assert config.is_authenticated is False

    def test_trailing_slash_removed(self):
        """Test trailing slash is removed from base_url."""
        config = ClientConfig(base_url="https://api.github.com/")
        assert config.base_url == "https://api.github.com"

    def test_immutability(self):
        """Test configuration is immutable (frozen dataclass)."""
        config = ClientConfig()
        with pytest.raises(FrozenInstanceError):
            config.token = "new_token"  # type: ignore

    def test_with_overrides(self):
        """Test creating a new config with overrides."""
        original = ClientConfig(token="original", timeout=30.0)
        modified = original.with_overrides(timeout=60.0, max_retries=5)

        # Original unchanged
        assert original.timeout == 30.0
        assert original.max_retries == 3

        # Modified has new values
        assert modified.timeout == 60.0
        assert modified.max_retries == 5
        assert modified.token == "original"  # Inherited


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_base_url_empty(self):
        """Test empty base_url raises error."""
        with pytest.raises(ConfigurationError, match="cannot be empty"):
            ClientConfig(base_url="")

    def test_invalid_base_url_no_scheme(self):
        """Test base_url without scheme raises error."""
        with pytest.raises(ConfigurationError, match="must start with http"):
            ClientConfig(base_url="api.github.com")

    def test_invalid_timeout_zero(self):
        """Test zero timeout raises error."""
        with pytest.raises(ConfigurationError, match="timeout must be positive"):
            ClientConfig(timeout=0)

    def test_invalid_timeout_negative(self):
        """Test negative timeout raises error."""
        with pytest.raises(ConfigurationError, match="timeout must be positive"):
            ClientConfig(timeout=-1.0)

    def test_invalid_max_retries_negative(self):
        """Test negative max_retries raises error."""
        with pytest.raises(ConfigurationError, match="cannot be negative"):
            ClientConfig(max_retries=-1)

    def test_invalid_retry_backoff_factor(self):
        """Test backoff factor < 1.0 raises error."""
        with pytest.raises(ConfigurationError, match=r"must be >= 1\.0"):
            ClientConfig(retry_backoff_factor=0.5)

    def test_invalid_cache_ttl_negative(self):
        """Test negative cache_ttl raises error."""
        with pytest.raises(ConfigurationError, match="cannot be negative"):
            ClientConfig(cache_ttl=-1)

    def test_invalid_rate_limit_buffer_negative(self):
        """Test negative rate_limit_buffer raises error."""
        with pytest.raises(ConfigurationError, match=r"between 0\.0 and 1\.0"):
            ClientConfig(rate_limit_buffer=-0.1)

    def test_invalid_rate_limit_buffer_too_high(self):
        """Test rate_limit_buffer >= 1.0 raises error."""
        with pytest.raises(ConfigurationError, match=r"between 0\.0 and 1\.0"):
            ClientConfig(rate_limit_buffer=1.0)

    def test_invalid_per_page_zero(self):
        """Test per_page of 0 raises error."""
        with pytest.raises(ConfigurationError, match="between 1 and"):
            ClientConfig(per_page=0)

    def test_invalid_per_page_too_high(self):
        """Test per_page > 100 raises error."""
        with pytest.raises(ConfigurationError, match="between 1 and"):
            ClientConfig(per_page=101)

    def test_valid_edge_cases(self):
        """Test valid edge case values."""
        # These should all succeed
        config = ClientConfig(
            timeout=0.001,  # Very small but positive
            max_retries=0,  # Zero retries is valid
            cache_ttl=0,  # Zero TTL is valid (no cache)
            rate_limit_buffer=0.0,  # No buffer is valid
            per_page=1,  # Minimum valid
        )
        assert config.timeout == 0.001
        assert config.max_retries == 0
        assert config.cache_ttl == 0
        assert config.rate_limit_buffer == 0.0
        assert config.per_page == 1

        config2 = ClientConfig(per_page=100)  # Maximum valid
        assert config2.per_page == 100
