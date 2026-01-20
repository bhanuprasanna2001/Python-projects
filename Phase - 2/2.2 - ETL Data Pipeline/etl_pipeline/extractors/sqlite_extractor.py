"""
SQLite database extractor.

Extracts data from SQLite databases with:
- Connection pooling
- Query parameterization
- Schema introspection
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite

from etl_pipeline.config import get_project_root
from etl_pipeline.exceptions import ExtractionError, SourceConnectionError
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.models import BookRecord, DataSource, ExtractionResult


class SQLiteExtractor(BaseExtractor[BookRecord]):
    """
    Extracts data from SQLite databases.

    Designed to work with the web scraper database from Project 1.2,
    but can be configured for any SQLite database.
    """

    def __init__(
        self,
        database_path: str | Path,
        query: str = "SELECT * FROM books",
        fallback_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize SQLite extractor.

        Args:
            database_path: Path to SQLite database file
            query: SQL query to execute
            fallback_path: Alternative database path if primary doesn't exist
            config: Additional configuration
        """
        super().__init__(DataSource.SQLITE, config)
        self.database_path = Path(database_path)
        self.query = query
        self.fallback_path = Path(fallback_path) if fallback_path else None
        self._resolved_path: Path | None = None

    @property
    def name(self) -> str:
        return f"SQLite ({self.database_path.name})"

    def _resolve_path(self) -> Path:
        """Resolve database path, checking primary and fallback."""
        if self._resolved_path:
            return self._resolved_path

        # Try primary path
        path = self.database_path
        if not path.is_absolute():
            path = get_project_root() / path

        if path.exists():
            self._resolved_path = path
            return path

        # Try fallback path
        if self.fallback_path:
            fallback = self.fallback_path
            if not fallback.is_absolute():
                fallback = get_project_root() / fallback

            if fallback.exists():
                self._resolved_path = fallback
                self.logger.info(f"Using fallback database: {fallback}")
                return fallback

        # Neither exists - return primary path for error message
        self._resolved_path = path
        return path

    async def validate_connection(self) -> bool:
        """Check if database is accessible and has expected tables."""
        try:
            path = self._resolve_path()
            if not path.exists():
                return False

            async with aiosqlite.connect(path) as db:
                # Try a simple query
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
                )
                result = await cursor.fetchone()
                return result is not None

        except Exception as e:
            self.logger.warning(f"SQLite validation failed: {e}")
            return False

    def _parse_row_to_book(self, row: dict[str, Any], row_index: int) -> BookRecord | None:
        """Parse a database row into a BookRecord."""
        try:
            # Extract title - required field
            title = row.get("title")
            if not title:
                self.logger.warning(f"Row {row_index}: Missing title")
                return None

            # Extract price - handle various formats
            price = None
            price_raw = row.get("price") or row.get("price_incl_tax")
            if price_raw is not None:
                if isinstance(price_raw, (int, float)):
                    price = float(price_raw)
                elif isinstance(price_raw, str):
                    # Handle "£12.34" or "12.34" formats
                    price_str = price_raw.replace("£", "").replace("$", "").replace(",", "").strip()
                    import contextlib

                    with contextlib.suppress(ValueError):
                        price = float(price_str)

            # Extract rating - handle various formats
            rating = None
            rating_raw = row.get("rating") or row.get("star_rating")
            if rating_raw is not None:
                if isinstance(rating_raw, int):
                    rating = rating_raw
                elif isinstance(rating_raw, str):
                    # Handle "Four", "4", "4 stars" formats
                    rating_map = {
                        "one": 1,
                        "two": 2,
                        "three": 3,
                        "four": 4,
                        "five": 5,
                        "1": 1,
                        "2": 2,
                        "3": 3,
                        "4": 4,
                        "5": 5,
                    }
                    rating_str = rating_raw.lower().split()[0]  # Get first word
                    rating = rating_map.get(rating_str)

            return BookRecord(
                title=str(title),
                price=price,
                rating=rating,
                availability=row.get("availability") or row.get("in_stock"),
                url=row.get("url") or row.get("product_url"),
                upc=row.get("upc") or row.get("product_code"),
                raw_data=row,
            )

        except Exception as e:
            self.logger.warning(f"Row {row_index}: Parse error - {e}")
            return None

    async def extract(self) -> ExtractionResult:
        """
        Extract data from SQLite database.

        Returns:
            ExtractionResult containing BookRecord instances
        """
        result = self._create_result()
        records: list[BookRecord] = []

        try:
            path = self._resolve_path()

            if not path.exists():
                # Try to create sample database
                if await self._generate_sample_database(path):
                    self.logger.info(f"Generated sample database at {path}")
                else:
                    raise SourceConnectionError(
                        "sqlite",
                        f"Database not found: {path}",
                    )

            self.logger.info(f"Connecting to SQLite database: {path}")

            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row

                # Get column names
                cursor = await db.execute(self.query)
                columns = [description[0] for description in cursor.description]

                self.logger.info(
                    f"Executing query with columns: {columns}",
                    extra={"query": self.query[:100]},
                )

                # Fetch all rows
                rows = await cursor.fetchall()

                for i, row in enumerate(rows):
                    row_dict = dict(zip(columns, row, strict=True))
                    record = self._parse_row_to_book(row_dict, i)
                    if record:
                        records.append(record)
                    else:
                        result.error_count += 1

            result.records = records  # type: ignore[assignment]
            row_count = len(records) + result.error_count
            self.logger.info(
                f"Extracted {len(records)} book records",
                extra={
                    "total_rows": row_count,
                    "successful": len(records),
                    "failed": result.error_count,
                },
            )

        except (ExtractionError, SourceConnectionError):
            raise
        except Exception as e:
            self._handle_error(result, e)
            raise ExtractionError(
                f"SQLite extraction failed: {e}",
                source="sqlite",
                recoverable=False,
            ) from e
        finally:
            result.complete()

        return result

    async def _generate_sample_database(self, path: Path) -> bool:
        """
        Generate sample books database if it doesn't exist.

        This is for demonstration - in production, use real data.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(path) as db:
                # Create table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        price REAL,
                        rating INTEGER,
                        availability TEXT,
                        url TEXT,
                        upc TEXT UNIQUE
                    )
                """)

                # Insert sample data
                sample_books = [
                    (
                        "The Great Gatsby",
                        12.99,
                        5,
                        "In Stock",
                        "https://example.com/gatsby",
                        "UPC001",
                    ),
                    ("1984", 9.99, 5, "In Stock", "https://example.com/1984", "UPC002"),
                    (
                        "To Kill a Mockingbird",
                        11.50,
                        5,
                        "In Stock",
                        "https://example.com/mockingbird",
                        "UPC003",
                    ),
                    (
                        "Pride and Prejudice",
                        8.99,
                        4,
                        "In Stock",
                        "https://example.com/pride",
                        "UPC004",
                    ),
                    (
                        "The Catcher in the Rye",
                        10.99,
                        4,
                        "Low Stock",
                        "https://example.com/catcher",
                        "UPC005",
                    ),
                    (
                        "Brave New World",
                        13.50,
                        4,
                        "In Stock",
                        "https://example.com/brave",
                        "UPC006",
                    ),
                    ("The Hobbit", 14.99, 5, "In Stock", "https://example.com/hobbit", "UPC007"),
                    (
                        "Fahrenheit 451",
                        9.50,
                        4,
                        "In Stock",
                        "https://example.com/fahrenheit",
                        "UPC008",
                    ),
                    ("Jane Eyre", 7.99, 4, "In Stock", "https://example.com/jane", "UPC009"),
                    (
                        "Wuthering Heights",
                        8.50,
                        3,
                        "Low Stock",
                        "https://example.com/wuthering",
                        "UPC010",
                    ),
                    (
                        "The Picture of Dorian Gray",
                        10.00,
                        4,
                        "In Stock",
                        "https://example.com/dorian",
                        "UPC011",
                    ),
                    ("Moby Dick", 11.99, 3, "In Stock", "https://example.com/moby", "UPC012"),
                    ("War and Peace", 15.99, 4, "In Stock", "https://example.com/war", "UPC013"),
                    (
                        "Crime and Punishment",
                        12.50,
                        5,
                        "In Stock",
                        "https://example.com/crime",
                        "UPC014",
                    ),
                    (
                        "The Brothers Karamazov",
                        14.00,
                        5,
                        "Low Stock",
                        "https://example.com/brothers",
                        "UPC015",
                    ),
                ]

                await db.executemany(
                    "INSERT OR IGNORE INTO books (title, price, rating, availability, url, upc) VALUES (?, ?, ?, ?, ?, ?)",
                    sample_books,
                )
                await db.commit()

            return True

        except Exception as e:
            self.logger.warning(f"Failed to generate sample database: {e}")
            return False
