"""Parser for the Scrapped Response"""

from __future__ import annotations

import logging
from bs4 import BeautifulSoup

from web_scraper.exceptions import ParseError

logger = logging.getLogger(__name__)


class Parser:
    """Handles parsing the scrapped response
    
    This class uses the Beautiful Soap library for parsing.
    """
    
    def __init__(self, response_content: bytes) -> None:
        """Initialize Parser"""
        self.response_content = response_content
        
        try:
            self.soup = BeautifulSoup(self.response_content, "html.parser")
            logger.debug("Initialized BeautifulSoup parser")
        except Exception as e:
            logger.error(f"Failed to initialize parser: {e}")
            raise ParseError(f"Invalid HTML content: {e}") from e
        
    def parse(self) -> None:
        """Parse response text with bs4 selectors.
        
        Raises:
            ParseError: If parsing fails or required elements are missing
        """
        try:
            ol_element = self.soup.find("ol")
            if not ol_element:
                raise ParseError("Required <ol> element not found")
            
            li_results = ol_element.find_all("li")
            if not li_results:
                raise ParseError("No <li> elements found in <ol>")
            
            logger.info(f"Found {len(li_results)} books to parse")
            
            for idx, li_result in enumerate(li_results, start=1):
                try:
                    title = self._extract_title(li_result)
                    price = self._extract_price(li_result)
                    rating = self._extract_rating(li_result)
                    
                    print(f"Book Title:  {title}")
                    print(f"Book Price:  {price}")
                    print(f"Book star :  {rating}")
                    print()
                    
                except Exception as e:
                    logger.warning(f"Failed to parse book {idx}: {e}")
                    continue
                    
        except ParseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            raise ParseError(f"Parsing failed: {e}") from e
    
    def _extract_title(self, element) -> str:
        """Extract book title with error handling."""
        h3 = element.find("h3")
        if not h3:
            raise ParseError("Missing <h3> element")
        
        anchor = h3.find("a")
        if not anchor or "title" not in anchor.attrs:
            raise ParseError("Missing title attribute")
        
        return anchor["title"]
    
    def _extract_price(self, element) -> str:
        """Extract book price with error handling."""
        price_elem = element.find("p", class_="price_color")
        if not price_elem:
            raise ParseError("Missing price element")
        
        return price_elem.get_text().strip()
    
    def _extract_rating(self, element) -> str:
        """Extract book rating with error handling."""
        rating_elem = element.find("p", class_="star-rating")
        if not rating_elem or "class" not in rating_elem.attrs:
            raise ParseError("Missing rating element")
        
        classes = rating_elem["class"]
        if len(classes) < 2:
            raise ParseError("Invalid rating format")
        
        return classes[-1]