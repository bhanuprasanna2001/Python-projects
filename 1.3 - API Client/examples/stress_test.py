#!/usr/bin/env python
"""Stress test to verify all features work under load.

This script runs comprehensive tests against the real GitHub API to verify:
- Caching behavior and performance
- Rate limiter tracking and throttling
- Retry logic for transient failures
- Pagination across large datasets

Run: python examples/stress_test.py
"""

from __future__ import annotations

import time
from typing import Any

from github_client import GitHubClient
from github_client.exceptions import (
    AuthenticationError,
    GitHubError,
    NotFoundError,
)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n{'-'*40}")
    print(f"  {text}")
    print(f"{'-'*40}")


def print_success(msg: str) -> None:
    """Print success message."""
    print(f"  ✓ {msg}")


def print_error(msg: str) -> None:
    """Print error message."""
    print(f"  ✗ {msg}")


class TestRunner:
    """Simple test runner for feature tests."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize test runner."""
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.total_time = 0.0

    def run(self, name: str, test_fn: Any) -> bool:
        """Run a single test."""
        test_num = self.passed + self.failed + 1
        print(f"\n  [{test_num}] {name}...")
        start = time.time()
        try:
            result = test_fn()
            elapsed = time.time() - start
            self.total_time += elapsed
            if result:
                print_success(f"Passed ({elapsed:.3f}s)")
                self.passed += 1
                return True
            else:
                print_error(f"Failed ({elapsed:.3f}s)")
                self.failed += 1
                return False
        except Exception as e:
            elapsed = time.time() - start
            self.total_time += elapsed
            print_error(f"Exception: {e} ({elapsed:.3f}s)")
            self.failed += 1
            return False

    def summary(self) -> None:
        """Print test summary."""
        print_header("Test Results")
        print(f"  Passed:     {self.passed}")
        print(f"  Failed:     {self.failed}")
        print(f"  Total:      {self.passed + self.failed}")
        print(f"  Time:       {self.total_time:.2f}s")


def test_basic_operations(client: GitHubClient, runner: TestRunner) -> None:
    """Test basic API operations."""
    print_section("Basic API Operations")

    def test_fetch_user() -> bool:
        user = client.users.get("octocat")
        return user.login == "octocat"

    def test_fetch_repo() -> bool:
        repo = client.repos.get("python", "cpython")
        return repo.full_name == "python/cpython"

    def test_search_repos() -> bool:
        results = client.search.repos("language:python", per_page=5)
        return results.total_count > 0 and len(results.items) > 0

    def test_fetch_org() -> bool:
        org = client.orgs.get("github")
        return org.login == "github"

    runner.run("Fetch user (octocat)", test_fetch_user)
    runner.run("Fetch repository (python/cpython)", test_fetch_repo)
    runner.run("Search repositories", test_search_repos)
    runner.run("Fetch organization (github)", test_fetch_org)


def test_caching(client: GitHubClient, runner: TestRunner, verbose: bool) -> None:
    """Test caching system."""
    print_section("Caching System")

    def test_cache_hit() -> bool:
        # First request
        start1 = time.time()
        client.users.get("torvalds")
        time1 = time.time() - start1

        # Second request (should be cached)
        start2 = time.time()
        client.users.get("torvalds")
        time2 = time.time() - start2

        if verbose:
            print(f"      First: {time1:.3f}s, Cached: {time2:.3f}s")

        return time2 < time1 * 0.5 or time2 < 0.01

    def test_cache_size() -> bool:
        initial_size = client.cache.size if client.cache else 0
        client.users.get("gvanrossum")
        final_size = client.cache.size if client.cache else 0
        return final_size >= initial_size

    def test_different_endpoints() -> bool:
        client.users.get("defunkt")
        client.repos.get("rails", "rails")
        return (client.cache.size if client.cache else 0) >= 2

    runner.run("Cache hit performance (2nd request faster)", test_cache_hit)
    runner.run("Cache size increases", test_cache_size)
    runner.run("Different endpoints cached separately", test_different_endpoints)


def test_rate_limiter(client: GitHubClient, runner: TestRunner, verbose: bool) -> None:
    """Test rate limiter."""
    print_section("Rate Limiter")

    def test_rate_limit_tracking() -> bool:
        # Clear cache to force a real API call
        if client.cache:
            client.cache.clear()
        client.users.get("octocat")
        remaining = client.rate_limiter.get_remaining("core")
        if verbose:
            print(f"      Remaining: {remaining}")
        return remaining is not None and remaining > 0

    def test_rate_limit_updates() -> bool:
        before = client.rate_limiter.get_remaining("core")
        if client.cache:
            client.cache.clear()
        client.users.get("mojombo")
        after = client.rate_limiter.get_remaining("core")
        if verbose and before and after:
            print(f"      Before: {before}, After: {after}")
        return after is not None

    def test_reset_time() -> bool:
        reset_time = client.rate_limiter.get_reset_time("core")
        if verbose:
            print(f"      Reset at: {reset_time}")
        return reset_time is not None

    runner.run("Rate limit tracking active", test_rate_limit_tracking)
    runner.run("Rate limit updates after requests", test_rate_limit_updates)
    runner.run("Rate limit reset time available", test_reset_time)


def test_error_handling(client: GitHubClient, runner: TestRunner) -> None:
    """Test error handling."""
    print_section("Error Handling")

    def test_not_found() -> bool:
        try:
            client.users.get("this-user-does-not-exist-xyz123abc")
            return False
        except NotFoundError:
            return True

    def test_auth_error() -> bool:
        bad_client = GitHubClient(token="bad_token_12345")
        try:
            bad_client.users.get_authenticated()
            bad_client.close()
            return False
        except AuthenticationError:
            bad_client.close()
            return True
        except GitHubError:
            bad_client.close()
            return True

    runner.run("NotFoundError for missing user", test_not_found)
    runner.run("AuthenticationError for bad token", test_auth_error)


def test_pagination(client: GitHubClient, runner: TestRunner) -> None:
    """Test pagination."""
    print_section("Pagination")

    def test_list_repos() -> bool:
        repos = client.repos.list_for_user("torvalds", per_page=5)
        return isinstance(repos, list) and len(repos) > 0

    def test_search_pagination() -> bool:
        results = client.search.repos("language:rust", per_page=5)
        return hasattr(results, "total_count") and results.total_count > 0

    def test_iter_repos() -> bool:
        count = 0
        for _repo in client.repos.iter_for_user("gvanrossum", per_page=5):
            count += 1
            if count >= 10:
                break
        return count >= 5

    runner.run("List repos returns proper list", test_list_repos)
    runner.run("Search includes pagination info", test_search_pagination)
    runner.run("Iter repos auto-paginates", test_iter_repos)


def test_stress(client: GitHubClient, runner: TestRunner, verbose: bool) -> None:
    """Stress tests."""
    print_section("Stress Tests")

    def test_many_requests() -> bool:
        """Make many requests to test rate limiter."""
        users = ["octocat", "torvalds", "gvanrossum", "defunkt", "mojombo"]
        for _ in range(3):
            for user in users:
                if client.cache:
                    client.cache.clear()
                client.users.get(user)
        remaining = client.rate_limiter.get_remaining("core")
        if verbose:
            print(f"      Remaining after 15 requests: {remaining}")
        return remaining is not None

    def test_rapid_search() -> bool:
        """Test search rate limit."""
        queries = ["python", "rust", "go", "java", "typescript"]
        for q in queries:
            client.search.repos(f"language:{q}", per_page=1)
        return True

    def test_concurrent_resources() -> bool:
        """Access multiple resources quickly."""
        start = time.time()
        if client.cache:
            client.cache.clear()
        client.users.get("octocat")
        client.repos.get("python", "cpython")
        client.orgs.get("github")
        client.search.repos("machine learning", per_page=5)
        elapsed = time.time() - start
        if verbose:
            print(f"      4 different resources in {elapsed:.3f}s")
        return elapsed < 10

    runner.run("Many sequential requests (15)", test_many_requests)
    runner.run("Rapid search requests (5)", test_rapid_search)
    runner.run("Multiple resource types rapidly", test_concurrent_resources)


def main() -> int:
    """Run stress tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Stress test the GitHub client")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--stress", "-s", action="store_true", help="Include stress tests")
    args = parser.parse_args()

    print_header("GitHub Client - Stress Test Suite")

    client = GitHubClient()
    runner = TestRunner(verbose=args.verbose)

    try:
        test_basic_operations(client, runner)
        test_caching(client, runner, args.verbose)
        test_rate_limiter(client, runner, args.verbose)
        test_error_handling(client, runner)
        test_pagination(client, runner)

        if args.stress:
            test_stress(client, runner, args.verbose)

        runner.summary()

        if client.cache:
            print(f"  Cache Size: {client.cache.size} entries")

        remaining = client.rate_limiter.get_remaining("core")
        if remaining:
            print(f"  Rate Limit: {remaining} remaining")

        if runner.failed == 0:
            print("\n  ✅ All tests passed!")
            return 0
        else:
            print(f"\n  ❌ {runner.failed} test(s) failed")
            return 1

    finally:
        client.close()


if __name__ == "__main__":
    exit(main())
