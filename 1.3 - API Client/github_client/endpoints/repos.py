"""Repositories endpoint implementation.

This module provides methods for interacting with GitHub's Repositories API:
- Get repository information
- List repositories for users and organizations
- List commits, contributors, languages
- Repository operations (for authenticated users)

API Reference: https://docs.github.com/en/rest/repos

"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from github_client.endpoints.base import BaseEndpoint
from github_client.exceptions import AuthenticationError
from github_client.models import Commit, Repository

if TYPE_CHECKING:
    from github_client.utils.pagination import PaginatedResponse


class ReposEndpoint(BaseEndpoint):
    """Endpoint for repository-related API calls.

    Example:
        >>> repo = client.repos.get("microsoft", "vscode")
        >>> print(f"{repo.full_name}: {repo.stargazers_count} stars")
        >>>
        >>> repos = client.repos.list_for_user("torvalds")
        >>> for repo in repos:
        ...     print(repo.name)

    """

    def get(self, owner: str, repo: str) -> Repository:
        """Get a repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.

        Returns:
            Repository object with full details.

        Raises:
            NotFoundError: If the repository doesn't exist or is private.
            NetworkError: If the request fails.

        Example:
            >>> repo = client.repos.get("python", "cpython")
            >>> print(f"Language: {repo.language}")
            >>> print(f"Stars: {repo.stargazers_count}")
            >>> print(f"License: {repo.license.name if repo.license else 'None'}")

        """
        response = self._http.get(f"/repos/{owner}/{repo}")
        return self._parse_response(response.data, Repository)  # type: ignore[arg-type]

    def list_for_user(
        self,
        username: str,
        *,
        type_: str = "owner",
        sort: str = "full_name",
        direction: str = "asc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Repository]:
        """List repositories for a user.

        Args:
            username: The GitHub username.
            type_: Type filter ("all", "owner", "member"). Default "owner".
            sort: Sort field ("created", "updated", "pushed", "full_name").
            direction: Sort direction ("asc", "desc").
            page: Page number for pagination.
            per_page: Results per page (max 100).

        Returns:
            List of Repository objects.

        Example:
            >>> repos = client.repos.list_for_user("torvalds", sort="pushed")
            >>> for repo in repos[:5]:
            ...     print(f"{repo.name}: {repo.stargazers_count} stars")

        """
        params: dict[str, Any] = {
            "type": type_,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/users/{username}/repos", params=params)
        return self._parse_list_response(response.data, Repository)  # type: ignore[arg-type]

    def iter_for_user(
        self,
        username: str,
        *,
        type_: str = "owner",
        sort: str = "full_name",
        direction: str = "asc",
        per_page: int = 100,
        max_items: int | None = None,
    ) -> Iterator[Repository]:
        """Iterate through all repositories for a user.

        Memory-efficient iteration that fetches pages as needed.

        Args:
            username: The GitHub username.
            type_: Type filter ("all", "owner", "member").
            sort: Sort field.
            direction: Sort direction.
            per_page: Items per page.
            max_items: Maximum items to yield.

        Yields:
            Repository objects.

        Example:
            >>> for repo in client.repos.iter_for_user("torvalds"):
            ...     print(repo.name)
            ...     if repo.stargazers_count < 100:
            ...         break

        """
        params: dict[str, Any] = {
            "type": type_,
            "sort": sort,
            "direction": direction,
        }
        yield from self._iter_pages(
            f"/users/{username}/repos",
            Repository,
            params=params,
            per_page=per_page,
            max_items=max_items,
        )

    def list_for_user_paginated(
        self,
        username: str,
        *,
        type_: str = "owner",
        sort: str = "full_name",
        direction: str = "asc",
        page: int = 1,
        per_page: int | None = None,
    ) -> PaginatedResponse[Repository]:
        """Get a page of repositories with pagination controls.

        Args:
            username: The GitHub username.
            type_: Type filter.
            sort: Sort field.
            direction: Sort direction.
            page: Page number.
            per_page: Items per page.

        Returns:
            PaginatedResponse with navigation methods.

        Example:
            >>> page = client.repos.list_for_user_paginated("torvalds")
            >>> print(f"Page 1: {len(page.items)} repos")
            >>> if page.has_next:
            ...     page2 = page.fetch_next()

        """
        params: dict[str, Any] = {
            "type": type_,
            "sort": sort,
            "direction": direction,
        }
        return self._get_paginated(
            f"/users/{username}/repos",
            Repository,
            params=params,
            page=page,
            per_page=per_page,
        )

    def list_for_org(
        self,
        org: str,
        *,
        type_: str = "all",
        sort: str = "full_name",
        direction: str = "asc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Repository]:
        """List repositories for an organization.

        Args:
            org: The organization name.
            type_: Type filter ("all", "public", "private", "forks", "sources", "member").
            sort: Sort field ("created", "updated", "pushed", "full_name").
            direction: Sort direction ("asc", "desc").
            page: Page number for pagination.
            per_page: Results per page (max 100).

        Returns:
            List of Repository objects.

        Example:
            >>> repos = client.repos.list_for_org("microsoft", sort="stars")
            >>> print(f"Microsoft has {len(repos)} repos on this page")

        """
        params: dict[str, Any] = {
            "type": type_,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/orgs/{org}/repos", params=params)
        return self._parse_list_response(response.data, Repository)  # type: ignore[arg-type]

    def list_for_authenticated_user(
        self,
        *,
        visibility: str = "all",
        affiliation: str = "owner,collaborator,organization_member",
        type_: str = "all",
        sort: str = "full_name",
        direction: str = "asc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Repository]:
        """List repositories for the authenticated user.

        This includes private repositories the user has access to.

        Args:
            visibility: Visibility filter ("all", "public", "private").
            affiliation: Comma-separated list of affiliations.
            type_: Type filter ("all", "owner", "public", "private", "member").
            sort: Sort field.
            direction: Sort direction.
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of Repository objects including private repos.

        Raises:
            AuthenticationError: If not authenticated.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params: dict[str, Any] = {
            "visibility": visibility,
            "affiliation": affiliation,
            "type": type_,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get("/user/repos", params=params)
        return self._parse_list_response(response.data, Repository)  # type: ignore[arg-type]

    def list_commits(
        self,
        owner: str,
        repo: str,
        *,
        sha: str | None = None,
        path: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Commit]:
        """List commits in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: SHA or branch name to start listing from.
            path: Only commits containing this file path.
            author: GitHub login or email to filter by.
            since: ISO 8601 timestamp for start date.
            until: ISO 8601 timestamp for end date.
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of Commit objects.

        Example:
            >>> commits = client.repos.list_commits("python", "cpython", per_page=10)
            >>> for commit in commits:
            ...     print(f"{commit.sha[:7]}: {commit.commit.message.split()[0]}")

        """
        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        response = self._http.get(f"/repos/{owner}/{repo}/commits", params=params)
        return self._parse_list_response(response.data, Commit)  # type: ignore[arg-type]

    def get_commit(self, owner: str, repo: str, ref: str) -> Commit:
        """Get a specific commit.

        Args:
            owner: Repository owner.
            repo: Repository name.
            ref: Commit SHA, branch name, or tag name.

        Returns:
            Commit object with full details.

        """
        response = self._http.get(f"/repos/{owner}/{repo}/commits/{ref}")
        return self._parse_response(response.data, Commit)  # type: ignore[arg-type]

    def list_contributors(
        self,
        owner: str,
        repo: str,
        *,
        anon: bool = False,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[dict[str, Any]]:
        """List repository contributors.

        Args:
            owner: Repository owner.
            repo: Repository name.
            anon: Include anonymous contributors.
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of contributor objects (User + contribution count).

        """
        params: dict[str, Any] = {
            "anon": str(anon).lower(),
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/repos/{owner}/{repo}/contributors", params=params)
        return response.data  # type: ignore[return-value]

    def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Get repository languages.

        Returns a dictionary of languages and their byte counts.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary mapping language names to byte counts.

        Example:
            >>> languages = client.repos.get_languages("python", "cpython")
            >>> for lang, bytes_ in sorted(languages.items(), key=lambda x: -x[1])[:5]:
            ...     print(f"{lang}: {bytes_:,} bytes")

        """
        response = self._http.get(f"/repos/{owner}/{repo}/languages")
        data = response.data
        if isinstance(data, dict):
            return {k: int(v) for k, v in data.items()}
        return {}

    def list_topics(self, owner: str, repo: str) -> list[str]:
        """Get repository topics.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            List of topic names.

        """
        response = self._http.get(f"/repos/{owner}/{repo}/topics")
        data = response.data
        if isinstance(data, dict):
            names = data.get("names", [])
            return list(names) if names else []
        return []

    def list_forks(
        self,
        owner: str,
        repo: str,
        *,
        sort: str = "newest",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Repository]:
        """List repository forks.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sort: Sort order ("newest", "oldest", "stargazers", "watchers").
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of Repository objects (forks).

        """
        params: dict[str, Any] = {
            "sort": sort,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/repos/{owner}/{repo}/forks", params=params)
        return self._parse_list_response(response.data, Repository)  # type: ignore[arg-type]

    def list_stargazers(
        self,
        owner: str,
        repo: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[dict[str, Any]]:
        """List users who starred a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of user objects.

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(f"/repos/{owner}/{repo}/stargazers", params=params)
        return response.data  # type: ignore[return-value]
