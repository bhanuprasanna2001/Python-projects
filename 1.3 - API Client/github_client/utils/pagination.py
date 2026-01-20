"""Pagination utilities for GitHub API responses.

This module provides pagination handling for GitHub's Link header-based
pagination system.

Pagination Patterns:
    1. PaginatedResponse: Manual page-by-page control
    2. Iterator: Memory-efficient lazy iteration
    3. Collect all: Convenience method for small datasets

GitHub Link Header Format:
    Link: <url>; rel="next", <url>; rel="last", <url>; rel="first", <url>; rel="prev"

"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    pass

T = TypeVar("T")

# Regex to parse Link header
# Matches: <url>; rel="relation"
LINK_PATTERN = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


@dataclass
class LinkInfo:
    """Parsed pagination links from GitHub's Link header.

    Attributes:
        next_url: URL for next page.
        prev_url: URL for previous page.
        first_url: URL for first page.
        last_url: URL for last page.

    """

    next_url: str | None = None
    prev_url: str | None = None
    first_url: str | None = None
    last_url: str | None = None

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.next_url is not None

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.prev_url is not None


def parse_link_header(link_header: str | None) -> LinkInfo:
    """Parse GitHub's Link header into structured data.

    Args:
        link_header: The Link header value.

    Returns:
        LinkInfo with parsed URLs.

    Example:
        >>> header = '<https://api.github.com/repos?page=2>; rel="next"'
        >>> info = parse_link_header(header)
        >>> info.next_url
        'https://api.github.com/repos?page=2'

    """
    if not link_header:
        return LinkInfo()

    links = LinkInfo()

    for match in LINK_PATTERN.finditer(link_header):
        url, rel = match.groups()
        if rel == "next":
            links.next_url = url
        elif rel == "prev":
            links.prev_url = url
        elif rel == "first":
            links.first_url = url
        elif rel == "last":
            links.last_url = url

    return links


def extract_page_from_url(url: str) -> int | None:
    """Extract page number from a pagination URL.

    Args:
        url: The pagination URL.

    Returns:
        Page number if found, None otherwise.

    """
    match = re.search(r"[?&]page=(\d+)", url)
    if match:
        return int(match.group(1))
    return None


@dataclass
class PaginatedResponse(Generic[T]):
    """A paginated API response with navigation capabilities.

    This class wraps a single page of results with metadata
    for navigating to other pages.

    Attributes:
        items: The items on the current page.
        page: Current page number.
        per_page: Items per page.
        total_count: Total items (if known, e.g., from search).
        link_info: Parsed pagination links.

    Example:
        >>> page = client.repos.list_for_user_paginated("torvalds")
        >>> for repo in page.items:
        ...     print(repo.name)
        >>> if page.has_next:
        ...     next_page = page.fetch_next()

    """

    items: list[T]
    page: int = 1
    per_page: int = 30
    total_count: int | None = None
    link_info: LinkInfo = field(default_factory=LinkInfo)
    _fetch_page: Callable[[int], PaginatedResponse[T]] | None = field(default=None, repr=False)

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.link_info.has_next

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.link_info.has_prev

    @property
    def next_page(self) -> int | None:
        """Get the next page number."""
        if self.link_info.next_url:
            return extract_page_from_url(self.link_info.next_url)
        return None

    @property
    def last_page(self) -> int | None:
        """Get the last page number (total pages)."""
        if self.link_info.last_url:
            return extract_page_from_url(self.link_info.last_url)
        return None

    def fetch_next(self) -> PaginatedResponse[T] | None:
        """Fetch the next page of results.

        Returns:
            Next page, or None if no next page.

        Raises:
            RuntimeError: If no fetch function is configured.

        """
        if not self.has_next:
            return None

        if self._fetch_page is None:
            raise RuntimeError("Pagination fetch function not configured")

        next_num = self.next_page
        if next_num is None:
            return None

        return self._fetch_page(next_num)

    def fetch_prev(self) -> PaginatedResponse[T] | None:
        """Fetch the previous page of results.

        Returns:
            Previous page, or None if no previous page.

        """
        if not self.has_prev or self._fetch_page is None:
            return None

        if self.link_info.prev_url:
            prev_num = extract_page_from_url(self.link_info.prev_url)
            if prev_num:
                return self._fetch_page(prev_num)

        return None

    def __len__(self) -> int:
        """Return the number of items on this page."""
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        """Iterate over items on this page."""
        return iter(self.items)


def paginate(
    fetch_func: Callable[[int, int], tuple[list[T], dict[str, str]]],
    per_page: int = 30,
    max_pages: int | None = None,
) -> Iterator[T]:
    """Create an iterator that automatically paginates through results.

    This is a memory-efficient way to iterate through all results
    without loading everything into memory.

    Args:
        fetch_func: Function that takes (page, per_page) and returns
                    (items, headers) tuple.
        per_page: Items per page.
        max_pages: Maximum pages to fetch (None for unlimited).

    Yields:
        Individual items from all pages.

    Example:
        >>> for repo in paginate(lambda p, pp: fetch_repos(user, p, pp)):
        ...     print(repo.name)
        ...     if repo.stars < 100:
        ...         break  # Stops fetching early!

    """
    page = 1

    while True:
        if max_pages and page > max_pages:
            return

        items, headers = fetch_func(page, per_page)

        if not items:
            return

        yield from items

        # Check for next page
        link_info = parse_link_header(headers.get("Link"))
        if not link_info.has_next:
            return

        page += 1


def collect_all(
    fetch_func: Callable[[int, int], tuple[list[T], dict[str, str]]],
    per_page: int = 100,
    max_items: int | None = None,
) -> list[T]:
    """Collect all items from a paginated endpoint.

    Warning: This loads everything into memory. Use paginate()
    for large datasets.

    Args:
        fetch_func: Function that takes (page, per_page) and returns
                    (items, headers) tuple.
        per_page: Items per page (use 100 for efficiency).
        max_items: Maximum items to collect (None for unlimited).

    Returns:
        List of all items.

    """
    all_items: list[T] = []

    for item in paginate(fetch_func, per_page=per_page):
        all_items.append(item)
        if max_items and len(all_items) >= max_items:
            break

    return all_items


def create_paginated_response(
    items: list[T],
    headers: dict[str, str],
    page: int,
    per_page: int,
    fetch_page: Callable[[int], PaginatedResponse[T]] | None = None,
) -> PaginatedResponse[T]:
    """Create a PaginatedResponse from raw API data.

    Args:
        items: The parsed items for this page.
        headers: Response headers (for Link header).
        page: Current page number.
        per_page: Items per page.
        fetch_page: Optional function to fetch other pages.

    Returns:
        PaginatedResponse with navigation capabilities.

    """
    link_info = parse_link_header(headers.get("Link"))

    return PaginatedResponse(
        items=items,
        page=page,
        per_page=per_page,
        link_info=link_info,
        _fetch_page=fetch_page,
    )
