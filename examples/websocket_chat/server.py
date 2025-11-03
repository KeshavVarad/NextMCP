"""
WebSocket Chat Server - Example NextMCP Application with WebSocket Transport

This example demonstrates:
- Using WebSocket transport instead of HTTP
- Real-time bidirectional communication
- Broadcasting messages to multiple clients
- Async tools with WebSocket
"""

import asyncio
from nextmcp import NextMCP, setup_logging, log_calls_async, error_handler_async
from nextmcp.transport import WebSocketTransport
from datetime import datetime, timezone
from typing import List

# Setup logging
setup_logging(level="INFO")

# Create the MCP application
app = NextMCP(
    name="websocket-chat-server",
    description="A real-time chat server using WebSocket transport"
)

# Add global async middleware
app.add_middleware(log_calls_async)
app.add_middleware(error_handler_async)

# Store chat messages in memory
chat_history: List[dict] = []


@app.tool(
    name="send_message",
    description="Send a chat message"
)
async def send_message(username: str, message: str) -> dict:
    """
    Send a chat message.

    Args:
        username: Username of the sender
        message: Message content

    Returns:
        Message confirmation with timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    chat_message = {
        "username": username,
        "message": message,
        "timestamp": timestamp
    }

    chat_history.append(chat_message)

    print(f"[{timestamp}] {username}: {message}")

    return {
        "status": "sent",
        "message": chat_message
    }


@app.tool(
    name="get_messages",
    description="Get recent chat messages"
)
async def get_messages(limit: int = 10) -> dict:
    """
    Get recent chat messages.

    Args:
        limit: Maximum number of messages to return

    Returns:
        List of recent messages
    """
    recent_messages = chat_history[-limit:] if limit > 0 else chat_history

    return {
        "messages": recent_messages,
        "total": len(chat_history)
    }


@app.tool(
    name="get_stats",
    description="Get chat statistics"
)
async def get_stats() -> dict:
    """
    Get chat server statistics.

    Returns:
        Server statistics
    """
    unique_users = set(msg["username"] for msg in chat_history)

    return {
        "total_messages": len(chat_history),
        "unique_users": len(unique_users),
        "users": list(unique_users)
    }


@app.tool(
    name="clear_history",
    description="Clear chat history (admin only)"
)
async def clear_history() -> dict:
    """
    Clear all chat history.

    Returns:
        Confirmation message
    """
    global chat_history
    message_count = len(chat_history)
    chat_history = []

    return {
        "status": "cleared",
        "messages_deleted": message_count
    }


@app.tool(
    name="echo",
    description="Echo a message back (for testing)"
)
async def echo(message: str) -> dict:
    """
    Echo a message back.

    Args:
        message: Message to echo

    Returns:
        Echoed message
    """
    await asyncio.sleep(0.1)  # Simulate processing

    return {
        "echoed": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Run the WebSocket server
if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Chat Server")
    print("=" * 60)
    print("Starting server...")
    print(f"Registered tools: {list(app.get_tools().keys())}")
    print()

    # Create WebSocket transport
    transport = WebSocketTransport(app)

    # Run on ws://0.0.0.0:8765
    print("Server will be available at: ws://localhost:8765")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        transport.run(host="0.0.0.0", port=8765)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
