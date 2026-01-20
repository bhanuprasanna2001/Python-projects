# Project 1: WebSockets

## 🎯 Learning Objectives
- Understand WebSocket protocol vs HTTP
- Implement real-time bidirectional communication
- Manage multiple concurrent connections
- Handle connection lifecycle (connect, message, disconnect)
- Implement room-based messaging and broadcasting

## 📁 Project Structure
```
01-websockets/
├── server.py           # WebSocket server implementation
├── client.py           # WebSocket client for testing
├── connection_manager.py # Connection management class
├── models.py           # Message models
├── rooms.py            # Room-based messaging
├── static/
│   └── index.html      # Browser-based client
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py

# Open browser at http://localhost:8000 for web client
# Or run the Python client
python client.py
```

## 🔑 Key Concepts

### WebSocket vs HTTP
- **HTTP**: Request-Response, stateless, client initiates
- **WebSocket**: Full-duplex, persistent connection, both can initiate

### Connection Lifecycle
1. **Handshake**: HTTP upgrade request
2. **Open**: Connection established
3. **Message**: Bidirectional data exchange
4. **Close**: Connection terminated

## 📚 Topics Covered
- FastAPI WebSocket endpoints
- Connection manager pattern
- Broadcasting to all/specific clients
- Room/channel-based messaging
- Heartbeat (ping/pong)
- Error handling and reconnection
