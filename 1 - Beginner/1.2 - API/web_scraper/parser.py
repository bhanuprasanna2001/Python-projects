"""Parser for scraped HTML content."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from web_scraper.exceptions import ParseError
from web_scraper.models import Book

logger = logging.getLogger(__name__)


class Parser:
    """Parses HTML content and extracts structured data.

    Responsible only for parsing - no HTTP requests.
    """

    def __init__(self, content: bytes, base_url: str = "") -> None:
        """Initialize parser with HTML content.

        Args:
            content: Raw HTML bytes to parse
            base_url: Base URL for resolving relative links
        """
        self._base_url = base_url
        try:
            self._soup = BeautifulSoup(content, "html.parser")
        except Exception as e:
            raise ParseError(f"Invalid HTML content: {e}") from e

    def get_next_page_url(self) -> str | None:
        """Extract next page URL if pagination exists.

        Returns:
            Absolute URL of next page, or None if no next page
        """
        next_link = self._soup.select_one("li.next > a")
        if not next_link or "href" not in next_link.attrs:
            return None
        href = next_link["href"]
        # Handle case where href might be a list (multiple values)
        if isinstance(href, list):
            href = href[0] if href else ""
        return urljoin(self._base_url, str(href))

    def parse(self) -> list[Book]:
        """Parse page content and extract Book objects.

        Returns:
            List of parsed Book objects

        Raises:
            ParseError: If required elements are missing
        """
        try:
            ol_element = self._soup.find("ol")
            if not ol_element or not isinstance(ol_element, Tag):
                raise ParseError("Required <ol> element not found")

            li_results = ol_element.find_all("li")
            if not li_results:
                raise ParseError("No <li> elements found in <ol>")

            logger.info(f"Found {len(li_results)} books to parse")

            books: list[Book] = []
            for idx, li_result in enumerate(li_results, start=1):
                try:
                    title = self._extract_title(li_result)
                    price = self._extract_price(li_result)
                    rating = self._extract_rating(li_result)

                    books.append(Book(title=title, price=price, rating=rating))

                except Exception as e:
                    logger.warning(f"Failed to parse book {idx}: {e}")
                    continue

            return books

        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            raise ParseError(f"Parsing failed: {e}") from e

    def _extract_title(self, element: Tag) -> str:
        """Extract book title with error handling."""
        h3 = element.find("h3")
        if not h3:
            raise ParseError("Missing <h3> element")

        anchor = h3.find("a") if isinstance(h3, Tag) else None
        if not anchor or not isinstance(anchor, Tag) or "title" not in anchor.attrs:
            raise ParseError("Missing title attribute")

        title = anchor["title"]
        return str(title[0]) if isinstance(title, list) else str(title)

    def _extract_price(self, element: Tag) -> str:
        """Extract book price with error handling."""
        price_elem = element.find("p", class_="price_color")
        if not price_elem:
            raise ParseError("Missing price element")

        return str(price_elem.get_text().strip())

    def _extract_rating(self, element: Tag) -> str:
        """Extract book rating with error handling."""
        rating_elem = element.find("p", class_="star-rating")
        if not rating_elem or not isinstance(rating_elem, Tag) or "class" not in rating_elem.attrs:
            raise ParseError("Missing rating element")

        classes = rating_elem["class"]
        if not isinstance(classes, list) or len(classes) < 2:
            raise ParseError("Invalid rating format")

        return str(classes[-1])
