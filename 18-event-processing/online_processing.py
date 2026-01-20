"""
Online (Real-time) Event Processing
===================================
Processing events as they arrive in real-time.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import deque
import uuid
from abc import ABC, abstractmethod
from event_basics import Event, OrderCreated, PaymentReceived, OrderShipped


# =============================================================================
# Event Stream
# =============================================================================

class EventStream:
    """
    In-memory event stream for real-time processing.
    Simulates Kafka/Redis Streams behavior.
    """
    
    def __init__(self, name: str, max_size: int = 10000):
        self.name = name
        self.max_size = max_size
        self._events: deque = deque(maxlen=max_size)
        self._subscribers: List[asyncio.Queue] = []
        self._position = 0
        self._lock = asyncio.Lock()
    
    async def publish(self, event: Event) -> int:
        """Publish an event to the stream."""
        async with self._lock:
            self._position += 1
            entry = {
                "position": self._position,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event.to_dict(),
            }
            self._events.append(entry)
            
            # Notify subscribers
            for queue in self._subscribers:
                await queue.put(entry)
            
            return self._position
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to receive events."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def read(self, from_position: int = 0, count: int = 100) -> List[Dict]:
        """Read historical events."""
        async with self._lock:
            return [
                e for e in self._events
                if e["position"] > from_position
            ][:count]


# =============================================================================
# Real-time Event Processor
# =============================================================================

class EventProcessor(ABC):
    """Abstract base for event processors."""
    
    @abstractmethod
    async def process(self, event: Dict[str, Any]) -> None:
        """Process a single event."""
        pass


class HandlerBasedProcessor(EventProcessor):
    """
    Processor that routes events to type-specific handlers.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
    
    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def process(self, event: Dict[str, Any]) -> None:
        """Process event by calling registered handlers."""
        event_data = event.get("event", {})
        event_type = event_data.get("event_type")
        
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                print(f"Handler error for {event_type}: {e}")


# =============================================================================
# Real-time Consumer
# =============================================================================

class RealTimeConsumer:
    """
    Consumes events from a stream in real-time.
    """
    
    def __init__(
        self,
        stream: EventStream,
        processor: EventProcessor,
        consumer_group: str = "default",
    ):
        self.stream = stream
        self.processor = processor
        self.consumer_group = consumer_group
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_count = 0
    
    async def start(self) -> None:
        """Start consuming events."""
        self._running = True
        self._task = asyncio.create_task(self._consume())
        print(f"Consumer started for stream '{self.stream.name}'")
    
    async def stop(self) -> None:
        """Stop consuming events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print(f"Consumer stopped. Processed {self._processed_count} events.")
    
    async def _consume(self) -> None:
        """Main consumption loop."""
        queue = self.stream.subscribe()
        
        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    await self.processor.process(event)
                    self._processed_count += 1
                except asyncio.TimeoutError:
                    continue
        finally:
            self.stream.unsubscribe(queue)


# =============================================================================
# Real-time Aggregations
# =============================================================================

class RealTimeAggregator:
    """
    Performs real-time aggregations on event streams.
    
    Example: Count orders per customer in sliding window.
    """
    
    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self._data: Dict[str, deque] = {}
        self._lock = asyncio.Lock()
    
    async def add(self, key: str, value: Any = 1) -> None:
        """Add a value to aggregation."""
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            
            if key not in self._data:
                self._data[key] = deque()
            
            self._data[key].append((now, value))
            self._cleanup(key)
    
    def _cleanup(self, key: str) -> None:
        """Remove expired entries."""
        cutoff = datetime.now(timezone.utc).timestamp() - self.window_seconds
        
        while self._data[key] and self._data[key][0][0] < cutoff:
            self._data[key].popleft()
    
    async def count(self, key: str) -> int:
        """Get count for a key in current window."""
        async with self._lock:
            if key not in self._data:
                return 0
            self._cleanup(key)
            return len(self._data[key])
    
    async def sum(self, key: str) -> float:
        """Get sum for a key in current window."""
        async with self._lock:
            if key not in self._data:
                return 0.0
            self._cleanup(key)
            return sum(v for _, v in self._data[key])
    
    async def get_all_counts(self) -> Dict[str, int]:
        """Get counts for all keys."""
        async with self._lock:
            result = {}
            for key in list(self._data.keys()):
                self._cleanup(key)
                result[key] = len(self._data[key])
            return result


# =============================================================================
# Real-time Alerts
# =============================================================================

@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    
    name: str
    condition: Callable[[Dict], bool]
    action: Callable[[Dict], Any]
    cooldown_seconds: float = 60.0
    last_triggered: Optional[datetime] = None
    
    def can_trigger(self) -> bool:
        """Check if alert can trigger (respects cooldown)."""
        if self.last_triggered is None:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_triggered).total_seconds()
        return elapsed >= self.cooldown_seconds


class AlertManager:
    """
    Manages real-time alerts based on event patterns.
    """
    
    def __init__(self):
        self._rules: List[AlertRule] = []
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules.append(rule)
    
    async def evaluate(self, event: Dict[str, Any]) -> List[str]:
        """Evaluate all rules against an event."""
        triggered = []
        
        for rule in self._rules:
            try:
                if rule.can_trigger() and rule.condition(event):
                    rule.last_triggered = datetime.now(timezone.utc)
                    
                    if asyncio.iscoroutinefunction(rule.action):
                        await rule.action(event)
                    else:
                        rule.action(event)
                    
                    triggered.append(rule.name)
            except Exception as e:
                print(f"Alert rule '{rule.name}' error: {e}")
        
        return triggered


# =============================================================================
# Demo: Order Processing Pipeline
# =============================================================================

async def demo():
    print("=" * 60)
    print("Online (Real-time) Event Processing Demo")
    print("=" * 60)
    
    # Create stream
    order_stream = EventStream("orders")
    
    # Create processor with handlers
    processor = HandlerBasedProcessor()
    
    # Real-time aggregator
    order_counter = RealTimeAggregator(window_seconds=60.0)
    revenue_tracker = RealTimeAggregator(window_seconds=60.0)
    
    # Alert manager
    alerts = AlertManager()
    
    # Register handlers
    @processor.on("OrderCreated", processor)
    async def handle_order_created(event: Dict):
        data = event.get("data", {})
        customer_id = data.get("customer_id")
        total = data.get("total_amount", 0)
        
        print(f"  📦 New order from {customer_id}, total: ${total:.2f}")
        
        await order_counter.add(customer_id)
        await revenue_tracker.add("total", total)
    
    processor.on("OrderCreated", handle_order_created)
    
    async def handle_payment(event: Dict):
        data = event.get("data", {})
        print(f"  💳 Payment received: ${data.get('amount', 0):.2f}")
    
    processor.on("PaymentReceived", handle_payment)
    
    # Add alert rules
    alerts.add_rule(AlertRule(
        name="high_value_order",
        condition=lambda e: e.get("data", {}).get("total_amount", 0) > 100,
        action=lambda e: print(f"  🚨 ALERT: High value order! ${e['data']['total_amount']:.2f}"),
        cooldown_seconds=5,
    ))
    
    # Start consumer
    consumer = RealTimeConsumer(order_stream, processor)
    await consumer.start()
    
    # Simulate events
    print("\n=== Publishing Events ===\n")
    
    events = [
        OrderCreated(
            order_id="ord-1",
            customer_id="cust-A",
            items=[{"product": "Widget"}],
            total_amount=49.99,
        ),
        OrderCreated(
            order_id="ord-2",
            customer_id="cust-B",
            items=[{"product": "Gadget"}],
            total_amount=149.99,  # High value - triggers alert
        ),
        PaymentReceived(
            order_id="ord-1",
            payment_id="pay-1",
            amount=49.99,
            payment_method="card",
        ),
        OrderCreated(
            order_id="ord-3",
            customer_id="cust-A",
            items=[{"product": "Thing"}],
            total_amount=29.99,
        ),
    ]
    
    for event in events:
        await order_stream.publish(event)
        
        # Check alerts
        event_dict = event.to_dict()
        triggered = await alerts.evaluate(event_dict)
        
        await asyncio.sleep(0.5)  # Allow processing
    
    await asyncio.sleep(1)  # Let processing complete
    
    # Show aggregations
    print("\n=== Real-time Aggregations (60s window) ===\n")
    
    counts = await order_counter.get_all_counts()
    for customer, count in counts.items():
        print(f"  {customer}: {count} orders")
    
    total_revenue = await revenue_tracker.sum("total")
    print(f"\n  Total Revenue: ${total_revenue:.2f}")
    
    # Stop consumer
    await consumer.stop()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
