"""Test configuration and shared fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from github_client import ClientConfig

# =============================================================================
# Sample API Responses
# =============================================================================


@pytest.fixture
def sample_user_response() -> dict[str, Any]:
    """Sample GitHub user API response."""
    return {
        "login": "octocat",
        "id": 1,
        "node_id": "MDQ6VXNlcjE=",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
        "gravatar_id": "",
        "url": "https://api.github.com/users/octocat",
        "html_url": "https://github.com/octocat",
        "followers_url": "https://api.github.com/users/octocat/followers",
        "following_url": "https://api.github.com/users/octocat/following{/other_user}",
        "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
        "organizations_url": "https://api.github.com/users/octocat/orgs",
        "repos_url": "https://api.github.com/users/octocat/repos",
        "events_url": "https://api.github.com/users/octocat/events{/privacy}",
        "received_events_url": "https://api.github.com/users/octocat/received_events",
        "type": "User",
        "site_admin": False,
        "name": "The Octocat",
        "company": "@github",
        "blog": "https://github.blog",
        "location": "San Francisco",
        "email": "octocat@github.com",
        "hireable": None,
        "bio": "There once was...",
        "twitter_username": "monatheoctocat",
        "public_repos": 8,
        "public_gists": 8,
        "followers": 20,
        "following": 0,
        "created_at": "2008-01-14T04:33:35Z",
        "updated_at": "2008-01-14T04:33:35Z",
    }


@pytest.fixture
def sample_repo_response() -> dict[str, Any]:
    """Sample GitHub repository API response."""
    return {
        "id": 1296269,
        "node_id": "MDEwOlJlcG9zaXRvcnkxMjk2MjY5",
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "private": False,
        "owner": {
            "login": "octocat",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "url": "https://api.github.com/users/octocat",
            "html_url": "https://github.com/octocat",
            "type": "User",
            "site_admin": False,
            "followers_url": "https://api.github.com/users/octocat/followers",
            "following_url": "https://api.github.com/users/octocat/following{/other_user}",
            "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
            "repos_url": "https://api.github.com/users/octocat/repos",
            "events_url": "https://api.github.com/users/octocat/events{/privacy}",
            "received_events_url": "https://api.github.com/users/octocat/received_events",
        },
        "html_url": "https://github.com/octocat/Hello-World",
        "description": "This your first repo!",
        "fork": False,
        "url": "https://api.github.com/repos/octocat/Hello-World",
        "forks_url": "https://api.github.com/repos/octocat/Hello-World/forks",
        "keys_url": "https://api.github.com/repos/octocat/Hello-World/keys{/key_id}",
        "collaborators_url": "https://api.github.com/repos/octocat/Hello-World/collaborators{/collaborator}",
        "teams_url": "https://api.github.com/repos/octocat/Hello-World/teams",
        "hooks_url": "https://api.github.com/repos/octocat/Hello-World/hooks",
        "issue_events_url": "https://api.github.com/repos/octocat/Hello-World/issues/events{/number}",
        "events_url": "https://api.github.com/repos/octocat/Hello-World/events",
        "assignees_url": "https://api.github.com/repos/octocat/Hello-World/assignees{/user}",
        "branches_url": "https://api.github.com/repos/octocat/Hello-World/branches{/branch}",
        "tags_url": "https://api.github.com/repos/octocat/Hello-World/tags",
        "blobs_url": "https://api.github.com/repos/octocat/Hello-World/git/blobs{/sha}",
        "git_tags_url": "https://api.github.com/repos/octocat/Hello-World/git/tags{/sha}",
        "git_refs_url": "https://api.github.com/repos/octocat/Hello-World/git/refs{/sha}",
        "trees_url": "https://api.github.com/repos/octocat/Hello-World/git/trees{/sha}",
        "statuses_url": "https://api.github.com/repos/octocat/Hello-World/statuses/{sha}",
        "languages_url": "https://api.github.com/repos/octocat/Hello-World/languages",
        "stargazers_url": "https://api.github.com/repos/octocat/Hello-World/stargazers",
        "contributors_url": "https://api.github.com/repos/octocat/Hello-World/contributors",
        "subscribers_url": "https://api.github.com/repos/octocat/Hello-World/subscribers",
        "subscription_url": "https://api.github.com/repos/octocat/Hello-World/subscription",
        "commits_url": "https://api.github.com/repos/octocat/Hello-World/commits{/sha}",
        "git_commits_url": "https://api.github.com/repos/octocat/Hello-World/git/commits{/sha}",
        "comments_url": "https://api.github.com/repos/octocat/Hello-World/comments{/number}",
        "issue_comment_url": "https://api.github.com/repos/octocat/Hello-World/issues/comments{/number}",
        "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/{+path}",
        "compare_url": "https://api.github.com/repos/octocat/Hello-World/compare/{base}...{head}",
        "merges_url": "https://api.github.com/repos/octocat/Hello-World/merges",
        "archive_url": "https://api.github.com/repos/octocat/Hello-World/{archive_format}{/ref}",
        "downloads_url": "https://api.github.com/repos/octocat/Hello-World/downloads",
        "issues_url": "https://api.github.com/repos/octocat/Hello-World/issues{/number}",
        "pulls_url": "https://api.github.com/repos/octocat/Hello-World/pulls{/number}",
        "milestones_url": "https://api.github.com/repos/octocat/Hello-World/milestones{/number}",
        "notifications_url": "https://api.github.com/repos/octocat/Hello-World/notifications{?since,all,participating}",
        "labels_url": "https://api.github.com/repos/octocat/Hello-World/labels{/name}",
        "releases_url": "https://api.github.com/repos/octocat/Hello-World/releases{/id}",
        "deployments_url": "https://api.github.com/repos/octocat/Hello-World/deployments",
        "created_at": "2011-01-26T19:01:12Z",
        "updated_at": "2022-06-10T12:42:47Z",
        "pushed_at": "2022-06-10T12:41:42Z",
        "homepage": "https://github.com",
        "size": 1,
        "stargazers_count": 80000,
        "watchers_count": 80000,
        "language": "Python",
        "has_issues": True,
        "has_projects": True,
        "has_downloads": True,
        "has_wiki": True,
        "has_pages": False,
        "forks_count": 9000,
        "archived": False,
        "disabled": False,
        "open_issues_count": 0,
        "license": {
            "key": "mit",
            "name": "MIT License",
            "spdx_id": "MIT",
            "url": "https://api.github.com/licenses/mit",
            "node_id": "MDc6TGljZW5zZTEz",
        },
        "topics": ["octocat", "api", "example"],
        "visibility": "public",
        "forks": 9000,
        "open_issues": 0,
        "watchers": 80000,
        "default_branch": "main",
    }


@pytest.fixture
def sample_issue_response() -> dict[str, Any]:
    """Sample GitHub issue API response."""
    return {
        "id": 1,
        "node_id": "MDU6SXNzdWUx",
        "url": "https://api.github.com/repos/octocat/Hello-World/issues/1347",
        "repository_url": "https://api.github.com/repos/octocat/Hello-World",
        "labels_url": "https://api.github.com/repos/octocat/Hello-World/issues/1347/labels{/name}",
        "comments_url": "https://api.github.com/repos/octocat/Hello-World/issues/1347/comments",
        "events_url": "https://api.github.com/repos/octocat/Hello-World/issues/1347/events",
        "html_url": "https://github.com/octocat/Hello-World/issues/1347",
        "number": 1347,
        "state": "open",
        "title": "Found a bug",
        "body": "I'm having a problem with this.",
        "user": {
            "login": "octocat",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "url": "https://api.github.com/users/octocat",
            "html_url": "https://github.com/octocat",
            "type": "User",
            "site_admin": False,
            "followers_url": "https://api.github.com/users/octocat/followers",
            "following_url": "https://api.github.com/users/octocat/following{/other_user}",
            "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
            "repos_url": "https://api.github.com/users/octocat/repos",
            "events_url": "https://api.github.com/users/octocat/events{/privacy}",
            "received_events_url": "https://api.github.com/users/octocat/received_events",
        },
        "labels": [
            {
                "id": 208045946,
                "node_id": "MDU6TGFiZWwyMDgwNDU5NDY=",
                "url": "https://api.github.com/repos/octocat/Hello-World/labels/bug",
                "name": "bug",
                "description": "Something isn't working",
                "color": "f29513",
                "default": True,
            }
        ],
        "assignee": None,
        "assignees": [],
        "milestone": None,
        "locked": False,
        "comments": 0,
        "pull_request": None,
        "closed_at": None,
        "created_at": "2011-04-22T13:33:48Z",
        "updated_at": "2011-04-22T13:33:48Z",
        "author_association": "COLLABORATOR",
    }


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def config() -> ClientConfig:
    """Create a test configuration."""
    return ClientConfig(
        token="test_token_12345",
        timeout=5.0,
        cache_enabled=False,
    )


@pytest.fixture
def unauthenticated_config() -> ClientConfig:
    """Create an unauthenticated test configuration."""
    return ClientConfig(
        token=None,
        timeout=5.0,
        cache_enabled=False,
    )


# =============================================================================
# Rate Limit Headers
# =============================================================================


@pytest.fixture
def rate_limit_headers() -> dict[str, str]:
    """Sample rate limit headers."""
    return {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": "1609459200",
        "X-RateLimit-Resource": "core",
    }


@pytest.fixture
def rate_limit_exceeded_headers() -> dict[str, str]:
    """Rate limit exceeded headers."""
    return {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1609459200",
        "X-RateLimit-Resource": "core",
        "Retry-After": "3600",
    }
