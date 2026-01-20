"""Command-line interface for the GitHub Client.

A clean CLI for querying the GitHub API.

Usage:
    github-client user octocat
    github-client repo python cpython
    github-client search "language:python stars:>10000"
    github-client me
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from typing import Any

from github_client import GitHubClient
from github_client.exceptions import (
    AuthenticationError,
    GitHubError,
    NotFoundError,
    RateLimitError,
)

# ============================================================================
# Display Utilities
# ============================================================================


def format_header(text: str) -> str:
    """Format a header string."""
    return f"\n{'=' * 60}\n  {text}\n{'=' * 60}"


def format_json(data: dict[str, Any] | list[Any]) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=2, default=str)


# ============================================================================
# Command Handlers
# ============================================================================


def cmd_user(client: GitHubClient, username: str, as_json: bool) -> int:
    """Fetch and display a user's profile."""
    try:
        user = client.users.get(username)
        if as_json:
            print(format_json(user.model_dump()))
        else:
            print(format_header(f"User: {user.login}"))
            print(f"  Name:         {user.name or 'N/A'}")
            print(f"  Bio:          {user.bio or 'N/A'}")
            print(f"  Location:     {user.location or 'N/A'}")
            print(f"  Company:      {user.company or 'N/A'}")
            print(f"  Public Repos: {user.public_repos}")
            print(f"  Followers:    {user.followers}")
            print(f"  URL:          {user.html_url}")
        return 0
    except NotFoundError:
        print(f"Error: User '{username}' not found", file=sys.stderr)
        return 1


def cmd_me(client: GitHubClient, as_json: bool) -> int:
    """Fetch authenticated user's profile."""
    try:
        user = client.users.get_authenticated()
        if as_json:
            print(format_json(user.model_dump()))
        else:
            print(format_header(f"Authenticated as: {user.login}"))
            print(f"  Name:           {user.name or 'N/A'}")
            print(f"  Email:          {user.email or 'N/A'}")
            print(f"  Public Repos:   {user.public_repos}")
            remaining = client.rate_limiter.get_remaining("core")
            print(f"  Rate Limit:     {remaining}/5000 remaining")
        return 0
    except AuthenticationError:
        print("Error: Not authenticated. Set GITHUB_TOKEN.", file=sys.stderr)
        return 1


def cmd_repo(client: GitHubClient, owner: str, repo: str, as_json: bool) -> int:
    """Fetch and display repository info."""
    try:
        repository = client.repos.get(owner, repo)
        if as_json:
            print(format_json(repository.model_dump()))
        else:
            print(format_header(f"Repository: {repository.full_name}"))
            print(f"  Description:  {repository.description or 'N/A'}")
            print(f"  Language:     {repository.language or 'N/A'}")
            print(f"  Stars:        {repository.stargazers_count:,}")
            print(f"  Forks:        {repository.forks_count:,}")
            print(f"  Open Issues:  {repository.open_issues_count:,}")
            license_name = repository.license.name if repository.license else "N/A"
            print(f"  License:      {license_name}")
            print(f"  URL:          {repository.html_url}")
        return 0
    except NotFoundError:
        print(f"Error: Repository '{owner}/{repo}' not found", file=sys.stderr)
        return 1


def cmd_repos(client: GitHubClient, username: str, limit: int, as_json: bool) -> int:
    """List user's repositories."""
    try:
        repos = client.repos.list_for_user(username, per_page=min(limit, 100))
        if as_json:
            print(format_json([r.model_dump() for r in repos[:limit]]))
        else:
            print(format_header(f"Repositories for: {username}"))
            for i, repo in enumerate(repos[:limit], 1):
                stars = f"⭐ {repo.stargazers_count:,}".ljust(10)
                lang = f"[{repo.language}]" if repo.language else ""
                print(f"  {i:2}. {stars} {repo.name} {lang}")
        return 0
    except NotFoundError:
        print(f"Error: User '{username}' not found", file=sys.stderr)
        return 1


def cmd_search(client: GitHubClient, query: str, limit: int, as_json: bool) -> int:
    """Search repositories."""
    results = client.search.repos(query, per_page=min(limit, 100))
    if as_json:
        print(
            format_json(
                {
                    "total_count": results.total_count,
                    "items": [r.model_dump() for r in results.items[:limit]],
                }
            )
        )
    else:
        shown = min(limit, len(results.items))
        print(format_header(f"Search: {query}"))
        print(f"  Found {results.total_count:,} repositories (showing {shown})\n")
        for i, repo in enumerate(results.items[:limit], 1):
            stars = f"⭐ {repo.stars:,}".ljust(12)
            print(f"  {i:2}. {stars} {repo.full_name}")
            if repo.description:
                desc = (
                    repo.description[:55] + "..."
                    if len(repo.description) > 55
                    else repo.description
                )
                print(f"               {desc}")
        if results.total_count > limit:
            print(f"\n  Use -n {limit * 2} to see more results")
    return 0


def cmd_org(client: GitHubClient, name: str, as_json: bool) -> int:
    """Fetch organization info."""
    try:
        org = client.orgs.get(name)
        if as_json:
            print(format_json(org.model_dump()))
        else:
            print(format_header(f"Organization: {org.login}"))
            print(f"  Name:         {org.name or 'N/A'}")
            print(f"  Description:  {org.description or 'N/A'}")
            print(f"  Location:     {org.location or 'N/A'}")
            print(f"  Public Repos: {org.public_repos}")
            print(f"  URL:          {org.html_url}")
        return 0
    except NotFoundError:
        print(f"Error: Organization '{name}' not found", file=sys.stderr)
        return 1


def cmd_rate_limit(client: GitHubClient) -> int:
    """Show current rate limit status."""
    with contextlib.suppress(GitHubError):
        client.users.get("octocat")

    print(format_header("Rate Limit Status"))

    for resource in ["core"]:
        remaining = client.rate_limiter.get_remaining(resource)
        reset_time = client.rate_limiter.get_reset_time(resource)
        if remaining is not None:
            print(f"  {resource.upper():10} {remaining} remaining")
            if reset_time:
                print(f"             Resets at: {reset_time}")
        else:
            print(f"  {resource.upper():10} Not yet tracked")
    return 0


# ============================================================================
# Argument Parser
# ============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="github-client",
        description="GitHub API Client - Query GitHub from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  github-client user octocat           Fetch user profile
  github-client repo python cpython    Fetch repository info
  github-client search "stars:>50000"  Search repositories
  github-client repos torvalds         List user's repos
  github-client me                     Show authenticated user
  github-client rate-limit             Show rate limit status
        """,
    )

    parser.add_argument("--token", "-t", help="GitHub token (or set GITHUB_TOKEN)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # user
    p = subparsers.add_parser("user", help="Get user profile")
    p.add_argument("username", help="GitHub username")

    # me
    subparsers.add_parser("me", help="Get authenticated user")

    # repo
    p = subparsers.add_parser("repo", help="Get repository info")
    p.add_argument("owner", help="Repository owner")
    p.add_argument("name", help="Repository name")

    # repos
    p = subparsers.add_parser("repos", help="List user's repositories")
    p.add_argument("username", help="GitHub username")
    p.add_argument("-n", "--limit", type=int, default=10, help="Number of repos (default: 10)")

    # search
    p = subparsers.add_parser("search", help="Search repositories")
    p.add_argument("query", help="Search query")
    p.add_argument("-n", "--limit", type=int, default=10, help="Number of results (default: 10)")

    # org
    p = subparsers.add_parser("org", help="Get organization info")
    p.add_argument("name", help="Organization name")

    # rate-limit
    subparsers.add_parser("rate-limit", help="Show rate limit status")

    return parser


# ============================================================================
# Main Entry Point
# ============================================================================

# Command dispatch table
COMMANDS = {
    "user": lambda c, a: cmd_user(c, a.username, a.json),
    "me": lambda c, a: cmd_me(c, a.json),
    "repo": lambda c, a: cmd_repo(c, a.owner, a.name, a.json),
    "repos": lambda c, a: cmd_repos(c, a.username, a.limit, a.json),
    "search": lambda c, a: cmd_search(c, a.query, a.limit, a.json),
    "org": lambda c, a: cmd_org(c, a.name, a.json),
    "rate-limit": lambda c, _: cmd_rate_limit(c),
}


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    client = GitHubClient(
        token=args.token,
        cache_enabled=not args.no_cache,
    )

    try:
        handler = COMMANDS.get(args.command)
        if handler:
            return handler(client, args)  # type: ignore[no-untyped-call]
        parser.print_help()
        return 0
    except RateLimitError as e:
        print(f"Error: Rate limit exceeded! Resets at: {e.reset_at}", file=sys.stderr)
        return 1
    except GitHubError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
