"""Issues endpoint implementation.

This module provides methods for interacting with GitHub's Issues API:
- List issues for repositories
- Get issue details
- Create, update, and close issues
- Manage issue comments

API Reference: https://docs.github.com/en/rest/issues

"""

from __future__ import annotations

from typing import Any

from github_client.endpoints.base import BaseEndpoint
from github_client.exceptions import AuthenticationError
from github_client.models import Issue, IssueComment


class IssuesEndpoint(BaseEndpoint):
    """Endpoint for issue-related API calls.

    Example:
        >>> issues = client.issues.list_for_repo("python", "cpython", state="open")
        >>> for issue in issues[:5]:
        ...     print(f"#{issue.number}: {issue.title}")

    """

    def get(self, owner: str, repo: str, issue_number: int) -> Issue:
        """Get a specific issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Issue object with full details.

        Raises:
            NotFoundError: If the issue doesn't exist.

        Example:
            >>> issue = client.issues.get("python", "cpython", 12345)
            >>> print(f"#{issue.number}: {issue.title}")
            >>> print(f"State: {issue.state}")
            >>> print(f"Comments: {issue.comments}")

        """
        response = self._http.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
        return self._parse_response(response.data, Issue)  # type: ignore[arg-type]

    def list_for_repo(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        labels: str | None = None,
        sort: str = "created",
        direction: str = "desc",
        since: str | None = None,
        assignee: str | None = None,
        creator: str | None = None,
        mentioned: str | None = None,
        milestone: str | int | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Issue]:
        """List issues for a repository.

        Note: This may include pull requests (they are also issues).
        Check issue.is_pull_request to filter them out.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: State filter ("open", "closed", "all").
            labels: Comma-separated list of label names.
            sort: Sort field ("created", "updated", "comments").
            direction: Sort direction ("asc", "desc").
            since: ISO 8601 timestamp for filtering.
            assignee: Filter by assignee username, or "none"/"*".
            creator: Filter by creator username.
            mentioned: Filter by mentioned username.
            milestone: Milestone number, or "none"/"*".
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of Issue objects.

        Example:
            >>> # Get open bugs
            >>> bugs = client.issues.list_for_repo(
            ...     "python", "cpython", state="open", labels="type-bug"
            ... )

        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        if labels:
            params["labels"] = labels
        if since:
            params["since"] = since
        if assignee:
            params["assignee"] = assignee
        if creator:
            params["creator"] = creator
        if mentioned:
            params["mentioned"] = mentioned
        if milestone is not None:
            params["milestone"] = str(milestone)

        response = self._http.get(f"/repos/{owner}/{repo}/issues", params=params)
        return self._parse_list_response(response.data, Issue)  # type: ignore[arg-type]

    def create(
        self,
        owner: str,
        repo: str,
        title: str,
        *,
        body: str | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        r"""Create a new issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body (Markdown supported).
            assignees: List of usernames to assign.
            milestone: Milestone number to associate.
            labels: List of label names.

        Returns:
            The created Issue object.

        Raises:
            AuthenticationError: If not authenticated.
            AuthorizationError: If lacking write access.
            ValidationError: If the request is invalid.

        Example:
            >>> issue = client.issues.create(
            ...     "owner",
            ...     "repo",
            ...     title="Bug: Something is broken",
            ...     body="## Description\n\nDetails here...",
            ...     labels=["bug", "needs-triage"],
            ... )
            >>> print(f"Created issue #{issue.number}")

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required to create issues")

        data: dict[str, Any] = {"title": title}
        if body:
            data["body"] = body
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone
        if labels:
            data["labels"] = labels

        response = self._http.post(f"/repos/{owner}/{repo}/issues", json_data=data)
        return self._parse_response(response.data, Issue)  # type: ignore[arg-type]

    def update(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        *,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        """Update an existing issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number to update.
            title: New title (optional).
            body: New body (optional).
            state: New state ("open" or "closed").
            assignees: New list of assignees (replaces existing).
            milestone: New milestone number.
            labels: New list of labels (replaces existing).

        Returns:
            The updated Issue object.

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
        if assignees is not None:
            data["assignees"] = assignees
        if milestone is not None:
            data["milestone"] = milestone
        if labels is not None:
            data["labels"] = labels

        response = self._http.patch(
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json_data=data,
        )
        return self._parse_response(response.data, Issue)  # type: ignore[arg-type]

    def close(self, owner: str, repo: str, issue_number: int) -> Issue:
        """Close an issue.

        Convenience method for update(state="closed").

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number to close.

        Returns:
            The closed Issue object.

        """
        return self.update(owner, repo, issue_number, state="closed")

    def reopen(self, owner: str, repo: str, issue_number: int) -> Issue:
        """Reopen a closed issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number to reopen.

        Returns:
            The reopened Issue object.

        """
        return self.update(owner, repo, issue_number, state="open")

    def list_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        *,
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[IssueComment]:
        """List comments on an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            since: ISO 8601 timestamp for filtering.
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of IssueComment objects.

        """
        params: dict[str, Any] = self._build_pagination_params(page, per_page)
        if since:
            params["since"] = since

        response = self._http.get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            params=params,
        )
        return self._parse_list_response(response.data, IssueComment)  # type: ignore[arg-type]

    def create_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> IssueComment:
        """Create a comment on an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            body: Comment body (Markdown supported).

        Returns:
            The created IssueComment object.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        response = self._http.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json_data={"body": body},
        )
        return self._parse_response(response.data, IssueComment)  # type: ignore[arg-type]

    def list_for_authenticated_user(
        self,
        *,
        filter_: str = "assigned",
        state: str = "open",
        labels: str | None = None,
        sort: str = "created",
        direction: str = "desc",
        since: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[Issue]:
        """List issues assigned to the authenticated user.

        Args:
            filter_: Filter type ("assigned", "created", "mentioned", "subscribed", "all").
            state: State filter ("open", "closed", "all").
            labels: Comma-separated label names.
            sort: Sort field.
            direction: Sort direction.
            since: ISO 8601 timestamp.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of Issue objects.

        """
        if not self._config.is_authenticated:
            raise AuthenticationError("Authentication required")

        params: dict[str, Any] = {
            "filter": filter_,
            "state": state,
            "sort": sort,
            "direction": direction,
            **self._build_pagination_params(page, per_page),
        }
        if labels:
            params["labels"] = labels
        if since:
            params["since"] = since

        response = self._http.get("/issues", params=params)
        return self._parse_list_response(response.data, Issue)  # type: ignore[arg-type]
