"""
Metrics middleware for automatic metrics collection.
"""

import functools
import inspect
import logging
import time
from collections.abc import Callable

from nextmcp.metrics.collector import MetricsCollector
from nextmcp.metrics.config import MetricsConfig

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """
    Middleware that automatically collects metrics for tool invocations.

    Tracks:
    - Tool invocation counts
    - Tool execution duration
    - Success/failure rates
    - Errors by type
    """

    def __init__(
        self,
        collector: MetricsCollector | None = None,
        config: MetricsConfig | None = None,
    ):
        """
        Initialize metrics middleware.

        Args:
            collector: Metrics collector instance
            config: Metrics configuration
        """
        self.collector = collector or MetricsCollector()
        self.config = config or MetricsConfig()

    def __call__(self, fn: Callable) -> Callable:
        """
        Wrap a function to collect metrics.

        Args:
            fn: Function to wrap

        Returns:
            Wrapped function
        """
        tool_name = getattr(fn, "_tool_name", fn.__name__)
        is_async = inspect.iscoroutinefunction(fn)

        if is_async:
            return self._wrap_async(fn, tool_name)
        else:
            return self._wrap_sync(fn, tool_name)

    def _wrap_sync(self, fn: Callable, tool_name: str) -> Callable:
        """Wrap a synchronous function."""

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not self.config.enabled or not self.config.collect_tool_metrics:
                return fn(*args, **kwargs)

            labels = {"tool": tool_name}
            labels.update(self.config.labels)

            # Increment invocation counter
            self.collector.inc_counter("tool_invocations_total", labels=labels)

            # Track active invocations
            active_gauge = self.collector.gauge("tool_active_invocations", labels=labels)
            active_gauge.inc()

            start_time = time.perf_counter()
            error_occurred = False
            error_type = None

            try:
                result = fn(*args, **kwargs)
                return result

            except Exception as e:
                error_occurred = True
                error_type = type(e).__name__

                # Track error
                error_labels = {**labels, "error_type": error_type}
                self.collector.inc_counter("tool_errors_total", labels=error_labels)

                raise

            finally:
                # Record duration
                duration = time.perf_counter() - start_time
                self.collector.observe_histogram(
                    "tool_duration_seconds",
                    value=duration,
                    labels=labels,
                )

                # Decrement active invocations
                active_gauge.dec()

                # Track success/failure
                status_labels = {
                    **labels,
                    "status": "error" if error_occurred else "success",
                }
                self.collector.inc_counter("tool_completed_total", labels=status_labels)

        return wrapper

    def _wrap_async(self, fn: Callable, tool_name: str) -> Callable:
        """Wrap an asynchronous function."""

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            if not self.config.enabled or not self.config.collect_tool_metrics:
                return await fn(*args, **kwargs)

            labels = {"tool": tool_name}
            labels.update(self.config.labels)

            # Increment invocation counter
            self.collector.inc_counter("tool_invocations_total", labels=labels)

            # Track active invocations
            active_gauge = self.collector.gauge("tool_active_invocations", labels=labels)
            active_gauge.inc()

            start_time = time.perf_counter()
            error_occurred = False
            error_type = None

            try:
                result = await fn(*args, **kwargs)
                return result

            except Exception as e:
                error_occurred = True
                error_type = type(e).__name__

                # Track error
                error_labels = {**labels, "error_type": error_type}
                self.collector.inc_counter("tool_errors_total", labels=error_labels)

                raise

            finally:
                # Record duration
                duration = time.perf_counter() - start_time
                self.collector.observe_histogram(
                    "tool_duration_seconds",
                    value=duration,
                    labels=labels,
                )

                # Decrement active invocations
                active_gauge.dec()

                # Track success/failure
                status_labels = {
                    **labels,
                    "status": "error" if error_occurred else "success",
                }
                self.collector.inc_counter("tool_completed_total", labels=status_labels)

        return wrapper


def metrics_middleware(
    collector: MetricsCollector | None = None,
    config: MetricsConfig | None = None,
) -> Callable:
    """
    Create a metrics middleware function.

    Args:
        collector: Metrics collector instance
        config: Metrics configuration

    Returns:
        Middleware function

    Example:
        from nextmcp import NextMCP
        from nextmcp.metrics import metrics_middleware

        app = NextMCP("my-app")
        app.add_middleware(metrics_middleware())

        @app.tool()
        def my_tool():
            return "result"
    """
    middleware = MetricsMiddleware(collector=collector, config=config)
    return middleware
