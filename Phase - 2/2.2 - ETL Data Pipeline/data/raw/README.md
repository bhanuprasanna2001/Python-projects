# Sample data directory

This directory contains sample data for testing the ETL pipeline:

- `weather.csv` - Sample weather data for CSV extractor testing
- `sample.db` - Sample SQLite database (created automatically by tests)

## Generating Test Data

The pipeline can generate sample data if external sources are unavailable:

```bash
python -m etl_pipeline run --generate-sample-data
```
