# WebSocket Chat Example

This example demonstrates how to use SecureMCP with WebSocket transport for real-time, bidirectional communication.

## Features

- **WebSocket Transport**: Real-time bidirectional communication instead of HTTP
- **Multiple Clients**: Support for multiple concurrent WebSocket connections
- **Async Tools**: All tools are async for optimal performance
- **JSON-RPC Protocol**: Clean message format for tool invocation
- **Client Library**: Easy-to-use WebSocket client for connecting to servers

## Running the Example

### 1. Install Dependencies

```bash
pip install websockets
```

### 2. Start the Server

In one terminal:

```bash
cd examples/websocket_chat
python server.py
```

You should see:

```
===========================================================
WebSocket Chat Server
============================================================
Starting server...
Registered tools: ['send_message', 'get_messages', 'get_stats', 'clear_history', 'echo']

Server will be available at: ws://localhost:8765
Press Ctrl+C to stop
============================================================

[WS] Starting WebSocket server on ws://0.0.0.0:8765
[WS] Server started successfully
```

### 3. Run the Client

In another terminal:

```bash
cd examples/websocket_chat
python client.py
```

The client will:
1. Connect to the server
2. List available tools
3. Send chat messages
4. Retrieve message history
5. Get statistics
6. Test concurrent tool invocations

## Available Tools

### `send_message`
Send a chat message to the server.

```python
result = await client.invoke_tool(
    "send_message",
    {
        "username": "Alice",
        "message": "Hello, world!"
    }
)
```

### `get_messages`
Retrieve recent chat messages.

```python
result = await client.invoke_tool(
    "get_messages",
    {"limit": 10}
)
```

### `get_stats`
Get chat server statistics (total messages, unique users).

```python
stats = await client.invoke_tool("get_stats")
```

### `clear_history`
Clear all chat history.

```python
result = await client.invoke_tool("clear_history")
```

### `echo`
Echo a message back (useful for testing).

```python
result = await client.invoke_tool(
    "echo",
    {"message": "test"}
)
```

## WebSocket Protocol

The WebSocket transport uses JSON-RPC style messages:

### Request Format
```json
{
  "id": "unique-request-id",
  "method": "invoke_tool",
  "params": {
    "tool_name": "send_message",
    "params": {
      "username": "Alice",
      "message": "Hello!"
    }
  }
}
```

### Response Format
```json
{
  "id": "unique-request-id",
  "result": {
    "status": "sent",
    "message": {
      "username": "Alice",
      "message": "Hello!",
      "timestamp": "2025-11-03T10:00:00Z"
    }
  }
}
```

### Error Response
```json
{
  "id": "unique-request-id",
  "error": {
    "code": -32601,
    "message": "Tool not found: invalid_tool"
  }
}
```

## Built-in Methods

The WebSocket transport provides several built-in methods:

### `list_tools`
Get information about all available tools.

### `invoke_tool`
Invoke a tool with parameters.

### `ping`
Test connection health.

## Using in Your Own Application

### Server Side

```python
from securemcp import SecureMCP
from securemcp.transport import WebSocketTransport

app = SecureMCP("my-websocket-app")

@app.tool()
async def my_tool(param: str) -> dict:
    return {"result": param}

# Create WebSocket transport
transport = WebSocketTransport(app)

# Run server
transport.run(host="0.0.0.0", port=8765)
```

### Client Side

```python
from securemcp.transport import WebSocketClient

async def main():
    async with WebSocketClient("ws://localhost:8765") as client:
        # List tools
        tools = await client.list_tools()
        print(f"Available: {tools}")

        # Invoke tool
        result = await client.invoke_tool(
            "my_tool",
            {"param": "value"}
        )
        print(f"Result: {result}")
```

## Concurrent Connections

The WebSocket server can handle multiple clients simultaneously:

```python
# Terminal 1
python server.py

# Terminal 2
python client.py

# Terminal 3
python client.py  # Another client connects

# Terminal 4
python client.py  # Yet another client
```

All clients share the same chat history and can send/receive messages independently.

## Performance Benefits

WebSocket transport provides several advantages:

1. **Lower Latency**: Persistent connection eliminates HTTP handshake overhead
2. **Bidirectional**: Server can push updates to clients
3. **Efficient**: No HTTP header overhead for each request
4. **Real-time**: Perfect for chat, notifications, live updates
5. **Concurrent**: Handles multiple clients efficiently with async/await

## Comparison: HTTP vs WebSocket

| Feature | HTTP (FastMCP) | WebSocket |
|---------|----------------|-----------|
| Connection | One per request | Persistent |
| Latency | Higher | Lower |
| Bidirectional | No | Yes |
| Overhead | HTTP headers | Minimal |
| Use case | Request/response | Real-time |

## Next Steps

- Add authentication to tools
- Implement room-based chat
- Add message broadcasting
- Create a web-based UI
- Add rate limiting
- Implement message persistence
