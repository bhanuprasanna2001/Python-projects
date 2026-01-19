#!/usr/bin/env python
"""Authentication patterns for the GitHub Client.

GitHub API supports multiple authentication methods:
1. Personal Access Token (most common)
2. Environment variable (GITHUB_TOKEN)
3. No auth (limited to 60 requests/hour)

Run: GITHUB_TOKEN=your_token python examples/authentication.py
"""

import os

from github_client import GitHubClient
from github_client.exceptions import AuthenticationError


def demo_token_auth() -> None:
    """Authenticate with a personal access token."""
    print("\n1️⃣  Token Authentication")
    print("-" * 40)

    token = os.environ.get("GITHUB_TOKEN")

    if token:
        client = GitHubClient(token=token)
        print("  ✓ Authenticated with token")

        # With auth, you can access private data and have higher rate limits
        user = client.users.get_authenticated()
        print(f"  ✓ Logged in as: {user.login}")
        print(f"  ✓ Rate limit: 5,000 requests/hour")
        client.close()
    else:
        print("  ⚠ No GITHUB_TOKEN set, skipping authenticated example")
        print("  Set it with: export GITHUB_TOKEN=ghp_your_token")


def demo_env_auth() -> None:
    """Client automatically reads GITHUB_TOKEN from environment."""
    print("\n2️⃣  Environment Variable Authentication")
    print("-" * 40)

    # GitHubClient automatically reads GITHUB_TOKEN if no token provided
    client = GitHubClient()

    if os.environ.get("GITHUB_TOKEN"):
        print("  ✓ Auto-detected GITHUB_TOKEN from environment")
    else:
        print("  ℹ No GITHUB_TOKEN in environment")
        print("  ℹ Client will use unauthenticated requests (60/hour)")

    client.close()


def demo_unauthenticated() -> None:
    """Use the API without authentication (limited)."""
    print("\n3️⃣  Unauthenticated Access")
    print("-" * 40)

    # Temporarily unset token to demonstrate
    original_token = os.environ.pop("GITHUB_TOKEN", None)

    try:
        client = GitHubClient()
        print("  ✓ No authentication")
        print("  ✓ Rate limit: 60 requests/hour")

        # Public data is still accessible
        user = client.users.get("octocat")
        print(f"  ✓ Fetched public user: {user.login}")

        client.close()
    finally:
        # Restore token
        if original_token:
            os.environ["GITHUB_TOKEN"] = original_token


def demo_auth_error_handling() -> None:
    """Handle authentication errors gracefully."""
    print("\n4️⃣  Authentication Error Handling")
    print("-" * 40)

    try:
        # Using an invalid token
        client = GitHubClient(token="invalid_token_12345")
        client.users.get_authenticated()
    except AuthenticationError as e:
        print(f"  ✓ Caught AuthenticationError: {e}")
    except Exception:
        print("  ✓ Error handled (may vary based on network)")


def main() -> None:
    """Run all authentication demos."""
    print("=" * 50)
    print("GitHub Client - Authentication Patterns")
    print("=" * 50)

    demo_token_auth()
    demo_env_auth()
    demo_unauthenticated()
    demo_auth_error_handling()

    print("\n" + "=" * 50)
    print("💡 Tip: Create a token at https://github.com/settings/tokens")
    print("   Select 'repo' scope for full repository access")
    print("=" * 50)


if __name__ == "__main__":
    main()
