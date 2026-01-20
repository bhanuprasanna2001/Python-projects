"""Search endpoint implementation.

This module provides methods for interacting with GitHub's Search API:
- Search for repositories
- Search for users
- Search for issues and pull requests
- Search for code

API Reference: https://docs.github.com/en/rest/search

Note: Search API has a lower rate limit (30 requests/minute for authenticated users).
"""

from __future__ import annotations

from typing import Any

from github_client.endpoints.base import BaseEndpoint
from github_client.models import (
    Issue,
    IssueSearchResult,
    Repository,
    RepositorySearchResult,
    SimpleUser,
    UserSearchResult,
)


class SearchEndpoint(BaseEndpoint):
    """Endpoint for search-related API calls.

    Example:
        >>> results = client.search.repos("language:python stars:>10000")
        >>> for repo in results.items[:5]:
        ...     print(f"{repo.full_name}: {repo.stargazers_count} stars")

    Note:
        Search queries use GitHub's query syntax:
        https://docs.github.com/en/search-github/searching-on-github

    """

    def repos(
        self,
        query: str,
        *,
        sort: str | None = None,
        order: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> RepositorySearchResult:
        """Search for repositories.

        Args:
            query: Search query using GitHub search syntax.
            sort: Sort field ("stars", "forks", "help-wanted-issues", "updated").
            order: Sort order ("asc", "desc").
            page: Page number.
            per_page: Results per page (max 100).

        Returns:
            RepositorySearchResult with total_count and items.

        Example:
            >>> # Find popular Python web frameworks
            >>> results = client.search.repos("topic:web-framework language:python", sort="stars")
            >>> print(f"Found {results.total_count} repositories")

        """
        params: dict[str, Any] = {
            "q": query,
            "order": order,
            **self._build_pagination_params(page, per_page),
        }
        if sort:
            params["sort"] = sort

        response = self._http.get("/search/repositories", params=params)
        data = response.data
        if isinstance(data, dict):
            return RepositorySearchResult(
                total_count=data.get("total_count", 0),
                incomplete_results=data.get("incomplete_results", False),
                items=[Repository.model_validate(item) for item in data.get("items", [])],
            )
        return RepositorySearchResult(total_count=0, items=[])

    def users(
        self,
        query: str,
        *,
        sort: str | None = None,
        order: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> UserSearchResult:
        """Search for users.

        Args:
            query: Search query using GitHub search syntax.
            sort: Sort field ("followers", "repositories", "joined").
            order: Sort order ("asc", "desc").
            page: Page number.
            per_page: Results per page.

        Returns:
            UserSearchResult with total_count and items.

        Example:
            >>> # Find users in a location
            >>> results = client.search.users("location:Germany language:python")
            >>> print(f"Found {results.total_count} users")

        """
        params: dict[str, Any] = {
            "q": query,
            "order": order,
            **self._build_pagination_params(page, per_page),
        }
        if sort:
            params["sort"] = sort

        response = self._http.get("/search/users", params=params)
        data = response.data
        if isinstance(data, dict):
            return UserSearchResult(
                total_count=data.get("total_count", 0),
                incomplete_results=data.get("incomplete_results", False),
                items=[SimpleUser.model_validate(item) for item in data.get("items", [])],
            )
        return UserSearchResult(total_count=0, items=[])

    def issues(
        self,
        query: str,
        *,
        sort: str | None = None,
        order: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> IssueSearchResult:
        """Search for issues and pull requests.

        Args:
            query: Search query using GitHub search syntax.
            sort: Sort field ("comments", "reactions", "created", "updated").
            order: Sort order ("asc", "desc").
            page: Page number.
            per_page: Results per page.

        Returns:
            IssueSearchResult with total_count and items.

        Example:
            >>> # Find good first issues
            >>> results = client.search.issues('label:"good first issue" language:python is:open')

        """
        params: dict[str, Any] = {
            "q": query,
            "order": order,
            **self._build_pagination_params(page, per_page),
        }
        if sort:
            params["sort"] = sort

        response = self._http.get("/search/issues", params=params)
        data = response.data
        if isinstance(data, dict):
            return IssueSearchResult(
                total_count=data.get("total_count", 0),
                incomplete_results=data.get("incomplete_results", False),
                items=[Issue.model_validate(item) for item in data.get("items", [])],
            )
        return IssueSearchResult(total_count=0, items=[])

    def code(
        self,
        query: str,
        *,
        sort: str | None = None,
        order: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """Search for code.

        Note: Code search requires authentication.

        Args:
            query: Search query. Must include at least one of:
                   - a user/org/repo qualifier
                   - a file path qualifier
            sort: Sort field ("indexed" only).
            order: Sort order ("asc", "desc").
            page: Page number.
            per_page: Results per page.

        Returns:
            Search results with total_count and items.

        Example:
            >>> # Find uses of a function in a repo
            >>> results = client.search.code("def parse_config repo:owner/repo")

        """
        params: dict[str, Any] = {
            "q": query,
            "order": order,
            **self._build_pagination_params(page, per_page),
        }
        if sort:
            params["sort"] = sort

        response = self._http.get("/search/code", params=params)
        return response.data  # type: ignore[return-value]

    def commits(
        self,
        query: str,
        *,
        sort: str | None = None,
        order: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """Search for commits.

        Args:
            query: Search query using GitHub search syntax.
            sort: Sort field ("author-date", "committer-date").
            order: Sort order ("asc", "desc").
            page: Page number.
            per_page: Results per page.

        Returns:
            Search results with total_count and items.

        Example:
            >>> # Find commits by author
            >>> results = client.search.commits("author:torvalds repo:torvalds/linux")

        """
        params: dict[str, Any] = {
            "q": query,
            "order": order,
            **self._build_pagination_params(page, per_page),
        }
        if sort:
            params["sort"] = sort

        response = self._http.get("/search/commits", params=params)
        return response.data  # type: ignore[return-value]

    def topics(
        self,
        query: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """Search for topics.

        Args:
            query: Search query for topic names.
            page: Page number.
            per_page: Results per page.

        Returns:
            Search results with total_count and items.

        """
        params: dict[str, Any] = {
            "q": query,
            **self._build_pagination_params(page, per_page),
        }

        response = self._http.get("/search/topics", params=params)
        return response.data  # type: ignore[return-value]
