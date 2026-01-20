"""
Offline (Batch) Event Processing
================================
Processing historical events in batches for analytics and reporting.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Callable, Iterator
from dataclasses import dataclass, field
from collections import defaultdict
import json
from abc import ABC, abstractmethod


# =============================================================================
# Batch Processing Configuration
# =============================================================================

@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    
    batch_size: int = 1000
    parallelism: int = 4
    checkpoint_interval: int = 5000  # Events between checkpoints
    retry_on_failure: bool = True
    max_retries: int = 3


# =============================================================================
# Event Source (Simulated)
# =============================================================================

class EventSource:
    """
    Source of historical events for batch processing.
    Simulates reading from event store, data lake, etc.
    """
    
    def __init__(self, events: List[Dict[str, Any]]):
        self._events = events
        self._position = 0
    
    def read_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """Read a batch of events."""
        batch = self._events[self._position:self._position + batch_size]
        self._position += len(batch)
        return batch
    
    def seek(self, position: int) -> None:
        """Seek to a specific position."""
        self._position = position
    
    def reset(self) -> None:
        """Reset to beginning."""
        self._position = 0
    
    @property
    def total_events(self) -> int:
        return len(self._events)
    
    @property
    def current_position(self) -> int:
        return self._position
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        for event in self._events:
            yield event


# =============================================================================
# Batch Processor
# =============================================================================

class BatchProcessor(ABC):
    """Abstract base for batch processors."""
    
    @abstractmethod
    def process_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of events and return results."""
        pass
    
    @abstractmethod
    def finalize(self) -> Dict[str, Any]:
        """Finalize processing and return final results."""
        pass


class AggregationProcessor(BatchProcessor):
    """
    Processor that performs aggregations on events.
    """
    
    def __init__(self):
        self._counts: Dict[str, int] = defaultdict(int)
        self._sums: Dict[str, float] = defaultdict(float)
        self._total_processed = 0
    
    def process_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process batch and update aggregations."""
        batch_counts = defaultdict(int)
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            self._counts[event_type] += 1
            batch_counts[event_type] += 1
            
            # Sum amounts if present
            data = event.get("data", {})
            if "total_amount" in data:
                self._sums["revenue"] += data["total_amount"]
            if "amount" in data:
                self._sums["payments"] += data["amount"]
        
        self._total_processed += len(events)
        
        return {
            "batch_size": len(events),
            "batch_counts": dict(batch_counts),
        }
    
    def finalize(self) -> Dict[str, Any]:
        """Return final aggregation results."""
        return {
            "total_events": self._total_processed,
            "event_counts": dict(self._counts),
            "sums": dict(self._sums),
        }


# =============================================================================
# Batch Pipeline
# =============================================================================

@dataclass
class CheckpointState:
    """State saved at checkpoints."""
    
    position: int
    processed_count: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class BatchPipeline:
    """
    Pipeline for batch event processing.
    
    Features:
    - Batch reading
    - Checkpointing for resume
    - Progress tracking
    - Error handling
    """
    
    def __init__(
        self,
        source: EventSource,
        processor: BatchProcessor,
        config: BatchConfig = BatchConfig(),
    ):
        self.source = source
        self.processor = processor
        self.config = config
        
        self._checkpoint: Optional[CheckpointState] = None
        self._start_time: Optional[datetime] = None
        self._processed_count = 0
        self._failed_count = 0
    
    def run(self) -> Dict[str, Any]:
        """Run the batch pipeline."""
        self._start_time = datetime.now(timezone.utc)
        
        print(f"Starting batch processing of {self.source.total_events} events")
        print(f"Batch size: {self.config.batch_size}")
        
        # Resume from checkpoint if exists
        if self._checkpoint:
            self.source.seek(self._checkpoint.position)
            self._processed_count = self._checkpoint.processed_count
            print(f"Resuming from checkpoint at position {self._checkpoint.position}")
        
        while True:
            # Read batch
            batch = self.source.read_batch(self.config.batch_size)
            
            if not batch:
                break  # No more events
            
            # Process batch with retry
            self._process_batch_with_retry(batch)
            
            # Checkpoint if needed
            if self._processed_count % self.config.checkpoint_interval == 0:
                self._save_checkpoint()
            
            # Progress
            progress = (self.source.current_position / self.source.total_events) * 100
            print(f"Progress: {progress:.1f}% ({self._processed_count} events)")
        
        # Finalize
        results = self.processor.finalize()
        
        elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        events_per_second = self._processed_count / elapsed if elapsed > 0 else 0
        
        return {
            "results": results,
            "statistics": {
                "total_processed": self._processed_count,
                "failed_count": self._failed_count,
                "elapsed_seconds": elapsed,
                "events_per_second": events_per_second,
            },
        }
    
    def _process_batch_with_retry(self, batch: List[Dict[str, Any]]) -> None:
        """Process batch with retry logic."""
        retries = 0
        
        while retries <= self.config.max_retries:
            try:
                self.processor.process_batch(batch)
                self._processed_count += len(batch)
                return
            except Exception as e:
                retries += 1
                if retries > self.config.max_retries:
                    print(f"Batch failed after {self.config.max_retries} retries: {e}")
                    self._failed_count += len(batch)
                    if not self.config.retry_on_failure:
                        raise
                else:
                    print(f"Batch failed, retry {retries}/{self.config.max_retries}: {e}")
    
    def _save_checkpoint(self) -> None:
        """Save checkpoint state."""
        self._checkpoint = CheckpointState(
            position=self.source.current_position,
            processed_count=self._processed_count,
            timestamp=datetime.now(timezone.utc),
        )
        print(f"Checkpoint saved at position {self._checkpoint.position}")


# =============================================================================
# Map-Reduce Style Processing
# =============================================================================

class MapReduceProcessor:
    """
    Map-reduce style batch processor.
    """
    
    def __init__(
        self,
        mapper: Callable[[Dict], List[tuple]],
        reducer: Callable[[str, List[Any]], Any],
    ):
        self.mapper = mapper
        self.reducer = reducer
        self._intermediate: Dict[str, List] = defaultdict(list)
    
    def map_phase(self, events: List[Dict[str, Any]]) -> None:
        """Map phase: emit key-value pairs."""
        for event in events:
            pairs = self.mapper(event)
            for key, value in pairs:
                self._intermediate[key].append(value)
    
    def reduce_phase(self) -> Dict[str, Any]:
        """Reduce phase: aggregate by key."""
        results = {}
        
        for key, values in self._intermediate.items():
            results[key] = self.reducer(key, values)
        
        return results
    
    def run(self, events: List[Dict[str, Any]], batch_size: int = 1000) -> Dict[str, Any]:
        """Run map-reduce on events."""
        # Map phase (can be parallelized)
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            self.map_phase(batch)
        
        # Reduce phase
        return self.reduce_phase()


# =============================================================================
# Time-Window Aggregations
# =============================================================================

class TimeWindowAggregator:
    """
    Aggregate events into time windows (hourly, daily, etc.)
    """
    
    def __init__(self, window_size: timedelta):
        self.window_size = window_size
        self._windows: Dict[datetime, Dict[str, Any]] = defaultdict(
            lambda: defaultdict(lambda: {"count": 0, "sum": 0.0})
        )
    
    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get the start time of the window containing timestamp."""
        seconds = int(timestamp.timestamp())
        window_seconds = int(self.window_size.total_seconds())
        window_start_seconds = (seconds // window_seconds) * window_seconds
        return datetime.fromtimestamp(window_start_seconds, tz=timezone.utc)
    
    def add(self, timestamp: datetime, metric: str, value: float = 1.0) -> None:
        """Add a value to a metric in the appropriate window."""
        window = self._get_window_start(timestamp)
        self._windows[window][metric]["count"] += 1
        self._windows[window][metric]["sum"] += value
    
    def get_results(self) -> Dict[str, Any]:
        """Get aggregation results by window."""
        return {
            str(window): {
                metric: data
                for metric, data in metrics.items()
            }
            for window, metrics in sorted(self._windows.items())
        }


# =============================================================================
# Demo: Daily Sales Report
# =============================================================================

def generate_sample_events(count: int) -> List[Dict[str, Any]]:
    """Generate sample events for demo."""
    import random
    
    events = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)
    
    customers = ["cust-A", "cust-B", "cust-C", "cust-D", "cust-E"]
    
    for i in range(count):
        timestamp = base_time + timedelta(
            hours=random.randint(0, 168),  # Up to 7 days
            minutes=random.randint(0, 59),
        )
        
        if random.random() < 0.7:  # 70% orders
            event = {
                "event_id": f"evt-{i}",
                "event_type": "OrderCreated",
                "timestamp": timestamp.isoformat(),
                "data": {
                    "order_id": f"ord-{i}",
                    "customer_id": random.choice(customers),
                    "total_amount": round(random.uniform(10, 500), 2),
                },
            }
        else:  # 30% payments
            event = {
                "event_id": f"evt-{i}",
                "event_type": "PaymentReceived",
                "timestamp": timestamp.isoformat(),
                "data": {
                    "payment_id": f"pay-{i}",
                    "amount": round(random.uniform(10, 500), 2),
                },
            }
        
        events.append(event)
    
    # Sort by timestamp
    events.sort(key=lambda e: e["timestamp"])
    return events


def demo():
    print("=" * 60)
    print("Offline (Batch) Event Processing Demo")
    print("=" * 60)
    
    # Generate sample events
    print("\n=== Generating Sample Events ===\n")
    events = generate_sample_events(5000)
    print(f"Generated {len(events)} events")
    
    # Create source and processor
    source = EventSource(events)
    processor = AggregationProcessor()
    
    # Run pipeline
    print("\n=== Running Batch Pipeline ===\n")
    
    pipeline = BatchPipeline(
        source=source,
        processor=processor,
        config=BatchConfig(
            batch_size=500,
            checkpoint_interval=1000,
        ),
    )
    
    results = pipeline.run()
    
    print("\n=== Results ===\n")
    print(f"Total processed: {results['statistics']['total_processed']}")
    print(f"Events/second: {results['statistics']['events_per_second']:.1f}")
    print(f"\nEvent counts: {results['results']['event_counts']}")
    print(f"Revenue: ${results['results']['sums'].get('revenue', 0):,.2f}")
    
    # Map-Reduce example
    print("\n=== Map-Reduce: Orders by Customer ===\n")
    
    def order_mapper(event: Dict) -> List[tuple]:
        if event["event_type"] == "OrderCreated":
            customer = event["data"]["customer_id"]
            amount = event["data"]["total_amount"]
            return [(customer, amount)]
        return []
    
    def sum_reducer(key: str, values: List[float]) -> Dict:
        return {
            "order_count": len(values),
            "total_amount": sum(values),
            "average_amount": sum(values) / len(values) if values else 0,
        }
    
    mr = MapReduceProcessor(order_mapper, sum_reducer)
    customer_stats = mr.run(events)
    
    for customer, stats in sorted(customer_stats.items()):
        print(f"  {customer}: {stats['order_count']} orders, "
              f"${stats['total_amount']:,.2f} total, "
              f"${stats['average_amount']:.2f} avg")
    
    # Time-window aggregation
    print("\n=== Daily Revenue ===\n")
    
    daily_agg = TimeWindowAggregator(timedelta(days=1))
    
    for event in events:
        if event["event_type"] == "OrderCreated":
            timestamp = datetime.fromisoformat(event["timestamp"])
            amount = event["data"]["total_amount"]
            daily_agg.add(timestamp, "revenue", amount)
            daily_agg.add(timestamp, "orders", 1)
    
    daily_results = daily_agg.get_results()
    
    for day, metrics in list(daily_results.items())[:5]:  # Show first 5 days
        revenue = metrics.get("revenue", {}).get("sum", 0)
        orders = metrics.get("orders", {}).get("count", 0)
        print(f"  {day[:10]}: {orders} orders, ${revenue:,.2f}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
