"""
GitHub API extractor.

Extracts repository data from GitHub's REST API with:
- Rate limit handling
- Pagination support
- Retry on transient failures
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from etl_pipeline.exceptions import (
    ExtractionError,
    RateLimitError,
    SourceConnectionError,
)
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.models import DataSource, ExtractionResult, GitHubRepository
from etl_pipeline.utils.retry import with_async_retry


class GitHubExtractor(BaseExtractor[GitHubRepository]):
    """
    Extracts repository data from GitHub API.

    Supports:
    - User starred repositories
    - User owned repositories
    - Organization repositories

    Rate limits:
    - Unauthenticated: 60 requests/hour
    - Authenticated: 5,000 requests/hour
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        username: str = "torvalds",
        max_items: int = 100,
        token: str | None = None,
        rate_limit_delay: float = 1.0,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize GitHub extractor.

        Args:
            username: GitHub username to fetch data for
            max_items: Maximum number of repositories to fetch
            token: GitHub personal access token (optional, uses env var if not provided)
            rate_limit_delay: Delay between requests in seconds
            config: Additional configuration
        """
        super().__init__(DataSource.GITHUB, config)
        self.username = username
        self.max_items = max_items
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.rate_limit_delay = rate_limit_delay
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return f"GitHub API ({self.username})"

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ETL-Pipeline/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._get_headers(),
                timeout=30.0,
            )
        return self._client

    async def validate_connection(self) -> bool:
        """Check if GitHub API is accessible."""
        try:
            client = await self._get_client()
            response = await client.get("/rate_limit")
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"GitHub connection validation failed: {e}")
            return False

    @with_async_retry(max_attempts=3, retry_on=(httpx.HTTPError,))
    async def _fetch_page(self, url: str, params: dict[str, Any]) -> httpx.Response:
        """Fetch a single page of results with retry."""
        client = await self._get_client()
        response = await client.get(url, params=params)

        # Handle rate limiting
        if response.status_code == 403:
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            if remaining == 0:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                retry_after = max(0, reset_time - int(datetime.utcnow().timestamp()))
                raise RateLimitError("github", retry_after=retry_after)

        response.raise_for_status()
        return response

    def _parse_repository(self, data: dict[str, Any]) -> GitHubRepository:
        """Parse API response into GitHubRepository model."""
        return GitHubRepository(
            repo_id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            html_url=data["html_url"],
            language=data.get("language"),
            stargazers_count=data.get("stargazers_count", 0),
            forks_count=data.get("forks_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if data.get("updated_at")
            else None,
            topics=data.get("topics", []),
            owner_login=data.get("owner", {}).get("login", ""),
            raw_data=data,
        )

    async def extract(self) -> ExtractionResult:
        """
        Extract starred repositories for the configured user.

        Returns:
            ExtractionResult containing GitHubRepository records
        """
        result = self._create_result()
        records: list[GitHubRepository] = []

        try:
            self.logger.info(
                f"Starting GitHub extraction for user '{self.username}'",
                extra={"max_items": self.max_items},
            )

            # Fetch starred repos (paginated)
            page = 1
            per_page = min(100, self.max_items)  # GitHub max is 100 per page

            while len(records) < self.max_items:
                url = f"/users/{self.username}/starred"
                params = {"page": page, "per_page": per_page}

                try:
                    response = await self._fetch_page(url, params)
                    data = response.json()

                    if not data:  # No more results
                        break

                    for repo_data in data:
                        if len(records) >= self.max_items:
                            break
                        try:
                            repo = self._parse_repository(repo_data)
                            records.append(repo)
                        except Exception as e:
                            self._handle_error(result, e)

                    page += 1

                    # Respect rate limiting
                    import asyncio

                    await asyncio.sleep(self.rate_limit_delay)

                except RateLimitError:
                    raise
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise SourceConnectionError(
                            "github",
                            f"User '{self.username}' not found",
                        ) from e
                    raise

            result.records = records  # type: ignore[assignment]
            self.logger.info(
                f"Extracted {len(records)} repositories",
                extra={"record_count": len(records)},
            )

        except (RateLimitError, SourceConnectionError):
            raise
        except Exception as e:
            self._handle_error(result, e)
            raise ExtractionError(
                f"GitHub extraction failed: {e}",
                source="github",
                recoverable=True,
            ) from e
        finally:
            result.complete()

        return result

    async def __aexit__(self, *args: Any) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
