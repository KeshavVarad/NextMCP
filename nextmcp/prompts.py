"""
Prompt registration and metadata utilities.

This module provides decorators and utilities for defining MCP prompts
with argument completion support.
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any, get_type_hints

logger = logging.getLogger(__name__)


class PromptArgument:
    """
    Metadata for a prompt argument.

    Attributes:
        name: Argument name
        description: Human-readable description
        type: Argument type (string, integer, etc.)
        required: Whether the argument is required
        default: Default value if not required
        suggestions: Static list of suggested values
        suggestions_fn: Function to generate dynamic suggestions
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        type: str = "string",
        required: bool = True,
        default: Any = None,
        suggestions: list[str] | None = None,
        suggestions_fn: Callable | None = None,
    ):
        self.name = name
        self.description = description
        self.type = type
        self.required = required
        self.default = default
        self.suggestions = suggestions or []
        self.suggestions_fn = suggestions_fn

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "suggestions": self.suggestions,
        }


def prompt(name: str | None = None, description: str | None = None, tags: list[str] | None = None):
    """
    Standalone decorator for defining prompts.

    This can be used independently or in conjunction with NextMCP.prompt().

    Args:
        name: Optional custom name for the prompt
        description: Optional description of the prompt
        tags: Optional tags for categorization

    Example:
        from nextmcp.prompts import prompt

        @prompt(description="Plan a vacation", tags=["travel"])
        def vacation_planner(destination: str, budget: int) -> str:
            return f"Plan a vacation to {destination} with ${budget}"
    """

    def decorator(fn: Callable) -> Callable:
        # Store metadata on the function
        fn._prompt_name = name or fn.__name__
        fn._prompt_description = description or fn.__doc__
        fn._prompt_tags = tags or []
        fn._prompt_arguments = getattr(fn, "_prompt_arguments", [])
        fn._prompt_completions = getattr(fn, "_prompt_completions", {})

        return fn

    return decorator


def argument(
    name: str,
    description: str | None = None,
    type: str = "string",
    required: bool = True,
    default: Any = None,
    suggestions: list[str] | None = None,
    suggestions_fn: Callable | None = None,
):
    """
    Decorator to add argument metadata to a prompt.

    Can be stacked multiple times for multiple arguments.

    Args:
        name: Argument name
        description: Human-readable description
        type: Argument type (string, integer, etc.)
        required: Whether the argument is required
        default: Default value if not required
        suggestions: Static list of suggested values
        suggestions_fn: Function to generate dynamic suggestions

    Example:
        @prompt()
        @argument("destination", description="Where to go", suggestions=["Paris", "Tokyo"])
        @argument("budget", type="integer", description="Total budget")
        def plan_vacation(destination: str, budget: int) -> str:
            return f"Planning vacation to {destination}"
    """

    def decorator(fn: Callable) -> Callable:
        # Initialize arguments list if not present
        if not hasattr(fn, "_prompt_arguments"):
            fn._prompt_arguments = []

        # Add this argument
        arg = PromptArgument(
            name=name,
            description=description,
            type=type,
            required=required,
            default=default,
            suggestions=suggestions,
            suggestions_fn=suggestions_fn,
        )
        fn._prompt_arguments.append(arg)

        return fn

    return decorator


def get_prompt_metadata(fn: Callable) -> dict:
    """
    Extract metadata from a prompt function.

    Args:
        fn: A function decorated with @prompt or @app.prompt()

    Returns:
        Dictionary containing prompt metadata (name, description, arguments)
    """
    metadata = {
        "name": getattr(fn, "_prompt_name", fn.__name__),
        "description": getattr(fn, "_prompt_description", fn.__doc__ or ""),
        "tags": getattr(fn, "_prompt_tags", []),
    }

    # Get explicitly declared arguments
    explicit_args = getattr(fn, "_prompt_arguments", [])

    # Also extract from function signature
    sig = inspect.signature(fn)
    type_hints = get_type_hints(fn) if hasattr(fn, "__annotations__") else {}

    # Build complete argument list
    arguments = []
    for param_name, param in sig.parameters.items():
        # Check if we have explicit metadata for this param
        explicit = next((a for a in explicit_args if a.name == param_name), None)

        if explicit:
            arguments.append(explicit.to_dict())
        else:
            # Auto-generate from signature
            arg_info = {
                "name": param_name,
                "description": None,
                "type": _python_type_to_string(type_hints.get(param_name, str)),
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "suggestions": [],
            }
            arguments.append(arg_info)

    metadata["arguments"] = arguments

    return metadata


def _python_type_to_string(python_type) -> str:
    """Convert Python type to string representation for prompt schema."""
    type_map = {
        int: "integer",
        str: "string",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # Handle type hints
    if hasattr(python_type, "__origin__"):
        origin = python_type.__origin__
        return type_map.get(origin, "string")

    return type_map.get(python_type, "string")


def generate_prompt_docs(prompts: dict) -> str:
    """
    Generate markdown documentation for a set of prompts.

    Args:
        prompts: Dictionary mapping prompt names to prompt functions

    Returns:
        Markdown-formatted documentation string
    """
    docs = ["# MCP Prompts Documentation\n"]

    for _prompt_name, prompt_fn in prompts.items():
        metadata = get_prompt_metadata(prompt_fn)

        docs.append(f"\n## {metadata['name']}\n")
        docs.append(f"{metadata['description']}\n")

        if metadata.get("tags"):
            docs.append(f"\n**Tags:** {', '.join(metadata['tags'])}\n")

        if metadata["arguments"]:
            docs.append("\n### Arguments\n")
            for arg in metadata["arguments"]:
                required = "required" if arg["required"] else "optional"
                default = f" (default: {arg['default']})" if arg["default"] is not None else ""
                suggestions = (
                    f"\n  - Suggestions: {', '.join(arg['suggestions'])}"
                    if arg["suggestions"]
                    else ""
                )
                description = f" - {arg['description']}" if arg["description"] else ""
                docs.append(
                    f"- `{arg['name']}` ({arg['type']}, {required}){default}{description}{suggestions}\n"
                )

        docs.append("\n---\n")

    return "".join(docs)


class PromptRegistry:
    """
    Registry for managing prompts across multiple modules or packages.

    This allows for organizing prompts into namespaces or categories.
    """

    def __init__(self):
        self._prompts: dict = {}
        self._namespaces: dict = {}
        self._completions: dict = {}

    def register(self, fn: Callable, namespace: str | None = None):
        """
        Register a prompt function, optionally in a namespace.

        Args:
            fn: The prompt function to register
            namespace: Optional namespace/category for the prompt
        """
        prompt_name = getattr(fn, "_prompt_name", fn.__name__)

        if namespace:
            if namespace not in self._namespaces:
                self._namespaces[namespace] = {}
            self._namespaces[namespace][prompt_name] = fn
            full_name = f"{namespace}.{prompt_name}"
        else:
            full_name = prompt_name

        self._prompts[full_name] = fn
        logger.debug(f"Registered prompt in registry: {full_name}")

    def register_completion(self, prompt_name: str, arg_name: str, completion_fn: Callable):
        """
        Register a completion function for a prompt argument.

        Args:
            prompt_name: Name of the prompt
            arg_name: Name of the argument
            completion_fn: Function that returns completion suggestions
        """
        key = f"{prompt_name}.{arg_name}"
        self._completions[key] = completion_fn
        logger.debug(f"Registered completion: {key}")

    def get(self, name: str) -> Callable | None:
        """Get a prompt by its full name."""
        return self._prompts.get(name)

    def get_namespace(self, namespace: str) -> dict:
        """Get all prompts in a specific namespace."""
        return self._namespaces.get(namespace, {})

    def get_completion(self, prompt_name: str, arg_name: str) -> Callable | None:
        """Get a completion function for a prompt argument."""
        key = f"{prompt_name}.{arg_name}"
        return self._completions.get(key)

    def all(self) -> dict:
        """Get all registered prompts."""
        return self._prompts.copy()
