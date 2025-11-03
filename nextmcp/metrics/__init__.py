"""
NextMCP Metrics - Built-in monitoring and metrics collection.

Provides automatic and custom metrics collection for NextMCP applications.

Example:
    from nextmcp import NextMCP

    app = NextMCP("my-app")
    app.enable_metrics()  # Automatic metrics collection

    @app.tool()
    def my_tool():
        return "result"
"""

from nextmcp.metrics.collector import MetricsCollector
from nextmcp.metrics.config import MetricsConfig
from nextmcp.metrics.middleware import MetricsMiddleware, metrics_middleware
from nextmcp.metrics.registry import MetricsRegistry, get_registry
from nextmcp.metrics.types import Counter, Gauge, Histogram, Summary

__all__ = [
    # Metric types
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    # Collector
    "MetricsCollector",
    # Registry
    "MetricsRegistry",
    "get_registry",
    # Middleware
    "MetricsMiddleware",
    "metrics_middleware",
    # Config
    "MetricsConfig",
]
