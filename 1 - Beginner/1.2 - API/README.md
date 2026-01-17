# Web Scraper

A multi-page web scraper with rate limiting, robots.txt compliance, and SQLite storage.

Built as a learning project to understand HTTP requests, HTML parsing, and async Python.

## What It Does

- Scrapes books from [books.toscrape.com](https://books.toscrape.com)
- Follows pagination automatically (multi-page crawling)
- Respects rate limits and robots.txt rules
- Saves data to SQLite (with deduplication) or CSV
- Rotates user agents to avoid blocking
- Retries failed requests with exponential backoff

## Installation

```bash
pip install -e ".[dev]"
```

Or just the requirements:
```bash
pip install requests beautifulsoup4 pyyaml aiohttp
```

## Quick Start

```bash
# Scrape 3 pages, print to console
python -m web_scraper --pages 3

# Save to SQLite database
python -m web_scraper --pages 5 --output sqlite

# Save to both CSV and SQLite
python -m web_scraper --pages 10 --output both

# Use async crawler (same result, different implementation)
python -m web_scraper --pages 3 --async

# Slower crawling (be polite to servers)
python -m web_scraper --pages 5 --delay 2.0

# Verbose logging
python -m web_scraper --pages 3 --verbose
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--pages, -p` | Number of pages to scrape (default: 1) |
| `--delay, -d` | Delay between requests in seconds (default: 1.0) |
| `--output, -o` | Where to save: `csv`, `sqlite`, `both`, or `none` |
| `--async` | Use async crawler instead of sync |
| `--verbose, -v` | Show debug logs |

## Project Structure

```
1.2 - API/
├── web_scraper/
│   ├── __init__.py
│   ├── __main__.py        # Entry point
│   ├── cli.py             # Command-line interface
│   ├── config.py          # YAML config loader
│   ├── crawler.py         # Orchestrates scraping
│   ├── scraper.py         # HTTP fetching
│   ├── parser.py          # HTML parsing
│   ├── models.py          # Book dataclass
│   ├── exceptions.py      # Custom exceptions
│   ├── async_scraper.py   # Async HTTP (aiohttp)
│   ├── async_crawler.py   # Async crawler
│   ├── storage/
│   │   ├── base.py        # Abstract storage interface
│   │   ├── csv_storage.py
│   │   └── sqlite_storage.py
│   └── utils/
│       ├── rate_limiter.py
│       ├── robots.py      # robots.txt checker
│       ├── user_agents.py # User agent rotation
│       ├── retry.py       # Retry decorator
│       └── logger.py
├── tests/
│   ├── test_integration.py  # End-to-end tests
│   ├── test_parser.py
│   ├── test_storage.py
│   ├── test_retry.py
│   └── ...
├── configs/
│   └── sites.yaml         # Site configuration
├── data/                  # Output files (gitignored)
├── Makefile
└── pyproject.toml
```

## How It Works

```
CLI → Crawler → Scraper → Parser → Storage
         ↓         ↓
    RateLimiter  UserAgents
         ↓
    RobotsChecker
```

1. **Crawler** orchestrates the whole process
2. **Scraper** fetches HTML with retry logic and rotating user agents
3. **Parser** extracts book data using BeautifulSoup
4. **Storage** saves to SQLite (deduplicates) or CSV

## Development

```bash
make help      # Show all commands
make check     # Run lint + format + typecheck + tests
make fix       # Auto-fix code style issues
make test      # Run tests with coverage
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=web_scraper

# Just integration tests
pytest tests/test_integration.py -v
```

## Why Sync vs Async?

This project has both sync (`crawler.py`) and async (`async_crawler.py`) implementations.

**When sync is fine:**
- Single domain scraping
- Rate limiting is the bottleneck (you're waiting anyway)
- Simpler code, easier to debug

**When async helps:**
- Scraping multiple domains simultaneously
- Fetching many detail pages at once
- High-volume scraping where network I/O matters

For this project, sync is sufficient. Async is included for learning purposes.

## Design Decisions

- **Retry with backoff**: Server errors (5xx) are retried; client errors (4xx) fail fast
- **Fail fast on DNS errors**: If the URL is wrong, don't waste time retrying
- **SQLite deduplication**: Uses `INSERT OR IGNORE` with unique constraint on title
- **Iterator pattern**: Crawler yields results page-by-page (memory efficient)
- **Composition over inheritance**: Crawler composes Scraper + Parser + utilities

## License

MIT
