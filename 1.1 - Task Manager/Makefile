# =============================================================================
# Task Manager - Makefile for Development Tasks
# =============================================================================
# Usage:
#   make help     - Show available commands
#   make check    - Run all quality checks
#   make fix      - Auto-fix all fixable issues
#   make test     - Run tests with coverage
# =============================================================================

.PHONY: help install lint format typecheck security test check fix clean

# Default target
help:
	@echo ""
	@echo "Task Manager - Development Commands"
	@echo "===================================="
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
	ruff check task_manager tests
	@echo "✓ Linting passed\n"

format:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Checking Code Format"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format --check task_manager tests
	@echo "✓ Format check passed\n"

fix:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Auto-fixing Code Issues"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	ruff format task_manager tests
	ruff check --fix task_manager tests
	@echo "✓ Code fixed\n"

# =============================================================================
# Type Checking
# =============================================================================
typecheck:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running mypy Type Checker"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	mypy task_manager
	@echo "✓ Type checking passed\n"

# =============================================================================
# Security Scanning
# =============================================================================
security:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "▶ Running Bandit Security Scanner"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	bandit -r task_manager -c pyproject.toml -q
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
	pytest tests/ -v --cov=task_manager --cov-report=term-missing
	@echo "✓ All tests passed\n"

# =============================================================================
# Full Quality Check
# =============================================================================
check: lint format typecheck security test
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ All quality checks passed!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# =============================================================================
# Cleanup
# =============================================================================
clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__
	rm -rf task_manager/__pycache__ tests/__pycache__
	rm -rf .coverage htmlcov
	@echo "✓ Cleaned"
