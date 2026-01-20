# ETL Data Pipeline

An automated Extract-Transform-Load pipeline that processes data from multiple sources, applies transformations, and loads into a unified database.

## 🎯 Project Goals

This project demonstrates production ETL patterns:
- **Multiple extractors**: GitHub API, CSV files, SQLite databases
- **Composable transformers**: Cleaning, normalization, validation
- **Reliable loading**: Upsert logic with history tracking
- **Proper error handling**: Retry with backoff, dead-letter logging
- **Observability**: Structured logging, metrics, monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ETL Pipeline                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   EXTRACT    │───▶│  TRANSFORM   │───▶│    LOAD      │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                   │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐            │
│  │ GitHub API  │    │   Cleaner   │    │   SQLite    │            │
│  │ CSV Files   │    │ Normalizer  │    │ PostgreSQL  │            │
│  │ SQLite DB   │    │  Validator  │    │  (future)   │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- Make (optional, for convenience commands)

### Setup
```bash
# Clone and enter directory
cd "Phase - 2/2.2 - ETL Data Pipeline"

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env  # Edit with your settings
```

## 🚀 Quick Start

### Run the Pipeline
```bash
# Using Make
make run

# Using CLI directly
python -m etl_pipeline run

# Run specific sources only
python -m etl_pipeline run --source csv --source sqlite

# Dry run (extract + transform, no loading)
python -m etl_pipeline run --dry-run
```

### Check Pipeline Status
```bash
python -m etl_pipeline status
```

### Validate Configuration
```bash
python -m etl_pipeline validate
```

### List Available Sources
```bash
python -m etl_pipeline sources
```

## ⚙️ Configuration

Pipeline configuration lives in `configs/pipeline.yaml`:

```yaml
sources:
  github:
    enabled: true
    organization: "microsoft"
    max_repos: 100
  
  csv:
    enabled: true
    paths:
      - "data/raw/weather.csv"
  
  sqlite:
    enabled: true
    path: "../1.2 - Web Scraper/data/books.db"

transforms:
  cleaning:
    missing_value_strategy: fill_default
  normalization:
    deduplicate: true
  validation:
    completeness_threshold: 0.8

loading:
  database:
    type: sqlite
    path: "data/output/etl_output.db"
  upsert_strategy: update
  enable_history: true
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_transformers.py -v

# Run integration tests only
pytest tests/test_pipeline_integration.py -v
```

## 📊 Data Flow

### 1. Extraction
Raw data is pulled from configured sources:
- **GitHub API**: Repository metadata (stars, forks, topics)
- **CSV Files**: Weather data, custom datasets
- **SQLite**: Data from Phase 1 Web Scraper

### 2. Transformation
Data is cleaned, normalized, and validated:
- **Cleaning**: Handle missing values, whitespace, type coercion
- **Normalization**: UTC timestamps, tag normalization, deduplication
- **Validation**: Completeness checks, business rules

### 3. Loading
Transformed data is stored with:
- **Upsert logic**: Insert new, update existing records
- **History tracking**: Previous versions archived
- **Metrics**: Counts of inserts, updates, failures

## 🔧 Development

### Project Structure
```
etl_pipeline/
├── __init__.py
├── __main__.py
├── cli.py               # Typer CLI commands
├── config.py            # Settings and YAML loading
├── exceptions.py        # Custom exception hierarchy
├── models.py            # Pydantic data models
├── extractors/          # Data extraction
│   ├── base.py
│   ├── github_extractor.py
│   ├── csv_extractor.py
│   └── sqlite_extractor.py
├── transformers/        # Data transformation
│   ├── base.py
│   ├── cleaners.py
│   ├── normalizer.py
│   └── validators.py
├── loaders/             # Data loading
│   ├── base.py
│   └── sqlite_loader.py
├── orchestration/       # Pipeline coordination
│   └── pipeline.py
└── utils/               # Utilities
    ├── logging.py
    └── retry.py
```

### Make Commands
```bash
make install      # Install dependencies
make test         # Run tests
make test-cov     # Run tests with coverage
make lint         # Run linter
make format       # Format code
make typecheck    # Run type checker
make run          # Run pipeline
make clean        # Clean artifacts
```

### Adding a New Extractor
1. Create `etl_pipeline/extractors/my_extractor.py`
2. Inherit from `BaseExtractor`
3. Implement `extract()` method
4. Add configuration in `configs/pipeline.yaml`
5. Register in pipeline orchestration

```python
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.models import ExtractionResult

class MyExtractor(BaseExtractor[MySourceConfig]):
    async def extract(self) -> ExtractionResult:
        # Implementation here
        ...
```

## 📈 Metrics & Monitoring

The pipeline tracks:
- Records extracted/transformed/loaded per source
- Error counts and types
- Processing duration per stage
- Data quality scores

Metrics are logged and can be found in:
- Console output (Rich formatted)
- Log files (`logs/pipeline.log`)
- Metrics JSON (`data/metrics/pipeline_metrics.json`)

## 🏛️ Architecture Decisions

See [docs/adr/](docs/adr/) for Architecture Decision Records:
- [ADR-001: Orchestration Strategy](docs/adr/001-orchestration-strategy.md)
- [ADR-002: Data Sources](docs/adr/002-data-sources.md)
- [ADR-003: Transformation Framework](docs/adr/003-transformation-framework.md)
- [ADR-004: Error Handling](docs/adr/004-error-handling.md)
- [ADR-005: Storage Strategy](docs/adr/005-storage-strategy.md)
- [ADR-006: Testing Strategy](docs/adr/006-testing-strategy.md)

## 🗺️ Roadmap

### Week 1 ✅
- [x] Core infrastructure (config, models, exceptions)
- [x] Extractors (GitHub, CSV, SQLite)
- [x] Transformers (Cleaner, Normalizer, Validator)
- [x] SQLite Loader with history
- [x] Pipeline orchestration
- [x] CLI interface
- [x] Test suite

### Week 2 (Coming)
- [ ] Async parallel extraction
- [ ] APScheduler integration
- [ ] Monitoring dashboard
- [ ] Alert configuration

### Future
- [ ] PostgreSQL loader
- [ ] Data quality dashboard
- [ ] CDC (Change Data Capture)
- [ ] Data lineage tracking

## 📚 Learning Outcomes

This project teaches:
1. **ETL Patterns**: Extract-Transform-Load architecture
2. **Error Handling**: Retry, backoff, dead-letter queues
3. **Data Quality**: Validation, completeness metrics
4. **Async Python**: httpx, aiosqlite
5. **Modern Data Tools**: Polars, Pydantic
6. **Software Engineering**: ADRs, testing strategies, CLI design

## 🔗 Related Projects

- [Phase 1.2 - Web Scraper](../1.2%20-%20Web%20Scraper/): Source for SQLite extraction
- [Phase 1.3 - API Client](../1.3%20-%20API%20Client/): GitHub API patterns reused
- [Phase 2.1 - REST API](../2.1%20-%20REST%20API/): Similar project structure

## 📄 License

MIT License - See LICENSE file for details.
