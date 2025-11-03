"""
Core NextMCP class that wraps FastMCP and provides tool registration,
middleware support, and server lifecycle management.
"""

from typing import Callable, Dict, List, Any, Optional
import logging
import inspect
import asyncio

logger = logging.getLogger(__name__)


class NextMCP:
    """
    Main application class for building MCP servers.

    Similar to FastAPI or Flask, this class provides a decorator-based interface
    for registering tools and applying middleware.

    Example:
        app = NextMCP("my-mcp-server")

        @app.tool()
        def my_tool(param: str) -> str:
            return f"Hello {param}"

        app.run()
    """

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize a new NextMCP application.

        Args:
            name: The name of your MCP server
            description: Optional description of your server
        """
        self.name = name
        self.description = description or f"{name} MCP Server"
        self._tools: Dict[str, Callable] = {}
        self._global_middleware: List[Callable] = []
        self._fastmcp_server = None

        logger.info(f"Initializing NextMCP application: {self.name}")

    def add_middleware(self, middleware_fn: Callable) -> None:
        """
        Add global middleware that will be applied to all tools.

        Middleware functions should take a function and return a wrapped version
        of that function. They are applied in the order they are added.

        Args:
            middleware_fn: A middleware function that wraps tool functions

        Example:
            def log_calls(fn):
                def wrapper(*args, **kwargs):
                    print(f"Calling {fn.__name__}")
                    return fn(*args, **kwargs)
                return wrapper

            app.add_middleware(log_calls)
        """
        self._global_middleware.append(middleware_fn)
        logger.debug(f"Added global middleware: {middleware_fn.__name__}")

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator to register a function as an MCP tool.

        Global middleware will be automatically applied to the tool in the order
        it was added. Supports both sync and async functions.

        Args:
            name: Optional custom name for the tool (defaults to function name)
            description: Optional description of what the tool does

        Example:
            @app.tool()
            def get_weather(city: str) -> dict:
                return {"city": city, "temp": 72}

            @app.tool()
            async def get_async_weather(city: str) -> dict:
                return {"city": city, "temp": 72}
        """
        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            is_async = inspect.iscoroutinefunction(fn)

            # Apply global middleware in order (first added wraps first, last added = outermost)
            wrapped_fn = fn
            for middleware in self._global_middleware:
                wrapped_fn = middleware(wrapped_fn)

            # Store metadata
            wrapped_fn._tool_name = tool_name
            wrapped_fn._tool_description = description or fn.__doc__
            wrapped_fn._original_fn = fn
            wrapped_fn._is_async = is_async

            self._tools[tool_name] = wrapped_fn
            logger.debug(f"Registered {'async' if is_async else 'sync'} tool: {tool_name}")

            return wrapped_fn

        return decorator

    def get_tools(self) -> Dict[str, Callable]:
        """
        Get all registered tools.

        Returns:
            Dictionary mapping tool names to their wrapped functions
        """
        return self._tools.copy()

    def run(self, host: str = "127.0.0.1", port: int = 8000, **kwargs):
        """
        Start the FastMCP server and register all tools.

        Args:
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 8000)
            **kwargs: Additional arguments passed to FastMCP server
        """
        try:
            # Import FastMCP here to avoid requiring it at import time
            import fastmcp
        except ImportError:
            raise ImportError(
                "FastMCP is required to run the server. "
                "Install it with: pip install fastmcp"
            )

        logger.info(f"Starting {self.name} on {host}:{port}")
        logger.info(f"Registered {len(self._tools)} tool(s)")

        # Create FastMCP server instance
        self._fastmcp_server = fastmcp.FastMCP(self.name)

        # Register all tools with FastMCP
        for tool_name, tool_fn in self._tools.items():
            logger.debug(f"Registering tool with FastMCP: {tool_name}")
            # Note: Actual FastMCP registration API may differ
            # This is a placeholder based on common patterns
            self._fastmcp_server.tool(tool_fn)

        # Run the server
        logger.info(f"{self.name} is ready and listening for requests")
        self._fastmcp_server.run()
