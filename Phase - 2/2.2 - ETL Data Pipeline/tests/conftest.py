"""Test fixtures and configuration."""

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from etl_pipeline.config import Settings
from etl_pipeline.models import (
    BookRecord,
    DataSource,
    ExtractedRecord,
    GitHubRepository,
    TransformedRecord,
    WeatherRecord,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_settings(tmp_data_dir: Path) -> Settings:
    """Create test settings with temporary paths."""
    return Settings(
        log_level="DEBUG",
        pipeline={"name": "test-pipeline", "description": "Test pipeline"},
        sources={
            "github": {"enabled": False},  # Disable to avoid API calls
            "weather": {"enabled": True, "path": str(tmp_data_dir / "weather.csv")},
            "books": {"enabled": True, "fallback_path": str(tmp_data_dir / "books.db")},
        },
        loading={
            "target": "sqlite",
            "sqlite": {"path": str(tmp_data_dir / "output.db")},
        },
    )


# --- Sample Data Fixtures ---


@pytest.fixture
def sample_github_repo() -> GitHubRepository:
    """Create sample GitHub repository record."""
    return GitHubRepository(
        repo_id=12345,
        name="test-repo",
        full_name="test-user/test-repo",
        description="A test repository for ETL pipeline",
        html_url="https://github.com/test-user/test-repo",
        language="Python",
        stargazers_count=100,
        forks_count=25,
        open_issues_count=5,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2026, 1, 15),
        topics=["python", "etl", "testing"],
        owner_login="test-user",
        raw_data={},
    )


@pytest.fixture
def sample_weather_record() -> WeatherRecord:
    """Create sample weather record."""
    return WeatherRecord(
        date=datetime(2026, 1, 20),
        location="Berlin",
        temperature_celsius=5.5,
        humidity_percent=75.0,
        precipitation_mm=2.5,
        wind_speed_kmh=15.0,
        conditions="Cloudy",
        raw_data={},
    )


@pytest.fixture
def sample_book_record() -> BookRecord:
    """Create sample book record."""
    return BookRecord(
        title="The Great Gatsby",
        price=12.99,
        rating=5,
        availability="In Stock",
        url="https://example.com/gatsby",
        upc="UPC001",
        raw_data={},
    )


@pytest.fixture
def sample_transformed_record() -> TransformedRecord:
    """Create sample transformed record."""
    return TransformedRecord(
        source=DataSource.GITHUB,
        source_id="12345",
        title="test-user/test-repo",
        description="A test repository",
        url="https://github.com/test-user/test-repo",
        category="Python",
        numeric_value_1=100.0,
        numeric_value_2=25.0,
        source_created_at=datetime(2024, 1, 1),
        source_updated_at=datetime(2026, 1, 15),
        extracted_at=datetime(2026, 1, 20),
        tags=["python", "etl"],
        extra_data={"owner": "test-user"},
    )


@pytest.fixture
def multiple_extracted_records(
    sample_github_repo: GitHubRepository,
    sample_weather_record: WeatherRecord,
    sample_book_record: BookRecord,
) -> list[ExtractedRecord]:
    """Create list of various extracted records."""
    return [sample_github_repo, sample_weather_record, sample_book_record]


@pytest.fixture
def sample_csv_file(tmp_data_dir: Path) -> Path:
    """Create sample CSV file for testing."""
    csv_path = tmp_data_dir / "weather.csv"
    csv_content = """date,location,temperature,humidity,precipitation,wind_speed,conditions
2026-01-01,Berlin,5.5,75,2.5,15,Cloudy
2026-01-02,Berlin,3.0,80,5.0,20,Rainy
2026-01-03,Munich,2.0,70,0.0,10,Sunny
2026-01-04,Hamburg,-1.0,85,10.0,30,Stormy
2026-01-05,Frankfurt,4.5,72,1.0,12,Partly Cloudy
"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def sample_sqlite_db(tmp_data_dir: Path) -> Path:
    """Create sample SQLite database for testing."""
    import sqlite3

    db_path = tmp_data_dir / "books.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL,
            rating INTEGER,
            availability TEXT,
            url TEXT,
            upc TEXT UNIQUE
        )
    """)

    cursor.executemany(
        "INSERT INTO books (title, price, rating, availability, url, upc) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("The Great Gatsby", 12.99, 5, "In Stock", "https://example.com/gatsby", "UPC001"),
            ("1984", 9.99, 5, "In Stock", "https://example.com/1984", "UPC002"),
            (
                "To Kill a Mockingbird",
                11.50,
                5,
                "Low Stock",
                "https://example.com/mockingbird",
                "UPC003",
            ),
        ],
    )

    conn.commit()
    conn.close()

    return db_path
