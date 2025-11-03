"""
Transport layer for NextMCP.

Provides different transport mechanisms for MCP tool invocation:
- WebSocket transport for bidirectional, real-time communication
- HTTP transport (via FastMCP)
"""

from nextmcp.transport.websocket import WebSocketTransport, WSMessage
from nextmcp.transport.ws_client import WebSocketClient, invoke_remote_tool

__all__ = [
    "WebSocketTransport",
    "WSMessage",
    "WebSocketClient",
    "invoke_remote_tool",
]
