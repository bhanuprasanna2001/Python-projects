# ADR-003: Transformation Framework

## Status
Accepted

## Context
We need to choose how to implement data transformations. The framework must:
- Handle cleaning, normalization, and validation
- Work with different data shapes from multiple sources
- Be efficient for moderate data volumes (thousands of records)
- Support composable transformations

## Decision Drivers
- **Performance**: Should handle 10k+ records efficiently
- **Learning value**: Modern tool that's worth learning
- **Flexibility**: Support diverse transformation logic
- **Debugging**: Easy to understand what transformations did

## Options Considered

### Option 1: Polars
- **Pros**: 
  - 10-30x faster than Pandas
  - Rust-based, memory efficient
  - Modern, growing adoption
  - Lazy evaluation for optimization
- **Cons**: 
  - Newer API, smaller ecosystem
  - Different from Pandas (learning curve)
- **Cost**: Medium learning, low runtime

### Option 2: Pandas
- **Pros**: 
  - Ubiquitous, massive ecosystem
  - Excellent documentation
  - Known by most data engineers
- **Cons**: 
  - Slower, higher memory usage
  - Some API inconsistencies
- **Cost**: Low learning, medium runtime

### Option 3: Pure Python + Pydantic
- **Pros**: 
  - No dataframe dependencies
  - Explicit, easy to debug
  - Type-safe with Pydantic
- **Cons**: 
  - Verbose for complex transforms
  - No vectorized operations
- **Cost**: Low learning, high runtime for large data

### Option 4: DuckDB (SQL Transforms)
- **Pros**: 
  - SQL is universal
  - Very fast analytical queries
  - Works on files directly
- **Cons**: 
  - Less natural for procedural transforms
  - Another tool to integrate
- **Cost**: Low learning, low runtime

## Decision
**Polars for parsing, Pydantic for validation**, with transformation logic in Python classes.

### Rationale
1. **Polars for I/O**: Fast CSV/JSON parsing, type inference, null handling
2. **Pydantic for models**: Type validation, serialization, IDE support
3. **Python classes for logic**: Explicit, testable transformation steps
4. **Career investment**: Polars adoption is accelerating; worth learning now
5. **Hybrid approach**: Use the right tool for each job

### Architecture
```
CSV/API → Polars (parse) → Pydantic Models → Transform Classes → TransformedRecord
```

## Consequences

### Benefits
- Fast data loading with Polars
- Type-safe models with Pydantic
- Testable transformation logic
- Modern tooling skills gained

### Costs & Tradeoffs
- Must learn Polars API (different from Pandas)
- Pydantic adds some overhead vs raw dicts
- More moving parts than pure Pandas approach

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Polars API changes | Low | Low | Pin version, follow changelog |
| Complex transforms need Pandas | Low | Low | Can use Pandas for edge cases |
| Team unfamiliar with Polars | Medium | Low | Good documentation, familiar concepts |

## Validation
- [ ] Metric: Transform 10,000 records in <5 seconds
- [ ] Metric: Memory usage stays under 500MB for 100k records
- [ ] Test: All transformed records pass Pydantic validation
- [ ] Test: Transformations are deterministic (same input → same output)

## References
- [Polars User Guide](https://pola-rs.github.io/polars-book/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [Polars vs Pandas Benchmark](https://www.pola.rs/benchmarks.html)
