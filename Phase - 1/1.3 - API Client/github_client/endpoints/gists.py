"""Gists endpoint implementation.

This module provides methods for interacting with GitHub's Gists API:
- List gists (public, user, starred)
- Get gist details
- Create, update, and delete gists

API Reference: https://docs.github.com/en/rest/gists

"""

from __future__ import annotations

from typing import Any

from github_client.endpoints.base import BaseEndpoint
from github_client.exceptions import AuthenticationError
from github_client.models import Gist


class GistsEndpoint(BaseEndpoint):
    """Endpoint for gist-related API calls.

    Example:
        >>> gists = client.gists.list_for_user("octocat")
        >>> for gist in gists[:5]:
        ...     print(f"{gist.id}: {gist.description}")

    """

    def get(self, gist_id: str) -> Gist:
        """Get a specific gist.

        Args:
            gist_id: The gist ID.

        Returns:
            Gist object with full details including file contents.

        Example:
            >>> gist = client.gists.get("aa5a315d61ae9438b18d")
            >>> for filename, file in gist.files.items():
            ...     print(f"{filename}: {file.language}")

        """
        response = self._http.get(f"/gists/{gist_id}")
        return self._parse_response(response.data, Gist)  # type: ignore[arg-type]

    def list_for_user(
        self,
        username: str,
        *,
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Gist]:
        """List gists for a user.

        Args:
            username: The GitHub username.
            since: ISO 8601 timestamp for filtering.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of Gist objects.

        """
        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if since:
            params["since"] = since

        response = self._http.get(f"/users/{username}/gists", params=params)
        return self._parse_list_response(response.data, Gist)  # type: ignore[arg-type]

    def list_public(
        self,
        *,
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Gist]:
        """List public gists.

        Args:
            since: ISO 8601 timestamp for filtering.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of public Gist objects.

        """
        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if since:
            params["since"] = since

        response = self._http.get("/gists/public", params=params)
        return self._parse_list_response(response.data, Gist)  # type: ignore[arg-type]

    def list_for_authenticated_user(
        self,
        *,
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Gist]:
        """List gists for the authenticated user.

        Args:
            since: ISO 8601 timestamp for filtering.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of Gist objects.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if since:
            params["since"] = since

        response = self._http.get("/gists", params=params)
        return self._parse_list_response(response.data, Gist)  # type: ignore[arg-type]

    def list_starred(
        self,
        *,
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Gist]:
        """List gists starred by the authenticated user.

        Args:
            since: ISO 8601 timestamp for filtering.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of starred Gist objects.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if since:
            params["since"] = since

        response = self._http.get("/gists/starred", params=params)
        return self._parse_list_response(response.data, Gist)  # type: ignore[arg-type]

    def create(
        self,
        files: dict[str, dict[str, str]],
        *,
        description: str | None = None,
        public: bool = False,
    ) -> Gist:
        """Create a new gist.

        Args:
            files: Dictionary mapping filenames to file objects.
                   Each file object must have a "content" key.
            description: Gist description.
            public: Whether the gist is public.

        Returns:
            The created Gist object.

        Example:
            >>> gist = client.gists.create(
            ...     files={
            ...         "hello.py": {"content": "print('Hello, World!')"},
            ...         "readme.md": {"content": "# My Gist"},
            ...     },
            ...     description="Example gist",
            ...     public=True,
            ... )

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        data: dict[str, Any] = {"files": files, "public": public}
        if description:
            data["description"] = description

        response = self._http.post("/gists", json_data=data)
        return self._parse_response(response.data, Gist)  # type: ignore[arg-type]

    def update(
        self,
        gist_id: str,
        *,
        files: dict[str, dict[str, str] | None] | None = None,
        description: str | None = None,
    ) -> Gist:
        """Update a gist.

        Args:
            gist_id: The gist ID.
            files: Files to update/add/delete. Set value to None to delete a file.
            description: New description.

        Returns:
            The updated Gist object.

        Example:
            >>> # Update a file and delete another
            >>> gist = client.gists.update(
            ...     "aa5a315d61ae9438b18d",
            ...     files={
            ...         "hello.py": {"content": "print('Updated!')"},
            ...         "old_file.txt": None,  # Delete this file
            ...     },
            ... )

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        data: dict[str, Any] = {}
        if files is not None:
            data["files"] = files
        if description is not None:
            data["description"] = description

        response = self._http.patch(f"/gists/{gist_id}", json_data=data)
        return self._parse_response(response.data, Gist)  # type: ignore[arg-type]

    def delete(self, gist_id: str) -> None:
        """Delete a gist.

        Args:
            gist_id: The gist ID to delete.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        self._http.delete(f"/gists/{gist_id}")

    def star(self, gist_id: str) -> None:
        """Star a gist.

        Args:
            gist_id: The gist ID to star.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        self._http.put(f"/gists/{gist_id}/star")

    def unstar(self, gist_id: str) -> None:
        """Unstar a gist.

        Args:
            gist_id: The gist ID to unstar.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        self._http.delete(f"/gists/{gist_id}/star")

    def is_starred(self, gist_id: str) -> bool:
        """Check if a gist is starred.

        Args:
            gist_id: The gist ID to check.

        Returns:
            True if starred, False otherwise.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        try:
            self._http.get(f"/gists/{gist_id}/star")
            return True
        except Exception:
            return False

    def fork(self, gist_id: str) -> Gist:
        """Fork a gist.

        Args:
            gist_id: The gist ID to fork.

        Returns:
            The forked Gist object.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        response = self._http.post(f"/gists/{gist_id}/forks")
        return self._parse_response(response.data, Gist)  # type: ignore[arg-type]
