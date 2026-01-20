"""
Asynchronous Communication Patterns
===================================
Message-based service-to-service communication.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Callable, List, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod
import threading
import queue


# =============================================================================
# Message Models
# =============================================================================

class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Base message for async communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    
    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "priority": self.priority.value,
        })
    
    @classmethod
    def from_json(cls, data: str) -> "Message":
        obj = json.loads(data)
        obj["priority"] = MessagePriority(obj.get("priority", 1))
        return cls(**obj)


@dataclass
class Event(Message):
    """
    Event message - something that happened.
    Events are facts and cannot be rejected.
    """
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    version: int = 1


@dataclass
class Command(Message):
    """
    Command message - request to do something.
    Commands can be rejected by the handler.
    """
    target_service: str = ""
    expected_version: Optional[int] = None


# =============================================================================
# Message Broker (In-Memory Implementation)
# =============================================================================

class MessageHandler(ABC):
    """Abstract base for message handlers."""
    
    @abstractmethod
    async def handle(self, message: Message) -> Optional[Message]:
        """Handle a message, optionally returning a reply."""
        pass


class InMemoryMessageBroker:
    """
    Simple in-memory message broker for demonstration.
    In production, use RabbitMQ, Kafka, Redis Streams, etc.
    """
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    def create_queue(self, name: str, max_size: int = 1000):
        """Create a message queue."""
        if name not in self._queues:
            self._queues[name] = asyncio.Queue(maxsize=max_size)
            print(f"Created queue: {name}")
    
    async def publish(self, queue_name: str, message: Message):
        """Publish a message to a queue."""
        if queue_name not in self._queues:
            self.create_queue(queue_name)
        
        await self._queues[queue_name].put(message)
        print(f"Published {message.type} to {queue_name}")
    
    async def publish_event(self, topic: str, event: Event):
        """Publish an event to subscribers (pub/sub pattern)."""
        if topic not in self._subscribers:
            return
        
        for callback in self._subscribers[topic]:
            try:
                await callback(event)
            except Exception as e:
                print(f"Error in subscriber: {e}")
    
    def subscribe(self, topic: str, callback: Callable[[Event], Awaitable[None]]):
        """Subscribe to events on a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        
        self._subscribers[topic].append(callback)
        print(f"Subscribed to topic: {topic}")
    
    def register_handler(self, message_type: str, handler: MessageHandler):
        """Register a handler for a message type."""
        self._handlers[message_type] = handler
        print(f"Registered handler for: {message_type}")
    
    async def consume(self, queue_name: str) -> Optional[Message]:
        """Consume a message from a queue."""
        if queue_name not in self._queues:
            return None
        
        return await self._queues[queue_name].get()
    
    async def consume_with_handler(self, queue_name: str):
        """Consume and handle messages from a queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self.consume(queue_name),
                    timeout=1.0
                )
                
                if message and message.type in self._handlers:
                    handler = self._handlers[message.type]
                    
                    try:
                        reply = await handler.handle(message)
                        
                        # Send reply if requested
                        if reply and message.reply_to:
                            await self.publish(message.reply_to, reply)
                            
                    except Exception as e:
                        print(f"Handler error: {e}")
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Consume error: {e}")
    
    async def start(self, queues: List[str]):
        """Start consuming from queues."""
        self._running = True
        
        for queue_name in queues:
            self.create_queue(queue_name)
            task = asyncio.create_task(self.consume_with_handler(queue_name))
            self._tasks.append(task)
        
        print(f"Started consuming from {len(queues)} queues")
    
    async def stop(self):
        """Stop all consumers."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._tasks.clear()
        print("Stopped all consumers")


# Global broker instance
broker = InMemoryMessageBroker()


# =============================================================================
# Common Message Types
# =============================================================================

# User Events
class UserCreated(Event):
    def __init__(self, user_id: int, name: str, email: str, **kwargs):
        super().__init__(
            type="user.created",
            payload={"user_id": user_id, "name": name, "email": email},
            aggregate_id=str(user_id),
            aggregate_type="User",
            **kwargs
        )


class UserUpdated(Event):
    def __init__(self, user_id: int, changes: Dict, **kwargs):
        super().__init__(
            type="user.updated",
            payload={"user_id": user_id, "changes": changes},
            aggregate_id=str(user_id),
            aggregate_type="User",
            **kwargs
        )


# Order Events
class OrderCreated(Event):
    def __init__(self, order_id: int, user_id: int, total: float, **kwargs):
        super().__init__(
            type="order.created",
            payload={"order_id": order_id, "user_id": user_id, "total": total},
            aggregate_id=str(order_id),
            aggregate_type="Order",
            **kwargs
        )


class OrderStatusChanged(Event):
    def __init__(self, order_id: int, old_status: str, new_status: str, **kwargs):
        super().__init__(
            type="order.status_changed",
            payload={
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
            },
            aggregate_id=str(order_id),
            aggregate_type="Order",
            **kwargs
        )


# Commands
class CreateOrder(Command):
    def __init__(self, user_id: int, items: List[Dict], **kwargs):
        super().__init__(
            type="order.create",
            payload={"user_id": user_id, "items": items},
            target_service="order-service",
            **kwargs
        )


class SendNotification(Command):
    def __init__(self, user_id: int, channel: str, message: str, **kwargs):
        super().__init__(
            type="notification.send",
            payload={"user_id": user_id, "channel": channel, "message": message},
            target_service="notification-service",
            **kwargs
        )


# =============================================================================
# Message Handlers
# =============================================================================

class OrderCreatedHandler(MessageHandler):
    """Handle order created events by sending notifications."""
    
    async def handle(self, message: Message) -> Optional[Message]:
        order_id = message.payload.get("order_id")
        user_id = message.payload.get("user_id")
        total = message.payload.get("total")
        
        print(f"📬 OrderCreatedHandler: Order {order_id} for user {user_id}")
        
        # Create notification command
        notification = SendNotification(
            user_id=user_id,
            channel="email",
            message=f"Your order #{order_id} for ${total:.2f} has been received!",
            correlation_id=message.correlation_id,
        )
        
        # Publish to notification queue
        await broker.publish("notifications", notification)
        
        return None


class NotificationHandler(MessageHandler):
    """Handle notification commands."""
    
    async def handle(self, message: Message) -> Optional[Message]:
        user_id = message.payload.get("user_id")
        channel = message.payload.get("channel")
        msg = message.payload.get("message")
        
        print(f"📧 NotificationHandler: Sending {channel} to user {user_id}")
        print(f"   Message: {msg}")
        
        # Simulate sending
        await asyncio.sleep(0.1)
        
        return None


# =============================================================================
# Request/Reply Pattern
# =============================================================================

class RequestReplyClient:
    """
    Implements request/reply pattern over async messaging.
    """
    
    def __init__(self, broker: InMemoryMessageBroker):
        self.broker = broker
        self._pending: Dict[str, asyncio.Future] = {}
        self._reply_queue = f"replies-{uuid.uuid4().hex[:8]}"
    
    async def start(self):
        """Start listening for replies."""
        self.broker.create_queue(self._reply_queue)
        asyncio.create_task(self._consume_replies())
    
    async def _consume_replies(self):
        """Consume reply messages."""
        while True:
            try:
                message = await asyncio.wait_for(
                    self.broker.consume(self._reply_queue),
                    timeout=1.0
                )
                
                if message and message.correlation_id in self._pending:
                    future = self._pending.pop(message.correlation_id)
                    if not future.done():
                        future.set_result(message)
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Reply consumer error: {e}")
    
    async def request(
        self,
        queue: str,
        message: Message,
        timeout: float = 30.0,
    ) -> Optional[Message]:
        """
        Send a request and wait for reply.
        """
        # Setup reply tracking
        correlation_id = str(uuid.uuid4())
        message.correlation_id = correlation_id
        message.reply_to = self._reply_queue
        
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[correlation_id] = future
        
        # Send request
        await self.broker.publish(queue, message)
        
        try:
            # Wait for reply
            reply = await asyncio.wait_for(future, timeout=timeout)
            return reply
        except asyncio.TimeoutError:
            self._pending.pop(correlation_id, None)
            return None


# =============================================================================
# Dead Letter Queue
# =============================================================================

class DeadLetterQueue:
    """
    Handles messages that fail processing.
    """
    
    def __init__(self, broker: InMemoryMessageBroker):
        self.broker = broker
        self._dlq_name = "dead-letters"
        self.broker.create_queue(self._dlq_name)
        self._failed_messages: List[Dict] = []
    
    async def send_to_dlq(
        self,
        original_message: Message,
        error: str,
        original_queue: str,
        retry_count: int = 0,
    ):
        """Send a failed message to DLQ."""
        dlq_message = Message(
            type="dead_letter",
            payload={
                "original_message": original_message.to_json(),
                "error": error,
                "original_queue": original_queue,
                "retry_count": retry_count,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=original_message.correlation_id,
        )
        
        await self.broker.publish(self._dlq_name, dlq_message)
        self._failed_messages.append(dlq_message.payload)
        
        print(f"⚠️ Message sent to DLQ: {original_message.type}")
    
    def get_failed_messages(self) -> List[Dict]:
        """Get all failed messages."""
        return self._failed_messages


# =============================================================================
# Demo
# =============================================================================

async def demo():
    """Demonstrate async communication patterns."""
    
    print("=" * 60)
    print("Asynchronous Communication Patterns Demo")
    print("=" * 60)
    
    # 1. Setup handlers
    print("\n1. Setting up message handlers")
    print("-" * 40)
    
    broker.register_handler("order.created", OrderCreatedHandler())
    broker.register_handler("notification.send", NotificationHandler())
    
    # 2. Start consuming
    await broker.start(["orders", "notifications"])
    
    # 3. Publish events
    print("\n2. Publishing Events (Pub/Sub)")
    print("-" * 40)
    
    # Subscribe to events
    async def log_event(event: Event):
        print(f"📢 Event received: {event.type}")
    
    broker.subscribe("user.*", log_event)
    broker.subscribe("order.*", log_event)
    
    # Publish events
    user_event = UserCreated(user_id=1, name="John", email="john@example.com")
    await broker.publish_event("user.*", user_event)
    
    order_event = OrderCreated(order_id=100, user_id=1, total=99.99)
    await broker.publish("orders", order_event)  # To queue
    await broker.publish_event("order.*", order_event)  # To subscribers
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    # 4. Command pattern
    print("\n3. Sending Commands")
    print("-" * 40)
    
    create_cmd = CreateOrder(
        user_id=1,
        items=[{"product": "Widget", "qty": 2}],
        correlation_id="cmd-123",
    )
    
    await broker.publish("orders", create_cmd)
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    # 5. Dead letter queue
    print("\n4. Dead Letter Queue Demo")
    print("-" * 40)
    
    dlq = DeadLetterQueue(broker)
    
    # Simulate failed message
    failed_msg = Message(type="test.failed", payload={"data": "important"})
    await dlq.send_to_dlq(
        failed_msg,
        error="Processing failed: connection timeout",
        original_queue="test-queue",
        retry_count=3,
    )
    
    print(f"DLQ messages: {len(dlq.get_failed_messages())}")
    
    # Cleanup
    await broker.stop()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("""
    ================================================
    Asynchronous Communication Patterns
    ================================================
    
    This module demonstrates:
    
    1. Message Types
       - Events (facts that happened)
       - Commands (requests to do something)
    
    2. Message Broker
       - Queue-based messaging
       - Pub/Sub pattern
       - Message handlers
    
    3. Patterns
       - Request/Reply
       - Dead Letter Queue
       - Event-driven workflows
    
    In production, replace InMemoryMessageBroker with:
    - RabbitMQ (pika/aio-pika)
    - Apache Kafka (aiokafka)
    - Redis Streams (redis-py)
    - AWS SQS/SNS
    ================================================
    """)
    
    asyncio.run(demo())
