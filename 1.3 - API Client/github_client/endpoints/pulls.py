"""Pull Requests endpoint implementation.

This module provides methods for interacting with GitHub's Pull Requests API:
- List pull requests for repositories
- Get PR details
- Create, update, and merge PRs
- List PR reviews and comments

API Reference: https://docs.github.com/en/rest/pulls

"""

from __future__ import annotations

from typing import Any

from github_client.endpoints.base import BaseEndpoint
from github_client.exceptions import AuthenticationError
from github_client.models import PullRequest


class PullsEndpoint(BaseEndpoint):
    """Endpoint for pull request-related API calls.

    Example:
        >>> prs = client.pulls.list_for_repo("python", "cpython", state="open")
        >>> for pr in prs[:5]:
        ...     print(f"#{pr.number}: {pr.title}")

    """

    def get(self, owner: str, repo: str, pull_number: int) -> PullRequest:
        """Get a specific pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull request number.

        Returns:
            PullRequest object with full details.

        Example:
            >>> pr = client.pulls.get("python", "cpython", 12345)
            >>> print(f"#{pr.number}: {pr.title}")
            >>> print(f"State: {pr.state}, Merged: {pr.merged}")

        """
        response = self._http.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
        return self._parse_response(response.data, PullRequest)  # type: ignore[arg-type]

    def list_for_repo(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        sort: str = "created",
        direction: str = "desc",
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[PullRequest]:
        """List pull requests for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: State filter ("open", "closed", "all").
            head: Filter by head user/branch (format: "user:branch").
            base: Filter by base branch name.
            sort: Sort field ("created", "updated", "popularity", "long-running").
            direction: Sort direction ("asc", "desc").
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of PullRequest objects.

        Example:
            >>> # Get open PRs targeting main branch
            >>> prs = client.pulls.list_for_repo("owner", "repo", state="open", base="main")

        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        if head:
            params["head"] = head
        if base:
            params["base"] = base

        response = self._http.get(f"/repos/{owner}/{repo}/pulls", params=params)
        return self._parse_list_response(response.data, PullRequest)  # type: ignore[arg-type]

    def create(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        *,
        body: str | None = None,
        maintainer_can_modify: bool = True,
        draft: bool = False,
    ) -> PullRequest:
        r"""Create a new pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: PR title.
            head: The name of the branch with changes (format: "user:branch" for cross-repo).
            base: The branch to merge into.
            body: PR body (Markdown supported).
            maintainer_can_modify: Allow maintainers to push to head branch.
            draft: Create as draft PR.

        Returns:
            The created PullRequest object.

        Example:
            >>> pr = client.pulls.create(
            ...     "owner",
            ...     "repo",
            ...     title="Add new feature",
            ...     head="feature-branch",
            ...     base="main",
            ...     body="## Changes\n\n- Added X\n- Fixed Y",
            ... )

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        data: dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "maintainer_can_modify": maintainer_can_modify,
            "draft": draft,
        }
        if body:
            data["body"] = body

        response = self._http.post(f"/repos/{owner}/{repo}/pulls", json_data=data)
        return self._parse_response(response.data, PullRequest)  # type: ignore[arg-type]

    def update(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        base: str | None = None,
        maintainer_can_modify: bool | None = None,
    ) -> PullRequest:
        """Update a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: PR number to update.
            title: New title.
            body: New body.
            state: New state ("open" or "closed").
            base: New base branch.
            maintainer_can_modify: Update maintainer modify permission.

        Returns:
            The updated PullRequest object.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        data: dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if base is not None:
            data["base"] = base
        if maintainer_can_modify is not None:
            data["maintainer_can_modify"] = maintainer_can_modify

        response = self._http.patch(
            f"/repos/{owner}/{repo}/pulls/{pull_number}",
            json_data=data,
        )
        return self._parse_response(response.data, PullRequest)  # type: ignore[arg-type]

    def list_commits(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[dict[str, Any]]:
        """List commits on a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: PR number.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of commit objects.

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(
            f"/repos/{owner}/{repo}/pulls/{pull_number}/commits",
            params=params,
        )
        return response.data  # type: ignore[return-value]

    def list_files(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[dict[str, Any]]:
        """List files changed in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: PR number.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of file objects with status, additions, deletions.

        Example:
            >>> files = client.pulls.list_files("owner", "repo", 123)
            >>> for f in files:
            ...     print(f"{f['status']}: {f['filename']} (+{f['additions']}/-{f['deletions']})")

        """
        params = self._build_pagination_params(page, per_page)
        response = self._http.get(
            f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
            params=params,
        )
        return response.data  # type: ignore[return-value]

    def check_merged(self, owner: str, repo: str, pull_number: int) -> bool:
        """Check if a pull request has been merged.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: PR number.

        Returns:
            True if merged, False otherwise.

        """
        try:
            self._http.get(f"/repos/{owner}/{repo}/pulls/{pull_number}/merge")
            return True
        except Exception:
            return False

    def merge(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        commit_title: str | None = None,
        commit_message: str | None = None,
        sha: str | None = None,
        merge_method: str = "merge",
    ) -> dict[str, Any]:
        """Merge a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: PR number.
            commit_title: Title for merge commit.
            commit_message: Body for merge commit.
            sha: SHA that head must match (for safety).
            merge_method: Merge method ("merge", "squash", "rebase").

        Returns:
            Merge result with sha and merged status.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        data: dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        if sha:
            data["sha"] = sha

        response = self._http.put(
            f"/repos/{owner}/{repo}/pulls/{pull_number}/merge",
            json_data=data,
        )
        return response.data  # type: ignore[return-value]
