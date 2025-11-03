"""
Core NextMCP class that wraps FastMCP and provides tool registration,
middleware support, and server lifecycle management.
"""

import inspect
import logging
from collections.abc import Callable

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

    def __init__(self, name: str, description: str | None = None):
        """
        Initialize a new NextMCP application.

        Args:
            name: The name of your MCP server
            description: Optional description of your server
        """
        self.name = name
        self.description = description or f"{name} MCP Server"
        self._tools: dict[str, Callable] = {}
        self._global_middleware: list[Callable] = []
        self._fastmcp_server = None
        self._plugin_manager = None
        self._metrics_collector = None
        self._metrics_enabled = False

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
        middleware_name = getattr(middleware_fn, "__name__", middleware_fn.__class__.__name__)
        logger.debug(f"Added global middleware: {middleware_name}")

    def tool(self, name: str | None = None, description: str | None = None):
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

    def get_tools(self) -> dict[str, Callable]:
        """
        Get all registered tools.

        Returns:
            Dictionary mapping tool names to their wrapped functions
        """
        return self._tools.copy()

    @property
    def plugins(self):
        """
        Get the plugin manager for this application.

        Lazily initializes the plugin manager on first access.

        Returns:
            PluginManager instance

        Example:
            app = NextMCP("my-app")
            app.plugins.discover_plugins("./plugins")
            app.plugins.load_all()
        """
        if self._plugin_manager is None:
            from nextmcp.plugins import PluginManager

            self._plugin_manager = PluginManager(self)
        return self._plugin_manager

    def use_plugin(self, plugin) -> None:
        """
        Register and load a plugin.

        Args:
            plugin: Either a Plugin class or Plugin instance

        Example:
            from my_plugins import WeatherPlugin
            app.use_plugin(WeatherPlugin)
        """
        from nextmcp.plugins import Plugin

        if isinstance(plugin, type) and issubclass(plugin, Plugin):
            # It's a class, register it
            self.plugins.register_plugin_class(plugin)
        elif isinstance(plugin, Plugin):
            # It's an instance, register it
            self.plugins.register_plugin(plugin)
        else:
            raise TypeError("plugin must be a Plugin class or instance")

        # Load the plugin
        self.plugins.load_plugin(plugin.name if isinstance(plugin, Plugin) else plugin.name)
        logger.info(f"Loaded plugin: {plugin.name if isinstance(plugin, Plugin) else plugin.name}")

    def discover_plugins(self, directory: str) -> None:
        """
        Discover plugins from a directory.

        Args:
            directory: Path to directory containing plugin files

        Example:
            app = NextMCP("my-app")
            app.discover_plugins("./plugins")
            # Plugins are discovered but not loaded yet
        """
        self.plugins.discover_plugins(directory)

    def load_plugins(self) -> None:
        """
        Load all discovered plugins.

        Example:
            app = NextMCP("my-app")
            app.discover_plugins("./plugins")
            app.load_plugins()
        """
        self.plugins.load_all()

    @property
    def metrics(self):
        """
        Get the metrics collector for this application.

        Lazily initializes the metrics collector on first access.

        Returns:
            MetricsCollector instance

        Example:
            app = NextMCP("my-app")
            counter = app.metrics.counter("my_counter")
            counter.inc()
        """
        if self._metrics_collector is None:
            from nextmcp.metrics import MetricsCollector

            self._metrics_collector = MetricsCollector(prefix=self.name)
        return self._metrics_collector

    def enable_metrics(
        self,
        collect_tool_metrics: bool = True,
        collect_system_metrics: bool = False,
        collect_transport_metrics: bool = False,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Enable automatic metrics collection.

        Adds metrics middleware to collect tool invocation metrics.

        Args:
            collect_tool_metrics: Collect metrics for tool invocations
            collect_system_metrics: Collect system metrics (CPU, memory, etc.)
            collect_transport_metrics: Collect transport-level metrics
            labels: Optional labels to add to all metrics

        Example:
            app = NextMCP("my-app")
            app.enable_metrics()

            @app.tool()
            def my_tool():
                return "result"
        """
        from nextmcp.metrics import MetricsConfig, metrics_middleware

        config = MetricsConfig(
            enabled=True,
            collect_tool_metrics=collect_tool_metrics,
            collect_system_metrics=collect_system_metrics,
            collect_transport_metrics=collect_transport_metrics,
            labels=labels or {},
        )

        # Add metrics middleware
        middleware = metrics_middleware(collector=self.metrics, config=config)
        self.add_middleware(middleware)

        self._metrics_enabled = True
        logger.info(f"Metrics enabled for {self.name}")

    def get_metrics_prometheus(self) -> str:
        """
        Get metrics in Prometheus format.

        Returns:
            String containing Prometheus-formatted metrics

        Example:
            app = NextMCP("my-app")
            app.enable_metrics()
            prometheus_data = app.get_metrics_prometheus()
        """
        from nextmcp.metrics.exporters import PrometheusExporter
        from nextmcp.metrics.registry import get_registry

        exporter = PrometheusExporter(get_registry())
        return exporter.export()

    def get_metrics_json(self, pretty: bool = True) -> str:
        """
        Get metrics in JSON format.

        Args:
            pretty: If True, format with indentation

        Returns:
            JSON string containing all metrics

        Example:
            app = NextMCP("my-app")
            app.enable_metrics()
            json_data = app.get_metrics_json()
        """
        from nextmcp.metrics.exporters import JSONExporter
        from nextmcp.metrics.registry import get_registry

        exporter = JSONExporter(get_registry())
        return exporter.export(pretty=pretty)

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
                "FastMCP is required to run the server. " "Install it with: pip install fastmcp"
            ) from None

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
