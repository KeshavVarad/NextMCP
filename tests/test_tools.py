"""
Unit tests for nextmcp.tools module
"""

import pytest

from nextmcp.tools import ToolRegistry, generate_tool_docs, get_tool_metadata, tool


def test_tool_decorator_basic():
    """Test basic tool decorator"""

    @tool()
    def my_tool(x: int) -> int:
        return x * 2

    assert my_tool._tool_name == "my_tool"
    assert my_tool(5) == 10


def test_tool_decorator_with_name():
    """Test tool decorator with custom name"""

    @tool(name="custom_tool")
    def my_function():
        return "hello"

    assert my_function._tool_name == "custom_tool"


def test_tool_decorator_with_description():
    """Test tool decorator with description"""

    @tool(description="A test tool")
    def described_tool():
        return "test"

    assert described_tool._tool_description == "A test tool"


def test_get_tool_metadata():
    """Test extracting metadata from tool functions"""

    @tool(name="test_tool", description="A test tool")
    def my_tool(x: int, y: str = "default") -> str:
        return f"{x}: {y}"

    metadata = get_tool_metadata(my_tool)

    assert metadata["name"] == "test_tool"
    assert metadata["description"] == "A test tool"
    assert "x" in metadata["parameters"]
    assert "y" in metadata["parameters"]
    assert metadata["parameters"]["x"]["required"] is True
    assert metadata["parameters"]["y"]["required"] is False
    assert metadata["parameters"]["y"]["default"] == "default"


def test_generate_tool_docs():
    """Test generating markdown documentation for tools"""

    @tool(name="add", description="Add two numbers")
    def add_numbers(a: int, b: int) -> int:
        return a + b

    @tool(name="greet", description="Greet a person")
    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    tools = {"add": add_numbers, "greet": greet}

    docs = generate_tool_docs(tools)

    assert "# MCP Tools Documentation" in docs
    assert "## add" in docs
    assert "Add two numbers" in docs
    assert "## greet" in docs
    assert "Greet a person" in docs


def test_tool_registry():
    """Test ToolRegistry for organizing tools"""
    registry = ToolRegistry()

    @tool()
    def tool1():
        return 1

    @tool()
    def tool2():
        return 2

    registry.register(tool1)
    registry.register(tool2, namespace="math")

    # Check tools are registered
    assert registry.get("tool1") is tool1
    assert registry.get("math.tool2") is tool2

    # Check namespace
    math_tools = registry.get_namespace("math")
    assert "tool2" in math_tools

    # Check all tools
    all_tools = registry.all()
    assert "tool1" in all_tools
    assert "math.tool2" in all_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
