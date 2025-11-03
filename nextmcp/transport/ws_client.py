"""
WebSocket client for connecting to NextMCP WebSocket servers.

Provides a simple client interface for invoking tools over WebSocket.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

try:
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from nextmcp.transport.websocket import WSMessage

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    Client for connecting to NextMCP WebSocket servers.

    Example:
        async with WebSocketClient("ws://localhost:8765") as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {tools}")

            # Invoke a tool
            result = await client.invoke_tool("my_tool", {"param": "value"})
            print(f"Result: {result}")
    """

    def __init__(self, uri: str):
        """
        Initialize WebSocket client.

        Args:
            uri: WebSocket server URI (e.g., ws://localhost:8765)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library is required for WebSocket client. "
                "Install it with: pip install websockets"
            )

        self.uri = uri
        self.websocket = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._message_handler_task = None
        self._on_notification: Callable | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the WebSocket server."""
        logger.info(f"[WS Client] Connecting to {self.uri}")
        self.websocket = await connect(self.uri)

        # Start message handler
        self._message_handler_task = asyncio.create_task(self._handle_messages())

        # Wait for welcome message
        welcome = await self._wait_for_message("welcome", timeout=5.0)
        logger.info(f"[WS Client] Connected: {welcome}")

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if not self.websocket:
            return

        logger.info("[WS Client] Disconnecting...")

        # Cancel message handler
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass

        # Close connection
        await self.websocket.close()
        self.websocket = None

        logger.info("[WS Client] Disconnected")

    async def _handle_messages(self):
        """Handle incoming messages from the server."""
        try:
            async for message in self.websocket:
                ws_msg = WSMessage.from_json(message)

                # Handle response to pending request
                if ws_msg.id and ws_msg.id in self._pending_requests:
                    future = self._pending_requests.pop(ws_msg.id)

                    if ws_msg.error:
                        future.set_exception(Exception(f"Server error: {ws_msg.error['message']}"))
                    else:
                        future.set_result(ws_msg.result)

                # Handle server-initiated notifications
                elif ws_msg.method and self._on_notification:
                    await self._on_notification(ws_msg)

        except ConnectionClosed:
            logger.info("[WS Client] Connection closed by server")
        except Exception as e:
            logger.error(f"[WS Client] Error in message handler: {e}", exc_info=True)

    async def _send_request(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 30.0
    ) -> Any:
        """
        Send a request and wait for response.

        Args:
            method: Method name
            params: Method parameters
            timeout: Request timeout in seconds

        Returns:
            Response result

        Raises:
            Exception: If request fails or times out
        """
        if not self.websocket:
            raise Exception("Not connected")

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send request
        request = WSMessage.request(request_id, method, params)
        await self.websocket.send(request.to_json())
        logger.debug(f"[WS Client] Sent request: {method} (id: {request_id})")

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError as e:
            self._pending_requests.pop(request_id, None)
            raise Exception(f"Request timeout after {timeout}s") from e

    async def _wait_for_message(self, message_id: str, timeout: float = 5.0) -> Any:
        """Wait for a specific message by ID."""
        future = asyncio.Future()
        self._pending_requests[message_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError as e:
            self._pending_requests.pop(message_id, None)
            raise Exception(f"Timeout waiting for message: {message_id}") from e

    async def list_tools(self) -> dict[str, Any]:
        """
        List available tools on the server.

        Returns:
            Dictionary with tool information
        """
        result = await self._send_request("list_tools")
        return result

    async def invoke_tool(
        self, tool_name: str, params: dict[str, Any] | None = None, timeout: float = 30.0
    ) -> Any:
        """
        Invoke a tool on the server.

        Args:
            tool_name: Name of the tool to invoke
            params: Tool parameters
            timeout: Invocation timeout in seconds

        Returns:
            Tool execution result
        """
        request_params = {"tool_name": tool_name, "params": params or {}}
        result = await self._send_request("invoke_tool", request_params, timeout=timeout)
        return result

    async def ping(self) -> bool:
        """
        Send a ping to the server.

        Returns:
            True if pong received
        """
        result = await self._send_request("ping")
        return result.get("pong", False)

    def on_notification(self, handler: Callable):
        """
        Set handler for server-initiated notifications.

        Args:
            handler: Async function to handle notifications
        """
        self._on_notification = handler


# Convenience function for quick tool invocation
async def invoke_remote_tool(uri: str, tool_name: str, params: dict[str, Any] | None = None) -> Any:
    """
    Convenience function to invoke a tool on a remote server.

    Args:
        uri: WebSocket server URI
        tool_name: Tool to invoke
        params: Tool parameters

    Returns:
        Tool execution result

    Example:
        result = await invoke_remote_tool(
            "ws://localhost:8765",
            "my_tool",
            {"param": "value"}
        )
    """
    async with WebSocketClient(uri) as client:
        return await client.invoke_tool(tool_name, params)
