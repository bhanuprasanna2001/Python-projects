"""Tests for HTML parser.

WHY TEST THIS:
- Risk: CRITICAL - wrong parsing means wrong data stored
- Complexity: HIGH - HTML structure can vary, many edge cases
- Easy to test: YES - just pass HTML strings, check output

WHAT WE'RE TESTING:
1. Valid HTML → correct Book objects extracted
2. Missing required elements → ParseError raised
3. Partial data → handles gracefully (skip or default)
4. Pagination detection → correct next URL or None
"""

import pytest
from web_scraper.exceptions import ParseError
from web_scraper.models import Book
from web_scraper.parser import Parser

# =============================================================================
# TEST FIXTURES - Reusable test HTML
# =============================================================================

VALID_BOOK_HTML = """
<html>
<body>
<ol>
    <li class="product_pod">
        <h3><a href="book1.html" title="Test Book One">Test Book...</a></h3>
        <p class="price_color">£51.77</p>
        <p class="star-rating Three"></p>
    </li>
    <li class="product_pod">
        <h3><a href="book2.html" title="Test Book Two">Test Book...</a></h3>
        <p class="price_color">£23.99</p>
        <p class="star-rating Five"></p>
    </li>
</ol>
</body>
</html>
"""

HTML_WITH_NEXT_PAGE = """
<html>
<body>
<ol>
    <li class="product_pod">
        <h3><a href="book1.html" title="Test Book">Test</a></h3>
        <p class="price_color">£10.00</p>
        <p class="star-rating One"></p>
    </li>
</ol>
<li class="next"><a href="page-2.html">next</a></li>
</body>
</html>
"""

HTML_WITHOUT_NEXT_PAGE = """
<html>
<body>
<ol>
    <li class="product_pod">
        <h3><a href="book1.html" title="Test Book">Test</a></h3>
        <p class="price_color">£10.00</p>
        <p class="star-rating One"></p>
    </li>
</ol>
</body>
</html>
"""

HTML_MISSING_OL = """
<html>
<body>
<div>No book list here</div>
</body>
</html>
"""

HTML_EMPTY_OL = """
<html>
<body>
<ol></ol>
</body>
</html>
"""


class TestParserParsing:
    """Test book extraction from HTML."""

    def test_extracts_books_from_valid_html(self) -> None:
        """Valid HTML should produce correct Book objects.

        This is the happy path - most important test.
        """
        parser = Parser(VALID_BOOK_HTML.encode(), base_url="https://example.com")

        books = parser.parse()

        assert len(books) == 2
        assert books[0].title == "Test Book One"
        assert books[0].price == "£51.77"
        assert books[0].rating == "Three"
        assert books[1].title == "Test Book Two"
        assert books[1].price == "£23.99"
        assert books[1].rating == "Five"

    def test_raises_error_when_ol_missing(self) -> None:
        """Missing <ol> element should raise ParseError.

        Reasoning: The <ol> is required structure. If it's missing,
        something is fundamentally wrong with the page.
        """
        parser = Parser(HTML_MISSING_OL.encode(), base_url="")

        with pytest.raises(ParseError, match="Required <ol> element not found"):
            parser.parse()

    def test_raises_error_when_ol_empty(self) -> None:
        """Empty <ol> should raise ParseError.

        Reasoning: A page with no books is unexpected - could indicate
        a structural change or being blocked.
        """
        parser = Parser(HTML_EMPTY_OL.encode(), base_url="")

        with pytest.raises(ParseError, match="No <li> elements found"):
            parser.parse()

    def test_returns_book_objects_not_dicts(self) -> None:
        """Parser should return Book dataclass instances.

        Reasoning: Strong typing helps catch errors early.
        """
        parser = Parser(VALID_BOOK_HTML.encode(), base_url="")

        books = parser.parse()

        assert all(isinstance(book, Book) for book in books)


class TestParserPagination:
    """Test next page URL detection."""

    def test_extracts_next_page_url(self) -> None:
        """Should extract and resolve next page URL.

        Reasoning: Pagination is core to multi-page scraping.
        """
        parser = Parser(
            HTML_WITH_NEXT_PAGE.encode(),
            base_url="https://books.toscrape.com/catalogue/page-1.html",
        )

        next_url = parser.get_next_page_url()

        assert next_url == "https://books.toscrape.com/catalogue/page-2.html"

    def test_returns_none_when_no_next_page(self) -> None:
        """Should return None when there's no next page.

        Reasoning: Last page of pagination has no next link.
        """
        parser = Parser(HTML_WITHOUT_NEXT_PAGE.encode(), base_url="")

        next_url = parser.get_next_page_url()

        assert next_url is None

    def test_resolves_relative_urls(self) -> None:
        """Relative URLs should be resolved against base_url.

        Reasoning: HTML often contains relative hrefs; we need
        absolute URLs to fetch the next page.
        """
        parser = Parser(HTML_WITH_NEXT_PAGE.encode(), base_url="https://example.com/books/")

        next_url = parser.get_next_page_url()

        assert next_url.startswith("https://example.com")


class TestParserEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_malformed_html_gracefully(self) -> None:
        """Malformed HTML should not crash the parser.

        Reasoning: Real-world HTML is often messy. BeautifulSoup
        handles this, but we should verify.
        """
        malformed = b"<html><body><ol><li><h3><a title='Test'>unclosed"
        parser = Parser(malformed, base_url="")

        # Should not raise - BeautifulSoup handles malformed HTML
        books = parser.parse()

        # May or may not extract the book depending on BS4's handling
        # The important thing is it doesn't crash
        assert isinstance(books, list)

    def test_empty_content_raises_error(self) -> None:
        """Empty HTML should raise ParseError.

        Reasoning: Empty response indicates a problem (blocked, error).
        """
        parser = Parser(b"", base_url="")

        with pytest.raises(ParseError):
            parser.parse()
