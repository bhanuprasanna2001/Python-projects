"""
WebSocket Message Models
========================
Pydantic models for type-safe message handling.
"""

from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class BaseMessage(BaseModel):
    """Base message structure for all WebSocket communications."""
    type: str
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ChatMessage(BaseMessage):
    """Chat message sent between users."""
    type: Literal["chat"] = "chat"
    sender: str
    content: str
    room: Optional[str] = "general"


class SystemMessage(BaseMessage):
    """System notifications (join, leave, etc.)."""
    type: Literal["system"] = "system"
    event: Literal["join", "leave", "error", "info"]
    content: str
    user: Optional[str] = None


class PrivateMessage(BaseMessage):
    """Direct message between two users."""
    type: Literal["private"] = "private"
    sender: str
    recipient: str
    content: str


class RoomMessage(BaseMessage):
    """Room management messages."""
    type: Literal["room"] = "room"
    action: Literal["join", "leave", "create", "list"]
    room: str
    user: Optional[str] = None


class HeartbeatMessage(BaseMessage):
    """Ping/Pong for connection health."""
    type: Literal["heartbeat"] = "heartbeat"
    action: Literal["ping", "pong"]


class UserListMessage(BaseMessage):
    """List of connected users."""
    type: Literal["user_list"] = "user_list"
    users: list[str]
    room: Optional[str] = None


# Type alias for all message types
Message = ChatMessage | SystemMessage | PrivateMessage | RoomMessage | HeartbeatMessage | UserListMessage
