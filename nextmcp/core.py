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
        self._prompts: dict[str, Callable] = {}
        self._resources: dict[str, Callable] = {}
        self._resource_templates: dict[str, Callable] = {}
        self._prompt_completions: dict[str, Callable] = {}
        self._template_completions: dict[str, Callable] = {}
        self._resource_subscriptions: dict[str, list[str]] = {}  # Using list to maintain FIFO order
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

    def prompt(
        self, name: str | None = None, description: str | None = None, tags: list[str] | None = None
    ):
        """
        Decorator to register a function as an MCP prompt.

        Prompts are user-driven workflow templates that guide interactions.
        Global middleware will be automatically applied to the prompt.

        Args:
            name: Optional custom name for the prompt (defaults to function name)
            description: Optional description of what the prompt does
            tags: Optional tags for categorization

        Example:
            @app.prompt(tags=["travel"])
            def vacation_planner(destination: str, budget: int) -> str:
                return f"Plan a vacation to {destination} with ${budget}"

            @app.prompt()
            async def async_prompt(param: str) -> str:
                return await generate_prompt(param)
        """

        def decorator(fn: Callable) -> Callable:
            prompt_name = name or fn.__name__
            is_async = inspect.iscoroutinefunction(fn)

            # Apply global middleware in order
            wrapped_fn = fn
            for middleware in self._global_middleware:
                wrapped_fn = middleware(wrapped_fn)

            # Store metadata
            wrapped_fn._prompt_name = prompt_name
            wrapped_fn._prompt_description = description or fn.__doc__
            wrapped_fn._prompt_tags = tags or []
            wrapped_fn._original_fn = fn
            wrapped_fn._is_async = is_async

            self._prompts[prompt_name] = wrapped_fn
            logger.debug(f"Registered {'async' if is_async else 'sync'} prompt: {prompt_name}")

            return wrapped_fn

        return decorator

    def prompt_completion(self, prompt_name: str, arg_name: str):
        """
        Decorator to register a completion function for a prompt argument.

        Completion functions provide suggestions for prompt arguments.

        Args:
            prompt_name: Name of the prompt
            arg_name: Name of the argument to provide completions for

        Example:
            @app.prompt_completion("vacation_planner", "destination")
            async def complete_destinations(partial: str) -> list[str]:
                return ["Paris", "Tokyo", "New York", "London"]
        """

        def decorator(fn: Callable) -> Callable:
            key = f"{prompt_name}.{arg_name}"
            self._prompt_completions[key] = fn
            logger.debug(f"Registered prompt completion: {key}")
            return fn

        return decorator

    def get_prompts(self) -> dict[str, Callable]:
        """
        Get all registered prompts.

        Returns:
            Dictionary mapping prompt names to their wrapped functions
        """
        return self._prompts.copy()

    def resource(
        self,
        uri: str,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        subscribable: bool = False,
        max_subscribers: int = 100,
    ):
        """
        Decorator to register a function as an MCP resource.

        Resources provide read-only access to data with a unique URI.
        Global middleware will be automatically applied to the resource.

        Args:
            uri: Unique resource identifier (e.g., "file:///path/to/file")
            name: Human-readable name
            description: Description of the resource
            mime_type: MIME type of the content
            subscribable: Whether to support change notifications
            max_subscribers: Maximum number of subscribers

        Example:
            @app.resource("file:///logs/app.log", subscribable=True)
            def app_logs() -> str:
                return Path("/var/logs/app.log").read_text()

            @app.resource("config://app/settings", mime_type="application/json")
            async def app_settings() -> dict:
                return await load_settings()
        """

        def decorator(fn: Callable) -> Callable:
            from nextmcp.resources import ResourceMetadata

            is_async = inspect.iscoroutinefunction(fn)

            # Apply global middleware in order
            wrapped_fn = fn
            for middleware in self._global_middleware:
                wrapped_fn = middleware(wrapped_fn)

            # Store metadata
            metadata = ResourceMetadata(
                uri=uri,
                name=name,
                description=description or fn.__doc__,
                mime_type=mime_type,
                subscribable=subscribable,
                max_subscribers=max_subscribers,
            )

            wrapped_fn._resource_uri = uri
            wrapped_fn._resource_metadata = metadata
            wrapped_fn._resource_type = "direct"
            wrapped_fn._original_fn = fn
            wrapped_fn._is_async = is_async

            self._resources[uri] = wrapped_fn

            # Initialize subscription tracking if subscribable
            if subscribable:
                self._resource_subscriptions[uri] = []  # List for FIFO ordering

            logger.debug(f"Registered {'async' if is_async else 'sync'} resource: {uri}")

            return wrapped_fn

        return decorator

    def resource_template(self, uri_pattern: str, description: str | None = None):
        """
        Decorator to register a function as an MCP resource template.

        Resource templates have parameters in their URI that get mapped to function arguments.
        Global middleware will be automatically applied to the template.

        Args:
            uri_pattern: URI pattern with parameters in {braces}
            description: Description of the template

        Example:
            @app.resource_template("weather://forecast/{city}/{date}")
            async def weather_forecast(city: str, date: str) -> dict:
                return await fetch_weather(city, date)

            @app.resource_template("file:///docs/{category}/{filename}")
            def documentation(category: str, filename: str) -> str:
                return Path(f"/docs/{category}/{filename}").read_text()
        """

        def decorator(fn: Callable) -> Callable:
            from nextmcp.resources import ResourceTemplate

            is_async = inspect.iscoroutinefunction(fn)

            # Apply global middleware in order
            wrapped_fn = fn
            for middleware in self._global_middleware:
                wrapped_fn = middleware(wrapped_fn)

            # Create template metadata
            template = ResourceTemplate(
                uri_pattern=uri_pattern, description=description or fn.__doc__
            )

            # Store metadata
            wrapped_fn._resource_template = template
            wrapped_fn._resource_type = "template"
            wrapped_fn._original_fn = fn
            wrapped_fn._is_async = is_async

            self._resource_templates[uri_pattern] = wrapped_fn
            logger.debug(
                f"Registered {'async' if is_async else 'sync'} resource template: {uri_pattern}"
            )

            return wrapped_fn

        return decorator

    def template_completion(self, template_name: str, param_name: str):
        """
        Decorator to register a completion function for a resource template parameter.

        Args:
            template_name: Name of the template function
            param_name: Name of the parameter to provide completions for

        Example:
            @app.template_completion("weather_forecast", "city")
            def complete_cities(partial: str) -> list[str]:
                return ["London", "Paris", "Tokyo", "New York"]
        """

        def decorator(fn: Callable) -> Callable:
            key = f"{template_name}.{param_name}"
            self._template_completions[key] = fn
            logger.debug(f"Registered template completion: {key}")
            return fn

        return decorator

    def get_resources(self) -> dict[str, Callable]:
        """
        Get all registered resources.

        Returns:
            Dictionary mapping resource URIs to their wrapped functions
        """
        return self._resources.copy()

    def get_resource_templates(self) -> dict[str, Callable]:
        """
        Get all registered resource templates.

        Returns:
            Dictionary mapping template patterns to their wrapped functions
        """
        return self._resource_templates.copy()

    def notify_resource_changed(self, uri: str) -> int:
        """
        Notify subscribers that a resource has changed.

        Args:
            uri: URI of the resource that changed

        Returns:
            Number of subscribers notified

        Example:
            # After updating a file
            app.notify_resource_changed("file:///config/settings.json")
        """
        if uri not in self._resource_subscriptions:
            logger.warning(f"No subscriptions found for resource: {uri}")
            return 0

        subscribers = self._resource_subscriptions[uri]
        logger.info(f"Notifying {len(subscribers)} subscribers for resource: {uri}")

        # In a real implementation, this would send notifications via the MCP protocol
        # For now, we just log and return the count
        return len(subscribers)

    def subscribe_to_resource(self, uri: str, subscriber_id: str) -> bool:
        """
        Subscribe to resource changes.

        Args:
            uri: URI of the resource to subscribe to
            subscriber_id: Unique identifier for the subscriber

        Returns:
            True if subscription was successful
        """
        if uri not in self._resources:
            logger.warning(f"Resource not found: {uri}")
            return False

        resource = self._resources[uri]
        metadata = getattr(resource, "_resource_metadata", None)

        if not metadata or not metadata.subscribable:
            logger.warning(f"Resource is not subscribable: {uri}")
            return False

        if uri not in self._resource_subscriptions:
            self._resource_subscriptions[uri] = []

        # Check subscriber limit
        if len(self._resource_subscriptions[uri]) >= metadata.max_subscribers:
            logger.warning(f"Max subscribers reached for {uri}")
            # Remove oldest subscriber (FIFO) - first item in list
            oldest = self._resource_subscriptions[uri].pop(0)
            logger.info(f"Removed oldest subscriber {oldest} from {uri}")

        # Add new subscriber (avoid duplicates)
        if subscriber_id not in self._resource_subscriptions[uri]:
            self._resource_subscriptions[uri].append(subscriber_id)
            logger.debug(f"Subscriber {subscriber_id} subscribed to {uri}")
        return True

    def unsubscribe_from_resource(self, uri: str, subscriber_id: str) -> bool:
        """
        Unsubscribe from resource changes.

        Args:
            uri: URI of the resource
            subscriber_id: Unique identifier for the subscriber

        Returns:
            True if unsubscription was successful
        """
        if uri in self._resource_subscriptions:
            try:
                self._resource_subscriptions[uri].remove(subscriber_id)
                logger.debug(f"Subscriber {subscriber_id} unsubscribed from {uri}")
                return True
            except ValueError:
                # Subscriber not in list
                pass
        return False

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
        logger.info(f"Registered {len(self._prompts)} prompt(s)")
        logger.info(f"Registered {len(self._resources)} resource(s)")
        logger.info(f"Registered {len(self._resource_templates)} resource template(s)")

        # Create FastMCP server instance
        self._fastmcp_server = fastmcp.FastMCP(self.name)

        # Register all tools with FastMCP
        for tool_name, tool_fn in self._tools.items():
            logger.debug(f"Registering tool with FastMCP: {tool_name}")
            self._fastmcp_server.tool(tool_fn)

        # Register all prompts with FastMCP
        for prompt_name, prompt_fn in self._prompts.items():
            logger.debug(f"Registering prompt with FastMCP: {prompt_name}")
            self._fastmcp_server.prompt(prompt_fn)

        # Register all resources with FastMCP
        for uri, resource_fn in self._resources.items():
            logger.debug(f"Registering resource with FastMCP: {uri}")
            self._fastmcp_server.add_resource(uri, resource_fn)

        # Register all resource templates with FastMCP
        for pattern, template_fn in self._resource_templates.items():
            logger.debug(f"Registering resource template with FastMCP: {pattern}")
            self._fastmcp_server.add_template(pattern, template_fn)

        # Run the server
        logger.info(f"{self.name} is ready and listening for requests")
        self._fastmcp_server.run()
