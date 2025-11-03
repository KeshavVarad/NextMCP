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

from nextmcp.config import Config, load_config
from nextmcp.core import NextMCP
from nextmcp.logging import LoggerContext, get_logger, log_function_call, setup_logging
from nextmcp.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    MetricsConfig,
    MetricsRegistry,
    Summary,
    get_registry,
    metrics_middleware,
)
from nextmcp.middleware import (
    cache_results,
    cache_results_async,
    error_handler,
    error_handler_async,
    log_calls,
    log_calls_async,
    rate_limit,
    rate_limit_async,
    require_auth,
    require_auth_async,
    timeout,
    timeout_async,
    validate_inputs,
)
from nextmcp.plugins import Plugin, PluginManager, PluginMetadata
from nextmcp.tools import ToolRegistry, generate_tool_docs, get_tool_metadata, tool
from nextmcp.transport import WebSocketClient, WebSocketTransport, WSMessage, invoke_remote_tool

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
