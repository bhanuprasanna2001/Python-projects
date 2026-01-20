"""
WebSocket Server
================
FastAPI-based WebSocket server demonstrating real-time communication.

Features:
- Multiple concurrent connections
- Room-based messaging
- Private messaging
- Broadcasting
- Connection health monitoring (heartbeat)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import asyncio

from connection_manager import manager

app = FastAPI(title="WebSocket Demo Server")

# Serve static files for web client
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def get_web_client():
    """Serve the web-based WebSocket client."""
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/stats")
async def get_stats():
    """Get server statistics."""
    return {
        "total_connections": manager.connection_count,
        "rooms": manager.get_all_rooms(),
        "room_details": {
            room: len(users) 
            for room, users in manager.rooms.items()
        }
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: str,
    room: str = Query(default="general")
):
    """
    Main WebSocket endpoint.
    
    Args:
        websocket: The WebSocket connection
        client_id: Unique identifier for the client
        room: Initial room to join (default: general)
    """
    # Accept connection
    connected = await manager.connect(websocket, client_id)
    
    if not connected:
        await websocket.close(code=4000, reason="Client ID already in use")
        return
    
    # Join specified room if not general
    if room != "general":
        await manager.join_room(client_id, room)
    
    # Send welcome message
    await manager.send_personal(client_id, {
        "type": "system",
        "event": "info",
        "content": f"Welcome {client_id}! You are in room: {room}",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Notify others
    await manager.broadcast_to_room(
        room,
        {
            "type": "system",
            "event": "join",
            "content": f"{client_id} has joined the chat",
            "user": client_id,
            "timestamp": datetime.utcnow().isoformat()
        },
        exclude={client_id}
    )
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            await handle_message(client_id, data)
            
    except WebSocketDisconnect:
        await handle_disconnect(client_id)
    except Exception as e:
        print(f"[ERROR] {client_id}: {e}")
        await handle_disconnect(client_id)


async def handle_message(client_id: str, data: dict):
    """
    Route incoming messages to appropriate handlers.
    
    Message types:
    - chat: Broadcast to room
    - private: Send to specific user
    - room: Room management (join/leave)
    - heartbeat: Connection health check
    """
    msg_type = data.get("type", "chat")
    
    if msg_type == "chat":
        await handle_chat_message(client_id, data)
    
    elif msg_type == "private":
        await handle_private_message(client_id, data)
    
    elif msg_type == "room":
        await handle_room_message(client_id, data)
    
    elif msg_type == "heartbeat":
        await handle_heartbeat(client_id, data)
    
    else:
        await manager.send_personal(client_id, {
            "type": "system",
            "event": "error",
            "content": f"Unknown message type: {msg_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_chat_message(client_id: str, data: dict):
    """Handle chat messages - broadcast to room."""
    room = data.get("room", "general")
    content = data.get("content", "")
    
    if not content.strip():
        return
    
    message = {
        "type": "chat",
        "sender": client_id,
        "content": content,
        "room": room,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_room(room, message)


async def handle_private_message(client_id: str, data: dict):
    """Handle private messages between users."""
    recipient = data.get("recipient")
    content = data.get("content", "")
    
    if not recipient or not content.strip():
        await manager.send_personal(client_id, {
            "type": "system",
            "event": "error",
            "content": "Private message requires 'recipient' and 'content'",
            "timestamp": datetime.utcnow().isoformat()
        })
        return
    
    if recipient not in manager.active_connections:
        await manager.send_personal(client_id, {
            "type": "system",
            "event": "error",
            "content": f"User '{recipient}' is not online",
            "timestamp": datetime.utcnow().isoformat()
        })
        return
    
    message = {
        "type": "private",
        "sender": client_id,
        "recipient": recipient,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to both sender and recipient
    await manager.send_personal(recipient, message)
    await manager.send_personal(client_id, message)


async def handle_room_message(client_id: str, data: dict):
    """Handle room management messages."""
    action = data.get("action")
    room = data.get("room")
    
    if action == "join" and room:
        await manager.join_room(client_id, room)
        await manager.send_personal(client_id, {
            "type": "system",
            "event": "info",
            "content": f"Joined room: {room}",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif action == "leave" and room:
        await manager.leave_room(client_id, room)
        await manager.send_personal(client_id, {
            "type": "system",
            "event": "info",
            "content": f"Left room: {room}",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif action == "list":
        rooms = manager.get_all_rooms()
        await manager.send_personal(client_id, {
            "type": "room_list",
            "rooms": rooms,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif action == "users" and room:
        users = manager.get_room_users(room)
        await manager.send_personal(client_id, {
            "type": "user_list",
            "room": room,
            "users": users,
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_heartbeat(client_id: str, data: dict):
    """Handle heartbeat ping/pong."""
    action = data.get("action")
    
    if action == "ping":
        await manager.send_personal(client_id, {
            "type": "heartbeat",
            "action": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_disconnect(client_id: str):
    """Handle client disconnection."""
    # Get rooms before disconnecting
    user_rooms = list(manager.user_rooms.get(client_id, set()))
    
    await manager.disconnect(client_id)
    
    # Notify rooms about the departure
    for room in user_rooms:
        await manager.broadcast_to_room(
            room,
            {
                "type": "system",
                "event": "leave",
                "content": f"{client_id} has left the chat",
                "user": client_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Heartbeat background task to detect stale connections
async def heartbeat_checker():
    """Periodic heartbeat to detect dead connections."""
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds
        # In production, you'd track last activity and disconnect stale clients


@app.on_event("startup")
async def startup():
    """Start background tasks."""
    asyncio.create_task(heartbeat_checker())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
