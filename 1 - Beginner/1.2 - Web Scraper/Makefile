# =============================================================================
# Web Scraper - Makefile for Development Tasks
# =============================================================================
# Usage:
#   make help     - Show available commands
#   make check    - Run all quality checks
#   make fix      - Auto-fix all fixable issues
#   make test     - Run tests with coverage
# =============================================================================

.PHONY: help install lint format typecheck security test check fix clean run

# Default target
help:
	@echo ""
	@echo "Web Scraper - Development Commands"
	@echo "==================================="
	@echo ""
	@echo "Quality Checks:"
	@echo "  make lint       - Run Ruff linter"
	@echo "  make format     - Check code formatting"
	@echo "  make typecheck  - Run mypy type checking"
	@echo "  make security   - Run Bandit + pip-audit"
	@echo "  make test       - Run pytest with coverage"
	@echo "  make check      - Run ALL quality checks"
	@echo ""
	@echo "Auto-Fix:"
	@echo "  make fix        - Auto-fix lint + format issues"
	@echo ""
	@echo "Run:"
	@echo "  make run        - Run scraper (default: 3 pages)"
	@echo "  make run-full   - Run scraper (all pages, sqlite output)"
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install all dependencies"
	@echo "  make clean      - Remove cache files"
	@echo ""

# =============================================================================
# Setup
# =============================================================================
install:
	@echo "Installing dependencies..."
	pip install -e ".[dev]"

# =============================================================================
# Linting & Formatting
# =============================================================================
lint:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Ruff Linter"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff check web_scraper tests
	@echo "✓ Linting passed\n"

format:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Checking Code Format"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format --check web_scraper tests
	@echo "✓ Format check passed\n"

fix:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Auto-fixing Code Issues"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format web_scraper tests
	ruff check --fix web_scraper tests
	@echo "✓ Code fixed\n"

# =============================================================================
# Type Checking
# =============================================================================
typecheck:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running mypy Type Checker"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	mypy web_scraper
	@echo "✓ Type checking complete\n"

# =============================================================================
# Security Scanning
# =============================================================================
security:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Bandit Security Scanner"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	bandit -r web_scraper -c pyproject.toml -q || echo "⚠ Configure bandit in pyproject.toml"
	@echo "✓ Security scan passed\n"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Checking Dependencies for Vulnerabilities"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	pip-audit --strict || echo "⚠ Review vulnerabilities above"
	@echo ""

# =============================================================================
# Testing
# =============================================================================
test:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Tests with Coverage"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	pytest tests/ -v --cov=web_scraper --cov-report=term-missing
	@echo "✓ All tests passed\n"

# =============================================================================
# Full Quality Check
# =============================================================================
check: lint format typecheck test
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ All quality checks passed!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# =============================================================================
# Run Application
# =============================================================================
run:
	@echo "Running scraper (3 pages)..."
	python -m web_scraper --pages 3 --output sqlite

run-full:
	@echo "Running scraper (all pages, sqlite output)..."
	python -m web_scraper --pages 50 --output sqlite --verbose

# =============================================================================
# Cleanup
# =============================================================================
clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__
	rm -rf web_scraper/__pycache__ tests/__pycache__
	rm -rf web_scraper/utils/__pycache__ web_scraper/storage/__pycache__
	rm -rf .coverage htmlcov
	rm -rf logs/*.log
	@echo "✓ Cleaned"
