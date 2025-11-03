"""
SecureMCP - Production-grade MCP server toolkit

A Python SDK for building MCP servers with minimal boilerplate,
inspired by Next.js's developer experience.

Example:
    from securemcp import SecureMCP, tool

    app = SecureMCP("my-server")

    @app.tool()
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    if __name__ == "__main__":
        app.run()
"""

__version__ = "0.1.0"

# Core imports
from securemcp.core import SecureMCP

# Tool utilities
from securemcp.tools import (
    tool,
    get_tool_metadata,
    generate_tool_docs,
    ToolRegistry,
)

# Configuration
from securemcp.config import Config, load_config

# Logging
from securemcp.logging import (
    setup_logging,
    get_logger,
    LoggerContext,
    log_function_call,
)

# Middleware
from securemcp.middleware import (
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
from securemcp.transport import (
    WebSocketTransport,
    WebSocketClient,
    WSMessage,
    invoke_remote_tool,
)

# Define public API
__all__ = [
    # Version
    "__version__",
    # Core
    "SecureMCP",
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
]
