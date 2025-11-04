"""
Tests for async functionality in NextMCP.

This module tests:
- Async tool registration and execution
- Async middleware application
- Mixed sync/async tool support
- Async middleware behavior
"""

import asyncio
import time

import pytest

from nextmcp import NextMCP
from nextmcp.middleware import (
    cache_results_async,
    error_handler_async,
    log_calls_async,
    rate_limit_async,
    require_auth_async,
    timeout_async,
)


class TestAsyncToolRegistration:
    """Test async tool registration and metadata."""

    def test_async_tool_registration(self):
        """Test that async tools are properly registered."""
        app = NextMCP("test-app")

        @app.tool()
        async def async_tool(x: int) -> int:
            return x * 2

        tools = app.get_tools()
        assert "async_tool" in tools
        assert hasattr(tools["async_tool"], "_is_async")
        assert tools["async_tool"]._is_async is True

    def test_sync_tool_registration(self):
        """Test that sync tools are properly marked as non-async."""
        app = NextMCP("test-app")

        @app.tool()
        def sync_tool(x: int) -> int:
            return x * 2

        tools = app.get_tools()
        assert "sync_tool" in tools
        assert hasattr(tools["sync_tool"], "_is_async")
        assert tools["sync_tool"]._is_async is False

    def test_mixed_sync_async_tools(self):
        """Test that both sync and async tools can coexist."""
        app = NextMCP("test-app")

        @app.tool()
        def sync_tool(x: int) -> int:
            return x * 2

        @app.tool()
        async def async_tool(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 3

        tools = app.get_tools()
        assert len(tools) == 2
        assert tools["sync_tool"]._is_async is False
        assert tools["async_tool"]._is_async is True


class TestAsyncToolExecution:
    """Test execution of async tools."""

    @pytest.mark.asyncio
    async def test_basic_async_tool(self):
        """Test that async tools execute correctly."""
        app = NextMCP("test-app")

        @app.tool()
        async def add(a: int, b: int) -> int:
            await asyncio.sleep(0.01)
            return a + b

        result = await add(5, 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_async_tool_with_await(self):
        """Test async tool that awaits other async operations."""
        app = NextMCP("test-app")

        async def fetch_data():
            await asyncio.sleep(0.01)
            return {"data": "value"}

        @app.tool()
        async def process_data() -> dict:
            data = await fetch_data()
            data["processed"] = True
            return data

        result = await process_data()
        assert result["data"] == "value"
        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_concurrent_async_tools(self):
        """Test that async tools can run concurrently."""
        app = NextMCP("test-app")

        @app.tool()
        async def slow_task(duration: float, value: int) -> int:
            await asyncio.sleep(duration)
            return value

        # Run multiple tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(
            slow_task(0.1, 1),
            slow_task(0.1, 2),
            slow_task(0.1, 3),
        )
        elapsed = time.time() - start_time

        # Should take ~0.1s (concurrent), not 0.3s (sequential)
        assert elapsed < 0.2
        assert results == [1, 2, 3]


class TestAsyncMiddleware:
    """Test async middleware functionality."""

    @pytest.mark.asyncio
    async def test_log_calls_async(self):
        """Test async logging middleware."""
        app = NextMCP("test-app")
        app.add_middleware(log_calls_async)

        @app.tool()
        async def sample_tool(x: int) -> int:
            return x * 2

        result = await sample_tool(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_error_handler_async(self):
        """Test async error handling middleware."""
        app = NextMCP("test-app")
        app.add_middleware(error_handler_async)

        @app.tool()
        async def failing_tool(x: int) -> int:
            raise ValueError("Test error")

        result = await failing_tool(5)
        assert result["error"] is True
        assert result["error_type"] == "ValueError"
        assert "Test error" in result["error_message"]

    @pytest.mark.asyncio
    async def test_rate_limit_async(self):
        """Test async rate limiting middleware."""
        app = NextMCP("test-app")
        app.add_middleware(rate_limit_async(max_calls=2, time_window=1))

        @app.tool()
        async def limited_tool(x: int) -> int:
            return x * 2

        # First two calls should succeed
        result1 = await limited_tool(1)
        result2 = await limited_tool(2)
        assert result1 == 2
        assert result2 == 4

        # Third call should fail
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await limited_tool(3)

    @pytest.mark.asyncio
    async def test_cache_results_async(self):
        """Test async result caching middleware."""
        call_count = {"count": 0}

        app = NextMCP("test-app")

        @app.tool()
        @cache_results_async(ttl_seconds=1)
        async def cached_tool(x: int) -> int:
            call_count["count"] += 1
            await asyncio.sleep(0.01)
            return x * 2

        # First call - should execute
        result1 = await cached_tool(5)
        assert result1 == 10
        assert call_count["count"] == 1

        # Second call with same args - should use cache
        result2 = await cached_tool(5)
        assert result2 == 10
        assert call_count["count"] == 1  # Not incremented

        # Call with different args - should execute
        result3 = await cached_tool(10)
        assert result3 == 20
        assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_timeout_async(self):
        """Test async timeout middleware."""
        app = NextMCP("test-app")

        @app.tool()
        @timeout_async(seconds=1)
        async def quick_tool(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        @app.tool()
        @timeout_async(seconds=1)
        async def slow_tool(x: int) -> int:
            await asyncio.sleep(2)
            return x * 2

        # Quick tool should succeed
        result = await quick_tool(5)
        assert result == 10

        # Slow tool should timeout
        with pytest.raises(TimeoutError, match="exceeded .* second timeout"):
            await slow_tool(5)

    @pytest.mark.asyncio
    async def test_require_auth_async(self):
        """Test async authentication middleware."""
        app = NextMCP("test-app")
        app.add_middleware(require_auth_async(valid_keys={"secret-key"}))

        @app.tool()
        async def protected_tool(auth_key: str, data: str) -> dict:
            return {"data": data, "authenticated": True}

        # With valid key
        result = await protected_tool(auth_key="secret-key", data="test")
        assert result["authenticated"] is True

        # With invalid key
        with pytest.raises(ValueError, match="Authentication failed"):
            await protected_tool(auth_key="wrong-key", data="test")

        # Without key
        with pytest.raises(ValueError, match="Authentication required"):
            await protected_tool(data="test")


class TestAsyncMiddlewareStacking:
    """Test that async middleware stack correctly."""

    @pytest.mark.asyncio
    async def test_multiple_async_middleware(self):
        """Test stacking multiple async middleware."""
        execution_order = []

        def make_tracking_middleware(name: str):
            def middleware(fn):
                async def wrapper(*args, **kwargs):
                    execution_order.append(f"{name}_before")
                    result = await fn(*args, **kwargs)
                    execution_order.append(f"{name}_after")
                    return result

                return wrapper

            return middleware

        app = NextMCP("test-app")
        app.add_middleware(make_tracking_middleware("first"))
        app.add_middleware(make_tracking_middleware("second"))

        @app.tool()
        async def sample_tool(x: int) -> int:
            execution_order.append("tool_execution")
            return x * 2

        await sample_tool(5)

        # Middleware should execute in correct order
        # First middleware added wraps first (innermost), second wraps that (outermost)
        assert execution_order == [
            "second_before",  # Second middleware (outermost) executes first
            "first_before",
            "tool_execution",
            "first_after",
            "second_after",  # Second middleware (outermost) finishes last
        ]

    @pytest.mark.asyncio
    async def test_async_middleware_with_error_handler(self):
        """Test that error handler works with other async middleware."""
        app = NextMCP("test-app")
        app.add_middleware(log_calls_async)
        app.add_middleware(error_handler_async)

        @app.tool()
        async def failing_tool(x: int) -> int:
            raise ValueError("Test error")

        result = await failing_tool(5)
        # Error handler should catch the error and return structured response
        assert result["error"] is True
        assert result["error_type"] == "ValueError"


class TestAsyncPerformance:
    """Test performance characteristics of async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_execution_is_faster(self):
        """Verify that concurrent async execution is faster than sequential."""
        app = NextMCP("test-app")

        @app.tool()
        async def slow_operation(duration: float) -> str:
            await asyncio.sleep(duration)
            return "done"

        # Concurrent execution
        start_time = time.time()
        await asyncio.gather(
            slow_operation(0.1),
            slow_operation(0.1),
            slow_operation(0.1),
        )
        concurrent_time = time.time() - start_time

        # Sequential execution
        start_time = time.time()
        await slow_operation(0.1)
        await slow_operation(0.1)
        await slow_operation(0.1)
        sequential_time = time.time() - start_time

        # Concurrent should be significantly faster
        assert concurrent_time < 0.2  # ~0.1s
        assert sequential_time > 0.3  # ~0.3s
        assert concurrent_time < sequential_time * 0.5


class TestAsyncEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_async_tool_with_exception(self):
        """Test that exceptions in async tools are properly raised."""
        app = NextMCP("test-app")

        @app.tool()
        async def failing_tool() -> int:
            raise RuntimeError("Something went wrong")

        with pytest.raises(RuntimeError, match="Something went wrong"):
            await failing_tool()

    @pytest.mark.asyncio
    async def test_async_tool_returns_none(self):
        """Test async tools that return None."""
        app = NextMCP("test-app")

        @app.tool()
        async def none_tool() -> None:
            await asyncio.sleep(0.01)
            return None

        result = await none_tool()
        assert result is None

    @pytest.mark.asyncio
    async def test_async_tool_with_default_args(self):
        """Test async tools with default arguments."""
        app = NextMCP("test-app")

        @app.tool()
        async def tool_with_defaults(a: int, b: int = 10) -> int:
            await asyncio.sleep(0.01)
            return a + b

        result1 = await tool_with_defaults(5)
        assert result1 == 15

        result2 = await tool_with_defaults(5, 20)
        assert result2 == 25
