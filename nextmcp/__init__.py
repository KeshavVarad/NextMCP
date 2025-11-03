"""
NextMCP - Production-grade MCP server toolkit

A Python SDK for building MCP servers with minimal boilerplate,
inspired by Next.js's developer experience.

Example:
    from nextmcp import NextMCP, tool

    app = NextMCP("my-server")

    @app.tool()
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    if __name__ == "__main__":
        app.run()
"""

__version__ = "0.1.0"

# Core imports
from nextmcp.core import NextMCP

# Tool utilities
from nextmcp.tools import (
    tool,
    get_tool_metadata,
    generate_tool_docs,
    ToolRegistry,
)

# Configuration
from nextmcp.config import Config, load_config

# Logging
from nextmcp.logging import (
    setup_logging,
    get_logger,
    LoggerContext,
    log_function_call,
)

# Middleware
from nextmcp.middleware import (
    log_calls,
    require_auth,
    error_handler,
    rate_limit,
    validate_inputs,
    cache_results,
    timeout,
    # Async middleware
    log_calls_async,
    require_auth_async,
    error_handler_async,
    rate_limit_async,
    cache_results_async,
    timeout_async,
)

# Transport
from nextmcp.transport import (
    WebSocketTransport,
    WebSocketClient,
    WSMessage,
    invoke_remote_tool,
)

# Plugins
from nextmcp.plugins import (
    Plugin,
    PluginManager,
    PluginMetadata,
)

# Metrics
from nextmcp.metrics import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricsCollector,
    MetricsRegistry,
    get_registry,
    MetricsConfig,
    metrics_middleware,
)

# Define public API
__all__ = [
    # Version
    "__version__",
    # Core
    "NextMCP",
    # Tools
    "tool",
    "get_tool_metadata",
    "generate_tool_docs",
    "ToolRegistry",
    # Config
    "Config",
    "load_config",
    # Logging
    "setup_logging",
    "get_logger",
    "LoggerContext",
    "log_function_call",
    # Middleware
    "log_calls",
    "require_auth",
    "error_handler",
    "rate_limit",
    "validate_inputs",
    "cache_results",
    "timeout",
    # Async middleware
    "log_calls_async",
    "require_auth_async",
    "error_handler_async",
    "rate_limit_async",
    "cache_results_async",
    "timeout_async",
    # Transport
    "WebSocketTransport",
    "WebSocketClient",
    "WSMessage",
    "invoke_remote_tool",
    # Plugins
    "Plugin",
    "PluginManager",
    "PluginMetadata",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricsCollector",
    "MetricsRegistry",
    "get_registry",
    "MetricsConfig",
    "metrics_middleware",
]
