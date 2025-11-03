"""
Metrics collector for NextMCP applications.
"""

import logging

from nextmcp.metrics.registry import MetricsRegistry, get_registry
from nextmcp.metrics.types import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    High-level metrics collector with convenient methods.

    Provides easy-to-use methods for common metrics operations.
    """

    def __init__(self, registry: MetricsRegistry | None = None, prefix: str = "nextmcp"):
        """
        Initialize the metrics collector.

        Args:
            registry: Metrics registry to use (default: global registry)
            prefix: Prefix for all metric names
        """
        self.registry = registry if registry is not None else get_registry()
        self.prefix = prefix

    def counter(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> Counter:
        """
        Get or create a counter metric.

        Args:
            name: Counter name
            description: Counter description
            labels: Optional labels

        Returns:
            Counter instance
        """
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        return self.registry.get_or_create(
            name=full_name,
            metric_type=Counter,
            description=description,
            labels=labels,
        )

    def gauge(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> Gauge:
        """
        Get or create a gauge metric.

        Args:
            name: Gauge name
            description: Gauge description
            labels: Optional labels

        Returns:
            Gauge instance
        """
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        return self.registry.get_or_create(
            name=full_name,
            metric_type=Gauge,
            description=description,
            labels=labels,
        )

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list | None = None,
    ) -> Histogram:
        """
        Get or create a histogram metric.

        Args:
            name: Histogram name
            description: Histogram description
            labels: Optional labels
            buckets: Optional bucket boundaries

        Returns:
            Histogram instance
        """
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        kwargs = {}
        if buckets is not None:
            kwargs["buckets"] = buckets

        return self.registry.get_or_create(
            name=full_name,
            metric_type=Histogram,
            description=description,
            labels=labels,
            **kwargs,
        )

    def summary(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> Summary:
        """
        Get or create a summary metric.

        Args:
            name: Summary name
            description: Summary description
            labels: Optional labels

        Returns:
            Summary instance
        """
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        return self.registry.get_or_create(
            name=full_name,
            metric_type=Summary,
            description=description,
            labels=labels,
        )

    def inc_counter(
        self,
        name: str,
        amount: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter (creates if doesn't exist).

        Args:
            name: Counter name
            amount: Amount to increment
            labels: Optional labels
        """
        counter = self.counter(name, labels=labels)
        counter.inc(amount)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Set a gauge value (creates if doesn't exist).

        Args:
            name: Gauge name
            value: Value to set
            labels: Optional labels
        """
        gauge = self.gauge(name, labels=labels)
        gauge.set(value)

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Observe a value in a histogram (creates if doesn't exist).

        Args:
            name: Histogram name
            value: Value to observe
            labels: Optional labels
        """
        histogram = self.histogram(name, labels=labels)
        histogram.observe(value)

    def time_histogram(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ):
        """
        Context manager to time a code block with a histogram.

        Args:
            name: Histogram name
            labels: Optional labels

        Example:
            with collector.time_histogram("request_duration"):
                # Code to time
                pass
        """
        histogram = self.histogram(name, labels=labels)
        return histogram.time()

    def get_all_metrics(self) -> dict[str, dict]:
        """
        Get all metrics as a dictionary.

        Returns:
            Dictionary of metric names to their values
        """
        result = {}

        for metric in self.registry.list_metrics():
            key = metric.name + metric._label_string()

            if isinstance(metric, Counter):
                result[key] = {
                    "type": "counter",
                    "value": metric.get(),
                    "description": metric.description,
                }
            elif isinstance(metric, Gauge):
                result[key] = {
                    "type": "gauge",
                    "value": metric.get(),
                    "description": metric.description,
                }
            elif isinstance(metric, Histogram):
                result[key] = {
                    "type": "histogram",
                    "count": metric.get_count(),
                    "sum": metric.get_sum(),
                    "buckets": metric.get_buckets(),
                    "description": metric.description,
                }
            elif isinstance(metric, Summary):
                result[key] = {
                    "type": "summary",
                    "count": metric.get_count(),
                    "sum": metric.get_sum(),
                    "percentiles": metric.get_percentiles(),
                    "description": metric.description,
                }

        return result
