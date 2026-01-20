# ADR-002: Data Source Selection

## Status
Accepted

## Context
We need to select 3 data sources that:
- Demonstrate different extraction patterns (API, file, database)
- Are reliable and available for testing
- Provide enough data variety for transformation practice
- Ideally connect to previous Phase 1 projects

## Decision Drivers
- **Learning diversity**: Each source should teach different skills
- **Reliability**: Sources must be stable for consistent testing
- **Project coherence**: Building on Phase 1 work creates continuity
- **Real-world relevance**: Patterns should transfer to production scenarios

## Options Considered

### API Sources
| Option | Pros | Cons |
|--------|------|------|
| GitHub API | Free, well-documented, used in Phase 1 | Rate limited |
| OpenWeather API | Real data, simple | Requires API key |
| JSONPlaceholder | Always available, no auth | Fake data |

### File Sources
| Option | Pros | Cons |
|--------|------|------|
| Local CSV | Full control, no network | Must create/find data |
| Remote CSV | Real data | Network dependency |
| Kaggle datasets | Rich, real data | Download complexity |

### Database Sources
| Option | Pros | Cons |
|--------|------|------|
| Phase 1 Web Scraper DB | Project continuity | May not exist |
| Phase 1 Task Manager DB | Project continuity | Simple schema |
| Sample SQLite | Consistent testing | Not "real" |

## Decision
Selected sources:

1. **GitHub API** (API Source)
   - Reuses patterns from Phase 1.3 (API Client)
   - Demonstrates: Rate limiting, pagination, authentication, JSON parsing
   - Data: Repository metadata (stars, forks, topics)

2. **CSV Files** (File Source)
   - Weather data (sample or public dataset)
   - Demonstrates: Schema inference, type coercion, missing value handling
   - Data: Temperature, humidity, location, conditions

3. **SQLite Database** (Database Source)
   - Phase 1.2 Web Scraper output (books.db) with fallback
   - Demonstrates: SQL extraction, connection management
   - Data: Book titles, prices, ratings

### Rationale
1. **Phase 1 integration**: GitHub API and Web Scraper DB connect learning journey
2. **Pattern variety**: REST API, flat file, relational DB cover main extraction types
3. **Fallback strategy**: Sample data generated if real sources unavailable
4. **Testing friendly**: All sources can work offline with sample data

## Consequences

### Benefits
- Each source teaches distinct extraction pattern
- Project builds on Phase 1 work (continuity)
- Can run entirely locally with sample data
- GitHub API provides substantial real data

### Costs & Tradeoffs
- GitHub API requires network (mitigated: optional/can skip in tests)
- Must maintain sample data generators
- Phase 1 databases may not exist (mitigated: fallback paths)

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub API unavailable | Low | Medium | Disable in config, use cached data |
| Phase 1 DB structure changed | Medium | Low | Flexible parser, fallback sample DB |
| CSV schema changes | Low | Low | Schema inference handles variations |

## Validation
- [ ] Test: Extraction works with sample data only (offline)
- [ ] Test: Each extractor handles missing/invalid data
- [ ] Metric: Can extract 100+ records from each source
- [ ] Metric: Extraction completes in <30 seconds per source

## References
- [GitHub REST API](https://docs.github.com/en/rest)
- [Polars CSV Reader](https://pola-rs.github.io/polars/py-polars/html/reference/api/polars.read_csv.html)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)
