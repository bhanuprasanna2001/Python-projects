"""
Connection Manager
==================
Central hub for managing all WebSocket connections.
Demonstrates the Manager pattern for WebSocket handling.
"""

from fastapi import WebSocket
from typing import Dict, Set, Optional
import asyncio
import json
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections with support for:
    - Individual connections
    - Room-based grouping
    - Broadcasting
    - Private messaging
    """
    
    def __init__(self):
        # All active connections: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Room memberships: {room_name: {client_ids}}
        self.rooms: Dict[str, Set[str]] = {"general": set()}
        
        # Reverse lookup: {client_id: {room_names}}
        self.user_rooms: Dict[str, Set[str]] = {}
        
        # Connection metadata
        self.connection_times: Dict[str, datetime] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket instance
            client_id: Unique identifier for the client
            
        Returns:
            bool: True if connection successful, False if client_id already exists
        """
        if client_id in self.active_connections:
            return False
        
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_times[client_id] = datetime.utcnow()
        self.user_rooms[client_id] = set()
        
        # Auto-join general room
        await self.join_room(client_id, "general")
        
        print(f"[CONNECT] {client_id} connected. Total: {len(self.active_connections)}")
        return True
    
    async def disconnect(self, client_id: str):
        """
        Handle client disconnection with cleanup.
        
        Args:
            client_id: The disconnecting client's ID
        """
        if client_id not in self.active_connections:
            return
        
        # Remove from all rooms
        rooms_to_leave = list(self.user_rooms.get(client_id, set()))
        for room in rooms_to_leave:
            await self.leave_room(client_id, room, notify=False)
        
        # Clean up connection data
        del self.active_connections[client_id]
        del self.connection_times[client_id]
        if client_id in self.user_rooms:
            del self.user_rooms[client_id]
        
        print(f"[DISCONNECT] {client_id} disconnected. Total: {len(self.active_connections)}")
    
    async def join_room(self, client_id: str, room: str, notify: bool = True):
        """
        Add a client to a room.
        
        Args:
            client_id: Client to add
            room: Room name to join
            notify: Whether to notify room members
        """
        if room not in self.rooms:
            self.rooms[room] = set()
        
        self.rooms[room].add(client_id)
        self.user_rooms[client_id].add(room)
        
        if notify:
            await self.broadcast_to_room(
                room,
                {
                    "type": "system",
                    "event": "join",
                    "content": f"{client_id} joined {room}",
                    "user": client_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude={client_id}
            )
        
        print(f"[ROOM] {client_id} joined '{room}'")
    
    async def leave_room(self, client_id: str, room: str, notify: bool = True):
        """
        Remove a client from a room.
        
        Args:
            client_id: Client to remove
            room: Room name to leave
            notify: Whether to notify room members
        """
        if room in self.rooms and client_id in self.rooms[room]:
            self.rooms[room].discard(client_id)
            self.user_rooms[client_id].discard(room)
            
            if notify:
                await self.broadcast_to_room(
                    room,
                    {
                        "type": "system",
                        "event": "leave",
                        "content": f"{client_id} left {room}",
                        "user": client_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Clean up empty rooms (except general)
            if not self.rooms[room] and room != "general":
                del self.rooms[room]
            
            print(f"[ROOM] {client_id} left '{room}'")
    
    async def send_personal(self, client_id: str, message: dict):
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client ID
            message: Message dict to send
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"[ERROR] Failed to send to {client_id}: {e}")
                await self.disconnect(client_id)
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message dict to broadcast
            exclude: Set of client_ids to exclude
        """
        exclude = exclude or set()
        
        # Create tasks for parallel sending
        tasks = []
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                tasks.append(self._safe_send(client_id, websocket, message))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def broadcast_to_room(
        self, 
        room: str, 
        message: dict, 
        exclude: Optional[Set[str]] = None
    ):
        """
        Broadcast a message to all clients in a specific room.
        
        Args:
            room: Room name
            message: Message dict to broadcast
            exclude: Set of client_ids to exclude
        """
        exclude = exclude or set()
        
        if room not in self.rooms:
            return
        
        tasks = []
        for client_id in self.rooms[room]:
            if client_id not in exclude and client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                tasks.append(self._safe_send(client_id, websocket, message))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _safe_send(self, client_id: str, websocket: WebSocket, message: dict):
        """
        Safely send a message, handling failures gracefully.
        
        Args:
            client_id: Client identifier
            websocket: WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[ERROR] Send failed for {client_id}: {e}")
            # Don't disconnect here to avoid recursion in broadcast
    
    def get_room_users(self, room: str) -> list[str]:
        """Get list of users in a room."""
        return list(self.rooms.get(room, set()))
    
    def get_all_rooms(self) -> list[str]:
        """Get list of all active rooms."""
        return list(self.rooms.keys())
    
    def get_user_info(self, client_id: str) -> Optional[dict]:
        """Get information about a connected user."""
        if client_id not in self.active_connections:
            return None
        
        return {
            "client_id": client_id,
            "connected_at": self.connection_times[client_id].isoformat(),
            "rooms": list(self.user_rooms.get(client_id, set()))
        }
    
    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)


# Singleton instance
manager = ConnectionManager()
