# Project 17: Resilience Patterns
# Rate Limiting, Retry, Circuit Breaker, Exponential Backoff

## Overview

This project covers essential resilience patterns for building fault-tolerant systems:
- Rate limiting (token bucket, sliding window)
- Retry patterns with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Bulkhead pattern

## Project Structure

```
17-resilience-patterns/
├── README.md
├── requirements.txt
├── rate_limiting.py       # Rate limiter implementations
├── retry_patterns.py      # Retry with backoff strategies
├── circuit_breaker.py     # Circuit breaker pattern
├── fastapi_resilience.py  # FastAPI integration
└── combined_patterns.py   # All patterns together
```

## Key Concepts

### Rate Limiting Algorithms

1. **Token Bucket**: Allows bursts, tokens replenish at fixed rate
2. **Sliding Window**: Counts requests in sliding time window
3. **Fixed Window**: Simple counter per time window
4. **Leaky Bucket**: Smooths out traffic

### Retry Strategies

1. **Immediate Retry**: No delay (rarely appropriate)
2. **Fixed Delay**: Constant wait between retries
3. **Exponential Backoff**: Doubling delay (1s, 2s, 4s, 8s...)
4. **Exponential Backoff + Jitter**: Adds randomness to prevent thundering herd

### Circuit Breaker States

```
CLOSED (normal) → failures exceed threshold → OPEN (fail fast)
                                                    ↓
                                               timeout
                                                    ↓
CLOSED ← success ← HALF_OPEN (test with one request)
        failure → OPEN
```

## Running Examples

```bash
# Install dependencies
pip install -r requirements.txt

# Run rate limiting examples
python rate_limiting.py

# Run retry patterns
python retry_patterns.py

# Run circuit breaker
python circuit_breaker.py

# Run FastAPI with all patterns
uvicorn fastapi_resilience:app --reload
```

## Best Practices

1. **Rate Limiting**: Apply at API gateway level
2. **Retries**: Only for transient failures (network, 503)
3. **Circuit Breaker**: Protect downstream services
4. **Timeouts**: Always set timeouts for external calls
5. **Monitoring**: Track circuit breaker state changes
