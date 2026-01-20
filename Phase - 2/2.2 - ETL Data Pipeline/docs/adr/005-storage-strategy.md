# ADR-005: Storage and State Management

## Status
Accepted

## Context
The pipeline needs to store:
1. **Output data**: Transformed records
2. **Pipeline state**: Job runs, stage results, metrics
3. **Intermediate data**: Raw extracts (optional, for replay)
4. **Configuration**: Pipeline settings

We need to decide where and how to store each type.

## Decision Drivers
- **Simplicity**: Minimal infrastructure for learning project
- **Durability**: Data shouldn't be lost on restart
- **Query-ability**: Should be able to inspect stored data
- **Production relevance**: Patterns should transfer to real systems

## Options Considered

### Output Data Storage
| Option | Pros | Cons |
|--------|------|------|
| PostgreSQL | Production-grade, full SQL | Requires Docker/infra |
| SQLite | Zero setup, file-based | Limited concurrency |
| DuckDB | Fast analytics, Parquet support | Newer, less tooling |

### Pipeline State Storage
| Option | Pros | Cons |
|--------|------|------|
| Same DB as output | Single source of truth | Mixes concerns |
| Separate SQLite | Isolated, portable | Another database |
| JSON files | Simple, human-readable | No querying |

### Intermediate Data
| Option | Pros | Cons |
|--------|------|------|
| Filesystem (JSON/CSV) | Simple, inspectable | Manual cleanup |
| Memory only | Fast, simple | Lost on crash |
| Blob storage | Scalable | Infrastructure |

## Decision
**SQLite for everything** in the learning project, with PostgreSQL as optional upgrade path.

### Storage Layout
```
data/
├── raw/                    # Intermediate: timestamped extraction results
│   ├── 2026-01-20/
│   │   ├── github.json
│   │   ├── weather.csv
│   │   └── books.json
│   └── ...
├── output/
│   └── etl_output.db       # Main output database
└── metrics/
    └── pipeline_metrics.json
```

### Database Schema
```sql
-- Output: Transformed records
etl_records (
    id, source, source_id, source_identifier,
    title, description, url, category,
    numeric_value_1, numeric_value_2,
    extracted_at, transformed_at, loaded_at,
    tags, extra_data, version
)

-- History: Record versions (for audit)
etl_records_history (
    history_id, record_id, ..., archived_at
)

-- State: Pipeline runs
pipeline_runs (
    run_id, pipeline_name, status,
    started_at, completed_at,
    total_extracted, total_transformed, total_loaded,
    error_count, config_snapshot
)
```

### Rationale
1. **SQLite first**: Zero infrastructure, immediate productivity
2. **Single output database**: Unified querying, simpler operations
3. **Filesystem for raw data**: Human-inspectable, cheap storage
4. **PostgreSQL ready**: Schema designed to work with Postgres (via SQLAlchemy)

## Consequences

### Benefits
- Zero infrastructure to get started
- Easy backup (copy files)
- Can inspect data with any SQLite tool
- Path to PostgreSQL is clear

### Costs & Tradeoffs
- SQLite limited to single writer
- No advanced PostgreSQL features (yet)
- Must manage file cleanup

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQLite file corruption | Low | High | Regular backups, WAL mode |
| Raw data fills disk | Medium | Medium | Retention policy, cleanup script |
| Need PostgreSQL features | Medium | Low | Schema is compatible, easy migration |

## Validation
- [ ] Test: Data survives pipeline restart
- [ ] Test: Can query records by source, date
- [ ] Test: History table captures updates
- [ ] Metric: Database size tracked over time
- [ ] Runbook: Migration to PostgreSQL documented

## References
- [SQLite Best Practices](https://www.sqlite.org/whentouse.html)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Data Versioning Patterns](https://www.red-gate.com/simple-talk/databases/sql-server/database-administration-sql-server/database-design-versioning/)
