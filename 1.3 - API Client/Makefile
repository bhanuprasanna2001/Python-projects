# =============================================================================
# GitHub Client Library - Makefile for Development Tasks
# =============================================================================
# Usage:
#   make help     - Show available commands
#   make check    - Run all quality checks
#   make fix      - Auto-fix all fixable issues
#   make test     - Run tests with coverage
# =============================================================================

.PHONY: help install lint format typecheck security test test-unit test-integration check fix clean

# Default target
help:
	@echo ""
	@echo "GitHub Client Library - Development Commands"
	@echo "============================================="
	@echo ""
	@echo "Quality Checks:"
	@echo "  make lint            - Run Ruff linter"
	@echo "  make format          - Check code formatting"
	@echo "  make typecheck       - Run mypy type checking"
	@echo "  make security        - Run Bandit"
	@echo "  make test            - Run all tests with coverage"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration- Run integration tests only"
	@echo "  make check           - Run ALL quality checks"
	@echo ""
	@echo "Auto-Fix:"
	@echo "  make fix             - Auto-fix lint + format issues"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install all dependencies"
	@echo "  make clean           - Remove cache files"
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
	ruff check github_client tests
	@echo "✓ Linting passed\n"

format:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Checking Code Format"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format --check github_client tests
	@echo "✓ Format check passed\n"

fix:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Auto-fixing Code Issues"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format github_client tests
	ruff check --fix github_client tests
	@echo "✓ Code fixed\n"

# =============================================================================
# Type Checking
# =============================================================================
typecheck:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running mypy Type Checker"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	mypy github_client
	@echo "✓ Type checking passed\n"

# =============================================================================
# Security
# =============================================================================
security:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Bandit Security Scan"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	bandit -r github_client -c pyproject.toml
	@echo "✓ Security checks passed\n"

# =============================================================================
# Testing
# =============================================================================
test:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running All Tests with Coverage"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	pytest --cov=github_client --cov-report=term-missing --cov-report=html
	@echo "✓ Tests passed\n"

test-unit:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Unit Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	pytest tests/unit -v
	@echo "✓ Unit tests passed\n"

test-integration:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Integration Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	pytest tests/integration -v -m integration
	@echo "✓ Integration tests passed\n"

# =============================================================================
# Combined Checks
# =============================================================================
check: lint format typecheck security test
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ All checks passed!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# =============================================================================
# Cleanup
# =============================================================================
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov github_client.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned\n"
