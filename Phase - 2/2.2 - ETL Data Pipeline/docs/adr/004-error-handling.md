# ADR-004: Error Handling Philosophy

## Status
Accepted

## Context
ETL pipelines must handle various failure modes:
- Network errors during extraction
- Malformed data during transformation
- Database errors during loading
- Partial failures (some records succeed, some fail)

We need a consistent strategy that balances data integrity with pipeline resilience.

## Decision Drivers
- **Data integrity**: Invalid data shouldn't corrupt the database
- **Resilience**: Transient errors shouldn't stop the entire pipeline
- **Visibility**: Errors must be logged and traceable
- **Recoverability**: Should be able to resume from failures

## Options Considered

### Extraction Error Strategies
| Strategy | Behavior | Use When |
|----------|----------|----------|
| Fail-fast | Stop on first error | Source is critical, no partial data |
| Retry with backoff | Attempt recovery | Transient errors (network) |
| Skip and continue | Log error, proceed | Non-critical sources |

### Transformation Error Strategies
| Strategy | Behavior | Use When |
|----------|----------|----------|
| Fail-fast | Stop pipeline | Schema errors, critical validation |
| Dead-letter | Log bad records, continue | Malformed data is common |
| Impute defaults | Fill missing values | Missing ≠ Invalid |

### Loading Error Strategies
| Strategy | Behavior | Use When |
|----------|----------|----------|
| Transaction rollback | All or nothing | Data integrity paramount |
| Skip bad records | Log failures, continue | Partial success acceptable |
| Retry batch | Re-attempt failed batch | Transient DB issues |

## Decision
**Layered error handling** with different strategies per stage:

### Extraction
- **Strategy**: Retry with exponential backoff
- **Reason**: Network errors are transient; APIs have rate limits
- **Config**: 3 retries, 1s base delay, 60s max delay
- **On final failure**: Log, mark source as failed, continue other sources

### Transformation
- **Strategy**: Dead-letter queue (log and continue)
- **Reason**: Bad records shouldn't block good ones
- **Tracking**: Count dropped records, log reasons
- **Quality gate**: Fail if >20% records invalid

### Loading
- **Strategy**: Per-record with batch transactions
- **Reason**: One bad record shouldn't rollback entire batch
- **Tracking**: Count inserts, updates, failures
- **On failure**: Log record, continue batch

### Error Hierarchy
```python
ETLError (base)
├── ExtractionError
│   ├── SourceConnectionError (retry)
│   ├── RateLimitError (wait and retry)
│   └── DataValidationError (skip record)
├── TransformationError
│   ├── SchemaError (fail pipeline)
│   └── DataQualityError (warn or fail based on threshold)
└── LoadingError
    ├── DatabaseConnectionError (retry)
    └── IntegrityError (skip record)
```

## Consequences

### Benefits
- Pipeline continues despite partial failures
- Transient errors recovered automatically
- Full visibility into what failed and why
- Data quality protected by thresholds

### Costs & Tradeoffs
- More complex error handling code
- Must monitor error rates (could silently degrade)
- Retry delays extend pipeline runtime

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Silent data loss | Medium | High | Quality metrics, alerts on high error rates |
| Infinite retry loops | Low | Medium | Max retries + circuit breaker pattern |
| Error logs overwhelming | Medium | Low | Structured logging, aggregation |

## Validation
- [ ] Test: Network error triggers retry with backoff
- [ ] Test: Invalid record logged, pipeline continues
- [ ] Test: Database transaction rolls back on integrity error
- [ ] Metric: Error rate tracked per stage
- [ ] Alert: Fires when error rate > 10%

## References
- [Retry Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Dead Letter Queue](https://en.wikipedia.org/wiki/Dead_letter_queue)
