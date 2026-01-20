# Project 8: Testing

## 🎯 Learning Objectives
- Write effective unit tests with pytest
- Use fixtures for test setup/teardown
- Mock external dependencies
- Write integration tests
- Measure test coverage

## 📁 Project Structure
```
08-testing/
├── src/
│   ├── calculator.py     # Simple module to test
│   ├── user_service.py   # Service with dependencies
│   └── api_client.py     # External API client
├── tests/
│   ├── conftest.py       # Shared fixtures
│   ├── test_calculator.py
│   ├── test_user_service.py
│   ├── test_api_client.py
│   └── integration/
│       └── test_full_flow.py
├── pytest.ini            # Pytest configuration
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_calculator.py

# Run specific test
pytest tests/test_calculator.py::test_add -v
```

## 📚 Topics Covered
- pytest basics
- Fixtures and parametrization
- Mocking with unittest.mock
- Integration testing
- Test coverage
- Test organization
