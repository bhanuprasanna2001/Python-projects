#!/usr/bin/env python
"""Basic usage examples for the GitHub Client library.

This demonstrates the most common operations you'll perform.
No authentication required for public data.

Run: python examples/basic_usage.py
"""

from github_client import GitHubClient


def main() -> None:
    """Demonstrate basic GitHub API operations."""
    # Create client (no token needed for public data)
    client = GitHubClient()

    print("=" * 50)
    print("GitHub Client - Basic Usage Examples")
    print("=" * 50)

    # --- Users ---
    print("\n📧 Fetching a user...")
    user = client.users.get("octocat")
    print(f"  Login: {user.login}")
    print(f"  Name: {user.name}")
    print(f"  Public repos: {user.public_repos}")
    print(f"  Followers: {user.followers}")

    # --- Repositories ---
    print("\n📁 Fetching a repository...")
    repo = client.repos.get("python", "cpython")
    print(f"  Full name: {repo.full_name}")
    print(f"  Stars: {repo.stargazers_count:,}")
    print(f"  Language: {repo.language}")
    print(f"  Open issues: {repo.open_issues_count:,}")

    # --- List user's repos ---
    print("\n📚 Listing repos for a user...")
    repos = client.repos.list_for_user("torvalds", per_page=5)
    for repo in repos[:5]:
        print(f"  - {repo.name}: ⭐ {repo.stargazers_count:,}")

    # --- Search ---
    print("\n🔍 Searching repositories...")
    results = client.search.repos("language:python stars:>50000", per_page=5)
    print(f"  Found {results.total_count} repos matching criteria")
    for repo in results.items[:5]:
        print(f"  - {repo.full_name}: ⭐ {repo.stars:,}")

    # --- Organizations ---
    print("\n🏢 Fetching an organization...")
    org = client.orgs.get("python")
    print(f"  Name: {org.name}")
    print(f"  Public repos: {org.public_repos}")

    # Always close the client when done
    client.close()

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
