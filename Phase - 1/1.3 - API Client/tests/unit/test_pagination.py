"""Unit tests for the pagination module."""

from __future__ import annotations

from github_client.utils.pagination import (
    LinkInfo,
    PaginatedResponse,
    extract_page_from_url,
    parse_link_header,
)


class TestParseLinkHeader:
    """Tests for parse_link_header function."""

    def test_empty_header(self):
        """Empty header should return empty LinkInfo."""
        result = parse_link_header("")
        assert result.next_url is None
        assert result.prev_url is None
        assert result.first_url is None
        assert result.last_url is None

    def test_none_header(self):
        """None header should return empty LinkInfo."""
        result = parse_link_header(None)
        assert result.next_url is None

    def test_single_link(self):
        """Should parse single link."""
        header = '<https://api.github.com/repos?page=2>; rel="next"'
        result = parse_link_header(header)

        assert result.next_url == "https://api.github.com/repos?page=2"
        assert result.prev_url is None

    def test_multiple_links(self):
        """Should parse multiple links."""
        header = (
            '<https://api.github.com/repos?page=2>; rel="next", '
            '<https://api.github.com/repos?page=1>; rel="prev", '
            '<https://api.github.com/repos?page=1>; rel="first", '
            '<https://api.github.com/repos?page=10>; rel="last"'
        )
        result = parse_link_header(header)

        assert result.next_url == "https://api.github.com/repos?page=2"
        assert result.prev_url == "https://api.github.com/repos?page=1"
        assert result.first_url == "https://api.github.com/repos?page=1"
        assert result.last_url == "https://api.github.com/repos?page=10"


class TestExtractPageFromUrl:
    """Tests for extract_page_from_url function."""

    def test_extract_page(self):
        """Should extract page number from URL."""
        url = "https://api.github.com/repos?page=5"
        assert extract_page_from_url(url) == 5

    def test_no_page_param(self):
        """Should return None if no page param."""
        url = "https://api.github.com/repos"
        assert extract_page_from_url(url) is None

    def test_page_one(self):
        """Should extract page 1."""
        url = "https://api.github.com/repos?page=1"
        assert extract_page_from_url(url) == 1

    def test_page_with_other_params(self):
        """Should extract page when other params present."""
        url = "https://api.github.com/repos?per_page=30&page=3&sort=full_name"
        assert extract_page_from_url(url) == 3


class TestLinkInfo:
    """Tests for LinkInfo dataclass."""

    def test_has_next_true(self):
        """has_next should be True when next_url is set."""
        info = LinkInfo(next_url="https://example.com/page=2")
        assert info.has_next is True

    def test_has_next_false(self):
        """has_next should be False when next_url is None."""
        info = LinkInfo()
        assert info.has_next is False

    def test_has_prev_true(self):
        """has_prev should be True when prev_url is set."""
        info = LinkInfo(prev_url="https://example.com/page=1")
        assert info.has_prev is True

    def test_has_prev_false(self):
        """has_prev should be False when prev_url is None."""
        info = LinkInfo()
        assert info.has_prev is False


class TestPaginatedResponse:
    """Tests for PaginatedResponse class."""

    def test_items(self):
        """Should store items."""
        items = [{"id": 1}, {"id": 2}]
        paginated = PaginatedResponse(items=items)
        assert paginated.items == items

    def test_has_next_with_link(self):
        """has_next should use link_info."""
        link_info = LinkInfo(next_url="https://api.github.com/repos?page=2")
        paginated = PaginatedResponse(items=[], link_info=link_info)
        assert paginated.has_next is True

    def test_has_next_no_link(self):
        """has_next should be False without link."""
        paginated = PaginatedResponse(items=[])
        assert paginated.has_next is False

    def test_has_prev_first_page(self):
        """has_prev should be False on first page."""
        paginated = PaginatedResponse(items=[], page=1)
        assert paginated.has_prev is False

    def test_has_prev_with_link(self):
        """has_prev should use link_info."""
        link_info = LinkInfo(prev_url="https://api.github.com/repos?page=1")
        paginated = PaginatedResponse(items=[], link_info=link_info)
        assert paginated.has_prev is True

    def test_next_page(self):
        """Should extract next page number."""
        link_info = LinkInfo(next_url="https://api.github.com/repos?page=3")
        paginated = PaginatedResponse(items=[], link_info=link_info)
        assert paginated.next_page == 3

    def test_last_page(self):
        """Should extract last page number."""
        link_info = LinkInfo(last_url="https://api.github.com/repos?page=10")
        paginated = PaginatedResponse(items=[], link_info=link_info)
        assert paginated.last_page == 10

    def test_last_page_none(self):
        """last_page should be None without last link."""
        paginated = PaginatedResponse(items=[])
        assert paginated.last_page is None

    def test_iteration(self):
        """Should support iteration over items."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        paginated = PaginatedResponse(items=items)

        collected = list(paginated)
        assert collected == items

    def test_len(self):
        """Should support len() on items."""
        items = [{"id": 1}, {"id": 2}]
        paginated = PaginatedResponse(items=items)
        assert len(paginated) == 2
