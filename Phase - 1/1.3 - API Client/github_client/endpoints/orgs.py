"""Organizations endpoint implementation.

This module provides methods for interacting with GitHub's Organizations API:
- Get organization details
- List organization repositories
- List organization members

API Reference: https://docs.github.com/en/rest/orgs

"""

from __future__ import annotations

from typing import Any

from github_client.endpoints.base import BaseEndpoint
from github_client.models import Organization, Repository, SimpleUser


class OrgsEndpoint(BaseEndpoint):
    """Endpoint for organization-related API calls.

    Example:
        >>> org = client.orgs.get("microsoft")
        >>> print(f"{org.name}: {org.public_repos} repos")

    """

    def get(self, org: str) -> Organization:
        """Get an organization.

        Args:
            org: The organization login name.

        Returns:
            Organization object with full details.

        Example:
            >>> org = client.orgs.get("python")
            >>> print(f"{org.name}")
            >>> print(f"Repos: {org.public_repos}")

        """
        response = self._http.get(f"/orgs/{org}")
        return self._parse_response(response.data, Organization)  # type: ignore[arg-type]

    def list_repos(
        self,
        org: str,
        *,
        type_: str = "all",
        sort: str = "created",
        direction: str = "asc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Repository]:
        """List repositories for an organization.

        Args:
            org: The organization login name.
            type_: Type filter ("all", "public", "private", "forks", "sources", "member").
            sort: Sort field ("created", "updated", "pushed", "full_name").
            direction: Sort direction ("asc", "desc").
            page: Page number.
            per_page: Results per page.

        Returns:
            List of Repository objects.

        Example:
            >>> repos = client.orgs.list_repos("microsoft", sort="stars", per_page=10)
            >>> for repo in repos:
            ...     print(f"{repo.name}: {repo.stargazers_count} stars")

        """
        params: dict[str, Any] = {
            "type": type_,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/orgs/{org}/repos", params=params)
        return self._parse_list_response(response.data, Repository)  # type: ignore[arg-type]

    def list_members(
        self,
        org: str,
        *,
        filter_: str = "all",
        role: str = "all",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[SimpleUser]:
        """List public members of an organization.

        Args:
            org: The organization login name.
            filter_: Membership filter ("2fa_disabled", "all").
            role: Role filter ("all", "admin", "member").
            page: Page number.
            per_page: Results per page.

        Returns:
            List of SimpleUser objects (public members only).

        Note:
            This only returns public members. For all members,
            you need organization admin access.

        """
        params: dict[str, Any] = {
            "filter": filter_,
            "role": role,
            **self._build_pagination_params(page, per_page),
        }
        response = self._http.get(f"/orgs/{org}/members", params=params)
        return self._parse_list_response(response.data, SimpleUser)  # type: ignore[arg-type]

    def list_public_members(
        self,
        org: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[SimpleUser]:
        """List public members of an organization.

        Args:
            org: The organization login name.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of SimpleUser objects.

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(f"/orgs/{org}/public_members", params=params)
        return self._parse_list_response(response.data, SimpleUser)  # type: ignore[arg-type]

    def check_membership(self, org: str, username: str) -> bool:
        """Check if a user is a public member of an organization.

        Args:
            org: The organization login name.
            username: The username to check.

        Returns:
            True if the user is a public member.

        """
        try:
            self._http.get(f"/orgs/{org}/public_members/{username}")
            return True
        except Exception:
            return False

    def list_for_user(
        self,
        username: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Organization]:
        """List organizations for a user.

        Args:
            username: The GitHub username.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of Organization objects.

        Example:
            >>> orgs = client.orgs.list_for_user("torvalds")
            >>> for org in orgs:
            ...     print(org.login)

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(f"/users/{username}/orgs", params=params)
        return self._parse_list_response(response.data, Organization)  # type: ignore[arg-type]
