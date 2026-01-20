# Project 19: Prometheus & Grafana Monitoring
# Metrics, Dashboards, Alerting

## Overview

This project covers application monitoring with Prometheus and Grafana:
- Prometheus metrics types (Counter, Gauge, Histogram, Summary)
- Instrumenting Python applications
- FastAPI metrics integration
- Grafana dashboards
- Alerting rules

## Project Structure

```
19-prometheus-grafana/
├── README.md
├── requirements.txt
├── docker-compose.yml        # Prometheus, Grafana, Alertmanager
├── prometheus/
│   ├── prometheus.yml        # Prometheus configuration
│   └── alerts.yml            # Alert rules
├── grafana/
│   └── dashboards/           # Dashboard JSON files
├── metrics_basics.py         # Prometheus client basics
├── fastapi_metrics.py        # FastAPI with metrics
└── custom_metrics.py         # Custom business metrics
```

## Key Concepts

### Metric Types

| Type | Description | Example |
|------|-------------|---------|
| Counter | Only increases | Total requests, errors |
| Gauge | Can increase/decrease | Active connections, temp |
| Histogram | Distribution of values | Request latency |
| Summary | Similar to histogram | Percentiles |

### Prometheus Labels

```python
# Good: Low cardinality labels
http_requests_total{method="GET", status="200"}

# Bad: High cardinality (user_id has many values)
http_requests_total{user_id="12345"}
```

### RED Method for Services

- **R**ate: Requests per second
- **E**rrors: Error rate
- **D**uration: Latency percentiles

### USE Method for Resources

- **U**tilization: % time busy
- **S**aturation: Queue depth
- **E**rrors: Error count

## Running the Stack

```bash
# Start Prometheus and Grafana
docker-compose up -d

# Run FastAPI with metrics
uvicorn fastapi_metrics:app --reload --port 8000

# Access services
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# App: http://localhost:8000
# Metrics: http://localhost:8000/metrics
```

## Example PromQL Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

## Grafana Dashboard Tips

1. Use template variables for flexibility
2. Set appropriate time ranges
3. Use thresholds for visual alerts
4. Group related metrics
5. Include documentation panels

## Best Practices

1. **Naming**: Use `<namespace>_<name>_<unit>` format
2. **Labels**: Keep cardinality low
3. **Help text**: Always add descriptions
4. **Histogram buckets**: Match your SLOs
5. **Push vs Pull**: Prefer pull model
