# ADR-001: Pipeline Orchestration Strategy

## Status
Accepted

## Context
We need to decide how to schedule and coordinate ETL pipeline stages. The orchestrator must:
- Run stages (Extract, Transform, Load) in sequence
- Handle failures at any stage
- Support both manual and scheduled execution
- Track execution metrics
- Be simple enough for a learning project but teach transferable patterns

## Decision Drivers
- **Learning value**: Should teach patterns used in production systems
- **Complexity budget**: Must not overshadow the core ETL learning goals
- **Operational cost**: Minimal infrastructure requirements
- **Debuggability**: Easy to understand what happened in each run

## Options Considered

### Option 1: APScheduler (In-Process)
- **Pros**: 
  - Zero infrastructure dependencies
  - Simple Python-native API
  - Persistent job store (SQLite)
  - Good for learning scheduling concepts
- **Cons**: 
  - Single point of failure
  - No distributed execution
  - Limited monitoring UI
- **Cost**: Low development, low operational

### Option 2: Celery + Redis
- **Pros**: 
  - Battle-tested, industry standard
  - Distributed task execution
  - Rich monitoring (Flower)
  - Scales horizontally
- **Cons**: 
  - Requires Redis infrastructure
  - Complex for simple pipelines
  - Overkill for learning project
- **Cost**: Medium development, high operational

### Option 3: Prefect/Dagster
- **Pros**: 
  - Modern DX, excellent UI
  - Built-in observability
  - Cloud offerings with free tiers
  - First-class data engineering support
- **Cons**: 
  - New tools to learn
  - Potential vendor lock-in
  - Abstracts away scheduling internals
- **Cost**: Medium development, medium operational

### Option 4: Simple Manual Script
- **Pros**: 
  - Zero dependencies
  - Maximum control
  - Clear execution flow
- **Cons**: 
  - No scheduling built-in
  - Must implement retry, logging manually
- **Cost**: Low development, low operational

## Decision
**APScheduler** for scheduled execution, with a **manual CLI** as the primary interface.

### Rationale
1. **Learning-first**: Understanding how scheduling works under the hood is valuable before using abstracted tools like Airflow/Prefect
2. **Minimal infrastructure**: No Redis/external services required
3. **Patterns transfer**: Job scheduling, retry logic, and persistence concepts apply to any orchestrator
4. **Appropriate scope**: Week 2 adds scheduling on top of a working pipeline, not the other way around
5. **CLI-first**: Most debugging happens via manual runs; scheduling is an enhancement

## Consequences

### Benefits
- Simple setup and debugging
- Full visibility into orchestration code
- Easy to test pipeline stages independently
- Patterns learned transfer to Celery/Airflow

### Costs & Tradeoffs
- Not horizontally scalable (acceptable for learning project)
- No fancy dashboard (Rich CLI output instead)
- Must implement job tracking ourselves

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| In-process scheduler dies | Low | Medium | Use persistent job store |
| Complex job dependencies needed | Low | Low | Can migrate to Celery if needed |
| Outgrow single-machine | Low | Low | Learning project scale is limited |

## Validation
- [ ] Metric: Pipeline can run on schedule (hourly/daily)
- [ ] Metric: Failed jobs are retried automatically
- [ ] Test: Job state persists across restarts
- [ ] Test: Manual CLI works without scheduler running

## References
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [Prefect Core Concepts](https://docs.prefect.io/concepts/)
