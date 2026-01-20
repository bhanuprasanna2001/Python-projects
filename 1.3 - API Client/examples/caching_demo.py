#!/usr/bin/env python
"""Caching behavior demonstration.

The client implements intelligent caching to reduce API calls
and improve performance.

Run: python examples/caching_demo.py
"""

import time

from github_client import GitHubClient


def demo_basic_caching() -> None:
    """Show cache hit/miss behavior."""
    print("\n1️⃣  Basic Caching (TTL-based)")
    print("-" * 40)

    client = GitHubClient(cache_ttl=300)  # 5 minute cache

    # First request - cache miss
    print("  First request (cache miss)...")
    start = time.time()
    user1 = client.users.get("octocat")
    time1 = time.time() - start
    print(f"    Time: {time1:.3f}s")
    print(f"    User: {user1.login}")

    # Second request - cache hit
    print("\n  Second request (cache hit)...")
    start = time.time()
    user2 = client.users.get("octocat")
    time2 = time.time() - start
    print(f"    Time: {time2:.3f}s")
    print(f"    Speedup: {time1/max(time2, 0.001):.0f}x faster")

    print(f"\n  Cache stats:")
    print(f"    Size: {client.cache.size} entries")

    client.close()


def demo_cache_configuration() -> None:
    """Show cache configuration options."""
    print("\n2️⃣  Cache Configuration")
    print("-" * 40)

    # Cache enabled with custom TTL
    print("  Default (cache enabled, 300s TTL):")
    client1 = GitHubClient()
    print(f"    Cache enabled: True")
    print(f"    TTL: 300 seconds")
    client1.close()

    # Custom TTL
    print("\n  Custom TTL (60 seconds):")
    client2 = GitHubClient(cache_ttl=60)
    print(f"    TTL: 60 seconds")
    client2.close()

    # Cache disabled
    print("\n  Cache disabled:")
    client3 = GitHubClient(cache_enabled=False)
    print(f"    Cache enabled: False")
    print(f"    Every request hits the API")
    client3.close()


def demo_cache_benefits() -> None:
    """Demonstrate the performance benefits of caching."""
    print("\n3️⃣  Cache Performance Benefits")
    print("-" * 40)

    client = GitHubClient()

    users = ["torvalds", "gvanrossum", "octocat"]

    # First pass - all cache misses
    print("  First pass (populating cache)...")
    start = time.time()
    for username in users:
        client.users.get(username)
    first_pass = time.time() - start
    print(f"    Time: {first_pass:.3f}s")

    # Second pass - all cache hits
    print("\n  Second pass (from cache)...")
    start = time.time()
    for username in users:
        client.users.get(username)
    second_pass = time.time() - start
    print(f"    Time: {second_pass:.3f}s")

    print(f"\n  Results:")
    print(f"    First pass: {first_pass:.3f}s (3 API calls)")
    print(f"    Second pass: {second_pass:.3f}s (0 API calls)")
    print(f"    Time saved: {first_pass - second_pass:.3f}s")

    client.close()


def demo_cache_invalidation() -> None:
    """Show how to manually clear the cache."""
    print("\n4️⃣  Cache Invalidation")
    print("-" * 40)

    client = GitHubClient()

    # Populate cache
    client.users.get("octocat")
    print(f"  Cache size after request: {client.cache.size}")

    # Clear specific entry (if needed)
    print("\n  To force fresh data, you have options:")
    print("    1. Wait for TTL to expire")
    print("    2. Create a new client")
    print("    3. Disable cache for specific operations")

    # The cache respects ETags for conditional requests
    print("\n  ETag support:")
    print("    - Client sends If-None-Match header")
    print("    - Server returns 304 if unchanged")
    print("    - Saves bandwidth, counts toward rate limit")

    client.close()


def demo_what_gets_cached() -> None:
    """Explain what types of requests get cached."""
    print("\n5️⃣  What Gets Cached?")
    print("-" * 40)

    print("  ✓ Cached (GET requests):")
    print("    - User profiles")
    print("    - Repository details")
    print("    - Organization info")
    print("    - Search results")
    print("    - Lists (repos, issues, etc.)")

    print("\n  ✗ Not Cached:")
    print("    - POST requests (create)")
    print("    - PATCH requests (update)")
    print("    - DELETE requests")
    print("    - Authenticated user data (varies)")


def main() -> None:
    """Run all caching demos."""
    print("=" * 50)
    print("GitHub Client - Caching Demonstration")
    print("=" * 50)

    demo_basic_caching()
    demo_cache_configuration()
    demo_cache_benefits()
    demo_cache_invalidation()
    demo_what_gets_cached()

    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   - Caching reduces API calls and improves speed")
    print("   - Tune cache_ttl based on data freshness needs")
    print("   - Disable cache for real-time data requirements")
    print("=" * 50)


if __name__ == "__main__":
    main()
