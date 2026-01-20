"""
Event Store
===========
Event store implementation for event sourcing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Type, Callable
from abc import ABC, abstractmethod
import json
import uuid
import sqlite3
from contextlib import contextmanager
import threading
from event_basics import Event, OrderCreated, PaymentReceived, OrderShipped, OrderDelivered


# =============================================================================
# Event Store Interface
# =============================================================================

class EventStore(ABC):
    """Abstract base class for event stores."""
    
    @abstractmethod
    def append(self, stream_id: str, events: List[Event], expected_version: int = -1) -> int:
        """
        Append events to a stream.
        
        Args:
            stream_id: Identifier for the event stream
            events: List of events to append
            expected_version: Expected current version for optimistic concurrency
        
        Returns:
            New version number
        
        Raises:
            ConcurrencyError: If expected_version doesn't match
        """
        pass
    
    @abstractmethod
    def read(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None
    ) -> List[Event]:
        """Read events from a stream."""
        pass
    
    @abstractmethod
    def read_all(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[Event]:
        """Read all events across all streams."""
        pass


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""
    pass


# =============================================================================
# In-Memory Event Store
# =============================================================================

@dataclass
class StoredEvent:
    """Event as stored in the event store."""
    
    position: int  # Global position
    stream_id: str
    version: int  # Stream version
    event_type: str
    data: str  # JSON data
    metadata: str  # JSON metadata
    timestamp: datetime


class InMemoryEventStore(EventStore):
    """
    In-memory event store for development/testing.
    """
    
    def __init__(self):
        self._events: List[StoredEvent] = []
        self._streams: Dict[str, List[StoredEvent]] = {}
        self._lock = threading.Lock()
        self._position = 0
    
    def append(
        self,
        stream_id: str,
        events: List[Event],
        expected_version: int = -1
    ) -> int:
        with self._lock:
            # Check expected version
            current_version = len(self._streams.get(stream_id, []))
            
            if expected_version >= 0 and current_version != expected_version:
                raise ConcurrencyError(
                    f"Expected version {expected_version}, "
                    f"but current version is {current_version}"
                )
            
            # Initialize stream if needed
            if stream_id not in self._streams:
                self._streams[stream_id] = []
            
            # Append events
            new_version = current_version
            for event in events:
                self._position += 1
                new_version += 1
                
                stored = StoredEvent(
                    position=self._position,
                    stream_id=stream_id,
                    version=new_version,
                    event_type=event.event_type,
                    data=json.dumps(event.to_dict()),
                    metadata="{}",
                    timestamp=event.timestamp,
                )
                
                self._events.append(stored)
                self._streams[stream_id].append(stored)
            
            return new_version
    
    def read(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None
    ) -> List[StoredEvent]:
        with self._lock:
            events = self._streams.get(stream_id, [])
            
            if to_version is None:
                to_version = len(events)
            
            return [
                e for e in events
                if from_version < e.version <= to_version
            ]
    
    def read_all(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[StoredEvent]:
        with self._lock:
            return [
                e for e in self._events
                if e.position > from_position
            ][:batch_size]
    
    def get_stream_version(self, stream_id: str) -> int:
        """Get current version of a stream."""
        with self._lock:
            return len(self._streams.get(stream_id, []))


# =============================================================================
# SQLite Event Store
# =============================================================================

class SQLiteEventStore(EventStore):
    """
    SQLite-based event store for persistence.
    """
    
    def __init__(self, db_path: str = "events.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    position INTEGER PRIMARY KEY AUTOINCREMENT,
                    stream_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    timestamp TEXT NOT NULL,
                    UNIQUE(stream_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stream_id 
                ON events(stream_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON events(event_type)
            """)
    
    def append(
        self,
        stream_id: str,
        events: List[Event],
        expected_version: int = -1
    ) -> int:
        with self._get_connection() as conn:
            # Get current version
            cursor = conn.execute(
                "SELECT MAX(version) FROM events WHERE stream_id = ?",
                (stream_id,)
            )
            result = cursor.fetchone()[0]
            current_version = result if result is not None else 0
            
            # Check expected version
            if expected_version >= 0 and current_version != expected_version:
                raise ConcurrencyError(
                    f"Expected version {expected_version}, "
                    f"but current version is {current_version}"
                )
            
            # Append events
            new_version = current_version
            for event in events:
                new_version += 1
                conn.execute(
                    """
                    INSERT INTO events (stream_id, version, event_type, data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        stream_id,
                        new_version,
                        event.event_type,
                        json.dumps(event.to_dict()),
                        event.timestamp.isoformat(),
                    )
                )
            
            return new_version
    
    def read(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None
    ) -> List[StoredEvent]:
        with self._get_connection() as conn:
            if to_version is None:
                cursor = conn.execute(
                    """
                    SELECT * FROM events 
                    WHERE stream_id = ? AND version > ?
                    ORDER BY version
                    """,
                    (stream_id, from_version)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM events 
                    WHERE stream_id = ? AND version > ? AND version <= ?
                    ORDER BY version
                    """,
                    (stream_id, from_version, to_version)
                )
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def read_all(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[StoredEvent]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events 
                WHERE position > ?
                ORDER BY position
                LIMIT ?
                """,
                (from_position, batch_size)
            )
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def _row_to_event(self, row) -> StoredEvent:
        return StoredEvent(
            position=row["position"],
            stream_id=row["stream_id"],
            version=row["version"],
            event_type=row["event_type"],
            data=row["data"],
            metadata=row["metadata"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )


# =============================================================================
# Aggregate Root with Event Sourcing
# =============================================================================

class AggregateRoot(ABC):
    """
    Base class for event-sourced aggregates.
    """
    
    def __init__(self, aggregate_id: str):
        self._id = aggregate_id
        self._version = 0
        self._uncommitted_events: List[Event] = []
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def version(self) -> int:
        return self._version
    
    def _apply_event(self, event: Event, is_new: bool = True) -> None:
        """Apply an event to update state."""
        # Call the appropriate handler
        handler_name = f"_on_{self._to_snake_case(event.event_type)}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            handler(event)
        
        if is_new:
            self._uncommitted_events.append(event)
        
        self._version += 1
    
    def _raise_event(self, event: Event) -> None:
        """Raise a new event."""
        self._apply_event(event, is_new=True)
    
    def load_from_history(self, events: List[Event]) -> None:
        """Reconstruct state from events."""
        for event in events:
            self._apply_event(event, is_new=False)
    
    def get_uncommitted_events(self) -> List[Event]:
        """Get events not yet persisted."""
        return self._uncommitted_events.copy()
    
    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events after persistence."""
        self._uncommitted_events.clear()
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


# =============================================================================
# Example: Order Aggregate
# =============================================================================

class OrderStatus:
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class Order(AggregateRoot):
    """
    Order aggregate with event sourcing.
    """
    
    def __init__(self, order_id: str):
        super().__init__(order_id)
        self.customer_id: Optional[str] = None
        self.items: list = []
        self.total_amount: float = 0.0
        self.status: str = ""
        self.tracking_number: Optional[str] = None
    
    # Commands
    @classmethod
    def create(cls, order_id: str, customer_id: str, items: list, total: float) -> "Order":
        """Create a new order."""
        order = cls(order_id)
        order._raise_event(OrderCreated(
            order_id=order_id,
            customer_id=customer_id,
            items=items,
            total_amount=total,
        ))
        return order
    
    def receive_payment(self, payment_id: str, amount: float, method: str) -> None:
        """Record payment received."""
        if self.status != OrderStatus.CREATED:
            raise ValueError(f"Cannot receive payment for order in status: {self.status}")
        
        self._raise_event(PaymentReceived(
            order_id=self._id,
            payment_id=payment_id,
            amount=amount,
            payment_method=method,
        ))
    
    def ship(self, tracking_number: str, carrier: str) -> None:
        """Ship the order."""
        if self.status != OrderStatus.PAID:
            raise ValueError(f"Cannot ship order in status: {self.status}")
        
        self._raise_event(OrderShipped(
            order_id=self._id,
            tracking_number=tracking_number,
            carrier=carrier,
        ))
    
    def deliver(self) -> None:
        """Mark order as delivered."""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError(f"Cannot deliver order in status: {self.status}")
        
        self._raise_event(OrderDelivered(order_id=self._id))
    
    # Event handlers (update state)
    def _on_order_created(self, event: OrderCreated) -> None:
        self.customer_id = event.customer_id
        self.items = event.items
        self.total_amount = event.total_amount
        self.status = OrderStatus.CREATED
    
    def _on_payment_received(self, event: PaymentReceived) -> None:
        self.status = OrderStatus.PAID
    
    def _on_order_shipped(self, event: OrderShipped) -> None:
        self.tracking_number = event.tracking_number
        self.status = OrderStatus.SHIPPED
    
    def _on_order_delivered(self, event: OrderDelivered) -> None:
        self.status = OrderStatus.DELIVERED


# =============================================================================
# Repository
# =============================================================================

class OrderRepository:
    """
    Repository for Order aggregate.
    Handles persistence through event store.
    """
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def save(self, order: Order) -> None:
        """Save order by appending uncommitted events."""
        events = order.get_uncommitted_events()
        
        if events:
            stream_id = f"order-{order.id}"
            expected_version = order.version - len(events)
            
            self.event_store.append(stream_id, events, expected_version)
            order.clear_uncommitted_events()
    
    def get(self, order_id: str) -> Optional[Order]:
        """Load order from events."""
        stream_id = f"order-{order_id}"
        stored_events = self.event_store.read(stream_id)
        
        if not stored_events:
            return None
        
        order = Order(order_id)
        
        # Reconstruct events from stored data
        events = [self._deserialize_event(se) for se in stored_events]
        order.load_from_history(events)
        
        return order
    
    def _deserialize_event(self, stored: StoredEvent) -> Event:
        """Deserialize stored event to domain event."""
        data = json.loads(stored.data)["data"]
        
        # Map event types to classes
        event_classes = {
            "OrderCreated": OrderCreated,
            "PaymentReceived": PaymentReceived,
            "OrderShipped": OrderShipped,
            "OrderDelivered": OrderDelivered,
        }
        
        event_class = event_classes.get(stored.event_type)
        if not event_class:
            raise ValueError(f"Unknown event type: {stored.event_type}")
        
        # Create event with data
        return event_class(**data)


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Event Store Demo")
    print("=" * 60)
    
    # Create event store and repository
    store = InMemoryEventStore()
    repo = OrderRepository(store)
    
    # Create an order
    print("\n=== Creating Order ===\n")
    
    order = Order.create(
        order_id="order-001",
        customer_id="cust-123",
        items=[{"product": "Widget", "qty": 2, "price": 29.99}],
        total=59.98,
    )
    
    print(f"Order created: {order.id}")
    print(f"Status: {order.status}")
    print(f"Version: {order.version}")
    
    # Save order
    repo.save(order)
    print("\nOrder saved to event store")
    
    # Process payment
    print("\n=== Processing Payment ===\n")
    
    order.receive_payment("pay-001", 59.98, "credit_card")
    print(f"Payment received, status: {order.status}")
    repo.save(order)
    
    # Ship order
    print("\n=== Shipping Order ===\n")
    
    order.ship("TRACK123", "FedEx")
    print(f"Order shipped, tracking: {order.tracking_number}")
    repo.save(order)
    
    # Load order from events
    print("\n=== Loading Order from Events ===\n")
    
    loaded_order = repo.get("order-001")
    print(f"Loaded order: {loaded_order.id}")
    print(f"Customer: {loaded_order.customer_id}")
    print(f"Status: {loaded_order.status}")
    print(f"Tracking: {loaded_order.tracking_number}")
    print(f"Version: {loaded_order.version}")
    
    # View events in store
    print("\n=== Events in Store ===\n")
    
    events = store.read("order-order-001")
    for e in events:
        print(f"  [{e.version}] {e.event_type} at {e.timestamp}")
    
    print("\n" + "=" * 60)
