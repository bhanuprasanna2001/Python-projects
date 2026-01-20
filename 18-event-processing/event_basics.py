"""
Event Basics
============
Fundamental event classes and patterns for event-driven architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, TypeVar
from abc import ABC, abstractmethod
import uuid
import json
from enum import Enum


# =============================================================================
# Base Event Classes
# =============================================================================

@dataclass
class Event(ABC):
    """
    Base class for all events.
    
    Events are immutable records of something that happened.
    They should be named in past tense (e.g., OrderCreated, PaymentReceived).
    """
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1  # For schema versioning
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the event type name."""
        pass
    
    @property
    def aggregate_id(self) -> Optional[str]:
        """Return the aggregate ID this event belongs to."""
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": self._get_data(),
        }
    
    @abstractmethod
    def _get_data(self) -> Dict[str, Any]:
        """Return event-specific data."""
        pass
    
    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Deserialize event from dictionary."""
        # Override in subclasses
        raise NotImplementedError


# =============================================================================
# Domain Events Example: E-commerce
# =============================================================================

@dataclass
class OrderCreated(Event):
    """Event raised when a new order is created."""
    
    order_id: str = ""
    customer_id: str = ""
    items: list = field(default_factory=list)
    total_amount: float = 0.0
    
    @property
    def event_type(self) -> str:
        return "OrderCreated"
    
    @property
    def aggregate_id(self) -> str:
        return self.order_id
    
    def _get_data(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "items": self.items,
            "total_amount": self.total_amount,
        }


@dataclass
class PaymentReceived(Event):
    """Event raised when payment is received."""
    
    order_id: str = ""
    payment_id: str = ""
    amount: float = 0.0
    payment_method: str = ""
    
    @property
    def event_type(self) -> str:
        return "PaymentReceived"
    
    @property
    def aggregate_id(self) -> str:
        return self.order_id
    
    def _get_data(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "payment_id": self.payment_id,
            "amount": self.amount,
            "payment_method": self.payment_method,
        }


@dataclass
class OrderShipped(Event):
    """Event raised when order is shipped."""
    
    order_id: str = ""
    tracking_number: str = ""
    carrier: str = ""
    
    @property
    def event_type(self) -> str:
        return "OrderShipped"
    
    @property
    def aggregate_id(self) -> str:
        return self.order_id
    
    def _get_data(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
        }


@dataclass
class OrderDelivered(Event):
    """Event raised when order is delivered."""
    
    order_id: str = ""
    delivered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def event_type(self) -> str:
        return "OrderDelivered"
    
    @property
    def aggregate_id(self) -> str:
        return self.order_id
    
    def _get_data(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "delivered_at": self.delivered_at.isoformat(),
        }


# =============================================================================
# Event Envelope (Metadata Wrapper)
# =============================================================================

@dataclass
class EventEnvelope:
    """
    Wrapper that adds metadata to events.
    Useful for tracking, routing, and debugging.
    """
    
    event: Event
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None  # ID of event that caused this
    user_id: Optional[str] = None
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": self.user_id,
            "source": self.source,
            "metadata": self.metadata,
            "event": self.event.to_dict(),
        }


# =============================================================================
# Event Handler Interface
# =============================================================================

T = TypeVar("T", bound=Event)


class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle an event."""
        pass


class TypedEventHandler(EventHandler):
    """Event handler that handles specific event types."""
    
    def __init__(self):
        self._handlers: Dict[str, callable] = {}
    
    def register(self, event_type: Type[Event]):
        """Decorator to register a handler for an event type."""
        def decorator(func):
            self._handlers[event_type.__name__] = func
            return func
        return decorator
    
    async def handle(self, event: Event) -> None:
        """Route event to appropriate handler."""
        handler = self._handlers.get(event.event_type)
        if handler:
            await handler(event)


# =============================================================================
# Event Bus (In-Memory)
# =============================================================================

class EventBus:
    """
    Simple in-memory event bus for publishing and subscribing to events.
    """
    
    def __init__(self):
        self._handlers: Dict[str, list] = {}
        self._global_handlers: list = []
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def subscribe_all(self, handler: callable) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        # Call type-specific handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            await handler(event)
        
        # Call global handlers
        for handler in self._global_handlers:
            await handler(event)
    
    async def publish_many(self, events: list) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)


# =============================================================================
# Event Priority
# =============================================================================

class EventPriority(Enum):
    """Priority levels for event processing."""
    
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PrioritizedEvent:
    """Event with priority for ordered processing."""
    
    event: Event
    priority: EventPriority = EventPriority.NORMAL
    
    def __lt__(self, other: "PrioritizedEvent") -> bool:
        return self.priority.value > other.priority.value  # Higher priority first


# =============================================================================
# Demo
# =============================================================================

async def demo():
    print("=" * 60)
    print("Event Basics Demo")
    print("=" * 60)
    
    # Create events
    print("\n=== Creating Events ===\n")
    
    order_created = OrderCreated(
        order_id="order-123",
        customer_id="customer-456",
        items=[
            {"product_id": "prod-1", "quantity": 2, "price": 29.99},
            {"product_id": "prod-2", "quantity": 1, "price": 49.99},
        ],
        total_amount=109.97,
    )
    
    payment_received = PaymentReceived(
        order_id="order-123",
        payment_id="pay-789",
        amount=109.97,
        payment_method="credit_card",
    )
    
    print(f"Event 1: {order_created.event_type}")
    print(f"  ID: {order_created.event_id}")
    print(f"  Aggregate: {order_created.aggregate_id}")
    print(f"  Time: {order_created.timestamp}")
    
    print(f"\nEvent 2: {payment_received.event_type}")
    print(f"  ID: {payment_received.event_id}")
    
    # Serialize
    print("\n=== Serialization ===\n")
    
    event_dict = order_created.to_dict()
    print(f"To dict: {json.dumps(event_dict, indent=2)}")
    
    # Event envelope
    print("\n=== Event Envelope ===\n")
    
    envelope = EventEnvelope(
        event=order_created,
        user_id="user-123",
        source="order-service",
        metadata={"ip_address": "192.168.1.1"},
    )
    
    print(f"Correlation ID: {envelope.correlation_id}")
    print(f"Source: {envelope.source}")
    
    # Event bus
    print("\n=== Event Bus ===\n")
    
    bus = EventBus()
    
    # Subscribe to events
    async def on_order_created(event: OrderCreated):
        print(f"  Handler received: {event.event_type} for order {event.order_id}")
    
    async def on_any_event(event: Event):
        print(f"  Global handler: {event.event_type}")
    
    bus.subscribe("OrderCreated", on_order_created)
    bus.subscribe_all(on_any_event)
    
    # Publish events
    print("Publishing events...")
    await bus.publish(order_created)
    await bus.publish(payment_received)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
