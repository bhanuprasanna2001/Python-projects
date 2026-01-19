"""Base class for API endpoints.

This module provides the abstract base class that all endpoint
implementations inherit from. It provides common functionality
for making API requests and processing responses.

"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from github_client.utils.pagination import (
    PaginatedResponse,
    create_paginated_response,
    parse_link_header,
)

if TYPE_CHECKING:
    from github_client.config import ClientConfig
    from github_client.utils.http import HTTPClient

T = TypeVar("T", bound=BaseModel)


class BaseEndpoint:
    """Base class for API endpoint groups.

    Each endpoint group (users, repos, etc.) inherits from this class
    to get access to the HTTP client and common helper methods.

    Attributes:
        _http: The HTTP client for making requests.
        _config: Client configuration.

    """

    __slots__ = ("_config", "_http")

    def __init__(self, http: HTTPClient, config: ClientConfig) -> None:
        """Initialize the endpoint with HTTP client and config.

        Args:
            http: The HTTP client for making requests.
            config: Client configuration.

        """
        self._http = http
        self._config = config

    def _parse_response(self, data: dict[str, Any], model: type[T]) -> T:
        """Parse a dictionary response into a Pydantic model.

        Args:
            data: Raw dictionary from API response.
            model: Pydantic model class to parse into.

        Returns:
            Parsed model instance.

        """
        return model.model_validate(data)

    def _parse_list_response(
        self,
        data: list[dict[str, Any]],
        model: type[T],
    ) -> list[T]:
        """Parse a list of dictionaries into Pydantic models.

        Args:
            data: List of raw dictionaries from API response.
            model: Pydantic model class to parse each item into.

        Returns:
            List of parsed model instances.

        """
        return [model.model_validate(item) for item in data]

    def _build_pagination_params(
        self,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, int]:
        """Build pagination query parameters.

        Args:
            page: Page number (1-indexed).
            per_page: Items per page (max 100).

        Returns:
            Dictionary of pagination parameters.

        """
        params: dict[str, int] = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = min(per_page, self._config.MAX_PER_PAGE)
        elif self._config.per_page != self._config.DEFAULT_PER_PAGE:
            params["per_page"] = self._config.per_page
        return params

    def _iter_pages(
        self,
        endpoint: str,
        model: type[T],
        params: dict[str, Any] | None = None,
        per_page: int = 100,
        max_items: int | None = None,
    ) -> Iterator[T]:
        """Iterate through all pages of a paginated endpoint.

        This is memory-efficient as it yields items one at a time
        and only fetches pages as needed.

        Args:
            endpoint: API endpoint path.
            model: Pydantic model class for parsing items.
            params: Additional query parameters.
            per_page: Items per page (use 100 for efficiency).
            max_items: Maximum items to yield (None for unlimited).

        Yields:
            Parsed model instances from all pages.

        """
        params = params or {}
        params["per_page"] = per_page
        page = 1
        yielded = 0

        while True:
            params["page"] = page
            response = self._http.get(endpoint, params=params)

            items = response.data
            if not isinstance(items, list) or not items:
                return

            for item in items:
                yield model.model_validate(item)
                yielded += 1
                if max_items and yielded >= max_items:
                    return

            # Check for next page
            link_info = parse_link_header(response.link_header)
            if not link_info.has_next:
                return

            page += 1

    def _get_paginated(
        self,
        endpoint: str,
        model: type[T],
        params: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int | None = None,
    ) -> PaginatedResponse[T]:
        """Get a single page with pagination metadata.

        Args:
            endpoint: API endpoint path.
            model: Pydantic model class for parsing items.
            params: Additional query parameters.
            page: Page number to fetch.
            per_page: Items per page.

        Returns:
            PaginatedResponse with items and navigation.

        """
        params = params or {}
        params.update(self._build_pagination_params(page, per_page))

        response = self._http.get(endpoint, params=params)

        items_data = response.data
        if not isinstance(items_data, list):
            items_data = []

        items = [model.model_validate(item) for item in items_data]

        actual_per_page = per_page or self._config.per_page

        # Create fetch function for navigation
        def fetch_page(p: int) -> PaginatedResponse[T]:
            return self._get_paginated(endpoint, model, params, p, actual_per_page)

        return create_paginated_response(
            items=items,
            headers=response.headers,
            page=page,
            per_page=actual_per_page,
            fetch_page=fetch_page,
        )
