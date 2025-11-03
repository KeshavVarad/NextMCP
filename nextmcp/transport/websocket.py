"""
WebSocket transport for NextMCP.

Provides WebSocket server and client implementations for MCP tool invocation
over WebSocket connections using JSON-RPC style messaging.
"""

import asyncio
import inspect
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

try:
    from websockets.asyncio.server import ServerConnection, serve
    from websockets.exceptions import ConnectionClosed

    WEBSOCKETS_AVAILABLE = True
    WebSocketServerProtocol = ServerConnection  # Type alias for compatibility
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any  # Type hint fallback
    ServerConnection = Any

logger = logging.getLogger(__name__)


@dataclass
class WSMessage:
    """WebSocket message structure following JSON-RPC pattern."""

    id: str | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Convert message to JSON string."""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        """Parse message from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)

    @classmethod
    def request(cls, id: str, method: str, params: dict[str, Any] | None = None) -> "WSMessage":
        """Create a request message."""
        return cls(id=id, method=method, params=params or {})

    @classmethod
    def response(cls, id: str, result: Any) -> "WSMessage":
        """Create a success response message."""
        return cls(id=id, result=result)

    @classmethod
    def error_response(
        cls, id: str | None, error_message: str, error_code: int = -1
    ) -> "WSMessage":
        """Create an error response message."""
        return cls(id=id, error={"code": error_code, "message": error_message})


class WebSocketTransport:
    """
    WebSocket transport for NextMCP applications.

    Provides a WebSocket server that can handle tool invocations over
    WebSocket connections using JSON-RPC style messaging.

    Example:
        app = NextMCP("ws-server")

        @app.tool()
        async def my_tool(param: str) -> str:
            return f"Hello {param}"

        transport = WebSocketTransport(app)
        await transport.start(host="0.0.0.0", port=8765)
    """

    def __init__(self, app: Any):
        """
        Initialize WebSocket transport.

        Args:
            app: NextMCP application instance
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library is required for WebSocket transport. "
                "Install it with: pip install websockets"
            )

        self.app = app
        self.connections: set[WebSocketServerProtocol] = set()
        self.server = None
        self._stop_event = asyncio.Event()

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """
        Handle a WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        # Register connection
        self.connections.add(websocket)
        remote_addr = websocket.remote_address
        logger.info(f"[WS] New connection from {remote_addr}")

        try:
            # Send welcome message
            welcome = WSMessage.response(
                id="welcome",
                result={
                    "message": f"Connected to {self.app.name}",
                    "tools": list(self.app.get_tools().keys()),
                },
            )
            await websocket.send(welcome.to_json())

            # Handle messages
            async for message in websocket:
                await self.handle_message(websocket, message)

        except ConnectionClosed:
            logger.info(f"[WS] Connection closed: {remote_addr}")
        except Exception as e:
            logger.error(f"[WS] Error handling connection: {e}", exc_info=True)
        finally:
            # Unregister connection
            self.connections.discard(websocket)
            logger.info(
                f"[WS] Disconnected: {remote_addr} ({len(self.connections)} active connections)"
            )

    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """
        Handle an incoming WebSocket message.

        Args:
            websocket: WebSocket connection
            message: Raw message string
        """
        try:
            # Parse message
            ws_msg = WSMessage.from_json(message)
            logger.debug(f"[WS] Received: {ws_msg.method} (id: {ws_msg.id})")

            # Handle different message types
            if ws_msg.method == "list_tools":
                # List available tools
                tools = self.app.get_tools()
                tool_info = []
                for name, fn in tools.items():
                    tool_info.append(
                        {
                            "name": name,
                            "description": getattr(fn, "_tool_description", None),
                            "is_async": getattr(fn, "_is_async", False),
                        }
                    )

                response = WSMessage.response(ws_msg.id, {"tools": tool_info})
                await websocket.send(response.to_json())

            elif ws_msg.method == "invoke_tool":
                # Invoke a tool
                await self.invoke_tool(websocket, ws_msg)

            elif ws_msg.method == "ping":
                # Ping/pong for connection health
                response = WSMessage.response(ws_msg.id, {"pong": True})
                await websocket.send(response.to_json())

            else:
                # Unknown method
                error = WSMessage.error_response(
                    ws_msg.id, f"Unknown method: {ws_msg.method}", error_code=-32601
                )
                await websocket.send(error.to_json())

        except json.JSONDecodeError as e:
            logger.error(f"[WS] Invalid JSON: {e}")
            error = WSMessage.error_response(None, f"Invalid JSON: {str(e)}", error_code=-32700)
            await websocket.send(error.to_json())

        except Exception as e:
            logger.error(f"[WS] Error handling message: {e}", exc_info=True)
            error = WSMessage.error_response(None, f"Internal error: {str(e)}", error_code=-32603)
            await websocket.send(error.to_json())

    async def invoke_tool(self, websocket: WebSocketServerProtocol, message: WSMessage):
        """
        Invoke a tool and send the response.

        Args:
            websocket: WebSocket connection
            message: Request message
        """
        try:
            tool_name = message.params.get("tool_name")
            tool_params = message.params.get("params", {})

            if not tool_name:
                error = WSMessage.error_response(
                    message.id, "Missing tool_name in params", error_code=-32602
                )
                await websocket.send(error.to_json())
                return

            # Get tool
            tools = self.app.get_tools()
            if tool_name not in tools:
                error = WSMessage.error_response(
                    message.id, f"Tool not found: {tool_name}", error_code=-32601
                )
                await websocket.send(error.to_json())
                return

            tool_fn = tools[tool_name]

            # Invoke tool (handle both sync and async)
            logger.info(f"[WS] Invoking tool: {tool_name} with params: {tool_params}")

            if inspect.iscoroutinefunction(tool_fn):
                result = await tool_fn(**tool_params)
            else:
                # Run sync function in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool_fn(**tool_params))

            # Send response
            response = WSMessage.response(message.id, result)
            await websocket.send(response.to_json())
            logger.debug(f"[WS] Tool {tool_name} completed successfully")

        except TypeError as e:
            # Invalid parameters
            error = WSMessage.error_response(
                message.id, f"Invalid parameters: {str(e)}", error_code=-32602
            )
            await websocket.send(error.to_json())

        except Exception as e:
            # Tool execution error
            logger.error(f"[WS] Tool execution error: {e}", exc_info=True)
            error = WSMessage.error_response(
                message.id, f"Tool execution error: {str(e)}", error_code=-32000
            )
            await websocket.send(error.to_json())

    async def broadcast(self, message: WSMessage):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast
        """
        if not self.connections:
            logger.debug("[WS] No connections to broadcast to")
            return

        logger.info(f"[WS] Broadcasting to {len(self.connections)} connection(s)")

        # Send to all connections concurrently
        tasks = [websocket.send(message.to_json()) for websocket in self.connections]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Start the WebSocket server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info(f"[WS] Starting WebSocket server on ws://{host}:{port}")
        logger.info(f"[WS] Available tools: {list(self.app.get_tools().keys())}")

        async with serve(self.handle_connection, host, port) as server:
            self.server = server
            logger.info("[WS] Server started successfully")

            # Wait until stop is requested
            await self._stop_event.wait()

    async def stop(self):
        """Stop the WebSocket server."""
        logger.info("[WS] Stopping WebSocket server...")
        self._stop_event.set()

        # Close all connections
        if self.connections:
            close_tasks = [ws.close() for ws in self.connections]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self.connections.clear()

        logger.info("[WS] Server stopped")

    def run(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Run the WebSocket server (blocking).

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        try:
            asyncio.run(self.start(host, port))
        except KeyboardInterrupt:
            logger.info("[WS] Server interrupted by user")
