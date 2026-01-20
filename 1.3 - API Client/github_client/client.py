"""Main GitHub Client class.

This module provides the main entry point for the GitHub API client.
The GitHubClient class orchestrates all endpoint groups and manages
the HTTP client lifecycle.

Example:
    >>> from github_client import GitHubClient
    >>>
    >>> # Unauthenticated (60 requests/hour)
    >>> client = GitHubClient()
    >>> user = client.users.get("octocat")
    >>>
    >>> # Authenticated (5000 requests/hour)
    >>> client = GitHubClient(token="ghp_xxx")
    >>> me = client.users.get_authenticated()

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from github_client.auth import create_auth
from github_client.config import ClientConfig
from github_client.endpoints.gists import GistsEndpoint
from github_client.endpoints.issues import IssuesEndpoint
from github_client.endpoints.orgs import OrgsEndpoint
from github_client.endpoints.pulls import PullsEndpoint
from github_client.endpoints.repos import ReposEndpoint
from github_client.endpoints.search import SearchEndpoint
from github_client.endpoints.users import UsersEndpoint
from github_client.utils.cache import ResponseCache
from github_client.utils.http import HTTPClient
from github_client.utils.rate_limiter import RateLimiter

if TYPE_CHECKING:
    pass


class GitHubClient:
    """GitHub API client with typed endpoints.

    This is the main entry point for interacting with the GitHub API.
    It provides access to all API endpoints through typed endpoint classes.

    Attributes:
        users: User-related API endpoints.
        repos: Repository-related API endpoints.
        issues: Issue-related API endpoints.
        pulls: Pull request-related API endpoints.
        search: Search API endpoints.
        gists: Gist-related API endpoints.
        orgs: Organization-related API endpoints.

    Example:
        >>> client = GitHubClient(token="ghp_xxx")
        >>>
        >>> # Get a user
        >>> user = client.users.get("octocat")
        >>> print(f"{user.name} has {user.public_repos} repos")
        >>>
        >>> # Search repositories
        >>> results = client.search.repos("language:python stars:>1000")
        >>> for repo in results.items[:5]:
        ...     print(repo.full_name)
        >>>
        >>> # Clean up (or use context manager)
        >>> client.close()

    Context Manager:
        >>> with GitHubClient(token="ghp_xxx") as client:
        ...     user = client.users.get("octocat")

    """

    __slots__ = (
        "_config",
        "_gists",
        "_http",
        "_issues",
        "_orgs",
        "_pulls",
        "_repos",
        "_search",
        "_users",
    )

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cache_enabled: bool | None = None,
        cache_ttl: int | None = None,
        per_page: int | None = None,
    ) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token. If not provided, uses
                   GITHUB_TOKEN environment variable or anonymous access.
            base_url: GitHub API base URL. Defaults to https://api.github.com.
                      Override for GitHub Enterprise.
            timeout: Request timeout in seconds. Default 30.
            max_retries: Maximum retry attempts. Default 3.
            cache_enabled: Enable response caching. Default True.
            cache_ttl: Cache time-to-live in seconds. Default 300.
            per_page: Default items per page for pagination. Default 30.

        Example:
            >>> # Simple usage
            >>> client = GitHubClient(token="ghp_xxx")
            >>>
            >>> # GitHub Enterprise
            >>> client = GitHubClient(token="ghp_xxx", base_url="https://github.example.com/api/v3")
            >>>
            >>> # Custom settings
            >>> client = GitHubClient(token="ghp_xxx", timeout=60, per_page=100)

        """
        # Build configuration with overrides
        config_kwargs: dict[str, object] = {}
        if token is not None:
            config_kwargs["token"] = token
        if base_url is not None:
            config_kwargs["base_url"] = base_url
        if timeout is not None:
            config_kwargs["timeout"] = timeout
        if max_retries is not None:
            config_kwargs["max_retries"] = max_retries
        if cache_enabled is not None:
            config_kwargs["cache_enabled"] = cache_enabled
        if cache_ttl is not None:
            config_kwargs["cache_ttl"] = cache_ttl
        if per_page is not None:
            config_kwargs["per_page"] = per_page

        self._config = ClientConfig(**config_kwargs)  # type: ignore[arg-type]

        # Create auth strategy
        auth = create_auth(self._config.token)

        # Create HTTP client
        self._http = HTTPClient(self._config, auth)

        # Initialize endpoint groups (lazy would be better for large apps)
        self._users = UsersEndpoint(self._http, self._config)
        self._repos = ReposEndpoint(self._http, self._config)
        self._issues = IssuesEndpoint(self._http, self._config)
        self._pulls = PullsEndpoint(self._http, self._config)
        self._search = SearchEndpoint(self._http, self._config)
        self._gists = GistsEndpoint(self._http, self._config)
        self._orgs = OrgsEndpoint(self._http, self._config)

    # =========================================================================
    # Endpoint Properties
    # =========================================================================

    @property
    def users(self) -> UsersEndpoint:
        """Access user-related API endpoints.

        Returns:
            UsersEndpoint for user operations.

        Example:
            >>> user = client.users.get("octocat")
            >>> followers = client.users.list_followers("octocat")

        """
        return self._users

    @property
    def repos(self) -> ReposEndpoint:
        """Access repository-related API endpoints.

        Returns:
            ReposEndpoint for repository operations.

        Example:
            >>> repo = client.repos.get("microsoft", "vscode")
            >>> commits = client.repos.list_commits("microsoft", "vscode")

        """
        return self._repos

    @property
    def issues(self) -> IssuesEndpoint:
        """Access issue-related API endpoints.

        Returns:
            IssuesEndpoint for issue operations.

        Example:
            >>> issues = client.issues.list_for_repo("python", "cpython")
            >>> issue = client.issues.get("python", "cpython", 12345)

        """
        return self._issues

    @property
    def pulls(self) -> PullsEndpoint:
        """Access pull request-related API endpoints.

        Returns:
            PullsEndpoint for pull request operations.

        Example:
            >>> prs = client.pulls.list_for_repo("python", "cpython")
            >>> pr = client.pulls.get("python", "cpython", 12345)

        """
        return self._pulls

    @property
    def search(self) -> SearchEndpoint:
        """Access search API endpoints.

        Returns:
            SearchEndpoint for search operations.

        Example:
            >>> results = client.search.repos("language:python stars:>1000")
            >>> results = client.search.users("location:Germany")

        """
        return self._search

    @property
    def gists(self) -> GistsEndpoint:
        """Access gist-related API endpoints.

        Returns:
            GistsEndpoint for gist operations.

        Example:
            >>> gists = client.gists.list_for_user("octocat")
            >>> gist = client.gists.get("aa5a315d61ae9438b18d")

        """
        return self._gists

    @property
    def orgs(self) -> OrgsEndpoint:
        """Access organization-related API endpoints.

        Returns:
            OrgsEndpoint for organization operations.

        Example:
            >>> org = client.orgs.get("microsoft")
            >>> repos = client.orgs.list_repos("microsoft")

        """
        return self._orgs

    # =========================================================================
    # Client Properties
    # =========================================================================

    @property
    def config(self) -> ClientConfig:
        """Get the client configuration.

        Returns:
            The immutable ClientConfig instance.

        """
        return self._config

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated.

        Returns:
            True if a token is configured.

        """
        return self._config.is_authenticated

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get the rate limiter instance.

        Use this to check rate limit status or manually wait.

        Returns:
            The RateLimiter tracking GitHub's rate limits.

        Example:
            >>> remaining = client.rate_limiter.get_remaining("core")
            >>> print(f"Requests remaining: {remaining}")

        """
        return self._http.rate_limiter

    @property
    def cache(self) -> ResponseCache | None:
        """Get the response cache instance.

        Returns None if caching is disabled.

        Returns:
            The ResponseCache if enabled, None otherwise.

        Example:
            >>> if client.cache:
            ...     client.cache.clear()  # Clear all cached responses

        """
        return self._http.cache

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def close(self) -> None:
        """Close the client and release resources.

        This should be called when you're done using the client,
        or use the client as a context manager.

        Example:
            >>> client = GitHubClient()
            >>> try:
            ...     user = client.users.get("octocat")
            ... finally:
            ...     client.close()

        """
        self._http.close()

    def __enter__(self) -> GitHubClient:
        """Enter context manager.

        Returns:
            Self for use in with statement.

        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager and close the client."""
        self.close()

    def __repr__(self) -> str:
        """Return a string representation of the client."""
        auth_status = "authenticated" if self.is_authenticated else "anonymous"
        return f"GitHubClient(base_url={self._config.base_url!r}, {auth_status})"
