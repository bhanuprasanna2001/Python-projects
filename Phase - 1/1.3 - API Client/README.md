# GitHub Client Library

A Python client library for the GitHub REST API.

## Features

- **Token Authentication** - Secure API access with personal access tokens
- **Fully Typed** - Complete type hints with Pydantic models for IDE autocomplete
- **Clean API** - Intuitive, fluent interface organized by resource type
- **Retry Logic** - Automatic retry with exponential backoff
- **Rate Limiting** - Intelligent rate limit handling
- **Response Caching** - TTL-based caching with ETag support
- **Pagination** - Easy iteration over paginated results

## Installation

```bash
# Install in development mode
pip install -e ".[dev]"

# Or just the library
pip install -e .
```

## Setup (Authentication)

**No token required** for reading public data (60 requests/hour).  
**With token**: 5,000 requests/hour + access to private repos.

```bash
# Option 1: Set environment variable (recommended)
export GITHUB_TOKEN=ghp_your_personal_access_token

# Option 2: Copy .env.example to .env and edit
cp .env.example .env
```

Create a token at: https://github.com/settings/tokens

## Quick Start

```python
from github_client import GitHubClient

# Create a client (uses GITHUB_TOKEN env var if set)
client = GitHubClient(token="ghp_your_token_here")

# Get a user
user = client.users.get("octocat")
print(f"{user.name} has {user.public_repos} public repos")

# Search repositories
results = client.search.repos("language:python stars:>10000")
for repo in results.items[:5]:
    print(f"{repo.full_name}: {repo.stargazers_count} stars")

# List issues
issues = client.issues.list_for_repo("python", "cpython", state="open")
for issue in issues[:5]:
    print(f"#{issue.number}: {issue.title}")

# Clean up
client.close()
```

### Using Context Manager

```python
with GitHubClient(token="ghp_xxx") as client:
    user = client.users.get("octocat")
    # Client automatically closed when exiting the block
```

## Authentication

### Personal Access Token

```python
# Direct token
client = GitHubClient(token="ghp_your_token_here")

# Or set environment variable
# export GITHUB_TOKEN=ghp_your_token_here
client = GitHubClient()  # Automatically uses GITHUB_TOKEN
```

### Unauthenticated Access

```python
# No token = 60 requests/hour rate limit
client = GitHubClient()
user = client.users.get("octocat")  # Public data only
```

## API Reference

### Users

```python
# Get a user's public profile
user = client.users.get("octocat")

# Get authenticated user (requires token)
me = client.users.get_authenticated()

# List followers
followers = client.users.list_followers("octocat")

# List following
following = client.users.list_following("octocat")
```

### Repositories

```python
# Get a repository
repo = client.repos.get("microsoft", "vscode")

# List user's repositories
repos = client.repos.list_for_user("torvalds")

# List organization repositories
repos = client.repos.list_for_org("microsoft")

# List commits
commits = client.repos.list_commits("python", "cpython")

# Get languages
languages = client.repos.get_languages("python", "cpython")
```

### Issues

```python
# List issues for a repository
issues = client.issues.list_for_repo("python", "cpython", state="open")

# Get a specific issue
issue = client.issues.get("python", "cpython", 12345)

# Create an issue (requires authentication)
issue = client.issues.create(
    "owner", "repo",
    title="Bug: Something is broken",
    body="## Description\n\nDetails here...",
    labels=["bug"]
)

# List comments
comments = client.issues.list_comments("owner", "repo", 123)
```

### Pull Requests

```python
# List pull requests
prs = client.pulls.list_for_repo("python", "cpython", state="open")

# Get a specific PR
pr = client.pulls.get("python", "cpython", 12345)

# List changed files
files = client.pulls.list_files("owner", "repo", 123)
```

### Search

```python
# Search repositories
results = client.search.repos("language:python stars:>1000")

# Search users
results = client.search.users("location:Germany followers:>100")

# Search issues
results = client.search.issues('label:"good first issue" is:open')

# Search code (requires authentication)
results = client.search.code("def parse_config repo:owner/repo")
```

### Gists

```python
# List user's gists
gists = client.gists.list_for_user("octocat")

# Get a gist
gist = client.gists.get("aa5a315d61ae9438b18d")

# Create a gist
gist = client.gists.create(
    files={"hello.py": {"content": "print('Hello!')"}},
    description="My gist",
    public=True
)
```

### Organizations

```python
# Get an organization
org = client.orgs.get("microsoft")

# List organization repos
repos = client.orgs.list_repos("microsoft")

# List members
members = client.orgs.list_public_members("microsoft")
```

## Error Handling

```python
from github_client import GitHubClient
from github_client.exceptions import (
    NotFoundError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)

client = GitHubClient(token="ghp_xxx")

try:
    user = client.users.get("nonexistent-user-12345")
except NotFoundError as e:
    print(f"User not found: {e}")
except AuthenticationError as e:
    print(f"Invalid token: {e}")
except RateLimitError as e:
    print(f"Rate limited. Reset at: {e.reset_at}")
except ValidationError as e:
    print(f"Invalid request: {e.field_errors}")
```

## Configuration

```python
from github_client import GitHubClient, ClientConfig

# Custom configuration
client = GitHubClient(
    token="ghp_xxx",
    base_url="https://github.example.com/api/v3",  # GitHub Enterprise
    timeout=60.0,          # Request timeout in seconds
    max_retries=5,         # Retry attempts
    cache_enabled=True,    # Enable response caching
    cache_ttl=300,         # Cache TTL in seconds
    per_page=50,           # Default pagination size
)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | Personal access token | None |
| `GITHUB_BASE_URL` | API base URL | https://api.github.com |
| `GITHUB_TIMEOUT` | Request timeout (seconds) | 30 |
| `GITHUB_MAX_RETRIES` | Max retry attempts | 3 |
| `GITHUB_CACHE_TTL` | Cache TTL (seconds) | 300 |

## Development

```bash
# Install dev dependencies
make install

# Run all checks
make check

# Run tests only
make test

# Run linting
make lint

# Auto-fix issues
make fix
```

## License

MIT License
