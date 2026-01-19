"""Users endpoint implementation.

This module provides methods for interacting with GitHub's Users API:
- Get user profiles
- Get the authenticated user
- List followers and following
- List user's repositories, gists, etc.

API Reference: https://docs.github.com/en/rest/users

"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from github_client.endpoints.base import BaseEndpoint
from github_client.exceptions import AuthenticationError
from github_client.models import AuthenticatedUser, User

if TYPE_CHECKING:
    pass


class UsersEndpoint(BaseEndpoint):
    """Endpoint for user-related API calls.

    Example:
        >>> client = GitHubClient(token="ghp_xxx")
        >>> user = client.users.get("octocat")
        >>> print(user.login, user.public_repos)
        >>>
        >>> me = client.users.get_authenticated()
        >>> print(me.private_repos)

    """

    def get(self, username: str) -> User:
        """Get a user's public profile.

        Fetches publicly available information about a GitHub user.
        This works without authentication but has lower rate limits.

        Args:
            username: The GitHub username (login).

        Returns:
            User object with public profile information.

        Raises:
            NotFoundError: If the user doesn't exist.
            NetworkError: If the request fails.

        Example:
            >>> user = client.users.get("octocat")
            >>> print(f"{user.name} has {user.public_repos} public repos")

        """
        response = self._http.get(f"/users/{username}")
        return self._parse_response(response.data, User)  # type: ignore[arg-type]

    def get_authenticated(self) -> AuthenticatedUser:
        """Get the authenticated user's profile.

        Returns the full profile of the authenticated user, including
        private information like private repo count and 2FA status.

        Returns:
            AuthenticatedUser with full profile data.

        Raises:
            AuthenticationError: If not authenticated or token is invalid.
            NetworkError: If the request fails.

        Example:
            >>> me = client.users.get_authenticated()
            >>> print(f"Total repos: {me.public_repos + me.total_private_repos}")
            >>> print(f"2FA enabled: {me.two_factor_authentication}")

        """
        if not self._config.is_authenticated:
            raise AuthenticationError(
                "Authentication required. Provide a token to use this method."
            )

        response = self._http.get("/user")
        return self._parse_response(response.data, AuthenticatedUser)  # type: ignore[arg-type]

    def list_followers(
        self,
        username: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[User]:
        """List a user's followers.

        Args:
            username: The GitHub username.
            page: Page number for pagination (1-indexed).
            per_page: Number of results per page (max 100).

        Returns:
            List of User objects representing followers.

        Raises:
            NotFoundError: If the user doesn't exist.
            NetworkError: If the request fails.

        Example:
            >>> followers = client.users.list_followers("octocat")
            >>> for follower in followers:
            ...     print(follower.login)

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(f"/users/{username}/followers", params=params)
        return self._parse_list_response(response.data, User)  # type: ignore[arg-type]

    def iter_followers(
        self,
        username: str,
        *,
        per_page: int = 100,
        max_items: int | None = None,
    ) -> Iterator[User]:
        """Iterate through all followers of a user.

        Memory-efficient iteration that fetches pages as needed.

        Args:
            username: The GitHub username.
            per_page: Items per page.
            max_items: Maximum items to yield.

        Yields:
            User objects.

        Example:
            >>> for follower in client.users.iter_followers("octocat"):
            ...     print(follower.login)

        """
        yield from self._iter_pages(
            f"/users/{username}/followers",
            User,
            per_page=per_page,
            max_items=max_items,
        )

    def list_following(
        self,
        username: str,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[User]:
        """List users that a user is following.

        Args:
            username: The GitHub username.
            page: Page number for pagination (1-indexed).
            per_page: Number of results per page (max 100).

        Returns:
            List of User objects the user is following.

        Raises:
            NotFoundError: If the user doesn't exist.
            NetworkError: If the request fails.

        Example:
            >>> following = client.users.list_following("octocat")
            >>> print(f"Following {len(following)} users")

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(f"/users/{username}/following", params=params)
        return self._parse_list_response(response.data, User)  # type: ignore[arg-type]

    def check_following(self, username: str, target_user: str) -> bool:
        """Check if a user follows another user.

        Args:
            username: The user to check.
            target_user: The user who might be followed.

        Returns:
            True if username follows target_user.

        Example:
            >>> if client.users.check_following("user1", "user2"):
            ...     print("user1 follows user2")

        """
        try:
            self._http.get(f"/users/{username}/following/{target_user}")
            return True
        except Exception:
            return False

    def list_authenticated_followers(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[User]:
        """List followers of the authenticated user.

        Args:
            page: Page number for pagination (1-indexed).
            per_page: Number of results per page (max 100).

        Returns:
            List of User objects representing followers.

        Raises:
            AuthenticationError: If not authenticated.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params = self._build_pagination_params(page, per_page)
        response = self._http.get("/user/followers", params=params)
        return self._parse_list_response(response.data, User)  # type: ignore[arg-type]

    def list_authenticated_following(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[User]:
        """List users the authenticated user is following.

        Args:
            page: Page number for pagination (1-indexed).
            per_page: Number of results per page (max 100).

        Returns:
            List of User objects being followed.

        Raises:
            AuthenticationError: If not authenticated.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params = self._build_pagination_params(page, per_page)
        response = self._http.get("/user/following", params=params)
        return self._parse_list_response(response.data, User)  # type: ignore[arg-type]

    def follow(self, username: str) -> None:
        """Follow a user.

        Args:
            username: The user to follow.

        Raises:
            AuthenticationError: If not authenticated.
            NotFoundError: If the user doesn't exist.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        self._http.put(f"/user/following/{username}")

    def unfollow(self, username: str) -> None:
        """Unfollow a user.

        Args:
            username: The user to unfollow.

        Raises:
            AuthenticationError: If not authenticated.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        self._http.delete(f"/user/following/{username}")

    def get_by_id(self, user_id: int) -> User:
        """Get a user by their numeric ID.

        Args:
            user_id: The user's numeric ID.

        Returns:
            User object.

        Example:
            >>> user = client.users.get_by_id(583231)  # octocat's ID
            >>> print(user.login)  # "octocat"

        """
        response = self._http.get(f"/user/{user_id}")
        return self._parse_response(response.data, User)  # type: ignore[arg-type]
