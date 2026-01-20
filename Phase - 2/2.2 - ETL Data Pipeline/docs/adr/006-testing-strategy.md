# ADR-006: Testing Strategy

## Status
Accepted

## Context
We need a testing strategy that:
- Validates pipeline correctness without relying on external services
- Tests each stage (Extract, Transform, Load) independently
- Verifies end-to-end behavior
- Runs fast enough for TDD workflow
- Teaches good testing practices

## Decision Drivers
- **Speed**: Tests should run in <30 seconds total
- **Independence**: No external service dependencies for unit tests
- **Coverage**: Test the things that matter, skip the trivial
- **Maintainability**: Tests should survive refactoring

## Options Considered

### Mocking External Services
| Option | Pros | Cons |
|--------|------|------|
| respx (httpx mock) | httpx-native, simple | httpx-specific |
| responses | Popular, well-documented | requests-specific |
| pytest-httpx | Fixture-based | Limited flexibility |
| VCR.py | Record/replay real calls | Cassettes can be stale |

### Test Data Strategy
| Option | Pros | Cons |
|--------|------|------|
| Fixtures (static) | Deterministic, fast | May not cover edge cases |
| Factories (dynamic) | Flexible, property-based | More complex |
| Sample data files | Inspectable, realistic | Must maintain |

### Integration Testing
| Option | Pros | Cons |
|--------|------|------|
| SQLite in-memory | Fast, no cleanup | Slightly different from production |
| Testcontainers | Real PostgreSQL | Slower, Docker required |
| Mocked database | Fast, isolated | Less realistic |

## Decision
**Behavior-focused tests** with proper test boundaries:

### Test Pyramid
```
                 ╱╲
                ╱  ╲
               ╱ E2E ╲          <- Few: Full pipeline runs
              ╱────────╲
             ╱Integration╲      <- Some: Stage combinations
            ╱──────────────╲
           ╱   Unit Tests   ╲   <- Many: Individual functions
          ╱────────────────────╲
```

### Unit Tests
- **Scope**: Single class or function
- **Mocking**: External I/O only (network, database)
- **Speed**: <100ms per test
- **Focus**: Behavior, not implementation

```python
# Good: Tests behavior
def test_cleaner_handles_missing_values():
    """Empty strings should be converted to None"""
    records = [{"name": "", "value": "123"}]
    result = cleaner.clean(records)
    assert result[0].name is None

# Bad: Tests implementation
def test_cleaner_calls_strip_method():
    """Should call str.strip()"""  # Who cares HOW?
```

### Integration Tests
- **Scope**: Multiple stages working together
- **Database**: SQLite in-memory
- **Network**: Mocked with respx
- **Focus**: Data flows correctly through stages

### End-to-End Tests
- **Scope**: Full pipeline with real (sample) data
- **Database**: SQLite file (cleaned up after)
- **Network**: Optionally real GitHub API (skipped in CI)
- **Focus**: Pipeline produces correct output

### Test Organization
```
tests/
├── conftest.py           # Shared fixtures
├── test_models.py        # Pydantic model validation
├── test_extractors.py    # Extractor unit tests
├── test_transformers.py  # Transformer unit tests
├── test_loaders.py       # Loader unit tests
└── test_pipeline_integration.py  # End-to-end
```

### Fixture Strategy
```python
# conftest.py
@pytest.fixture
def sample_records() -> list[dict]:
    """Minimal valid records for testing"""
    return [
        {"source": "github", "title": "Test", ...},
        ...
    ]

@pytest.fixture
def temp_db(tmp_path) -> Path:
    """Temporary database that's cleaned up"""
    return tmp_path / "test.db"
```

## Consequences

### Benefits
- Fast test suite (<30s)
- Tests survive refactoring
- Clear test boundaries
- No flaky network tests

### Costs & Tradeoffs
- Must maintain mock fixtures
- In-memory SQLite may differ from production
- Real API tests require network (optional)

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mock drift from reality | Medium | Medium | Periodic real API tests |
| Tests too tied to implementation | Medium | Medium | Review for behavior focus |
| Test data becomes stale | Low | Low | Fixtures versioned with code |

## Validation
- [ ] Metric: Full test suite runs in <30 seconds
- [ ] Metric: Coverage >80% on core modules
- [ ] Test: All tests pass without network access
- [ ] Review: Tests describe behavior, not implementation

## Testing Checklist
For each new feature:
- [ ] Unit test for happy path
- [ ] Unit test for error cases
- [ ] Integration test if crossing boundaries
- [ ] E2E test if user-facing behavior

## References
- [Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [respx Documentation](https://lundberg.github.io/respx/)
- [Property-Based Testing with Hypothesis](https://hypothesis.readthedocs.io/)
