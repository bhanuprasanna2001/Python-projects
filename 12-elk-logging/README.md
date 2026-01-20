# Project 12: ELK Stack Logging

A comprehensive mini-project demonstrating structured logging with **Elasticsearch, Logstash, and Kibana (ELK)**.

## What You'll Learn

- Structured JSON logging
- Python-elasticsearch integration
- Log formatting for ELK
- Contextual logging
- Log correlation with request IDs
- FastAPI logging middleware
- Direct ES logging vs Logstash

## Project Structure

```
12-elk-logging/
├── README.md
├── requirements.txt
├── docker-compose.yml          # ELK stack setup
├── logstash/
│   └── pipeline.conf           # Logstash configuration
├── logging_config.py           # Python logging setup
├── structured_logging.py       # Structured logging examples
├── elasticsearch_handler.py    # Custom ES log handler
├── fastapi_logging.py          # FastAPI integration
└── log_examples.py             # Usage examples
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start ELK stack
docker-compose up -d

# Wait for services to start (about 1 minute)
# Access Kibana at http://localhost:5601

# Run examples
python log_examples.py
python fastapi_logging.py
```

## ELK Components

### Elasticsearch
- Document store for logs
- Full-text search
- Aggregations and analytics

### Logstash
- Log ingestion pipeline
- Parsing and transformation
- Multiple input/output options

### Kibana
- Visualization dashboard
- Log exploration
- Alerting (with X-Pack)

## Log Flow Options

```
Option 1: Direct to Elasticsearch
Python App → Elasticsearch Handler → Elasticsearch → Kibana

Option 2: Via Logstash
Python App → File/TCP → Logstash → Elasticsearch → Kibana

Option 3: Via Filebeat
Python App → File → Filebeat → Logstash → Elasticsearch → Kibana
```

## Best Practices

1. Use structured JSON logging
2. Include correlation/request IDs
3. Add contextual metadata
4. Use appropriate log levels
5. Don't log sensitive data
6. Index logs by date
7. Set up log retention policies
