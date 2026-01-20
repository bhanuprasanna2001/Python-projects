"""Endpoint modules for the GitHub API.

Each module in this package implements a group of related API endpoints,
following the Single Responsibility Principle.

Available endpoint groups:
    - users: User profiles and followers
    - repos: Repositories and contributors
    - issues: Issues and comments
    - pulls: Pull requests
    - search: Search for users, repos, issues
    - gists: Gists
    - orgs: Organizations

"""

from github_client.endpoints.base import BaseEndpoint
from github_client.endpoints.gists import GistsEndpoint
from github_client.endpoints.issues import IssuesEndpoint
from github_client.endpoints.orgs import OrgsEndpoint
from github_client.endpoints.pulls import PullsEndpoint
from github_client.endpoints.repos import ReposEndpoint
from github_client.endpoints.search import SearchEndpoint
from github_client.endpoints.users import UsersEndpoint

__all__ = [
    "BaseEndpoint",
    "GistsEndpoint",
    "IssuesEndpoint",
    "OrgsEndpoint",
    "PullsEndpoint",
    "ReposEndpoint",
    "SearchEndpoint",
    "UsersEndpoint",
]
