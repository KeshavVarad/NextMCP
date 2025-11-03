"""
Unit tests for nextmcp.core module
"""

import pytest
from nextmcp.core import NextMCP


def test_nextmcp_initialization():
    """Test that NextMCP can be initialized with a name"""
    app = NextMCP("test-app")
    assert app.name == "test-app"
    assert app.description == "test-app MCP Server"
    assert len(app._tools) == 0
    assert len(app._global_middleware) == 0


def test_tool_registration():
    """Test that tools can be registered with the @tool decorator"""
    app = NextMCP("test-app")

    @app.tool()
    def test_tool(x: int) -> int:
        return x * 2

    assert "test_tool" in app._tools
    assert app._tools["test_tool"](5) == 10


def test_tool_registration_with_custom_name():
    """Test tool registration with custom name"""
    app = NextMCP("test-app")

    @app.tool(name="custom_name")
    def my_tool():
        return "hello"

    assert "custom_name" in app._tools
    assert app._tools["custom_name"]() == "hello"


def test_global_middleware():
    """Test that global middleware is applied to all tools"""
    app = NextMCP("test-app")

    # Create a middleware that adds 1 to the result
    def add_one_middleware(fn):
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result + 1
        return wrapper

    app.add_middleware(add_one_middleware)

    @app.tool()
    def double(x: int) -> int:
        return x * 2

    # Middleware should be applied: (5 * 2) + 1 = 11
    assert app._tools["double"](5) == 11


def test_multiple_middleware_stacking():
    """Test that multiple middleware are applied in correct order"""
    app = NextMCP("test-app")

    # First middleware: multiply by 2
    def multiply_middleware(fn):
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result * 2
        return wrapper

    # Second middleware: add 1
    def add_one_middleware(fn):
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result + 1
        return wrapper

    # Add middleware in order
    app.add_middleware(multiply_middleware)
    app.add_middleware(add_one_middleware)

    @app.tool()
    def get_five() -> int:
        return 5

    # Should apply: ((5 * 2) + 1) = 11
    # First middleware applied = multiply (outermost)
    # Second middleware applied = add_one (innermost)
    assert app._tools["get_five"]() == 11


def test_get_tools():
    """Test that get_tools returns a copy of registered tools"""
    app = NextMCP("test-app")

    @app.tool()
    def tool1():
        return 1

    @app.tool()
    def tool2():
        return 2

    tools = app.get_tools()
    assert len(tools) == 2
    assert "tool1" in tools
    assert "tool2" in tools

    # Verify it's a copy
    tools["tool3"] = lambda: 3
    assert "tool3" not in app._tools


def test_tool_with_description():
    """Test tool registration with description"""
    app = NextMCP("test-app")

    @app.tool(description="This is a test tool")
    def described_tool():
        return "test"

    tool_fn = app._tools["described_tool"]
    assert tool_fn._tool_description == "This is a test tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
