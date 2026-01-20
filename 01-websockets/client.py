"""
WebSocket Client
================
Python-based WebSocket client for testing the server.
Demonstrates programmatic WebSocket interactions.
"""

import asyncio
import websockets
import json
from datetime import datetime


class WebSocketClient:
    """
    WebSocket client with automatic reconnection and message handling.
    """
    
    def __init__(self, uri: str, client_id: str):
        self.uri = uri
        self.client_id = client_id
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.websocket = await websockets.connect(f"{self.uri}/{self.client_id}")
            self.running = True
            print(f"[CONNECTED] as {self.client_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close the WebSocket connection."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            print("[DISCONNECTED]")
    
    async def send_message(self, message: dict):
        """Send a JSON message to the server."""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def send_chat(self, content: str, room: str = "general"):
        """Send a chat message."""
        await self.send_message({
            "type": "chat",
            "content": content,
            "room": room
        })
    
    async def send_private(self, recipient: str, content: str):
        """Send a private message."""
        await self.send_message({
            "type": "private",
            "recipient": recipient,
            "content": content
        })
    
    async def join_room(self, room: str):
        """Join a room."""
        await self.send_message({
            "type": "room",
            "action": "join",
            "room": room
        })
    
    async def leave_room(self, room: str):
        """Leave a room."""
        await self.send_message({
            "type": "room",
            "action": "leave",
            "room": room
        })
    
    async def list_rooms(self):
        """Request list of all rooms."""
        await self.send_message({
            "type": "room",
            "action": "list"
        })
    
    async def ping(self):
        """Send heartbeat ping."""
        await self.send_message({
            "type": "heartbeat",
            "action": "ping"
        })
    
    async def receive_messages(self):
        """
        Continuously receive and display messages.
        Run this in a separate task.
        """
        try:
            while self.running:
                message = await self.websocket.recv()
                data = json.loads(message)
                self._display_message(data)
        except websockets.ConnectionClosed:
            print("[CONNECTION CLOSED]")
        except Exception as e:
            print(f"[ERROR] Receive error: {e}")
    
    def _display_message(self, data: dict):
        """Format and display received message."""
        msg_type = data.get("type", "unknown")
        timestamp = data.get("timestamp", "")[:19]  # Trim microseconds
        
        if msg_type == "chat":
            sender = data.get("sender", "Unknown")
            room = data.get("room", "general")
            content = data.get("content", "")
            print(f"[{timestamp}] [{room}] {sender}: {content}")
        
        elif msg_type == "private":
            sender = data.get("sender", "Unknown")
            content = data.get("content", "")
            print(f"[{timestamp}] [PRIVATE from {sender}]: {content}")
        
        elif msg_type == "system":
            event = data.get("event", "info")
            content = data.get("content", "")
            print(f"[{timestamp}] [SYSTEM/{event.upper()}] {content}")
        
        elif msg_type == "heartbeat":
            print(f"[{timestamp}] [HEARTBEAT] pong received")
        
        elif msg_type == "room_list":
            rooms = data.get("rooms", [])
            print(f"[{timestamp}] [ROOMS] {', '.join(rooms)}")
        
        elif msg_type == "user_list":
            room = data.get("room", "")
            users = data.get("users", [])
            print(f"[{timestamp}] [USERS in {room}] {', '.join(users)}")
        
        else:
            print(f"[{timestamp}] [UNKNOWN] {data}")


async def interactive_client():
    """
    Interactive command-line WebSocket client.
    """
    print("=" * 50)
    print("WebSocket Interactive Client")
    print("=" * 50)
    
    client_id = input("Enter your username: ").strip() or "user1"
    server_url = input("Server URL (default: ws://localhost:8000/ws): ").strip()
    server_url = server_url or "ws://localhost:8000/ws"
    
    client = WebSocketClient(server_url, client_id)
    
    if not await client.connect():
        return
    
    # Start message receiver in background
    receiver_task = asyncio.create_task(client.receive_messages())
    
    print("\nCommands:")
    print("  /msg <text>          - Send message to current room")
    print("  /pm <user> <text>    - Send private message")
    print("  /join <room>         - Join a room")
    print("  /leave <room>        - Leave a room")
    print("  /rooms               - List all rooms")
    print("  /users <room>        - List users in room")
    print("  /ping                - Send heartbeat")
    print("  /quit                - Exit")
    print("-" * 50)
    
    current_room = "general"
    
    try:
        while True:
            # Use asyncio to handle input without blocking
            command = await asyncio.get_event_loop().run_in_executor(
                None, input
            )
            
            if not command:
                continue
            
            if command.startswith("/msg "):
                content = command[5:]
                await client.send_chat(content, current_room)
            
            elif command.startswith("/pm "):
                parts = command[4:].split(" ", 1)
                if len(parts) == 2:
                    await client.send_private(parts[0], parts[1])
                else:
                    print("Usage: /pm <user> <message>")
            
            elif command.startswith("/join "):
                room = command[6:].strip()
                await client.join_room(room)
                current_room = room
            
            elif command.startswith("/leave "):
                room = command[7:].strip()
                await client.leave_room(room)
                if room == current_room:
                    current_room = "general"
            
            elif command == "/rooms":
                await client.list_rooms()
            
            elif command.startswith("/users "):
                room = command[7:].strip()
                await client.send_message({
                    "type": "room",
                    "action": "users",
                    "room": room
                })
            
            elif command == "/ping":
                await client.ping()
            
            elif command == "/quit":
                break
            
            else:
                # Treat as chat message
                await client.send_chat(command, current_room)
    
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        receiver_task.cancel()


async def demo_client():
    """
    Automated demo showing various WebSocket features.
    """
    print("=" * 50)
    print("WebSocket Demo")
    print("=" * 50)
    
    client = WebSocketClient("ws://localhost:8000/ws", "demo_user")
    
    if not await client.connect():
        return
    
    # Start receiver
    receiver_task = asyncio.create_task(client.receive_messages())
    
    await asyncio.sleep(1)
    
    # Demo sequence
    print("\n--- Sending chat message ---")
    await client.send_chat("Hello everyone!")
    await asyncio.sleep(1)
    
    print("\n--- Creating and joining new room ---")
    await client.join_room("python-devs")
    await asyncio.sleep(1)
    
    print("\n--- Sending message to new room ---")
    await client.send_chat("Hello Python developers!", "python-devs")
    await asyncio.sleep(1)
    
    print("\n--- Listing all rooms ---")
    await client.list_rooms()
    await asyncio.sleep(1)
    
    print("\n--- Sending heartbeat ---")
    await client.ping()
    await asyncio.sleep(1)
    
    print("\n--- Demo complete ---")
    await client.disconnect()
    receiver_task.cancel()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_client())
    else:
        asyncio.run(interactive_client())
