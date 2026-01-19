"""Authentication strategies for the GitHub API.

This module provides a protocol-based authentication system that allows
for different authentication methods to be used interchangeably.

Supported Authentication Methods:
    - TokenAuth: Personal Access Token (PAT) authentication
    - NoAuth: Unauthenticated requests (lower rate limits)

The strategy pattern allows easy extension for future auth methods:
    - OAuth App authentication
    - GitHub App authentication (JWT + installation tokens)

Example:
    >>> from github_client.auth import TokenAuth, NoAuth
    >>>
    >>> # Using a personal access token
    >>> auth = TokenAuth("ghp_xxxxxxxxxxxx")
    >>>
    >>> # Unauthenticated requests
    >>> auth = NoAuth()

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


class AuthStrategy(ABC):
    """Abstract base class for authentication strategies.

    All authentication implementations must inherit from this class
    and implement the apply() method.

    """

    @abstractmethod
    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply authentication to an outgoing request.

        Args:
            request: The httpx request to authenticate.

        Returns:
            The request with authentication applied.

        """

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if this strategy provides authentication."""


class TokenAuth(AuthStrategy):
    """Personal Access Token (PAT) authentication.

    This is the most common authentication method for the GitHub API.
    Tokens can be created at: https://github.com/settings/tokens

    Attributes:
        token: The personal access token.

    Example:
        >>> auth = TokenAuth("ghp_xxxxxxxxxxxx")
        >>> # Token is applied as Bearer token in Authorization header

    """

    __slots__ = ("_token",)

    def __init__(self, token: str) -> None:
        """Initialize with a personal access token.

        Args:
            token: GitHub personal access token (starts with ghp_, github_pat_, etc.)

        Raises:
            ValueError: If token is empty or None.

        """
        if not token or not token.strip():
            raise ValueError("Token cannot be empty")
        self._token = token.strip()

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply Bearer token authentication to the request.

        Args:
            request: The httpx request to authenticate.

        Returns:
            The request with Authorization header set.

        """
        request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    @property
    def is_authenticated(self) -> bool:
        """Return True as this strategy provides authentication."""
        return True

    def __repr__(self) -> str:
        """Return a safe representation without exposing the token."""
        # Show only first 4 chars for debugging
        masked = f"{self._token[:4]}..." if len(self._token) > 4 else "***"
        return f"TokenAuth(token={masked!r})"


class NoAuth(AuthStrategy):
    """No authentication (anonymous requests).

    Use this for public endpoints when you don't need authentication.
    Note that unauthenticated requests have lower rate limits (60/hour).

    Example:
        >>> auth = NoAuth()
        >>> # No Authorization header is added

    """

    __slots__ = ()

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Return the request unchanged (no authentication).

        Args:
            request: The httpx request (unchanged).

        Returns:
            The same request without any authentication.

        """
        return request

    @property
    def is_authenticated(self) -> bool:
        """Return False as this strategy provides no authentication."""
        return False

    def __repr__(self) -> str:
        """Return a simple representation."""
        return "NoAuth()"


def create_auth(token: str | None) -> AuthStrategy:
    """Factory function to create the appropriate auth strategy.

    Args:
        token: Personal access token, or None for unauthenticated.

    Returns:
        TokenAuth if token provided, NoAuth otherwise.

    Example:
        >>> auth = create_auth("ghp_xxx")  # Returns TokenAuth
        >>> auth = create_auth(None)  # Returns NoAuth

    """
    if token:
        return TokenAuth(token)
    return NoAuth()
