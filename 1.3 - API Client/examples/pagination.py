#!/usr/bin/env python
"""Pagination examples for handling large datasets.

GitHub API returns paginated results for list endpoints.
This client provides multiple ways to handle pagination.

Run: python examples/pagination.py
"""

from github_client import GitHubClient


def demo_simple_list() -> None:
    """Basic list operation (returns first page)."""
    print("\n1️⃣  Simple List (First Page)")
    print("-" * 40)

    client = GitHubClient()

    # Get first 10 repos for a user
    repos = client.repos.list_for_user("torvalds", per_page=10)
    print(f"  Got {len(repos)} repos")
    for repo in repos[:5]:
        print(f"    - {repo.name}")

    client.close()


def demo_pagination_info() -> None:
    """Access pagination metadata from search results."""
    print("\n2️⃣  Search with Pagination Info")
    print("-" * 40)

    client = GitHubClient()

    # Search returns pagination metadata
    results = client.search.repos("language:rust", per_page=5)

    print(f"  Total matching repos: {results.total_count:,}")
    print(f"  Returned in this page: {len(results.items)}")
    print(f"  Incomplete results: {results.incomplete_results}")

    print("\n  Top 5 Rust repos:")
    for repo in results.items:
        print(f"    - {repo.full_name}: ⭐ {repo.stars:,}")

    client.close()


def demo_iter_all() -> None:
    """Iterate through ALL results across pages."""
    print("\n3️⃣  Iterate All Results (Auto-Pagination)")
    print("-" * 40)

    client = GitHubClient()

    # iter_* methods handle pagination automatically
    print("  Iterating through repos for 'gvanrossum'...")

    count = 0
    for repo in client.repos.iter_for_user("gvanrossum", per_page=10):
        count += 1
        if count <= 5:
            print(f"    {count}. {repo.name}")
        elif count == 6:
            print("    ...")

    print(f"\n  Total repos fetched: {count}")

    client.close()


def demo_controlled_pagination() -> None:
    """Manually control pagination for more complex scenarios."""
    print("\n4️⃣  Manual Pagination Control")
    print("-" * 40)

    client = GitHubClient()

    # For organizations with many repos, you might want to stop early
    print("  Fetching Microsoft repos (stopping after 20)...")

    count = 0
    max_repos = 20

    for repo in client.repos.iter_for_org("microsoft", per_page=10):
        count += 1
        if count <= 5:
            print(f"    - {repo.name}: ⭐ {repo.stargazers_count:,}")
        if count >= max_repos:
            print(f"    ... (stopped at {max_repos})")
            break

    client.close()


def demo_search_pagination() -> None:
    """Paginate through search results."""
    print("\n5️⃣  Search Pagination")
    print("-" * 40)

    client = GitHubClient()

    # GitHub search is limited to 1000 results total
    query = "language:python stars:>10000"
    print(f"  Searching: {query}")

    results = client.search.repos(query, per_page=10)
    print(f"  Total results: {results.total_count}")
    print(f"  First page ({len(results.items)} items):")

    for repo in results.items[:5]:
        print(f"    - {repo.full_name}")

    client.close()


def main() -> None:
    """Run all pagination demos."""
    print("=" * 50)
    print("GitHub Client - Pagination Examples")
    print("=" * 50)

    demo_simple_list()
    demo_pagination_info()
    demo_iter_all()
    demo_controlled_pagination()
    demo_search_pagination()

    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   - Use per_page to control batch size (max 100)")
    print("   - iter_* methods auto-paginate through all results")
    print("   - Search API limited to 1000 total results")
    print("=" * 50)


if __name__ == "__main__":
    main()
