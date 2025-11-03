"""
Metrics registry for managing metrics instances.
"""

import logging
import threading

from nextmcp.metrics.types import Metric

logger = logging.getLogger(__name__)


class MetricsRegistry:
    """
    Registry for managing metric instances.

    Provides a central place to register and retrieve metrics.
    """

    def __init__(self):
        """Initialize the metrics registry."""
        self._metrics: dict[str, Metric] = {}
        self._lock = threading.Lock()

    def register(self, metric: Metric) -> Metric:
        """
        Register a metric.

        Args:
            metric: The metric to register

        Returns:
            The registered metric

        Raises:
            ValueError: If metric with same name already registered
        """
        key = self._make_key(metric.name, metric.labels)

        with self._lock:
            if key in self._metrics:
                # Return existing metric if same type
                existing = self._metrics[key]
                if type(existing) is type(metric):
                    return existing
                raise ValueError(f"Metric '{key}' already registered with different type")

            self._metrics[key] = metric
            logger.debug(f"Registered metric: {key}")
            return metric

    def get(self, name: str, labels: dict[str, str] | None = None) -> Metric | None:
        """
        Get a registered metric.

        Args:
            name: Metric name
            labels: Optional labels

        Returns:
            The metric if found, None otherwise
        """
        key = self._make_key(name, labels or {})
        with self._lock:
            return self._metrics.get(key)

    def get_or_create(
        self,
        name: str,
        metric_type: type[Metric],
        description: str = "",
        labels: dict[str, str] | None = None,
        **kwargs,
    ) -> Metric:
        """
        Get an existing metric or create a new one.

        Args:
            name: Metric name
            metric_type: Type of metric to create if not found
            description: Metric description
            labels: Optional labels
            **kwargs: Additional arguments for metric creation

        Returns:
            The metric instance
        """
        key = self._make_key(name, labels or {})

        with self._lock:
            if key in self._metrics:
                return self._metrics[key]

            # Create new metric
            metric = metric_type(name=name, description=description, labels=labels, **kwargs)
            self._metrics[key] = metric
            logger.debug(f"Created and registered metric: {key}")
            return metric

    def unregister(self, name: str, labels: dict[str, str] | None = None) -> bool:
        """
        Unregister a metric.

        Args:
            name: Metric name
            labels: Optional labels

        Returns:
            True if metric was unregistered, False if not found
        """
        key = self._make_key(name, labels or {})

        with self._lock:
            if key in self._metrics:
                del self._metrics[key]
                logger.debug(f"Unregistered metric: {key}")
                return True
            return False

    def list_metrics(self) -> list[Metric]:
        """
        List all registered metrics.

        Returns:
            List of all metrics
        """
        with self._lock:
            return list(self._metrics.values())

    def clear(self) -> None:
        """Clear all registered metrics."""
        with self._lock:
            self._metrics.clear()
            logger.debug("Cleared all metrics")

    def _make_key(self, name: str, labels: dict[str, str]) -> str:
        """Create a unique key for a metric."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def __len__(self) -> int:
        """Return number of registered metrics."""
        with self._lock:
            return len(self._metrics)

    def __contains__(self, name: str) -> bool:
        """Check if a metric is registered."""
        with self._lock:
            # Check for exact match or any metric starting with name
            return any(key.startswith(name) for key in self._metrics.keys())


# Global registry instance
_global_registry: MetricsRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> MetricsRegistry:
    """
    Get the global metrics registry.

    Returns:
        The global MetricsRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = MetricsRegistry()

    return _global_registry
