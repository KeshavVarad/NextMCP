"""
Tool registration and schema validation utilities.

This module provides decorators and utilities for defining MCP tools
with optional Pydantic schema validation.
"""

import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    BaseModel = None
    ValidationError = None

logger = logging.getLogger(__name__)


def tool(schema: type | None = None, name: str | None = None, description: str | None = None):
    """
    Standalone decorator for defining tools with optional schema validation.

    This can be used independently or in conjunction with NextMCP.tool().

    Args:
        schema: Optional Pydantic BaseModel class for input validation
        name: Optional custom name for the tool
        description: Optional description of the tool

    Example:
        from nextmcp.tools import tool
        from pydantic import BaseModel

        class WeatherInput(BaseModel):
            city: str
            units: str = "fahrenheit"

        @tool(schema=WeatherInput)
        def get_weather(city: str, units: str = "fahrenheit"):
            return {"city": city, "temp": 72, "units": units}
    """

    def decorator(fn: Callable) -> Callable:
        # Store metadata on the function
        fn._tool_schema = schema
        fn._tool_name = name or fn.__name__
        fn._tool_description = description or fn.__doc__

        # If schema validation is requested, wrap the function
        if schema is not None:
            if BaseModel is None:
                logger.warning(
                    f"Pydantic schema specified for {fn.__name__} but pydantic is not installed. "
                    "Install with: pip install pydantic"
                )
                return fn

            @wraps(fn)
            def validated_wrapper(*args, **kwargs):
                try:
                    # Validate inputs using the schema
                    validated_input = schema(**kwargs)
                    # Call the original function with validated data
                    return fn(*args, **validated_input.model_dump())
                except ValidationError as e:
                    logger.error(f"Validation error in {fn.__name__}: {e}")
                    raise ValueError(f"Invalid input: {e}") from e

            # Preserve metadata on wrapped function
            validated_wrapper._tool_schema = schema
            validated_wrapper._tool_name = fn._tool_name
            validated_wrapper._tool_description = fn._tool_description
            validated_wrapper._original_fn = fn

            return validated_wrapper

        return fn

    return decorator


def get_tool_metadata(fn: Callable) -> dict:
    """
    Extract metadata from a tool function.

    Args:
        fn: A function decorated with @tool or @app.tool()

    Returns:
        Dictionary containing tool metadata (name, description, schema, parameters)
    """
    metadata = {
        "name": getattr(fn, "_tool_name", fn.__name__),
        "description": getattr(fn, "_tool_description", fn.__doc__ or ""),
        "schema": getattr(fn, "_tool_schema", None),
    }

    # Extract parameter information from function signature
    sig = inspect.signature(fn)
    type_hints = get_type_hints(fn) if hasattr(fn, "__annotations__") else {}

    parameters = {}
    for param_name, param in sig.parameters.items():
        param_info = {
            "name": param_name,
            "type": type_hints.get(param_name, Any).__name__ if param_name in type_hints else "Any",
            "required": param.default == inspect.Parameter.empty,
            "default": param.default if param.default != inspect.Parameter.empty else None,
        }
        parameters[param_name] = param_info

    metadata["parameters"] = parameters

    return metadata


def generate_tool_docs(tools: dict) -> str:
    """
    Generate markdown documentation for a set of tools.

    Args:
        tools: Dictionary mapping tool names to tool functions

    Returns:
        Markdown-formatted documentation string
    """
    docs = ["# MCP Tools Documentation\n"]

    for _tool_name, tool_fn in tools.items():
        metadata = get_tool_metadata(tool_fn)

        docs.append(f"\n## {metadata['name']}\n")
        docs.append(f"{metadata['description']}\n")

        if metadata["parameters"]:
            docs.append("\n### Parameters\n")
            for param_name, param_info in metadata["parameters"].items():
                required = "required" if param_info["required"] else "optional"
                default = (
                    f" (default: {param_info['default']})"
                    if param_info["default"] is not None
                    else ""
                )
                docs.append(f"- `{param_name}` ({param_info['type']}, {required}){default}\n")

        if metadata["schema"]:
            docs.append("\n### Schema\n")
            docs.append(f"Uses Pydantic model: `{metadata['schema'].__name__}`\n")

        docs.append("\n---\n")

    return "".join(docs)


class ToolRegistry:
    """
    Registry for managing tools across multiple modules or packages.

    This allows for organizing tools into namespaces or categories.
    """

    def __init__(self):
        self._tools: dict = {}
        self._namespaces: dict = {}

    def register(self, fn: Callable, namespace: str | None = None):
        """
        Register a tool function, optionally in a namespace.

        Args:
            fn: The tool function to register
            namespace: Optional namespace/category for the tool
        """
        tool_name = getattr(fn, "_tool_name", fn.__name__)

        if namespace:
            if namespace not in self._namespaces:
                self._namespaces[namespace] = {}
            self._namespaces[namespace][tool_name] = fn
            full_name = f"{namespace}.{tool_name}"
        else:
            full_name = tool_name

        self._tools[full_name] = fn
        logger.debug(f"Registered tool in registry: {full_name}")

    def get(self, name: str) -> Callable | None:
        """Get a tool by its full name."""
        return self._tools.get(name)

    def get_namespace(self, namespace: str) -> dict:
        """Get all tools in a specific namespace."""
        return self._namespaces.get(namespace, {})

    def all(self) -> dict:
        """Get all registered tools."""
        return self._tools.copy()
