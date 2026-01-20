"""GitHub Client Library - A Python client for the GitHub API.

This library provides a clean, typed interface for interacting with GitHub's REST API.
It includes automatic rate limiting, retry logic, response caching, and pagination handling.

Example:
    >>> from github_client import GitHubClient
    >>> client = GitHubClient(token="ghp_xxx")
    >>> user = client.users.get("octocat")
    >>> print(f"{user.login} has {user.public_repos} public repos")

"""

from github_client.client import GitHubClient
from github_client.config import ClientConfig
from github_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    GitHubError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

__version__ = "1.0.0"
__author__ = "Bhanu Prasanna"

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "ClientConfig",
    "ConfigurationError",
    "GitHubClient",
    "GitHubError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
]
