"""
Tests for WebSocket transport functionality.

This module tests:
- WebSocket server creation and connection handling
- Tool invocation over WebSocket
- Message framing and protocol
- WebSocket client functionality
- Error handling
"""

import pytest
import asyncio
import json
from nextmcp import NextMCP
from nextmcp.transport import WebSocketTransport, WebSocketClient, WSMessage

# Skip all tests if websockets is not available
pytest.importorskip("websockets")


class TestWSMessage:
    """Test WebSocket message structure."""

    def test_request_message(self):
        """Test creating a request message."""
        msg = WSMessage.request("123", "test_method", {"param": "value"})
        assert msg.id == "123"
        assert msg.method == "test_method"
        assert msg.params == {"param": "value"}
        assert msg.result is None
        assert msg.error is None

    def test_response_message(self):
        """Test creating a response message."""
        msg = WSMessage.response("123", {"result": "data"})
        assert msg.id == "123"
        assert msg.result == {"result": "data"}
        assert msg.method is None
        assert msg.error is None

    def test_error_message(self):
        """Test creating an error message."""
        msg = WSMessage.error_response("123", "Something went wrong", -1)
        assert msg.id == "123"
        assert msg.error == {"code": -1, "message": "Something went wrong"}
        assert msg.result is None

    def test_json_serialization(self):
        """Test JSON serialization."""
        msg = WSMessage.request("123", "test", {"key": "value"})
        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["id"] == "123"
        assert parsed["method"] == "test"
        assert parsed["params"] == {"key": "value"}
        assert "result" not in parsed  # None values should be omitted
        assert "error" not in parsed

    def test_json_deserialization(self):
        """Test JSON deserialization."""
        json_str = '{"id": "456", "method": "test", "params": {"x": 1}}'
        msg = WSMessage.from_json(json_str)

        assert msg.id == "456"
        assert msg.method == "test"
        assert msg.params == {"x": 1}


class TestWebSocketTransport:
    """Test WebSocket transport server."""

    @pytest.mark.asyncio
    async def test_server_creation(self):
        """Test creating a WebSocket transport server."""
        app = NextMCP("test-app")

        @app.tool()
        async def test_tool(x: int) -> int:
            return x * 2

        transport = WebSocketTransport(app)
        assert transport.app == app
        assert len(transport.connections) == 0

    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test starting and stopping the server."""
        app = NextMCP("test-app")
        transport = WebSocketTransport(app)

        # Start server in background
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8766)
        )

        # Give it time to start
        await asyncio.sleep(0.2)

        # Stop server
        await transport.stop()

        # Wait for server task to complete
        try:
            await asyncio.wait_for(server_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_client_connection(self):
        """Test client connecting to server."""
        app = NextMCP("test-app")

        @app.tool()
        async def add(a: int, b: int) -> int:
            return a + b

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8767)
        )

        # Give server time to start
        await asyncio.sleep(0.2)

        try:
            # Connect client
            async with WebSocketClient("ws://127.0.0.1:8767") as client:
                # Should connect successfully
                assert client.websocket is not None

        finally:
            # Stop server
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_list_tools_over_websocket(self):
        """Test listing tools over WebSocket."""
        app = NextMCP("test-app")

        @app.tool()
        async def tool1(x: int) -> int:
            """First tool"""
            return x * 2

        @app.tool()
        async def tool2(x: int) -> int:
            """Second tool"""
            return x * 3

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8768)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8768") as client:
                # List tools
                result = await client.list_tools()

                assert "tools" in result
                assert len(result["tools"]) == 2

                tool_names = [t["name"] for t in result["tools"]]
                assert "tool1" in tool_names
                assert "tool2" in tool_names

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_invoke_async_tool_over_websocket(self):
        """Test invoking an async tool over WebSocket."""
        app = NextMCP("test-app")

        @app.tool()
        async def multiply(x: int, y: int) -> int:
            await asyncio.sleep(0.01)
            return x * y

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8769)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8769") as client:
                # Invoke tool
                result = await client.invoke_tool("multiply", {"x": 5, "y": 3})
                assert result == 15

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_invoke_sync_tool_over_websocket(self):
        """Test invoking a sync tool over WebSocket."""
        app = NextMCP("test-app")

        @app.tool()
        def add(x: int, y: int) -> int:
            return x + y

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8770)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8770") as client:
                # Invoke sync tool
                result = await client.invoke_tool("add", {"x": 10, "y": 20})
                assert result == 30

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_concurrent_tool_invocations(self):
        """Test multiple concurrent tool invocations."""
        app = NextMCP("test-app")

        @app.tool()
        async def slow_double(x: int) -> int:
            await asyncio.sleep(0.1)
            return x * 2

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8771)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8771") as client:
                # Invoke multiple tools concurrently
                tasks = [
                    client.invoke_tool("slow_double", {"x": i})
                    for i in range(5)
                ]

                results = await asyncio.gather(*tasks)
                assert results == [0, 2, 4, 6, 8]

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self):
        """Test error when tool is not found."""
        app = NextMCP("test-app")

        @app.tool()
        async def existing_tool() -> str:
            return "ok"

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8772)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8772") as client:
                # Try to invoke non-existent tool
                with pytest.raises(Exception, match="Tool not found"):
                    await client.invoke_tool("nonexistent_tool", {})

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_invalid_parameters_error(self):
        """Test error when parameters are invalid."""
        app = NextMCP("test-app")

        @app.tool()
        async def requires_params(x: int, y: int) -> int:
            return x + y

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8773)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8773") as client:
                # Try with missing parameters
                with pytest.raises(Exception, match="Invalid parameters"):
                    await client.invoke_tool("requires_params", {"x": 5})  # Missing y

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_ping_pong(self):
        """Test ping/pong for connection health."""
        app = NextMCP("test-app")
        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8774)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8774") as client:
                # Test ping
                pong = await client.ping()
                assert pong is True

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Test multiple clients connecting to the same server."""
        app = NextMCP("test-app")

        @app.tool()
        async def get_value(x: int) -> int:
            return x * 2

        transport = WebSocketTransport(app)

        # Start server
        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8775)
        )

        await asyncio.sleep(0.2)

        try:
            # Connect multiple clients
            async with WebSocketClient("ws://127.0.0.1:8775") as client1:
                async with WebSocketClient("ws://127.0.0.1:8775") as client2:
                    # Both clients should be able to invoke tools
                    result1 = await client1.invoke_tool("get_value", {"x": 5})
                    result2 = await client2.invoke_tool("get_value", {"x": 10})

                    assert result1 == 10
                    assert result2 == 20

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass


class TestWebSocketClient:
    """Test WebSocket client functionality."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client as async context manager."""
        app = NextMCP("test-app")
        transport = WebSocketTransport(app)

        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8776)
        )

        await asyncio.sleep(0.2)

        try:
            async with WebSocketClient("ws://127.0.0.1:8776") as client:
                assert client.websocket is not None

            # After exiting context, connection should be closed
            assert client.websocket is None or client.websocket.closed

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_client_manual_connect_disconnect(self):
        """Test manual connect and disconnect."""
        app = NextMCP("test-app")
        transport = WebSocketTransport(app)

        server_task = asyncio.create_task(
            transport.start(host="127.0.0.1", port=8777)
        )

        await asyncio.sleep(0.2)

        try:
            client = WebSocketClient("ws://127.0.0.1:8777")

            # Connect
            await client.connect()
            assert client.websocket is not None

            # Disconnect
            await client.disconnect()
            assert client.websocket is None or client.websocket.closed

        finally:
            await transport.stop()
            try:
                await asyncio.wait_for(server_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass
