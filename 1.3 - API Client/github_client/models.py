"""Pydantic models for GitHub API responses.

This module contains typed data models for all GitHub API responses.
Using Pydantic provides:
- Automatic JSON parsing and validation
- Type coercion (strings to dates, etc.)
- IDE autocomplete for all fields
- Optional field handling

Models are designed to match GitHub's API response format while
providing a clean, Pythonic interface.

Example:
    >>> from github_client.models import User
    >>> user = User.model_validate(api_response)
    >>> print(user.login, user.created_at)

"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class GitHubModel(BaseModel):
    """Base model for all GitHub API responses.

    Provides common configuration for all models:
    - Allows extra fields (GitHub may add new fields)
    - Validates on assignment
    - Uses enum values directly

    """

    model_config = ConfigDict(
        extra="ignore",  # Ignore unknown fields from API
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,  # Allow both alias and field name
    )


# =============================================================================
# User Models
# =============================================================================


class User(GitHubModel):
    """GitHub user (public profile).

    This model represents the public profile of a GitHub user.
    For the authenticated user's private data, see AuthenticatedUser.

    Attributes:
        id: Unique identifier for the user.
        login: Username (handle).
        node_id: GraphQL node ID.
        avatar_url: URL to user's avatar image.
        url: API URL for this user.
        html_url: Web URL to user's profile.
        type: Account type ("User" or "Organization").
        site_admin: Whether user is a GitHub staff member.
        name: Display name (may be None).
        company: Company affiliation.
        blog: Personal website URL.
        location: Geographic location.
        email: Public email (may be None).
        bio: User's bio/description.
        twitter_username: Twitter handle.
        public_repos: Number of public repositories.
        public_gists: Number of public gists.
        followers: Number of followers.
        following: Number of users being followed.
        created_at: Account creation timestamp.
        updated_at: Last profile update timestamp.

    Example:
        >>> user = client.users.get("octocat")
        >>> print(f"{user.name} (@{user.login})")
        >>> print(f"Repos: {user.public_repos}, Followers: {user.followers}")

    """

    # Required fields (always present)
    id: int
    login: str
    node_id: str
    avatar_url: str
    url: str
    html_url: str
    type: str

    # URLs for related resources
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    repos_url: str
    events_url: str
    received_events_url: str

    # Optional public profile fields
    site_admin: bool = False
    name: str | None = None
    company: str | None = None
    blog: str | None = None
    location: str | None = None
    email: str | None = None
    hireable: bool | None = None
    bio: str | None = None
    twitter_username: str | None = None

    # Statistics (only present in full user response)
    public_repos: int | None = None
    public_gists: int | None = None
    followers: int | None = None
    following: int | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"User({self.login})"


class AuthenticatedUser(User):
    """Authenticated user with private data.

    This model extends User with fields only available when
    viewing your own profile with an authenticated request.

    Additional Attributes:
        total_private_repos: Number of private repositories.
        owned_private_repos: Number of owned private repos.
        private_gists: Number of private gists.
        disk_usage: Disk usage in kilobytes.
        collaborators: Number of collaborators.
        two_factor_authentication: Whether 2FA is enabled.
        plan: GitHub plan details.

    """

    # Private statistics
    total_private_repos: int | None = None
    owned_private_repos: int | None = None
    private_gists: int | None = None
    disk_usage: int | None = None
    collaborators: int | None = None

    # Security
    two_factor_authentication: bool | None = None

    # Plan information
    plan: dict[str, Any] | None = None


class SimpleUser(GitHubModel):
    """Minimal user representation (used in lists/references).

    This is a lightweight user model used when users appear as
    part of other resources (e.g., repository owner, issue author).

    """

    id: int
    login: str
    node_id: str
    avatar_url: str
    url: str
    html_url: str
    type: str
    site_admin: bool = False


# =============================================================================
# Repository Models
# =============================================================================


class License(GitHubModel):
    """Repository license information."""

    key: str
    name: str
    spdx_id: str | None = None
    url: str | None = None
    node_id: str | None = None


class Repository(GitHubModel):
    """GitHub repository.

    Attributes:
        id: Unique identifier.
        name: Repository name (without owner).
        full_name: Full name including owner (e.g., "owner/repo").
        owner: Repository owner.
        private: Whether the repository is private.
        description: Repository description.
        fork: Whether this is a fork.
        language: Primary programming language.
        stargazers_count: Number of stars.
        watchers_count: Number of watchers.
        forks_count: Number of forks.
        open_issues_count: Number of open issues.
        default_branch: Default branch name.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        pushed_at: Last push timestamp.

    """

    # Identifiers
    id: int
    node_id: str
    name: str
    full_name: str

    # Owner
    owner: SimpleUser

    # Basic info
    private: bool
    html_url: str
    description: str | None = None
    fork: bool
    url: str

    # URLs for related resources
    forks_url: str
    keys_url: str
    collaborators_url: str
    teams_url: str
    hooks_url: str
    issue_events_url: str
    events_url: str
    assignees_url: str
    branches_url: str
    tags_url: str
    blobs_url: str
    git_tags_url: str
    git_refs_url: str
    trees_url: str
    statuses_url: str
    languages_url: str
    stargazers_url: str
    contributors_url: str
    subscribers_url: str
    subscription_url: str
    commits_url: str
    git_commits_url: str
    comments_url: str
    issue_comment_url: str
    contents_url: str
    compare_url: str
    merges_url: str
    archive_url: str
    downloads_url: str
    issues_url: str
    pulls_url: str
    milestones_url: str
    notifications_url: str
    labels_url: str
    releases_url: str
    deployments_url: str

    # Repository metadata
    homepage: str | None = None
    language: str | None = None
    forks_count: int = 0
    stargazers_count: int = 0
    watchers_count: int = 0
    size: int = 0
    default_branch: str = "main"
    open_issues_count: int = 0

    # Flags
    has_issues: bool = True
    has_projects: bool = True
    has_wiki: bool = True
    has_pages: bool = False
    has_downloads: bool = True
    has_discussions: bool = False
    archived: bool = False
    disabled: bool = False
    is_template: bool = False
    allow_forking: bool = True
    visibility: str = "public"

    # License
    license: License | None = None

    # Topics
    topics: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None

    # Permissions (only present for authenticated user's repos)
    permissions: dict[str, bool] | None = None

    # Statistics for detailed view
    forks: int | None = None
    open_issues: int | None = None
    watchers: int | None = None
    network_count: int | None = None
    subscribers_count: int | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"Repository({self.full_name})"

    @property
    def stars(self) -> int:
        """Alias for stargazers_count."""
        return self.stargazers_count


# =============================================================================
# Issue Models
# =============================================================================


class Label(GitHubModel):
    """Issue/PR label."""

    id: int
    node_id: str
    url: str
    name: str
    color: str
    default: bool = False
    description: str | None = None


class Milestone(GitHubModel):
    """Issue/PR milestone."""

    id: int
    node_id: str
    number: int
    title: str
    description: str | None = None
    url: str
    html_url: str
    labels_url: str
    state: str = "open"
    creator: SimpleUser | None = None
    open_issues: int = 0
    closed_issues: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    due_on: datetime | None = None
    closed_at: datetime | None = None


class Issue(GitHubModel):
    """GitHub issue.

    Note: Pull requests are also issues, but have additional fields.
    Check the pull_request field to distinguish.

    Attributes:
        id: Unique identifier.
        number: Issue number within the repository.
        title: Issue title.
        body: Issue body/description.
        state: Current state ("open" or "closed").
        user: User who created the issue.
        labels: List of labels.
        assignees: List of assigned users.
        milestone: Associated milestone.
        comments: Number of comments.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        closed_at: When the issue was closed (if closed).

    """

    id: int
    node_id: str
    url: str
    repository_url: str
    labels_url: str
    comments_url: str
    events_url: str
    html_url: str
    number: int
    state: str
    title: str
    body: str | None = None
    user: SimpleUser | None = None

    # Labels and assignees
    labels: list[Label] = Field(default_factory=list)
    assignee: SimpleUser | None = None
    assignees: list[SimpleUser] = Field(default_factory=list)

    # Milestone
    milestone: Milestone | None = None

    # Metadata
    locked: bool = False
    active_lock_reason: str | None = None
    comments: int = 0
    pull_request: dict[str, str | None] | None = None  # Present if this is a PR
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author_association: str | None = None

    # Reactions
    reactions: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"Issue(#{self.number}: {self.title})"

    @property
    def is_pull_request(self) -> bool:
        """Check if this issue is actually a pull request."""
        return self.pull_request is not None


class IssueComment(GitHubModel):
    """Comment on an issue."""

    id: int
    node_id: str
    url: str
    html_url: str
    body: str
    user: SimpleUser | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author_association: str | None = None
    reactions: dict[str, Any] | None = None


# =============================================================================
# Pull Request Models
# =============================================================================


class PullRequest(GitHubModel):
    """GitHub pull request.

    Attributes:
        id: Unique identifier.
        number: PR number within the repository.
        title: PR title.
        body: PR body/description.
        state: Current state ("open", "closed", "merged").
        user: User who created the PR.
        head: Source branch information.
        base: Target branch information.
        merged: Whether the PR has been merged.
        mergeable: Whether the PR can be merged.
        comments: Number of review comments.
        commits: Number of commits.
        additions: Lines added.
        deletions: Lines deleted.
        changed_files: Number of files changed.

    """

    id: int
    node_id: str
    url: str
    html_url: str
    diff_url: str
    patch_url: str
    issue_url: str
    number: int
    state: str
    locked: bool = False
    title: str
    body: str | None = None
    user: SimpleUser | None = None

    # Labels and assignees
    labels: list[Label] = Field(default_factory=list)
    assignee: SimpleUser | None = None
    assignees: list[SimpleUser] = Field(default_factory=list)

    # Milestone
    milestone: Milestone | None = None

    # Branch info
    head: dict[str, Any]
    base: dict[str, Any]

    # Merge info
    merged: bool = False
    mergeable: bool | None = None
    rebaseable: bool | None = None
    mergeable_state: str | None = None
    merged_by: SimpleUser | None = None
    merge_commit_sha: str | None = None

    # Statistics
    comments: int = 0
    review_comments: int = 0
    maintainer_can_modify: bool = False
    commits: int | None = None
    additions: int | None = None
    deletions: int | None = None
    changed_files: int | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    merged_at: datetime | None = None

    # Flags
    draft: bool = False
    author_association: str | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"PullRequest(#{self.number}: {self.title})"


# =============================================================================
# Search Models
# =============================================================================


class SearchResult(GitHubModel):
    """Generic search result container.

    Attributes:
        total_count: Total number of matching items.
        incomplete_results: Whether results are incomplete (timeout).
        items: List of matching items.

    """

    total_count: int
    incomplete_results: bool = False
    items: list[Any] = Field(default_factory=list)


class UserSearchResult(SearchResult):
    """Search result for users."""

    items: list[SimpleUser] = Field(default_factory=list)


class RepositorySearchResult(SearchResult):
    """Search result for repositories."""

    items: list[Repository] = Field(default_factory=list)


class IssueSearchResult(SearchResult):
    """Search result for issues and pull requests."""

    items: list[Issue] = Field(default_factory=list)


# =============================================================================
# Gist Models
# =============================================================================


class GistFile(GitHubModel):
    """File within a gist."""

    filename: str
    type: str
    language: str | None = None
    raw_url: str
    size: int
    truncated: bool = False
    content: str | None = None


class Gist(GitHubModel):
    """GitHub gist.

    Attributes:
        id: Unique identifier.
        description: Gist description.
        public: Whether the gist is public.
        files: Dictionary of files in the gist.
        comments: Number of comments.
        owner: User who created the gist.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.

    """

    id: str
    node_id: str
    url: str
    html_url: str
    git_pull_url: str
    git_push_url: str
    commits_url: str
    forks_url: str

    # Content
    files: dict[str, GistFile]
    public: bool
    description: str | None = None

    # Metadata
    comments: int = 0
    owner: SimpleUser | None = None
    truncated: bool = False

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        desc = self.description or "(no description)"
        return f"Gist({self.id}: {desc[:30]})"


# =============================================================================
# Organization Models
# =============================================================================


class Organization(GitHubModel):
    """GitHub organization.

    Attributes:
        id: Unique identifier.
        login: Organization username.
        name: Display name.
        description: Organization description.
        public_repos: Number of public repositories.
        public_members: Number of public members.
        followers: Number of followers.

    """

    id: int
    login: str
    node_id: str
    url: str
    html_url: str
    avatar_url: str
    description: str | None = None
    name: str | None = None
    company: str | None = None
    blog: str | None = None
    location: str | None = None
    email: str | None = None
    twitter_username: str | None = None
    is_verified: bool = False
    has_organization_projects: bool = True
    has_repository_projects: bool = True
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    type: str = "Organization"

    # URLs
    repos_url: str | None = None
    events_url: str | None = None
    hooks_url: str | None = None
    issues_url: str | None = None
    members_url: str | None = None
    public_members_url: str | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"Organization({self.login})"


# =============================================================================
# Commit Models
# =============================================================================


class CommitUser(GitHubModel):
    """Git commit author/committer info."""

    name: str
    email: str
    date: datetime | None = None


class CommitData(GitHubModel):
    """Git commit data (author, message, tree)."""

    author: CommitUser
    committer: CommitUser
    message: str
    tree: dict[str, str]
    url: str
    comment_count: int = 0
    verification: dict[str, Any] | None = None


class Commit(GitHubModel):
    """GitHub commit.

    Attributes:
        sha: Commit SHA hash.
        commit: Git commit data.
        author: GitHub user who authored (may differ from git author).
        committer: GitHub user who committed.
        parents: List of parent commits.

    """

    sha: str
    node_id: str
    url: str
    html_url: str
    comments_url: str
    commit: CommitData
    author: SimpleUser | None = None
    committer: SimpleUser | None = None
    parents: list[dict[str, str]] = Field(default_factory=list)

    # Statistics (only in detailed view)
    stats: Annotated[dict[str, int] | None, Field(default=None)]
    files: Annotated[list[dict[str, Any]] | None, Field(default=None)]

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        short_sha = self.sha[:7]
        message = self.commit.message.split("\n")[0][:50]
        return f"Commit({short_sha}: {message})"
